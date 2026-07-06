# Handoff — Frente de Datos (Integrante 1)
**Issues cerradas:** #1–#12 · **Fecha:** 2026-07-06 · **Estado:** ✅ Completo

Documento de entrega del frente de Datos. En 5 minutos deja al equipo lo que
necesita para arrancar sin preguntarle nada a Integrante 1: qué archivos existen,
cómo se usan, qué decisiones tomadas les afectan y qué falta decidir. No repite
`CLAUDE.md` ni `README.md`.

## Lo que entrego

| Archivo | Ruta | Para quién |
|---|---|---|
| Dataset analítico | `data/03_primary/dataset_analitico.parquet` | Int. 2 (modelo), Int. 3 (clustering) |
| Geometría de zonas | `data/03_primary/zonas_bogota.geojson` | Int. 2 (API), Int. 3 (dashboard), Int. 4 (app) |
| Diccionario de datos | `docs/data_dictionary.md` | Todo el equipo |
| Fuentes de datos | `docs/fuentes_datos.md` | Todo el equipo (informe) |
| Variable objetivo | `docs/data-dictionaries/variable_objetivo.md` | Int. 2 (antes de #17) |
| EDA de calidad | `notebooks/01_EDA_exploracion_datos.ipynb` | Int. 3 (auditoría #31) |

> Los dos artefactos de `data/03_primary/` **no están versionados** (`data/` está
> en `.gitignore`). Se regeneran con el pipeline (ver más abajo).

## Cómo cargar el dataset analítico

```python
import pandas as pd

df = pd.read_parquet("data/03_primary/dataset_analitico.parquet")
assert list(df.columns) == [
    "cod_localidad", "localidad_nombre", "anio", "tipo_delito", "tipo_delito_nombre",
    "conteo_siedco", "conteo_nuse", "poblacion", "ipm_nbi", "split", "riesgo_alto",
]
train = df[df["split"] == "train"].copy()   # 1.540 filas (2018–2024) — usar para entrenar/clustering
test  = df[df["split"] == "test"].copy()    # 220 filas (2025) — solo evaluación final (#17)
print(df.shape)                             # (1760, 11)
df.head()
```

## Cómo regenerar todo desde cero

```bash
python pipelines/pipeline_ml.py
```

Reproduce **ambos** artefactos (`dataset_analitico.parquet` + `zonas_bogota.geojson`)
de punta a punta: limpieza → cruce por código DANE → split sin fuga → variable
objetivo `riesgo_alto`. Es idempotente y verifica sus propias salidas al final.

- **Requisitos previos:** los insumos de ingesta deben existir en
  `data/02_intermediate/` (`siedco_delitos.parquet`, `nuse_incidentes.parquet`,
  `localidades.geojson`, `dane_contexto.parquet`). Si falta `dane_contexto`, el
  pipeline lo genera al vuelo. Para bajar los crudos desde cero, correr antes los
  `src/ingest_*.py` (ver `docs/fuentes_datos.md`; NUSE descarga ~112 MB).
- **Tiempo estimado:** el pipeline en sí corre en **segundos** (opera sobre los
  intermedios ya descargados). Las ingestas iniciales tardan más por la descarga
  de NUSE.
- **Dependencias:** `pip install -r requirements.txt` (incluye `matplotlib`/`seaborn`
  para el notebook de EDA).

## Decisiones que afectan tu trabajo

### Para Integrante 2 (Predictivo + API)
- La columna `riesgo_alto` **ya viene en el parquet — no la recalcules.**
- Los umbrales están en `src/feature_engineering.py::umbrales_riesgo()` (P75 del
  `conteo_siedco` del mismo tipo de delito, aprendido solo de train).
- `ipm_nbi` es **NULL en Sumapaz (88 filas)** — decide si imputas o excluyes **antes
  de #17**. La sensibilidad está documentada en `variable_objetivo.md`.
- En **test solo el 14.1%** de las filas son positivas (vs 25% en train). Es correcto
  y **sin fuga**: los umbrales se calcularon solo con train. Tenlo en cuenta al
  configurar las métricas de evaluación (recall/F1 de la clase de riesgo alto).
- **Lee `variable_objetivo.md` completo y confirma las decisiones marcadas ahí antes
  de empezar #17** (definición del target, `class_weight="balanced"`, imputación de
  Sumapaz).

### Para Integrante 3 (Clustering + Dashboard)
- El dataset tiene exactamente **20 localidades × 11 tipos × 8 años = 1.760 filas**.
- Para clustering, usa las filas **`train` (1.540 filas, 2018–2024)**.
- **Sumapaz (cod 20)** tiene `ipm_nbi` nulo — documenta cómo lo tratas en el
  clustering (incluir, excluir, o imputar con la mediana).
- El EDA (#11) identificó que **las zonas pobres tienen más violencia interpersonal
  pero NO más hurto de bienes**. El clustering debería capturar esa asimetría si se
  incluye `ipm_nbi` como feature.
- La **nota de sesgo de sobre-vigilancia** está en el notebook — úsala directamente
  como insumo para la auditoría ética (#31).

### Para Integrante 4 (App móvil)
- `zonas_bogota.geojson` está en **EPSG:4326 (WGS84)** — el formato correcto para web
  y móvil. **No requiere reproyección.**
- El archivo tiene **3 campos por polígono**: `cod_localidad`, `localidad_nombre`,
  `cod_dane_mpio`. Los campos `riesgo` y `cluster` los añade la **API (Int. 2)** una
  vez que existan los modelos.
- Mientras la API no esté lista, usa el GeoJSON con **valores mock de riesgo** para
  construir el mapa.

## Lo que NO está resuelto (debes decidirlo tú)

- **Imputación de Sumapaz** (Int. 2, antes de #17): imputar la mediana de `ipm_nbi`
  o excluir Sumapaz del entrenamiento. Impacto documentado en `variable_objetivo.md`.
- **Umbral de `riesgo_alto` para el score de ruta** (Int. 2, issue #R2 / #46): el
  percentil P75 por tipo define la etiqueta del clasificador, pero el **score continuo**
  de la feature de ruta segura necesita un agregado distinto. Ver
  `diseño_tecnico_ruta_segura.md` §PARTE 3.
- **Tratamiento de Sumapaz en clustering** (Int. 3): incluir, excluir, o tratar como
  su propio cluster. Documentar la decisión en #27.

## Sesgos identificados — leer antes de modelar

> Los datos oficiales de criminalidad no retratan dónde ocurre el delito, sino dónde
> el Estado lo registra. En Bogotá, el delito registrado crece junto con las llamadas
> al 123 (correlación 0,92) y se concentra en zonas comerciales de alta afluencia como
> Chapinero y La Candelaria, donde la tasa de delitos registrados por llamada de
> emergencia supera la unidad; en cambio, en el sur residencial y más pobre —San
> Cristóbal, Usme, Rafael Uribe— abundan las llamadas pero se registran
> proporcionalmente menos delitos, señal de subregistro. Además, la pobreza se asocia
> con más violencia interpersonal (homicidio +0,60; violencia intrafamiliar +0,36)
> pero no con más hurto de bienes (automotores −0,19). Un modelo entrenado sin cuidado
> aprendería el mapa de la vigilancia y del registro, no el de la victimización real,
> y estigmatizaría barrios enteros. Por eso el riesgo se modela por tipo de delito y
> su uso exige lectura contextual, no punitiva.

Análisis completo (4 secciones, figuras e interpretación) en
`notebooks/01_EDA_exploracion_datos.ipynb`.
