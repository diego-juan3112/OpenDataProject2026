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

## Las 3 capas del mapa (Issues #33, #34)

1. **Riesgo por zona**: colorea cada localidad según `nivel_riesgo`
   (`"bajo"|"medio"|"alto"`), calculado por el **modelo predictivo real**
   (Random Forest/XGBoost, Issue #19) y servido en vivo por
   `GET /zonas-riesgo` (Issue #20) — no hay ningún mock ni fixture local
   para esta capa desde la Issue #34. El selector de año/tipo de delito del
   sidebar re-consulta la API de verdad. Requiere que la API esté corriendo
   (`uvicorn api.main:app`, ver más abajo) — si no responde, el dashboard
   muestra un error claro en vez de romperse.
2. **Densidad NUSE**: llamadas al 123 por localidad, coloreadas con una
   escala continua. *Limitación conocida:* el dato abierto real trae
   resolución de UPZ (más fina que localidad), pero el pipeline nunca
   ingirió la geometría de esas UPZ (solo la de localidad, Issue #5) — la
   capa muestra el agregado a nivel localidad. Ingerir geometría real de UPZ
   queda como trabajo futuro para Integrante 1. Esta capa **no** viene de
   la API (NUSE no forma parte de su contrato, ver `CLAUDE.md` §4) — sigue
   leyendo el fixture local `app/data/nuse_por_zona.json`.
3. **Tipología de zonas**: colorea por el perfil de K-Means real (Issue
   #27), con tooltip en lenguaje no técnico — viene de la misma respuesta
   de `GET /zonas-riesgo` que la capa de riesgo.

## Cómo correr con la API real (Issue #34)

El dashboard necesita la API corriendo para la capa de riesgo/tipología:

```bash
# Terminal 1 — API (necesita los artefactos entrenados, ver api/README.md)
.venv/Scripts/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — dashboard
.venv/Scripts/pip install -r app/requirements.txt
.venv/Scripts/streamlit run app/streamlit_app.py
```

Por defecto el dashboard apunta a `http://localhost:8000`. Para apuntar a
otra URL (ej. la API corriendo en otra máquina de la red), define la
variable de entorno `ALERTA_API_URL` antes de correr `streamlit run`.

La capa de riesgo siempre está visible (es la capa base); activa/desactiva
NUSE y tipología con los checkboxes del sidebar, no con un control flotante
sobre el mapa — mismo lugar que el resto de los controles (año, tipo de
delito), para una experiencia consistente.

## Reporte ciudadano simulado (Issue #36)

Haz clic en el mapa para elegir una ubicación, acepta el aviso de
privacidad, elige el tipo de delito y escribe una descripción — el reporte
se evalúa contra la línea base histórica real (Issue #26) con
`flag_zscore()` (Issue #29) y aparece como marcador en el mapa. Todo vive
en `st.session_state`: no hay base de datos, se pierde al cerrar la
pestaña (ver `CLAUDE.md` §1).

**Cómo leer el resultado:** cada reporte se evalúa solo (`conteo=1`) contra
un promedio **histórico anual** — por eso casi siempre sale "por debajo del
promedio" (un solo reporte nunca es comparable en escala a un año
completo). Esto es normal y se explica en el mensaje, no es una alerta de
peligro. La excepción real es una localidad sin ningún historial para ese
tipo de delito: ahí un solo reporte sí es una señal genuina.

Requiere `pandas` y `shapely` (agregados a `app/requirements.txt` en esta
issue — ambos ya estaban instalados en el venv compartido del repo, vía la
dependencia de `geopandas` del pipeline).

## Datos: `app/data/`

Los 3 archivos en `app/data/*.json`/`*.geojson` están **commiteados** (a
diferencia de `data/`, que es gitignored) — los sigue necesitando la capa
NUSE (`geometria_localidades.geojson`, `nuse_por_zona.json`) y el reporte
ciudadano (`linea_base_zscore.json`, Issue #36). La capa de riesgo/tipología
ya **no** usa un fixture local (retirado en la Issue #34) — viene de la API
real. Se generan una sola vez con datos reales:

```bash
.venv/Scripts/python app/data/generar_datasets_mapa.py
```

(Requiere haber corrido `pipelines/pipeline_ml.py` y
`models/clustering/train.py` localmente — este script sí necesita
`pandas`/`geopandas`, vía el `requirements.txt` raíz del repo, no el de
`app/`. Solo hace falta regenerarlo si cambian los datos o el clustering
reales.)
