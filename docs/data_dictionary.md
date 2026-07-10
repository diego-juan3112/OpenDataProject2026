# Diccionario de datos — `dataset_analitico.parquet`

**Grano:** una fila por `(cod_localidad × anio × tipo_delito)`
**Filas:** 1.760 (20 localidades × 11 tipos de delito × 8 años, 2018–2025)
**Columnas:** 10 + 1 (variable objetivo `riesgo_alto` añadida en #10)
**Generado por:** `python pipelines/pipeline_ml.py` (reproducible)
**Salida:** `data/03_primary/dataset_analitico.parquet`

Este es el **contrato de datos** que consumen Integrante 2 (predictivo/API) e
Integrante 3 (clustering/dashboard). El diccionario por fuente de origen está en
[`data-dictionaries/`](data-dictionaries/) (uno por fuente + reporte de calidad).

| Columna | Tipo | Descripción | Dominio | Notas |
|---|---|---|---|---|
| `cod_localidad` | str(2) | Código de localidad de Bogotá | `"01"`–`"20"` | **Llave de cruce por DANE** (string con cero a la izquierda). No cruzar por nombre. |
| `localidad_nombre` | str | Nombre de referencia de la localidad | 20 nombres | Solo para lectura/tooltips; **no usar para joins** (varía entre fuentes). |
| `anio` | int | Año del registro | 2018–2025 | Grano temporal del proyecto (no hay hora en el dato abierto). |
| `tipo_delito` | str | Código SIEDCO del delito | `H, LP, HP, HR, HA, HB, HC, HCE, HM, DS, VI` | Ver tabla de tipos abajo. |
| `tipo_delito_nombre` | str | Nombre legible del delito | — | Derivado de `tipo_delito` vía `config.SIEDCO_TIPOS`. |
| `conteo_siedco` | int | Casos oficiales SIEDCO (delito de alto impacto) | 0–17.656 | Fuente: SIEDCO (Sec. Seguridad Bogotá). Backbone del modelo. |
| `conteo_nuse` | int | Llamadas al 123 en esa localidad-año | 0–390.921 | Fuente: NUSE C4. Señal complementaria; cero = sin llamadas registradas (cero estructural). |
| `poblacion` | int | Habitantes proyectados de la localidad | 3.172–1.251.652 | Fuente: proyección SDP/DANE (base Censo 2018). Se repite por año. |
| `ipm_nbi` | float | % de pobreza multidimensional (IPM, Censo 2018) | 0.68–13.95 | **NULL en Sumapaz (cod 20): no cubierta por la Encuesta Multipropósito. 88 filas nulas. Imputación opcional — ver [`variable_objetivo.md`](data-dictionaries/variable_objetivo.md).** Variable estructural (mismo valor en todos los años). |
| `split` | str | Partición espacio-temporal del modelo | `"train"` / `"test"` | Sin fuga: `train` = 2018–2024 (1.540 filas), `test` = 2025 (220 filas). |
| `riesgo_alto` | int | **Variable objetivo** del predictivo (añadida en #10) | 0 / 1 | **Umbral: P75 del `conteo_siedco` del mismo tipo de delito en train. Ver [`variable_objetivo.md`](data-dictionaries/variable_objetivo.md). En test: 14.1% de positivos (vs 25% en train — documentado, sin fuga).** |

## Tabla de tipos de delito (`tipo_delito`)

| Código | Nombre |
|---|---|
| `H`   | Homicidios |
| `LP`  | Lesiones Personales |
| `HP`  | Hurto Personas |
| `HR`  | Hurto Residencias |
| `HA`  | Hurto Automotores |
| `HB`  | Hurto Bicicletas |
| `HC`  | Hurto Comercio |
| `HCE` | Hurto Celulares |
| `HM`  | Hurto Motocicletas |
| `DS`  | Delitos Sexuales |
| `VI`  | Violencia Intrafamiliar |

## Diccionarios por fuente de origen

| Fuente / tabla | Diccionario |
|---|---|
| SIEDCO — Delito de Alto Impacto | [`data-dictionaries/siedco.md`](data-dictionaries/siedco.md) |
| NUSE — C4 / Línea 123 | [`data-dictionaries/nuse.md`](data-dictionaries/nuse.md) |
| Localidad — geometría oficial | [`data-dictionaries/localidad.md`](data-dictionaries/localidad.md) |
| Policía Nacional (API datos.gov.co) | [`data-dictionaries/datosgov_policia.md`](data-dictionaries/datosgov_policia.md) |
| Contexto DANE/SDP (población + IPM) | [`data-dictionaries/dane_contexto.md`](data-dictionaries/dane_contexto.md) |
| Variable objetivo `riesgo_alto` (#10) | [`data-dictionaries/variable_objetivo.md`](data-dictionaries/variable_objetivo.md) |
| Features de zona + línea base z-score (#26) | [`data-dictionaries/features_clustering.md`](data-dictionaries/features_clustering.md) |
| Reporte de calidad (Issue #7) | [`data-dictionaries/reporte_calidad.md`](data-dictionaries/reporte_calidad.md) |
