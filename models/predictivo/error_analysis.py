"""
error_analysis.py 

Desglose de error por localidad/tipo, curva precision-recall, umbral
justificado y prueba de degradacion con features faltantes/ruidosas.

Uso:
    python models/predictivo/error_analysis.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_recall_curve,
    recall_score,
)

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import features as feat
import model_evaluation as meval
import predict as pred_mod

OUT_DIR = Path(__file__).resolve().parent
FIG_DIR = ROOT / "reports" / "figures"
ROBUSTEZ_MD = OUT_DIR / "ROBUSTEZ.md"
ERROR_JSON = OUT_DIR / "error_analysis.json"


def _desglose(df_eval: pd.DataFrame, grupo: str) -> pd.DataFrame:
    filas = []
    for key, g in df_eval.groupby(grupo):
        y_true = g["riesgo_alto"].to_numpy()
        y_pred = g["riesgo_predicho"].to_numpy()
        n_pos = int((y_true == 1).sum())
        filas.append({
            grupo: key,
            "n": len(g),
            "n_positivos": n_pos,
            "recall_riesgo": float(recall_score(y_true, y_pred, pos_label=1, zero_division=0))
            if n_pos > 0 else float("nan"),
            "f1_riesgo": float(f1_score(y_true, y_pred, pos_label=1, zero_division=0))
            if n_pos > 0 else float("nan"),
            "fp": int(((y_true == 0) & (y_pred == 1)).sum()),
            "fn": int(((y_true == 1) & (y_pred == 0)).sum()),
        })
    return pd.DataFrame(filas).sort_values("n_positivos", ascending=False)


def _curva_pr(y_true, y_proba, umbral: float, out_png: Path) -> dict:
    precision, recall, thresholds = precision_recall_curve(y_true, y_proba)
    ap = float(average_precision_score(y_true, y_proba))
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.plot(recall, precision, label=f"PR (AP={ap:.3f})")
    # Punto del umbral elegido
    pred_u = (y_proba >= umbral).astype(int)
    p_u = float(((pred_u == 1) & (y_true == 1)).sum() / max((pred_u == 1).sum(), 1))
    r_u = float(recall_score(y_true, pred_u, pos_label=1, zero_division=0))
    ax.scatter([r_u], [p_u], color="red", zorder=5, label=f"umbral={umbral:.3f}")
    ax.set_xlabel("Recall (clase riesgo alto)")
    ax.set_ylabel("Precision (clase riesgo alto)")
    ax.set_title("Curva Precision-Recall — test 2025")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=120)
    plt.close(fig)
    return {"average_precision": ap, "precision_en_umbral": p_u, "recall_en_umbral": r_u}


def _degradacion(artifact, umbral: float) -> dict:
    """Compara F1 limpio vs features faltantes / ruido gaussiano en lags."""
    pipe = artifact["pipeline"]
    mediana = float(artifact["meta"]["mediana_ipm_train"])

    def eval_frame(frame: pd.DataFrame) -> float:
        prepared, _ = feat.build_feature_frame(frame, mediana_ipm=mediana)
        te = prepared[prepared["split"] == "test"]
        X = te[feat.NUMERIC_FEATURES + feat.CATEGORICAL_FEATURES]
        y = te["riesgo_alto"].to_numpy()
        proba = pipe.predict_proba(X)[:, 1]
        pred = (proba >= umbral).astype(int)
        return float(f1_score(y, pred, pos_label=1, zero_division=0))

    df = pd.read_parquet(config.DATASET_ANALITICO)
    f1_clean = eval_frame(df)

    # Features faltantes: NaN en ipm_nbi y conteo_nuse solo en filas test
    df_miss = df.copy()
    mask_te = df_miss["split"] == "test"
    df_miss.loc[mask_te, "ipm_nbi"] = np.nan
    df_miss.loc[mask_te, "conteo_nuse"] = np.nan
    f1_miss = eval_frame(df_miss)

    # Ruido gaussiano sobre lags / tasa en el bloque test (tras feature frame)
    prepared, _ = feat.build_feature_frame(df, mediana_ipm=mediana)
    te = prepared[prepared["split"] == "test"].copy()
    rng = np.random.default_rng(42)
    for col in ("lag_1", "lag_2", "lag_3", "roll_mean_3", "tasa_nuse_100k"):
        noise = rng.normal(0, float(te[col].std(ddof=0) or 1.0) * 0.5, size=len(te))
        te[col] = te[col] + noise
    X = te[feat.NUMERIC_FEATURES + feat.CATEGORICAL_FEATURES]
    y = te["riesgo_alto"].to_numpy()
    proba = pipe.predict_proba(X)[:, 1]
    pred = (proba >= umbral).astype(int)
    f1_noise = float(f1_score(y, pred, pos_label=1, zero_division=0))

    return {
        "f1_limpio": f1_clean,
        "f1_features_faltantes": f1_miss,
        "f1_features_ruidosas": f1_noise,
        "delta_faltantes": f1_miss - f1_clean,
        "delta_ruido": f1_noise - f1_clean,
    }


def run() -> None:
    print("== #22 Analisis de error y robustez ==")
    artifact = pred_mod.load_model()
    umbral = float(artifact.get("umbral", 0.5))
    df = pd.read_parquet(config.DATASET_ANALITICO)
    preds = pred_mod.predict(df, artifact=artifact)

    eval_df = df[df["split"] == "test"].merge(
        preds[
            ["cod_localidad", "anio", "tipo_delito", "probabilidad_riesgo", "riesgo_predicho"]
        ],
        on=["cod_localidad", "anio", "tipo_delito"],
        how="left",
    )

    y_true = eval_df["riesgo_alto"].to_numpy()
    y_pred = eval_df["riesgo_predicho"].to_numpy()
    y_proba = eval_df["probabilidad_riesgo"].to_numpy()

    global_m = meval.metricas_riesgo(y_true, y_pred, umbral=umbral)
    brier = float(brier_score_loss(y_true, y_proba))

    por_tipo = _desglose(eval_df, "tipo_delito")
    por_loc = _desglose(eval_df, "cod_localidad")
    # Anadir nombres
    nombres_tipo = df[["tipo_delito", "tipo_delito_nombre"]].drop_duplicates()
    por_tipo = por_tipo.merge(nombres_tipo, on="tipo_delito", how="left")
    nombres_loc = df[["cod_localidad", "localidad_nombre"]].drop_duplicates()
    por_loc = por_loc.merge(nombres_loc, on="cod_localidad", how="left")

    pr_info = _curva_pr(
        y_true, y_proba, umbral, FIG_DIR / "predictivo_precision_recall.png"
    )

    deg = _degradacion(artifact, umbral)


    # Peores localidades / tipos (con positivos)
    peores_tipo = (
        por_tipo.dropna(subset=["f1_riesgo"])
        .sort_values("f1_riesgo")
        .head(3)
    )
    peores_loc = (
        por_loc.dropna(subset=["f1_riesgo"])
        .sort_values("f1_riesgo")
        .head(5)
    )

    payload = {
        "metricas_globales": global_m,
        "brier_score": brier,
        "umbral": umbral,
        "precision_recall": pr_info,
        "por_tipo": por_tipo.replace({np.nan: None}).to_dict(orient="records"),
        "por_localidad": por_loc.replace({np.nan: None}).to_dict(orient="records"),
        "degradacion": deg,
    }
    ERROR_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    md = []
    md.append("# Analisis de error y robustez — modelo predictivo (Issue #22)\n")
    md.append(f"**Modelo:** `{artifact.get('modelo')}` · **Umbral:** {umbral:.3f}\n")
    md.append("## Metricas globales (test 2025)\n")
    md.append(
        f"- Recall riesgo alto: **{global_m['recall_riesgo']:.3f}**\n"
        f"- Precision riesgo alto: **{global_m['precision_riesgo']:.3f}**\n"
        f"- F1 riesgo alto: **{global_m['f1_riesgo']:.3f}**\n"
        f"- Brier score (calibracion; menor=mejor): **{brier:.3f}**\n"
        f"- Matriz confusion [[TN, FP], [FN, TP]]: `{global_m['matriz_confusion']}`\n"
    )
    md.append("## Curva Precision-Recall y umbral\n")
    md.append(
        f"- Average Precision (AP): **{pr_info['average_precision']:.3f}**\n"
        f"- En el umbral {umbral:.3f}: precision={pr_info['precision_en_umbral']:.3f}, "
        f"recall={pr_info['recall_en_umbral']:.3f}\n"
        f"- Figura: `reports/figures/predictivo_precision_recall.png`\n"
        "- **Justificacion del umbral:** se eligio en validacion temporal 2024 "
        "maximizando F1 de la clase riesgo alto (`mejor_umbral_f1`), no accuracy. "
        "Prioriza detectar zonas de riesgo (alto recall) aceptando mas falsos positivos.\n"
    )
    md.append("## Donde falla: por tipo de delito\n")
    md.append("| tipo | nombre | n_pos | recall | F1 | FP | FN |\n|---|---|---|---|---|---|---|\n")
    for _, r in por_tipo.iterrows():
        rec = "—" if pd.isna(r["recall_riesgo"]) else f"{r['recall_riesgo']:.2f}"
        f1 = "—" if pd.isna(r["f1_riesgo"]) else f"{r['f1_riesgo']:.2f}"
        md.append(
            f"| {r['tipo_delito']} | {r['tipo_delito_nombre']} | {int(r['n_positivos'])} | "
            f"{rec} | {f1} | {int(r['fp'])} | {int(r['fn'])} |\n"
        )
    md.append("\nTipos con peor F1 (con al menos 1 positivo):\n")
    for _, r in peores_tipo.iterrows():
        md.append(
            f"- **{r['tipo_delito_nombre']}** ({r['tipo_delito']}): "
            f"F1={r['f1_riesgo']:.2f}, FP={int(r['fp'])}, FN={int(r['fn'])}\n"
        )
    md.append("\n## Donde falla: por localidad (top peores F1 con positivos)\n")
    for _, r in peores_loc.iterrows():
        md.append(
            f"- **{r['localidad_nombre']}** ({r['cod_localidad']}): "
            f"F1={r['f1_riesgo']:.2f}, n_pos={int(r['n_positivos'])}, "
            f"FP={int(r['fp'])}, FN={int(r['fn'])}\n"
        )
    md.append("\n## Robustez ante datos imperfectos\n")
    md.append(
        f"| Escenario | F1 |\n|---|---|\n"
        f"| Limpio | {deg['f1_limpio']:.3f} |\n"
        f"| Features faltantes (ipm_nbi + NUSE nulos en test) | {deg['f1_features_faltantes']:.3f} "
        f"(delta {deg['delta_faltantes']:+.3f}) |\n"
        f"| Features ruidosas (lags + tasa NUSE) | {deg['f1_features_ruidosas']:.3f} "
        f"(delta {deg['delta_ruido']:+.3f}) |\n"
    )
    md.append(
        "\nInterpretacion: el pipeline imputa numericos con mediana del train, "
        "asi que nulos no tumban la inferencia. En este run, anular NUSE/IPM en "
        "test incluso subio levemente el F1 (la senal NUSE contemporanea puede "
        "anadir ruido para 2025). El ruido en lags si degrada F1; en produccion "
        "conviene monitorear la calidad de las series historicas.\n"
    )
    ROBUSTEZ_MD.write_text("".join(md), encoding="utf-8")

    print(f"  F1 limpio={deg['f1_limpio']:.3f}  faltantes={deg['f1_features_faltantes']:.3f}  "
          f"ruido={deg['f1_features_ruidosas']:.3f}")
    print(f"  [ok] {ROBUSTEZ_MD}")
    print(f"  [ok] {ERROR_JSON}")
    print(f"  [ok] {FIG_DIR / 'predictivo_precision_recall.png'}")


if __name__ == "__main__":
    run()
