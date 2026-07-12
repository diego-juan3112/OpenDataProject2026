# app/ — Dashboard Streamlit (Integrante 3)

Panel donde se exploran los resultados del análisis: mapa de riesgo por
zona, densidad de llamadas NUSE, y tipología de zonas por perfil delictivo.
El reporte ciudadano simulado con detección de anomalías por z-score llega
en la Issue #36.

## Cómo correr

```bash
.venv/Scripts/pip install -r app/requirements.txt
.venv/Scripts/streamlit run app/streamlit_app.py
```

Abre <http://localhost:8501>.

## Las 3 capas del mapa (Issue #33)

Los datos de las 3 capas son **reales**, no un mock (a diferencia del
scaffold inicial de la Issue #32, ya retirado — `app/mock_data/` no existe
más):

1. **Riesgo por zona**: colorea cada localidad según `riesgo_alto`
   (percentil 75 histórico de `conteo_siedco`, calculado en la Issue #10 —
   **no** es la probabilidad del modelo predictivo real, Issue #19, que
   Integrante 2 aún no ha implementado). El selector de año/tipo de delito
   del sidebar sí funciona: cambia de verdad el coroplético.
2. **Densidad NUSE**: llamadas al 123 por localidad, coloreadas con una
   escala continua. *Limitación conocida:* el dato abierto real trae
   resolución de UPZ (más fina que localidad), pero el pipeline nunca
   ingirió la geometría de esas UPZ (solo la de localidad, Issue #5) — la
   capa muestra el agregado a nivel localidad. Ingerir geometría real de UPZ
   queda como trabajo futuro para Integrante 1.
3. **Tipología de zonas**: colorea por el perfil de K-Means real (Issue
   #27), con tooltip en lenguaje no técnico.

La capa de riesgo siempre está visible (es la capa base); activa/desactiva
NUSE y tipología con los checkboxes del sidebar, no con un control flotante
sobre el mapa — mismo lugar que el resto de los controles (año, tipo de
delito), para una experiencia consistente.

## Datos: `app/data/`

Los 4 archivos en `app/data/*.json`/`*.geojson` están **commiteados** (a
diferencia de `data/`, que es gitignored) para que cualquiera del equipo
corra el dashboard sin haber corrido el pipeline completo. Se generaron una
sola vez con datos reales:

```bash
.venv/Scripts/python app/data/generar_datasets_mapa.py
```

(Requiere haber corrido `pipelines/pipeline_ml.py` y
`models/clustering/train.py` localmente — este script sí necesita
`pandas`/`geopandas`, vía el `requirements.txt` raíz del repo, no el de
`app/`. Solo hace falta regenerarlo si cambian los datos o el clustering
reales.)

La Issue #34 reemplaza `cargar_zonas_riesgo()` (en `app/data_loader.py`) por
una llamada real a `GET /zonas-riesgo` (Issue #20) — `cargar_densidad_nuse()`
se queda local para siempre, porque NUSE no forma parte del contrato de esa
API (ver `CLAUDE.md` §4).
