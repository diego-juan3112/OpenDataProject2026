# Diseño — Scaffold del dashboard + consumo de `/zonas-riesgo` con mock (Issue [CLUST] #32)

**Fecha:** 2026-07-11 · **Pista:** 3 — Clustering + Dashboard (Integrante 3) · **Fase CRISP-ML:** 5

## Contexto

Issue #32 no depende de nada ("mock al inicio") y bloquea a #33 (capas del
mapa), #34 (integrar la API real) y #36 (reporte ciudadano). Es el primer
código de `app/` en el repo — hoy `app/` no existe en disco (confirmado con
`Glob`). El objetivo es levantar el dashboard Streamlit con un mapa Folium
base de Bogotá y una función de carga de datos con la forma que tendrá
`GET /zonas-riesgo` (#20, Integrante 2, aún no implementado), usando un
**mock** para no bloquear el trabajo de Integrante 3 con el de Integrante 2.

**Criterios de aceptación (del backlog):**
1. `streamlit run app/streamlit_app.py` levanta y muestra el mapa base de
   Bogotá.
2. Función de carga del GeoJSON (mock con el shape acordado en #20).
3. Layout base (sidebar de controles + área de mapa) + README de cómo correr.

## Decisión de diseño: fixture estática commiteada, no datos sintéticos

`app/` (dashboard) es un cliente nuevo que cualquier integrante del equipo
debe poder correr sin haber corrido el pipeline completo de datos (`data/` es
gitignored — confirmado en `.gitignore` y en `CLAUDE.md` §8). Se generó un
fixture **una sola vez**, ahora, combinando:

- **Geometría + identidad reales** de `data/03_primary/zonas_bogota.geojson`
  (#5): 20 localidades, `Polygon`, **EPSG:4326** (verificado con GeoPandas —
  compatible directo con Folium, que espera WGS84), propiedades
  `cod_localidad`, `localidad_nombre`, `cod_dane_mpio`.
- **Cluster + perfil reales** de `models/clustering/zona_cluster.parquet`
  (#27): `cluster`, `nombre_perfil` (verificado: 12 "bajo incidente relativo",
  6 "hurto de bienes / ingreso alto", 2 "alto impacto generalizado").
- **Riesgo FALSO** (`nivel_riesgo`, `probabilidad_riesgo`): el predictivo
  (#19, Integrante 2) no existe todavía. Se deriva del perfil de cluster real
  (alto impacto → `"alto"`, hurto de bienes → `"medio"`, bajo incidente →
  `"bajo"`) más un jitter determinístico (semilla fija) para que
  `probabilidad_riesgo` no sea un valor idéntico repetido 12/6/2 veces. Se
  documenta explícitamente como mock en el docstring del generador y en el
  README — nadie debe confundirlo con una predicción real.
- **Metadatos de consulta fijos**: `anio=2025`, `tipo_delito="HP"` (Hurto
  Personas, código real de `src/config.py::SIEDCO_TIPOS`) — la variación por
  parámetro es responsabilidad de #34 cuando se integre la API real, no de
  este scaffold.

El resultado se serializa una vez a
`app/mock_data/zonas_riesgo_mock.geojson` y **se commitea al repo** (a
diferencia de `data/`), junto con el script que lo generó
(`app/mock_data/generar_mock.py`, reproducible, documentado, no se corre
automáticamente en cada `streamlit run`).

## Dónde vive el código

```
app/
├── streamlit_app.py               # entrypoint: sidebar + mapa Folium
├── data_loader.py                 # cargar_zonas_riesgo() -> dict (GeoJSON), @st.cache_data
├── requirements.txt                # streamlit, streamlit-folium, folium
├── README.md                      # como correr
└── mock_data/
    ├── generar_mock.py            # regenera el fixture desde los pipelines reales de #5/#27
    └── zonas_riesgo_mock.geojson  # fixture commiteado, consumido por data_loader.py
```

- **`app/data_loader.py`**: `cargar_zonas_riesgo() -> dict` — lee
  `zonas_riesgo_mock.geojson` desde disco (ruta relativa al módulo, no a
  `cwd`), decorada con `@st.cache_data`. Única función que #34 reemplazará
  por una llamada HTTP real a `GET /zonas-riesgo` — mismo nombre y misma
  forma de retorno (`dict` GeoJSON), para que el resto de `streamlit_app.py`
  no cambie cuando eso pase.
- **`app/streamlit_app.py`**: `st.set_page_config`, sidebar con selectores de
  año (2018–2025) y tipo de delito (`SIEDCO_TIPOS` de `src/config.py`, solo
  UI por ahora — el mock no varía por parámetro), y un mapa Folium
  (`streamlit_folium.st_folium`) centrado en Bogotá con las 20 zonas del mock
  como capa `folium.GeoJson`, coloreadas por `nivel_riesgo`
  (bajo=verde/medio=amarillo/alto=rojo, `style_function` simple) y tooltip
  con `localidad_nombre` + `nombre_perfil`. **No** se construye todavía el
  sistema completo de capas (leyenda pulida, densidad NUSE, control de
  capas) — eso es #33.
- **`app/mock_data/generar_mock.py`**: script standalone, sigue el patrón de
  los orquestadores de `models/clustering/` (`build_features.py`,
  `train.py`): lee los 2 artefactos reales de arriba, construye el GeoJSON
  combinado + riesgo derivado, escribe `zonas_riesgo_mock.geojson`, imprime
  un resumen de verificación (20 features, distribución de `nivel_riesgo`).
- **`app/requirements.txt`**: `streamlit`, `folium`, `streamlit-folium`
  (ninguno está en el `requirements.txt` raíz — es del pipeline de datos,
  Integrante 1).
- **`app/README.md`**: instrucciones — instalar `app/requirements.txt`,
  `streamlit run app/streamlit_app.py`, nota de que el riesgo es mock hasta
  #34.

## Fuera de alcance

Capas NUSE, leyenda de riesgo pulida y control de capas (#33); integración
con la API real (#34); formulario de reporte ciudadano (#36). El sidebar
lleva los selectores de año/tipo pero no filtra nada todavía (el mock es
estático) — se conecta de verdad en #34.
