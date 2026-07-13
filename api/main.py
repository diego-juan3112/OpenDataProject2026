"""
main.py — FastAPI Alerta Ciudadana 
"""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import geopandas as gpd
import joblib
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import state as api_state
from api.routers import routing

# src/ al path para cargar el score de riesgo por localidad (feature Ruta Más Segura).
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))
import config
import model_evaluation


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Stack de /zonas-riesgo (#20): predictivo + clustering. Si faltan artefactos,
    # la app ARRANCA igual (para no bloquear /ruta-segura) y /zonas-riesgo
    # responde 503 hasta regenerarlos (su guard `predicciones is None` ya existe).
    try:
        api_state.load_state()
    except FileNotFoundError as exc:
        print(f"[api] /zonas-riesgo sin artefactos (regenerar con scripts de #19/#27): {exc}")

    # Estado de Ruta Más Segura (#48): scores + zonas, independientes del modelo.
    _app.state.scores_localidad = model_evaluation.calcular_scores_localidad(
        str(config.DATASET_ANALITICO)
    )
    zonas = gpd.read_file(config.ZONAS_GEOJSON)
    zonas["cod_localidad"] = zonas["cod_localidad"].astype(str).str.zfill(2)
    _app.state.zonas_gdf = zonas

    # El modelo predictivo NO es necesario para /ruta-segura (usa scores_localidad).
    try:
        _app.state.model = joblib.load(_ROOT / "models" / "predictivo" / "model.joblib")
    except FileNotFoundError:
        _app.state.model = None
        print("[api] models/predictivo/model.joblib no encontrado; /ruta-segura funciona sin el.")

    print(f"[api] Ruta Mas Segura lista: {len(_app.state.scores_localidad)} scores, "
          f"{len(_app.state.zonas_gdf)} zonas.")
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

# Endpoint de la feature Ruta Más Segura: POST /api/v1/ruta-segura
app.include_router(routing.router, prefix="/api/v1")


@app.get("/health")
def health(request: Request) -> dict[str, Any]:
    st = api_state.STATE
    scores = getattr(request.app.state, "scores_localidad", None) or {}
    zonas_rs = getattr(request.app.state, "zonas_gdf", None)
    return {
        "status": "ok",
        "modelo": (st.model_artifact or {}).get("modelo"),
        "anios": st.anios_disponibles,
        "tipos": st.tipos_disponibles,
        "n_zonas": 0 if st.zonas is None else len(st.zonas),
        "scores_cargados": len(scores),
        "zonas_cargadas": 0 if zonas_rs is None else len(zonas_rs),
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
