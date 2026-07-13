"""
routing.py — Endpoint POST /ruta-segura (feature Ruta Más Segura, Issue #48).

Calcula rutas alternativas (ORS) entre origen y destino, evalúa el riesgo de las
localidades que atraviesa cada una (funciones de #46/#47) y devuelve la
comparativa ordenada. Se monta bajo el prefijo /api/v1 en `api/main.py`.

Pydantic v2 (2.13.x en este repo) → validators con `@field_validator`.
Referencia de diseño: `diseño_tecnico_ruta_segura.md` §PARTE 4.
"""

from __future__ import annotations

import sys
from pathlib import Path

import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

# src/ al path para reutilizar el cliente de routing y config (misma raíz que api/state.py).
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import config
import routing_client as rc

router = APIRouter()


# ── Request ────────────────────────────────────────────────────────────────
class PuntoGeo(BaseModel):
    lat: float
    lon: float

    @field_validator("lat")
    @classmethod
    def lat_bogota(cls, v: float) -> float:
        if not (3.7 <= v <= 4.9):
            raise ValueError("Latitud fuera del rango de Bogotá (3.7–4.9)")
        return v

    @field_validator("lon")
    @classmethod
    def lon_bogota(cls, v: float) -> float:
        if not (-74.5 <= v <= -73.9):
            raise ValueError("Longitud fuera del rango de Bogotá (-74.5 a -73.9)")
        return v


class RutaRequest(BaseModel):
    origen: PuntoGeo
    destino: PuntoGeo
    modo: str = "driving-car"   # driving-car | foot-walking | cycling-regular


# ── Response ───────────────────────────────────────────────────────────────
class InfoRuta(BaseModel):
    id: str                    # "segura" | "rapida"
    distancia_m: int
    duracion_seg: int
    riesgo_score: float        # 0–10 (promedio)
    riesgo_nivel: str          # BAJO | MEDIO | ALTO | DESCONOCIDO
    riesgo_score_max: float    # score de la localidad más peligrosa que cruza
    localidades: list[str]     # nombres de localidades en orden
    geometry_geojson: dict     # LineString GeoJSON (dict, no string) para el mapa


class RutaResponse(BaseModel):
    ruta_recomendada: str      # "segura" | "rapida" | "misma"
    rutas: list[InfoRuta]
    advertencia: str | None = None


# ── Endpoint ───────────────────────────────────────────────────────────────
@router.post("/ruta-segura", response_model=RutaResponse)
async def calcular_ruta_segura(req: RutaRequest, request: Request) -> RutaResponse:
    """Rutas alternativas entre origen y destino, evaluadas por riesgo.

    Flujo: ORS → por cada ruta: decodificar → spatial join → score → ranking.
    """
    scores = request.app.state.scores_localidad   # {cod_localidad: score_0_10}
    zonas = request.app.state.zonas_gdf            # GeoDataFrame de los 20 polígonos

    # 1) Rutas de ORS. Cualquier fallo de red/HTTP → 502 (nunca stack trace al cliente).
    try:
        ors = rc.get_routes(
            req.origen.lon, req.origen.lat,
            req.destino.lon, req.destino.lat,
            api_key=config.ORS_API_KEY,
            perfil=req.modo,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502,
                            detail=f"Servicio de rutas no disponible: {exc}") from exc

    if not ors.get("routes"):
        raise HTTPException(status_code=404,
                            detail="No se encontró ruta entre los puntos indicados")

    nombres = zonas.set_index("cod_localidad")["localidad_nombre"].to_dict()

    # 2) Evaluar cada ruta.
    rutas_evaluadas: list[InfoRuta] = []
    for i, ruta_ors in enumerate(ors["routes"]):
        puntos = rc.decodificar_ruta_gdf(ruta_ors["geometry"])
        locs = rc.localidades_de_ruta(puntos, zonas)
        riesgo = rc.score_ruta(locs, scores)
        coords = rc.decodificar_ruta(ruta_ors["geometry"])   # [(lon, lat), ...]

        rutas_evaluadas.append(InfoRuta(
            id=f"ruta_{i + 1}",
            distancia_m=int(ruta_ors["summary"]["distance"]),
            duracion_seg=int(ruta_ors["summary"]["duration"]),
            riesgo_score=riesgo["score"],
            riesgo_nivel=riesgo["nivel"],
            riesgo_score_max=riesgo["score_max"],
            localidades=[nombres.get(c, c) for c in riesgo["localidades"]],
            geometry_geojson={"type": "LineString",
                              "coordinates": [list(p) for p in coords]},
        ))

    # 3) Ranking: menor score_max = más segura; empate → menor duración desempata
    #    (rutas cortas dentro de la misma zona dan score idéntico; ver #47).
    rutas_evaluadas.sort(key=lambda r: (r.riesgo_score_max, r.duracion_seg))
    if len(rutas_evaluadas) == 1:
        rutas_evaluadas[0].id = "segura"
        recomienda = "segura"
    else:
        rutas_evaluadas[0].id = "segura"
        rutas_evaluadas[-1].id = "rapida"
        recomienda = ("segura"
                      if rutas_evaluadas[0].riesgo_score_max < rutas_evaluadas[-1].riesgo_score_max
                      else "misma")

    # 4) Advertencia si el origen está en zona de riesgo alto (MVP+). Defensiva:
    #    envuelta en try/except para que NUNCA rompa la respuesta del endpoint.
    advertencia = _advertencia_origen(req.origen, zonas, scores)

    return RutaResponse(ruta_recomendada=recomienda, rutas=rutas_evaluadas,
                        advertencia=advertencia)


def _advertencia_origen(origen: PuntoGeo, zonas, scores: dict) -> str | None:
    """Devuelve un aviso si el punto de partida cae en una localidad de score ≥7.5."""
    try:
        import geopandas as gpd
        from shapely.geometry import Point

        punto = gpd.GeoDataFrame(geometry=[Point(origen.lon, origen.lat)], crs="EPSG:4326")
        join = gpd.sjoin(punto, zonas[["cod_localidad", "localidad_nombre", "geometry"]],
                         how="left", predicate="within")
        if join.empty:
            return None
        cod = join.iloc[0].get("cod_localidad")
        if cod is not None and scores.get(str(cod), 0) >= 7.5:
            return (f"Tu punto de partida está en una zona de riesgo ALTO "
                    f"({join.iloc[0]['localidad_nombre']}). Ten precaución.")
    except Exception:  # nunca romper la respuesta por la advertencia opcional
        return None
    return None
