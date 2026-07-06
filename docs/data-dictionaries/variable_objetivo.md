# Variable objetivo — `riesgo_alto` (Issue #10)

**Responsable:** Integrante 1 (Datos) · **En acuerdo con:** Integrante 2 (Predictivo)
**Estado:** definida y añadida al `dataset_analitico.parquet` · **Fecha:** 2026-07-06

Este documento define cómo se etiqueta "riesgo alto" para el modelo predictivo,
caracteriza el desbalance resultante y fija la estrategia de balanceo acordada.
Es el contrato que **Integrante 2 debe confirmar antes de arrancar la Issue #17**.

---

## 1. Definición

Para cada fila `(cod_localidad × anio × tipo_delito)`:

> `riesgo_alto = 1` si su `conteo_siedco` **supera estrictamente** el
> **percentil 75 (P75) del mismo tipo de delito** en el histórico de
> **entrenamiento** (años 2018–2024). En caso contrario, `riesgo_alto = 0`.

Implementación reproducible en
[`src/feature_engineering.py`](../../src/feature_engineering.py)
(`add_target_riesgo_alto`), invocada por
[`pipelines/pipeline_ml.py`](../../pipelines/pipeline_ml.py). La columna se
regenera al correr `python pipelines/pipeline_ml.py`.

### Por qué P75 por tipo de delito (y no un umbral global)

1. **Escalas incomparables entre delitos.** El conteo típico varía en tres
   órdenes de magnitud: Homicidios ronda decenas (P75 ≈ 76) mientras Hurto a
   Personas ronda miles (P75 ≈ 8.799). Un umbral global marcaría "riesgo alto"
   casi solo por hurto y nunca por homicidio. Normalizar *dentro de cada tipo*
   hace la etiqueta comparable: significa "esta zona-año está en el cuartil
   superior **para ese delito**".
2. **P75 = cuartil superior.** Es un corte estadístico estándar e interpretable
   ("el 25% peor"), no un número arbitrario. Da una clase positiva del ~25%:
   suficientemente frecuente para aprender, suficientemente minoritaria para que
   el problema siga siendo de detección (no de mayoría trivial).
3. **Umbral estricto (`>`, no `>=`).** Con 140 observaciones por tipo, `> P75`
   deja exactamente 35 positivos por tipo (25.0% limpio). `>=` inflaría la clase
   por empates en la cola.

### Alternativas consideradas

- **P90** (top 10%): produciría ~14 positivos por tipo → clase demasiado escasa
  para 1.540 filas, recall inestable. Descartado como umbral principal; queda
  como análisis de sensibilidad para #17 si se busca mayor precisión.
- **Umbral absoluto por experto**: no defendible sin criterio externo y no
  escala a otras ciudades. Descartado.

---

## 2. Umbrales aprendidos (train 2018–2024)

P75 de `conteo_siedco` por tipo de delito, calculado **solo con filas train**:

| tipo_delito | Nombre | P75 (umbral) |
|---|---|---|
| DS  | Delitos Sexuales        | 466.8  |
| H   | Homicidios              | 75.5   |
| HA  | Hurto Automotores       | 242.5  |
| HB  | Hurto Bicicletas        | 527.0  |
| HC  | Hurto Comercio          | 921.8  |
| HCE | Hurto Celulares         | 3665.2 |
| HM  | Hurto Motocicletas      | 316.0  |
| HP  | Hurto Personas          | 8798.5 |
| HR  | Hurto Residencias       | 482.2  |
| LP  | Lesiones Personales     | 1504.5 |
| VI  | Violencia Intrafamiliar | 2853.8 |

**Sin fuga:** los umbrales se aprenden únicamente de train y luego se **aplican**
a las filas test para dejar la etiqueta lista para la evaluación de #17. Test
nunca interviene en el cálculo del percentil (verificado: las etiquetas test se
reproducen exactamente a partir de los umbrales de train).

---

## 3. Desbalance resultante

### Global

| split | clase 0 | clase 1 | % clase 1 |
|---|---|---|---|
| **train** (1.540) | 1.155 | 385 | **25.0 %** |
| **test** (220)    | 189   | 31  | 14.1 %    |

