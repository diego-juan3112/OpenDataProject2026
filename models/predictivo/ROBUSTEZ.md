# Analisis de error y robustez — modelo predictivo (Issue #22)
**Modelo:** `xgboost` · **Umbral:** 0.560
## Metricas globales (test 2025)
- Recall riesgo alto: **0.968**
- Precision riesgo alto: **0.536**
- F1 riesgo alto: **0.690**
- Brier score (calibracion; menor=mejor): **0.102**
- Matriz confusion [[TN, FP], [FN, TP]]: `[[163, 26], [1, 30]]`
## Curva Precision-Recall y umbral
- Average Precision (AP): **0.737**
- En el umbral 0.560: precision=0.536, recall=0.968
- Figura: `reports/figures/predictivo_precision_recall.png`
- **Justificacion del umbral:** se eligio en validacion temporal 2024 maximizando F1 de la clase riesgo alto (`mejor_umbral_f1`), no accuracy. Prioriza detectar zonas de riesgo (alto recall) aceptando mas falsos positivos.
## Donde falla: por tipo de delito
| tipo | nombre | n_pos | recall | F1 | FP | FN |
|---|---|---|---|---|---|---|
| H | Homicidios | 6 | 0.83 | 0.77 | 2 | 1 |
| HM | Hurto Motocicletas | 5 | 1.00 | 1.00 | 0 | 0 |
| HA | Hurto Automotores | 4 | 1.00 | 0.89 | 1 | 0 |
| VI | Violencia Intrafamiliar | 4 | 1.00 | 0.89 | 1 | 0 |
| DS | Delitos Sexuales | 3 | 1.00 | 0.55 | 5 | 0 |
| HP | Hurto Personas | 3 | 1.00 | 0.60 | 4 | 0 |
| HB | Hurto Bicicletas | 3 | 1.00 | 1.00 | 0 | 0 |
| HR | Hurto Residencias | 2 | 1.00 | 0.67 | 2 | 0 |
| LP | Lesiones Personales | 1 | 1.00 | 0.33 | 4 | 0 |
| HCE | Hurto Celulares | 0 | — | — | 2 | 0 |
| HC | Hurto Comercio | 0 | — | — | 5 | 0 |

Tipos con peor F1 (con al menos 1 positivo):
- **Lesiones Personales** (LP): F1=0.33, FP=4, FN=0
- **Delitos Sexuales** (DS): F1=0.55, FP=5, FN=0
- **Hurto Personas** (HP): F1=0.60, FP=4, FN=0

## Donde falla: por localidad (top peores F1 con positivos)
- **SAN CRISTOBAL** (04): F1=0.00, n_pos=1, FP=0, FN=1
- **BOSA** (07): F1=0.57, n_pos=2, FP=3, FN=0
- **KENNEDY** (08): F1=0.78, n_pos=7, FP=4, FN=0
- **ENGATIVA** (10): F1=0.82, n_pos=7, FP=3, FN=0
- **SUBA** (11): F1=0.82, n_pos=7, FP=3, FN=0

## Robustez ante datos imperfectos
| Escenario | F1 |
|---|---|
| Limpio | 0.690 |
| Features faltantes (ipm_nbi + NUSE nulos en test) | 0.725 (delta +0.035) |
| Features ruidosas (lags + tasa NUSE) | 0.675 (delta -0.015) |

Interpretacion: el pipeline imputa numericos con mediana del train, asi que nulos no tumban la inferencia. En este run, anular NUSE/IPM en test incluso subio levemente el F1 (la senal NUSE contemporanea puede anadir ruido para 2025). El ruido en lags si degrada F1; en produccion conviene monitorear la calidad de las series historicas.
