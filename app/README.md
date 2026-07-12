# app/ — Dashboard Streamlit (Integrante 3)

Panel donde se exploran los resultados del análisis: mapa de riesgo por zona
(hoy con datos de ejemplo — ver nota abajo), tipología de zonas por perfil
delictivo (Issue #33) y reporte ciudadano simulado con detección de
anomalías por z-score (Issue #36).

## Cómo correr

```bash
.venv/Scripts/pip install -r app/requirements.txt
.venv/Scripts/streamlit run app/streamlit_app.py
```

Abre <http://localhost:8501>.

## Estado (Issue #32 — scaffold)

El mapa hoy usa **datos de ejemplo** (`app/mock_data/zonas_riesgo_mock.geojson`),
no el modelo predictivo real: la geometría y la tipología de cluster son
reales (de `data/03_primary/zonas_bogota.geojson` y
`models/clustering/zona_cluster.parquet`), pero el nivel de riesgo se derivó
del perfil de cluster con una regla simple, no del modelo Random
Forest/Gradient Boosting (Issue #19, Integrante 2 — aún no implementado). No
requiere correr el pipeline de datos ni instalar `geopandas`: el fixture ya
está commiteado en `app/mock_data/`.

Para regenerar el fixture (si cambia el clustering o la geometría real):

```bash
.venv/Scripts/python app/mock_data/generar_mock.py
```

(Requiere haber corrido `pipelines/pipeline_ml.py` y
`models/clustering/train.py` localmente — este script sí necesita
`geopandas`, vía el `requirements.txt` raíz del repo, no el de `app/`.)

La Issue #34 reemplaza el mock por una llamada real a `GET /zonas-riesgo`
(Issue #20) dentro de `app/data_loader.py`, sin tocar el resto del
dashboard.