Ratio de desbalance en train ≈ **3:1** (moderado, no severo).

### Por tipo de delito (train)

Por construcción del P75 por tipo, **cada tipo aporta exactamente 25.0%** de
clase positiva (35 de 140 filas). Esto es deseable: ningún tipo de delito domina
la definición de riesgo, y la clase positiva está balanceada entre delitos.

### Hallazgo: el test es naturalmente menos positivo (14.1% vs 25%)

Al aplicar los umbrales de 2018–2024, solo el 14.1% de las filas de 2025 quedan
como riesgo alto. Es coherente y **esperado sin fuga**: 2025 tiende a caer por
debajo del P75 histórico (posible descenso de conteos o efecto de promediar 7
años en el umbral). **Consecuencia para Integrante 2 (#17):** el recall en test
se interpreta sobre una base menos poblada de positivos; no re-etiquetar test con
su propio percentil (eso sería fuga).

---

## 4. Nota sobre Sumapaz (cod_localidad = "20")

Sumapaz es rural, ~3.172 habitantes, `conteo_siedco` casi nulo (máx. 28, media
1.9 en train) e `ipm_nbi` **nulo** (no la cubre la Encuesta Multipropósito).

**Decisión: Sumapaz se INCLUYE en el cálculo del percentil.** Razones:

- Es una unidad poblacional legítima; excluir filas para mover un umbral es una
  selección que exige justificación fuerte y sesga el resultado a conveniencia.
- Sumapaz **nunca** cruza el umbral (0 de 77 filas train son `riesgo_alto=1`):
  el modelo lo verá correctamente como zona de bajo riesgo, sin falsos positivos.

**Sensibilidad documentada (honestidad, no se esconde):** sus conteos casi nulos
sí empujan el P75 ligeramente hacia abajo. Si se excluyera Sumapaz, los umbrales
subirían entre +1.6% (HP, HC) y **+13.0% (VI)** — Violencia Intrafamiliar es el
más sensible. El efecto sobre el balance global es marginal porque la etiqueta es
un percentil dentro de cada tipo, pero puede mover filas urbanas fronterizas.

**`ipm_nbi` nulo de Sumapaz NO afecta esta etiqueta** (`riesgo_alto` depende solo
de `conteo_siedco`). La decisión de imputar o no `ipm_nbi` se deja explícitamente
a Integrante 2 como feature (ver Issue #12 / diccionario consolidado); aquí no se
imputa nada en silencio.

---

## 5. Estrategia de balanceo acordada

**Recomendación: `class_weight="balanced"` en el modelo (RF / Gradient Boosting).**

Justificación:

- El desbalance es **moderado (~3:1)**, no extremo. Con 385 positivos en 1.540
  filas hay señal suficiente sin sobre-muestrear.
- `class_weight="balanced"` penaliza el error en la clase minoritaria sin generar
  filas sintéticas → **sin riesgo de fuga espacio-temporal** que SMOTE sí puede
  introducir si se aplica mal (interpolar entre zonas-años distintos rompe el
  supuesto temporal). Para RF es directo y suele bastar.
- **SMOTE queda como plan B documentado:** si en #17 el recall de la clase de
  riesgo alto en test es insuficiente, aplicar SMOTE **solo sobre el fold de
  entrenamiento** (nunca sobre test ni antes del split temporal), o combinar
  SMOTE + `class_weight`. Debe reportarse como experimento comparado contra el
  baseline con `class_weight`.

---

## 6. Qué debe confirmar Integrante 2 antes de la Issue #17

- [ ] Acepta la definición **P75 por tipo de delito, umbral estricto** (o propone
      ajuste justificado antes de entrenar).
- [ ] Acepta `class_weight="balanced"` como estrategia base, con SMOTE como plan B
      documentado.
- [ ] Toma nota de que la **etiqueta test ya viene calculada** con umbrales de
      train y **no debe re-etiquetarse** (evitar fuga).
- [ ] Decide la **imputación de `ipm_nbi`** de Sumapaz como *feature* (no está
      resuelta aquí; `riesgo_alto` no depende de ella).
