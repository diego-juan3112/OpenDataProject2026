"""
baselines.py — Pisos de comparación del predictivo.

1) Trivial por mayoría: siempre predice clase 0 (riesgo bajo).
2) Regla histórica: zona–tipo "históricamente peligrosa" si la media de
   riesgo_alto en años PASADOS (estrictamente anteriores) ≥ 0.5.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def baseline_mayoria(y: np.ndarray | pd.Series) -> np.ndarray:
    """Clasificador trivial: predice siempre la clase mayoritaria (0)."""
    y = np.asarray(y)
    return np.zeros(len(y), dtype=int)


def baseline_zona_historica(df: pd.DataFrame) -> np.ndarray:
    """Regla: predecir 1 si la media de riesgo_alto en años anteriores ≥ 0.5.

    Calculado por (cod_localidad, tipo_delito) solo con el pasado.
    Sin historial → 0.
    """
    ordered = df.sort_values(["cod_localidad", "tipo_delito", "anio"]).copy()
    pred_by_idx: dict[object, int] = {}

    for _, grp in ordered.groupby(["cod_localidad", "tipo_delito"], sort=False):
        history: list[int] = []
        for idx, row in grp.iterrows():
            if not history:
                pred_by_idx[idx] = 0
            else:
                pred_by_idx[idx] = int(float(np.mean(history)) >= 0.5)
            history.append(int(row["riesgo_alto"]))

    return np.array([pred_by_idx[i] for i in df.index], dtype=int)
