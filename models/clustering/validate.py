"""
validate.py — Issue #28

Orquestador: valida que la segmentacion de #27 (K-Means, k=3) es estable y
no arbitraria. Corre las 3 pruebas del criterio de aceptacion (silhouette
por cluster, estabilidad ante semillas, comparacion contra el baseline
trivial de terciles por conteo) contra el modelo real serializado en
clusters.joblib, e imprime el resumen a consola. Los numeros se documentan
a mano en docs/data-dictionaries/validacion_clustering.md (mismo patron que
train.py -> clustering_perfiles.md en #27: este script no escribe el .md).

Uso:
    python models/clustering/validate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
import clustering
import config
import feature_engineering

SEMILLAS_ESTABILIDAD = range(10)

OUT_DIR = Path(__file__).resolve().parent
CLUSTERS_JOBLIB = OUT_DIR / "clusters.joblib"
FEATURES_PATH = OUT_DIR / "features_zona.parquet"


def run() -> None:
    print("== #28 Validacion interna del clustering ==")
    features = pd.read_parquet(FEATURES_PATH)
    bundle = joblib.load(CLUSTERS_JOBLIB)
    modelo = bundle["modelo"]
    nombres = bundle["nombre_perfil"]
    k = bundle["k"]
    n_init = bundle["n_init"]
    etiquetas_ref = modelo.predict(features.values)

    print("\n-- 1. Silhouette por cluster --")
    resumen_sil = clustering.silhouette_por_cluster(features, modelo)
    resumen_sil["nombre_perfil"] = resumen_sil["cluster"].map(nombres)
    print(resumen_sil.round(3).to_string(index=False))

    print("\n-- 2. Estabilidad ante semillas --")
    tabla_ari = clustering.evaluar_estabilidad_semillas(
        features, etiquetas_ref, k, SEMILLAS_ESTABILIDAD, n_init
    )
    print(tabla_ari.round(3).to_string(index=False))
    print(f"  media={tabla_ari['ari'].mean():.3f} min={tabla_ari['ari'].min():.3f} max={tabla_ari['ari'].max():.3f}")

    print("\n-- 3. Comparacion contra terciles por conteo total --")
    df = pd.read_parquet(config.DATASET_ANALITICO)
    conteo_total = feature_engineering.conteo_total_por_zona(df).reindex(features.index)
    terciles = clustering.terciles_por_conteo(conteo_total, k)
    ari_terciles = clustering.comparar_particiones(etiquetas_ref, terciles.values)
    print(f"  ARI (K-Means real vs. terciles por conteo total) = {ari_terciles:.3f}")
    crosstab = pd.crosstab(
        pd.Series(etiquetas_ref, index=features.index).map(nombres).rename("perfil_kmeans"),
        terciles.rename("tercil_conteo"),
    )
    print(crosstab.to_string())

    _verificar(resumen_sil, tabla_ari, ari_terciles)


def _verificar(resumen_sil: pd.DataFrame, tabla_ari: pd.DataFrame, ari_terciles: float) -> None:
    assert resumen_sil["n"].sum() == 20, "las 20 localidades deben quedar cubiertas"
    assert tabla_ari["ari"].between(-1.0, 1.0).all(), "ARI fuera de rango valido"
    assert -1.0 <= ari_terciles <= 1.0, "ARI fuera de rango valido"
    print("\n  [ok] validacion completa")


if __name__ == "__main__":
    run()
