# QA cruzada — Predictivo (Issue #30)

**Revisor:** Integrante 3 (Clustering) · **Objeto:** modelo predictivo de riesgo (RF/XGBoost) de Integrante 2
**Fecha:** 2026-07-13 · **Artefactos revisados:** `src/model_training.py`,
`src/model_evaluation.py`, `models/predictivo/{features.py, train.py,
error_analysis.py, DECISIONES.md, VALIDACION.md, ROBUSTEZ.md, MODEL_CARD.md,
FEATURES.md}`. Se corrió `models/predictivo/train.py` de punta a punta
(reproducible: `random_state=42`, la corrida no alteró ningún archivo
commiteado — confirmado con `git diff` antes y después) para verificar las
métricas y la importancia de features con evidencia de primera mano, no solo
leyendo la documentación.

> Nadie evalúa su propio modelo. Esta es la validación cruzada del predictivo
> para la sección compartida de evaluación del informe.

---

## 1. ¿Hay fuga temporal?

**No hay fuga clásica train/test.**

- `temporal_split()` (`src/model_training.py`) no solo separa por la columna
  `split` — tiene un `assert` en runtime que **lanza `ValueError` si
  `max(train.año) >= min(test.año)`**. Es una salvaguarda activa, no solo una
  convención documentada.
- Los lags (`lag_1`, `lag_2`, `lag_3`, `roll_mean_3`) se calculan con
  `.shift()` ordenado por año dentro de cada `(cod_localidad, tipo_delito)` —
  solo usan información pasada, verificado leyendo `_lags_sin_fuga()`.
- `conteo_siedco` del mismo año (la variable de la que se deriva
  `riesgo_alto`) está correctamente excluido de `NUMERIC_FEATURES` —
  confirmado en `features.py` y documentado explícitamente en `FEATURES.md`.
- El umbral de decisión (0.560) se calibró con `mejor_umbral_f1()` sobre un
  **holdout temporal interno** (fit ≤2023, val=2024), no sobre test — evita
  fuga en la selección del umbral, buena práctica que va más allá de lo
  mínimo exigido.

**Nota no bloqueante, para #34:** `tasa_nuse_100k` usa el conteo de NUSE del
**mismo año** que se está prediciendo. No es fuga train/test (NUSE es una
fuente distinta a SIEDCO, y el corte train/test se respeta igual), pero es
una **fuga de disponibilidad en producción**: si `GET /zonas-riesgo` llega a
servir predicciones para el año en curso, el conteo NUSE de ese año todavía
no estaría completo al momento de la consulta. Vale la pena que Integrante 2
y quien construya #34 definan explícitamente qué año(s) sirve la API en
producción (¿solo años ya cerrados?) para que esta feature no se convierta en
fuga real fuera del entorno de evaluación offline.

## 2. ¿La métrica es adecuada?

**Sí.**

