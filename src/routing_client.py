"""
routing_client.py — Cliente de OpenRouteService (feature Ruta Más Segura).

Issue #45: wrapper mínimo sobre el API REST de ORS para pedir rutas alternativas
entre dos puntos de Bogotá y decodificar su geometría. NO calcula riesgo ni hace
spatial join (eso es #46/#47) ni expone el endpoint (#48).

Referencia de diseño: `diseño_tecnico_ruta_segura.md` §PARTE 2.

Advertencia de coordenadas: ORS trabaja en orden **[lon, lat]**, no [lat, lon].
Invertirlas devuelve HTTP 400 o rutas fuera de Colombia.
"""

from __future__ import annotations

import sys
from pathlib import Path

import polyline as polyline_lib
import requests

# config.py vive en el mismo directorio; se añade src/ al path para que el
# import funcione tanto al importar como `src.routing_client` (desde la raíz)
# como al correr dentro de src/ (patrón usado en pipelines/pipeline_ml.py).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


def get_routes(
    origen_lon: float,
    origen_lat: float,
    destino_lon: float,
    destino_lat: float,
    api_key: str,
    perfil: str = "driving-car",
    n_rutas: int = 2,
) -> dict:
    """Pide `n_rutas` rutas alternativas a ORS entre origen y destino.

    Llama a `POST {ORS_BASE_URL}/{perfil}/json`. El perfil va en la URL, no en el
    body. Devuelve el JSON completo de ORS (clave `routes`, cada una con
    `summary` y `geometry` en polyline codificada).

    Lanza `requests.HTTPError` si la respuesta no es 2xx.
    """
    url = f"{config.ORS_BASE_URL}/{perfil}/json"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }
    body = {
        "coordinates": [
            [origen_lon, origen_lat],    # ORS usa [lon, lat] — no al revés
            [destino_lon, destino_lat],
        ],
        "alternative_routes": {
            "target_count": n_rutas,     # cuántas rutas pedir (2 para el MVP)
            "weight_factor": 1.6,        # qué tan distintas deben ser (1.4–2.0)
        },
        "geometry": True,                # devolver la geometría de la ruta
        "instructions": False,           # no se necesita giro a giro en el MVP
    }
    response = requests.post(url, json=body, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


def decodificar_ruta(encoded_geometry: str) -> list[tuple[float, float]]:
    """Decodifica la polyline codificada de ORS a lista de `(lon, lat)`.

    Se usa `geojson=True` para que `polyline` devuelva el orden [lon, lat]
    (el mismo que espera GeoJSON/Shapely), no [lat, lon].
    """
    return [tuple(p) for p in polyline_lib.decode(encoded_geometry, geojson=True)]
