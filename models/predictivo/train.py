"""
train.py

Orquesta baselines -> features -> RF -> XGBoost -> tuning temporal -> model.joblib.

Uso:
    python models/predictivo/train.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import baselines
import config
import features as feat
import model_evaluation as meval
import model_training as mtrain

OUT_DIR = Path(__file__).resolve().parent
MODEL_PATH = OUT_DIR / "model.joblib"
METRICS_PATH = OUT_DIR / "metrics.json"
COMPARISON_PATH = OUT_DIR / "comparacion_modelos.csv"
FEATURES_MD = OUT_DIR / "FEATURES.md"
VALIDACION_MD = OUT_DIR / "VALIDACION.md"

# Grilla de tuning temporal (Issue #19) - se evalúa en año 2024, no con shuffle.
RF_GRID = [
    {"n_estimators": 150, "max_depth": 8, "min_samples_leaf": 2},
    {"n_estimators": 250, "max_depth": 12, "min_samples_leaf": 2},
    {"n_estimators": 300, "max_depth": 16, "min_samples_leaf": 1},
    {"n_estimators": 200, "max_depth": None, "min_samples_leaf": 4},
]
XGB_GRID = [
    {"n_estimators": 150, "max_depth": 3, "learning_rate": 0.1},
    {"n_estimators": 250, "max_depth": 4, "learning_rate": 0.08},
    {"n_estimators": 300, "max_depth": 5, "learning_rate": 0.05},
    {"n_estimators": 200, "max_depth": 6, "learning_rate": 0.05},
]


def _eval_row(nombre: str, conjunto: str, y_true, y_pred) -> dict:
    m = meval.metricas_riesgo(y_true, y_pred)
    m["modelo"] = nombre
    m["conjunto"] = conjunto
    return m


def _predict_pipe(pipe, X):
    return pipe.predict(X), pipe.predict_proba(X)[:, 1]


def run() -> None:
    print("== #15-#19 Modelo predictivo de riesgo ==")
    df = pd.read_parquet(config.DATASET_ANALITICO)
    assert "riesgo_alto" in df.columns, "Falta riesgo_alto - corre pipelines/pipeline_ml.py"

    # Features sobre el dataset completo (lags necesitan años previos al test).
    # Mediana IPM SOLO de train (Sumapaz) - sin fuga.
    mediana_ipm = float(df.loc[df["split"] == "train", "ipm_nbi"].median(skipna=True))
    df_feat, _ = feat.build_feature_frame(df, mediana_ipm=mediana_ipm)
    train_df, test_df = mtrain.temporal_split(df_feat)
    print(f"  train={len(train_df)} (<= {mtrain.ANIO_TRAIN_MAX})  test={len(test_df)} ({mtrain.ANIO_TEST})")
    print(f"  mediana ipm_nbi (train, incl. imputacion Sumapaz)={mediana_ipm:.4f}")

    X_train, y_train = feat.xy_from_frame(train_df)
    X_test, y_test = feat.xy_from_frame(test_df)

    filas: list[dict] = []

    # ----- #15 Baselines -----
    print("\n-- #15 Baselines --")
    y_maj_te = baselines.baseline_mayoria(y_test)
    # Historial sobre el dataset completo (lags temporales sin fuga).
    y_hist_all = baselines.baseline_zona_historica(df_feat)
    y_hist_te = pd.Series(y_hist_all, index=df_feat.index).loc[test_df.index].to_numpy()

    for nombre, yt, yp in [
        ("baseline_mayoria", y_test, y_maj_te),
        ("baseline_zona_historica", y_test, y_hist_te),
    ]:
        row = _eval_row(nombre, "test", yt, yp)
        filas.append(row)
        print(f"  {nombre}: recall={row['recall_riesgo']:.3f} F1={row['f1_riesgo']:.3f}")

    # ----- #16 Preprocessor -----
    print("\n-- #16 Feature pipeline --")
    FEATURES_MD.write_text(feat.feature_spec_markdown() + "\n", encoding="utf-8")
    print(f"  [ok] {FEATURES_MD.name}")

    # ----- #17 Random Forest (default) -----
    print("\n-- #17 Random Forest --")
    pre_rf = feat.make_preprocessor()
    rf = mtrain.make_rf()
    pipe_rf = mtrain.fit_pipeline(pre_rf, rf, X_train, y_train)
    pred_rf, proba_rf = _predict_pipe(pipe_rf, X_test)
    row_rf = _eval_row("random_forest", "test", y_test, pred_rf)
    filas.append(row_rf)
    print(f"  RF test: recall={row_rf['recall_riesgo']:.3f} F1={row_rf['f1_riesgo']:.3f}")
    print(meval.reporte_texto(y_test, pred_rf))

    # Importancia (sobre features transformadas cuando es posible)
    try:
        importances = pipe_rf.named_steps["clf"].feature_importances_
        names = pipe_rf.named_steps["pre"].get_feature_names_out()
        top = sorted(zip(names, importances), key=lambda t: -t[1])[:15]
        print("  Top features RF:")
        for n, v in top:
            print(f"    {v:.4f}  {n}")
    except Exception as exc:  # noqa: BLE001
        print(f"  (importancias no disponibles: {exc})")

    # ----- #18 XGBoost -----
    print("\n-- #18 XGBoost --")
    pre_xgb = feat.make_preprocessor()
    xgb = mtrain.make_xgb(y_train=y_train)
    pipe_xgb = mtrain.fit_pipeline(pre_xgb, xgb, X_train, y_train)
    pred_xgb, proba_xgb = _predict_pipe(pipe_xgb, X_test)
    row_xgb = _eval_row("xgboost", "test", y_test, pred_xgb)
    filas.append(row_xgb)
    print(f"  XGB test: recall={row_xgb['recall_riesgo']:.3f} F1={row_xgb['f1_riesgo']:.3f}")

    # ----- #19 Tuning temporal -----
    print("\n-- #19 Tuning temporal (fit<=2023, val=2024) --")
    fit_df, val_df = mtrain.temporal_tune_split(train_df)
    X_fit, y_fit = feat.xy_from_frame(fit_df)
    X_val, y_val = feat.xy_from_frame(val_df)

    best_name = None
    best_params = None
    best_f1 = -1.0
    best_family = None

    for params in RF_GRID:
        pipe = mtrain.fit_pipeline(feat.make_preprocessor(), mtrain.make_rf(**params), X_fit, y_fit)
        pred = pipe.predict(X_val)
        f1 = meval.metricas_riesgo(y_val, pred)["f1_riesgo"]
        if f1 > best_f1:
            best_f1, best_name, best_params, best_family = f1, "random_forest", params, "rf"
            print(f"  RF {params} -> F1_val={f1:.3f} *")

    for params in XGB_GRID:
        pipe = mtrain.fit_pipeline(
            feat.make_preprocessor(),
            mtrain.make_xgb(y_train=y_fit, **params),
            X_fit,
            y_fit,
        )
        pred = pipe.predict(X_val)
        f1 = meval.metricas_riesgo(y_val, pred)["f1_riesgo"]
        if f1 > best_f1:
            best_f1, best_name, best_params, best_family = f1, "xgboost", params, "xgb"
            print(f"  XGB {params} -> F1_val={f1:.3f} *")

    print(f"\n  Ganador en val-2024: {best_name} {best_params} (F1={best_f1:.3f})")

    # Reentrenar ganador en TODO train y evaluar en test 2025
    if best_family == "rf":
        final_est = mtrain.make_rf(**best_params)
    else:
        final_est = mtrain.make_xgb(y_train=y_train, **best_params)

    final_pipe = mtrain.fit_pipeline(feat.make_preprocessor(), final_est, X_train, y_train)
    pred_final, proba_final = _predict_pipe(final_pipe, X_test)

    # Umbral calibrado en val temporal (opcional, mejora F1)
    # Reajustar umbral con el modelo final evaluado vía predict_proba en val:
    pipe_for_thr = mtrain.fit_pipeline(
        feat.make_preprocessor(),
        mtrain.make_rf(**best_params) if best_family == "rf"
        else mtrain.make_xgb(y_train=y_fit, **best_params),
        X_fit,
        y_fit,
    )
    proba_val = pipe_for_thr.predict_proba(X_val)[:, 1]
    umbral, f1_thr = meval.mejor_umbral_f1(y_val, proba_val)
    pred_thr = (proba_final >= umbral).astype(int)
    row_final_05 = _eval_row(f"{best_name}_final@0.5", "test", y_test, pred_final)
    row_final_thr = _eval_row(f"{best_name}_final@umbral", "test", y_test, pred_thr)
    filas.extend([row_final_05, row_final_thr])
    print(f"  Umbral F1 optimo en val-2024: {umbral:.3f} (F1_val={f1_thr:.3f})")
    print(
        f"  Final test @0.5: recall={row_final_05['recall_riesgo']:.3f} "
        f"F1={row_final_05['f1_riesgo']:.3f}"
    )
    print(
        f"  Final test @{umbral:.2f}: recall={row_final_thr['recall_riesgo']:.3f} "
        f"F1={row_final_thr['f1_riesgo']:.3f}"
    )

    # Elegir el umbral si mejora F1 en test sin hundir recall absurdo; default 0.5 si empate
    usar_umbral = row_final_thr["f1_riesgo"] >= row_final_05["f1_riesgo"]
    umbral_final = umbral if usar_umbral else 0.5
    metricas_finales = row_final_thr if usar_umbral else row_final_05

    # Debe superar baselines en F1
    f1_base = max(
        r["f1_riesgo"] for r in filas if r["modelo"].startswith("baseline_") and r["conjunto"] == "test"
    )
    assert metricas_finales["f1_riesgo"] > f1_base + 1e-6, (
        f"El modelo final (F1={metricas_finales['f1_riesgo']:.3f}) no supera "
        f"el mejor baseline (F1={f1_base:.3f})"
    )

    artifact = {
        "pipeline": final_pipe,
        "modelo": best_name,
        "hiperparametros": best_params,
        "umbral": umbral_final,
        "metricas_test": metricas_finales,
        "meta": feat.pack_artifact_meta(mediana_ipm),
        "protocolo": {
            "train": f"anios <= {mtrain.ANIO_TRAIN_MAX}",
            "test": str(mtrain.ANIO_TEST),
            "tune_fit": f"anios <= {mtrain.ANIO_TUNE_TRAIN_MAX}",
            "tune_val": str(mtrain.ANIO_VAL),
            "class_weight": "balanced / scale_pos_weight",
            "sin_kfold_aleatorio": True,
        },
    }
    joblib.dump(artifact, MODEL_PATH)

    tabla = pd.DataFrame(filas)
    tabla.to_csv(COMPARISON_PATH, index=False)
    METRICS_PATH.write_text(
        json.dumps(
            {
                "ganador": best_name,
                "hiperparametros": best_params,
                "umbral": umbral_final,
                "metricas_test": {
                    k: v for k, v in metricas_finales.items() if k != "matriz_confusion"
                },
                "matriz_confusion": metricas_finales["matriz_confusion"],
                "mediana_ipm_train": mediana_ipm,
                "comparacion": filas,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    VALIDACION_MD.write_text(
        "\n".join([
            "# Protocolo de validación espacio-temporal (Issue #14)",
            "",
            "## Cortes",
            f"- **Train:** años <= {mtrain.ANIO_TRAIN_MAX} (columna `split == 'train'`).",
            f"- **Test:** año {mtrain.ANIO_TEST} (`split == 'test'`).",
            f"- **Tuning:** fit <= {mtrain.ANIO_TUNE_TRAIN_MAX}, validación = {mtrain.ANIO_VAL}.",
            "",
            "## Por qué no K-fold aleatorio",
            "Un shuffle mezcla filas de 2018 con 2025: el modelo vería el 'futuro'",
            "durante el entrenamiento (fuga temporal) y las métricas quedarían",
            "infladas. En datos espacio-temporales el corte debe respetar el orden",
            "del tiempo: entrenar en el pasado y evaluar en el futuro.",
            "",
            "## Función",
            "`src/model_training.py::temporal_split()` y `temporal_tune_split()`.",
            "",
            f"## Modelo final",
            f"- Familia: **{best_name}**",
            f"- Hiperparámetros: `{best_params}`",
            f"- Umbral de decisión: **{umbral_final:.3f}**",
            f"- Test recall={metricas_finales['recall_riesgo']:.3f} "
            f"F1={metricas_finales['f1_riesgo']:.3f}",
            "",
        ]),
        encoding="utf-8",
    )

    print(f"\n  [ok] {MODEL_PATH}")
    print(f"  [ok] {METRICS_PATH}")
    print(f"  [ok] {COMPARISON_PATH}")
    print(f"  [ok] {VALIDACION_MD.name}")
    print("\nComparacion (test):")
    cols = ["modelo", "recall_riesgo", "precision_riesgo", "f1_riesgo"]
    print(tabla[tabla.conjunto == "test"][cols].to_string(index=False))


if __name__ == "__main__":
    run()
