"""
train.py — Issue #27

Orquestador: entrena el K-Means final sobre models/clustering/features_zona.parquet
(#26), justifica k con la curva de codo + silhouette, nombra cada cluster por
sus centroides reales, y serializa los dos entregables que consumen la API y
el dashboard (Integrante 2/3) y la app movil (Integrante 4, #37).

Uso:
    python models/clustering/train.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
import clustering
import config

# Parametros fijos y reproducibles (Issue #27). k=3 se justifica por el codo
# real de la inercia + interpretabilidad de los 3 perfiles resultantes, NO por
# silhouette maximo (silhouette es mayor en k=2, pero da un corte binario poco
# util). Ver docs/data-dictionaries/clustering_perfiles.md para el detalle.
K_FINAL = 3
N_INIT = 10
RANDOM_STATE = 42
RANGO_K_EXPLORADO = range(2, 8)

OUT_DIR = Path(__file__).resolve().parent
CLUSTERS_JOBLIB = OUT_DIR / "clusters.joblib"
ZONA_CLUSTER_PATH = OUT_DIR / "zona_cluster.parquet"
FIGURA_PATH = Path(__file__).resolve().parent.parent.parent / "reports" / "figures" / "clustering_elbow_silhouette.png"


def run() -> None:
    print("== #27 Entrenar K-Means + tipologia + clusters.joblib ==")
    features = pd.read_parquet(Path(__file__).resolve().parent / "features_zona.parquet")

    tabla_k = clustering.evaluar_k(features, RANGO_K_EXPLORADO, N_INIT, RANDOM_STATE)
    _graficar_codo_silhouette(tabla_k)

    modelo = clustering.entrenar_kmeans_final(features, K_FINAL, N_INIT, RANDOM_STATE)
    nombres = clustering.nombrar_clusters(features, modelo)
    zona_cluster = clustering.construir_zona_cluster(features, modelo, nombres)

    df = pd.read_parquet(config.DATASET_ANALITICO)
    nombres_loc = df.drop_duplicates("cod_localidad")[["cod_localidad", "localidad_nombre"]]
    zona_cluster = zona_cluster.merge(nombres_loc, on="cod_localidad", how="left")
    zona_cluster = zona_cluster[["cod_localidad", "localidad_nombre", "cluster", "nombre_perfil"]]

    joblib.dump({
        "modelo": modelo,
        "k": K_FINAL,
        "n_init": N_INIT,
        "random_state": RANDOM_STATE,
        "columnas_features": list(features.columns),
        "nombre_perfil": nombres,
    }, CLUSTERS_JOBLIB)
    zona_cluster.to_parquet(ZONA_CLUSTER_PATH, index=False)

    _verificar(tabla_k, zona_cluster)


def _graficar_codo_silhouette(tabla_k: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].plot(tabla_k["k"], tabla_k["inercia"], marker="o")
    axes[0].axvline(K_FINAL, color="red", ls="--", label=f"k={K_FINAL} elegido")
    axes[0].set_title("Curva de codo (inercia)")
    axes[0].set_xlabel("k")
    axes[0].legend()
    axes[1].plot(tabla_k["k"], tabla_k["silhouette"], marker="o", color="orange")
    axes[1].axvline(K_FINAL, color="red", ls="--")
    axes[1].set_title("Silhouette score")
    axes[1].set_xlabel("k")
    plt.tight_layout()
    FIGURA_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURA_PATH, dpi=110)
    plt.close(fig)


def _verificar(tabla_k: pd.DataFrame, zona_cluster: pd.DataFrame) -> None:
    print("\n-- Curva de codo + silhouette (k=2..7) --")
    print(tabla_k.round(3).to_string(index=False))
    print(f"\n  k elegido: {K_FINAL} (n_init={N_INIT}, random_state={RANDOM_STATE})")

    assert zona_cluster.shape[0] == 20, "deben quedar exactamente 20 localidades asignadas"
    print(f"\n  zona_cluster: {zona_cluster.shape[0]} localidades")
    print(zona_cluster["nombre_perfil"].value_counts().to_string())
    print(f"\n  Sumapaz (cod 20): {zona_cluster.loc[zona_cluster.cod_localidad=='20', 'nombre_perfil'].values[0]}")

    print(f"\n  [ok] {CLUSTERS_JOBLIB}")
    print(f"  [ok] {ZONA_CLUSTER_PATH}")
    print(f"  [ok] {FIGURA_PATH}")


if __name__ == "__main__":
    run()
