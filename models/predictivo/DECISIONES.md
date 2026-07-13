# Decisiones Integrante 2 — modelo predictivo

Confirmadas antes de #17 (contrato `variable_objetivo.md`):

| Decisión | Elección |
|---|---|
| Definición de `riesgo_alto` | P75 por tipo de delito, umbral estricto (`>`). **No se recalcula.** |
| Balanceo | `class_weight="balanced"` (RF) / `scale_pos_weight` (XGBoost). SMOTE como plan B no necesario. |
| Etiqueta test | Se usa la del parquet (umbrales de train). **No re-etiquetar.** |
| Sumapaz `ipm_nbi` nulo | **Imputar mediana de train** (misma lógica que clustering). |
| Feature prohibida | `conteo_siedco` del mismo año (fuga de etiqueta: el target se deriva de él). |

Modelo final: ver `metrics.json` y `VALIDACION.md`.
