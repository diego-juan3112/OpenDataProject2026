"""
main.py — FastAPI Alerta Ciudadana 
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import state as api_state


@asynccontextmanager
async def lifespan(_app: FastAPI):
    api_state.load_state()
    yield


app = FastAPI(
    title="Alerta Ciudadana API",
    description=(
        "API ligera: GeoJSON de riesgo por localidad + tipologia de clusters. "
        "Consumida por el dashboard Streamlit y la app movil Expo."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, Any]:
    st = api_state.STATE
    return {
        "status": "ok",
        "modelo": (st.model_artifact or {}).get("modelo"),
        "anios": st.anios_disponibles,
        "tipos": st.tipos_disponibles,
        "n_zonas": 0 if st.zonas is None else len(st.zonas),
    }


@app.get("/zonas-riesgo")
def zonas_riesgo(
    anio: int = Query(2025, description="Anio consultado (2018-2025)"),
    tipo: str = Query(
        "HP",
        description=(
            "Tipo de delito: codigo SIEDCO (HP, H, VI, ...) "
            "o slug (hurto_personas, homicidios, ...)"
        ),
    ),
) -> JSONResponse:
    """GeoJSON FeatureCollection: geometria + riesgo + cluster por localidad."""
    st = api_state.STATE
    if st.predicciones is None:
        raise HTTPException(status_code=503, detail="API aun no inicializada")

    if anio not in st.anios_disponibles:
        raise HTTPException(
            status_code=422,
            detail={
                "mensaje": f"anio={anio} no disponible",
                "anios_validos": st.anios_disponibles,
            },
        )

    try:
        tipo_code = api_state.resolver_tipo(tipo)
    except KeyError:
        raise HTTPException(
            status_code=422,
            detail={
                "mensaje": f"tipo='{tipo}' no reconocido",
                "tipos_validos": st.tipos_disponibles,
                "ejemplos_slug": ["hurto_personas", "homicidios", "violencia_intrafamiliar"],
            },
        ) from None

    try:
        geojson = api_state.build_geojson(anio, tipo_code)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return JSONResponse(content=geojson)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "servicio": "Alerta Ciudadana",
        "docs": "/docs",
        "zonas_riesgo": "/zonas-riesgo?anio=2025&tipo=HP",
        "health": "/health",
    }