- `model_evaluation.py::metricas_riesgo` reporta recall/precision/F1 de la
  clase `riesgo_alto` (`pos_label=1`) — nunca accuracy global — tal como
  exige `CLAUDE.md` §5 dado el desbalance de clases (only ~23.6% de las
  1760 combinaciones son `riesgo_alto=1`, ver #33).
- La justificación del umbral (priorizar recall, aceptar más falsos
  positivos) es coherente con el caso de uso: para una alerta de seguridad
  ciudadana, un falso negativo (no avisar de una zona realmente riesgosa) es
  más costoso que un falso positivo.

## 3. ¿Solo replica sesgo de vigilancia? — hallazgo accionable con evidencia

Corrí `train.py` completo para obtener la comparación real y la importancia
de features del Random Forest (no persistida en ningún artefacto —
solo se imprime en consola durante el entrenamiento, ver hallazgo aparte
abajo).

**3a. La ganancia sobre un baseline ingenuo es marginal.**

| modelo | recall | precision | F1 |
|---|---|---|---|
| `baseline_zona_historica` (heurística: "si fue riesgo antes, predecir riesgo otra vez") | 0.935 | 0.537 | 0.682 |
| `xgboost_final@umbral` (modelo final, tuneado) | 0.968 | 0.536 | **0.690** |

La precisión es prácticamente idéntica (0.537 vs 0.536); el modelo final solo
gana **un verdadero positivo adicional de 31 totales** sobre el baseline más
simple posible. Todo el pipeline de feature engineering + grid search
temporal + comparación RF/XGBoost produce una mejora de **+0.008 en F1**.
Esto no invalida el modelo (sí supera al baseline, que era el criterio de
aceptación de #19), pero es una ganancia mucho más modesta de lo que la
sofisticación del pipeline sugiere — vale la pena que el informe lo diga así
de explícito, en vez de presentar XGBoost como una mejora sustancial.

**3b. Sesgo de escala poblacional, no (solo) de vigilancia por identidad de zona.**

Importancia de features del Random Forest (top 10, sobre 1540 filas de
train):

| feature | importancia |
|---|---|
| `poblacion` | **0.335** |
| `tasa_nuse_100k` | 0.104 |
| `lag_1` | 0.078 |
| `roll_mean_3` | 0.069 |
| `ipm_nbi` | 0.052 |
| `cod_localidad` (dummy más fuerte, localidad 11/Suba) | 0.040 |
| `lag_2` | 0.038 |
| `cod_localidad` (localidad 08/Kennedy) | 0.035 |
| `lag_3` | 0.034 |
| `anio` | 0.022 |

`poblacion` domina con más del triple de la siguiente feature. Ninguna
dummy individual de `cod_localidad` pesa más del 4% — el modelo **no**
parece memorizar identidad de zona directamente, así que el riesgo de sesgo
de vigilancia "clásico" (repetir siempre las mismas zonas ya
sobre-vigiladas, por su nombre/código) es bajo.

Pero hay un sesgo distinto y más sutil: `riesgo_alto` se define sobre el
**conteo crudo** de `conteo_siedco` (percentil 75 por tipo de delito), **no**
una tasa per cápita — y `poblacion` es, por un margen amplio, la feature más
importante. Esto es consistente con que el modelo esté aprendiendo en buena
parte "esta es una localidad grande" (que mecánicamente tiene conteos
absolutos más altos) en vez de una señal de peligrosidad diferencial real
por residente. `MODEL_CARD.md` menciona el riesgo genérico de "sesgo de
vigilancia" pero no este mecanismo específico (conteo absoluto vs. tasa).

**Recomendación (accionable):**
1. Documentar este mecanismo explícitamente en `MODEL_CARD.md` — es más
   preciso que la mención genérica actual.
2. Para una iteración futura, evaluar una versión del target (o al menos una
   feature adicional) normalizada por población (tasa por 100k habitantes,
   igual que ya se hace con NUSE) para separar "zona grande" de "zona
   peligrosa".
3. Persistir la importancia de features en `metrics.json` o
   `error_analysis.json` (hoy solo se imprime en consola durante
   `train.py`, se pierde después de correr) para que este tipo de auditoría
   no dependa de re-entrenar el modelo desde cero.

## 4. Comentario de validación (para la sección compartida)

> **Validación cruzada (Int. 3):** Sin fuga temporal clásica — `temporal_split()`
> la verifica en runtime y los lags respetan el orden del tiempo; el umbral se
> calibró en un holdout temporal, no en test. La métrica (recall/F1 de la
> clase riesgo alto) es la correcta según `CLAUDE.md`. Hallazgo accionable:
> corriendo `train.py` de punta a punta, el modelo final apenas supera al
> baseline histórico ingenuo (F1 0.690 vs 0.682, +1 verdadero positivo de 31,
> precisión casi idéntica), y la importancia de features del RF muestra que
> `poblacion` domina (33%, el triple de la siguiente feature) — como
> `riesgo_alto` se define sobre conteo crudo y no tasa per cápita, el modelo
> puede estar aprendiendo en buena parte "zona grande" más que "zona
> peligrosa". No hay evidencia de memorización de `cod_localidad` (bajo riesgo
> de sesgo de vigilancia clásico), pero sí de un sesgo de escala poblacional
> no documentado hoy en `MODEL_CARD.md`. Se acepta el modelo (cumple el
> criterio de superar baselines y la métrica es la correcta), con la
> recomendación de documentar este sesgo y considerar una versión del target
> normalizada por población en una iteración futura.

---

## Checklist de aceptación #30

- [x] Comentario de validación cruzada escrito
- [x] Verificación explícita de ausencia de fuga temporal (con nota aparte
  sobre disponibilidad de NUSE contemporáneo para producción, #34)
- [x] Al menos 1 hallazgo accionable con evidencia (ganancia marginal sobre
  baseline histórico, +0.008 F1; y sesgo de escala poblacional via
  importancia de features, `poblacion`=0.335)
