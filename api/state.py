"""
Estado compartido de la API: modelos y datos cargados UNA vez al arranque.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import geopandas as gpd
import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "models" / "predictivo"))

import config
import predict as pred_mod

CLUSTERS_JOBLIB = ROOT / "models" / "clustering" / "clusters.joblib"
ZONA_CLUSTER_PATH = ROOT / "models" / "clustering" / "zona_cluster.parquet"
MODEL_PATH = ROOT / "models" / "predictivo" / "model.joblib"

CORRECCIONES_NOMBRE = {"15": "ANTONIO NARIÑO"}


def _alias_tipos() -> dict[str, str]:
    """Acepta codigo (HP), slug (hurto_personas) o nombre legible."""
    aliases: dict[str, str] = {}
    for code, nombre in config.SIEDCO_TIPOS.items():
        aliases[code.lower()] = code
        aliases[code] = code
        aliases[nombre.lower()] = code
        aliases[nombre.lower().replace(" ", "_")] = code
        # Variantes sin articulos / plurales comunes del backlog
        slug = (
            nombre.lower()
            .replace("á", "a").replace("é", "e").replace("í", "i")
            .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
            .replace(" ", "_")
        )
        aliases[slug] = code
    # Alias explicitos del backlog (?tipo=hurto_personas)
    aliases["hurto_personas"] = "HP"
    aliases["homicidios"] = "H"
    aliases["violencia_intrafamiliar"] = "VI"
    return aliases


@dataclass
class AppState:
    dataset: pd.DataFrame | None = None
    predicciones: pd.DataFrame | None = None
    zonas: gpd.GeoDataFrame | None = None
    zona_cluster: pd.DataFrame | None = None
    model_artifact: dict[str, Any] | None = None
    clusters_artifact: dict[str, Any] | None = None
    tipo_aliases: dict[str, str] = field(default_factory=_alias_tipos)
    anios_disponibles: list[int] = field(default_factory=list)
    tipos_disponibles: list[str] = field(default_factory=list)


STATE = AppState()


def _nivel_riesgo(proba: float, predicho: int, umbral: float) -> str:
    """Mapea probabilidad/prediccion a bajo|medio|alto (contrato dashboard/movil)."""
    if int(predicho) == 1 or proba >= umbral:
        return "alto"
    if proba >= max(0.25, umbral * 0.55):
        return "medio"
    return "bajo"


def load_state() -> AppState:
    """Carga artefactos en memoria. Lanza FileNotFoundError con mensaje claro."""
    missing = [
        p for p in (MODEL_PATH, CLUSTERS_JOBLIB, ZONA_CLUSTER_PATH,
                    config.DATASET_ANALITICO, config.ZONAS_GEOJSON)
        if not p.exists()
    ]
    if missing:
        raise FileNotFoundError(
            "Faltan artefactos para la API. Regenera con:\n"
            "  python pipelines/pipeline_ml.py\n"
            "  python models/predictivo/train.py\n"
            "  python models/clustering/build_features.py && "
            "python models/clustering/train.py\n"
            f"Ausentes: {[str(p) for p in missing]}"
        )

    print("[api] Cargando dataset y modelos...")
    dataset = pd.read_parquet(config.DATASET_ANALITICO)
    model_artifact = pred_mod.load_model(MODEL_PATH)
    clusters_artifact = joblib.load(CLUSTERS_JOBLIB)
    zona_cluster = pd.read_parquet(ZONA_CLUSTER_PATH)
    zonas = gpd.read_file(config.ZONAS_GEOJSON)

    # Predicciones para TODO el dataset una sola vez (lags necesitan historial).
    print("[api] Precomputando predicciones (una vez al arranque)...")
    predicciones = pred_mod.predict(dataset, artifact=model_artifact)
    umbral = float(model_artifact.get("umbral", 0.5))
    predicciones["nivel_riesgo"] = [
        _nivel_riesgo(p, y, umbral)
        for p, y in zip(
            predicciones["probabilidad_riesgo"],
            predicciones["riesgo_predicho"],
        )
    ]

    zonas = zonas.copy()
    zonas["localidad_nombre"] = zonas.apply(
        lambda r: CORRECCIONES_NOMBRE.get(str(r["cod_localidad"]), r["localidad_nombre"]),
        axis=1,
    )
    zonas["cod_localidad"] = zonas["cod_localidad"].astype(str).str.zfill(2)
    zona_cluster["cod_localidad"] = zona_cluster["cod_localidad"].astype(str).str.zfill(2)
    predicciones["cod_localidad"] = predicciones["cod_localidad"].astype(str).str.zfill(2)

    STATE.dataset = dataset
    STATE.predicciones = predicciones
    STATE.zonas = zonas
    STATE.zona_cluster = zona_cluster[
        ["cod_localidad", "cluster", "nombre_perfil"]
    ].drop_duplicates("cod_localidad")
    STATE.model_artifact = model_artifact
    STATE.clusters_artifact = clusters_artifact
    STATE.tipo_aliases = _alias_tipos()
    STATE.anios_disponibles = sorted(int(a) for a in dataset["anio"].unique())
    STATE.tipos_disponibles = sorted(dataset["tipo_delito"].unique().tolist())
    print(
        f"[api] Listo: {len(zonas)} zonas, "
        f"anios={STATE.anios_disponibles[0]}..{STATE.anios_disponibles[-1]}, "
        f"tipos={len(STATE.tipos_disponibles)}, "
        f"modelo={model_artifact.get('modelo')}"
    )
    return STATE


def resolver_tipo(tipo: str) -> str:
    key = tipo.strip()
    code = STATE.tipo_aliases.get(key) or STATE.tipo_aliases.get(key.lower())
    if code is None:
        raise KeyError(key)
    return code


def build_geojson(anio: int, tipo_delito: str) -> dict[str, Any]:
    """Arma FeatureCollection para anio + tipo (codigo SIEDCO)."""
    if STATE.predicciones is None or STATE.zonas is None or STATE.zona_cluster is None:
        raise RuntimeError("Estado de la API no inicializado")

    pred = STATE.predicciones[
        (STATE.predicciones["anio"] == int(anio))
        & (STATE.predicciones["tipo_delito"] == tipo_delito)
    ][
        ["cod_localidad", "probabilidad_riesgo", "riesgo_predicho", "nivel_riesgo",
         "anio", "tipo_delito"]
    ].copy()

    if pred.empty:
        raise ValueError(
            f"Sin predicciones para anio={anio}, tipo={tipo_delito}. "
            f"Anios: {STATE.anios_disponibles}; tipos: {STATE.tipos_disponibles}"
        )

    gdf = STATE.zonas.merge(STATE.zona_cluster, on="cod_localidad", how="left")
    gdf = gdf.merge(pred, on="cod_localidad", how="left")

    # Completar metadatos de consulta en todas las filas
    gdf["anio"] = int(anio)
    gdf["tipo_delito"] = tipo_delito
    gdf["tipo_delito_nombre"] = config.SIEDCO_TIPOS.get(tipo_delito, tipo_delito)
    gdf["probabilidad_riesgo"] = gdf["probabilidad_riesgo"].fillna(0.0).round(4)
    gdf["riesgo_predicho"] = gdf["riesgo_predicho"].fillna(0).astype(int)
    gdf["nivel_riesgo"] = gdf["nivel_riesgo"].fillna("bajo")
    gdf["cluster"] = gdf["cluster"].fillna(-1).astype(int)
    gdf["nombre_perfil"] = gdf["nombre_perfil"].fillna("sin_perfil")

    cols = [
        "cod_localidad", "localidad_nombre", "cod_dane_mpio",
        "cluster", "nombre_perfil",
        "nivel_riesgo", "probabilidad_riesgo", "riesgo_predicho",
        "anio", "tipo_delito", "tipo_delito_nombre",
        "geometry",
    ]
    gdf = gdf[cols].sort_values("cod_localidad")
    # GeoPandas -> GeoJSON dict (no string)
    return gdf.__geo_interface__
