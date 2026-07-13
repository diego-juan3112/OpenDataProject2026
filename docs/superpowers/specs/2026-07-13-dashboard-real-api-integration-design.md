# Diseño — Integrar la API real en el dashboard (Issue [CLUST] #34)

**Fecha:** 2026-07-13 · **Pista:** 3 — Clustering + Dashboard (Integrante 3) · **Fase CRISP-ML:** 5

## Contexto

Issue #34 depende de #20 (API real `GET /zonas-riesgo`, de Integrante 2,
completo) y #33 (capas del mapa, completo) y bloquea a #40 (app móvil).
Reemplaza la última pieza "mock" que queda en el dashboard: hasta ahora
`cargar_zonas_riesgo()` sintetizaba geometría + riesgo + cluster desde
fixtures locales (`app/data/riesgo_por_zona.json`,
`app/data/tipologia_zonas.json`, generados en #33 a partir de
`riesgo_alto`, un proxy propio basado en percentil histórico). Ahora que la
API real de Integrante 2 sirve el modelo predictivo entrenado de verdad
(`nivel_riesgo`, `probabilidad_riesgo`), el dashboard debe consumir esa API
en vez de seguir sintetizando su propio proxy.

**Criterios de aceptación (del backlog):**
1. El mapa de riesgo y la tipología se alimentan del endpoint real.
2. GeoJSON cacheado (`@st.cache_data`), no re-pedido por cada interacción.
3. Prueba end-to-end: API → dashboard lo refleja. Sin mocks.

## Verificación real del contrato de la API (hecha antes de diseñar)

Se instalaron las dependencias de la API (`fastapi`, `uvicorn`,
declaradas en el `requirements.txt` raíz pero no instaladas localmente) y
se levantó `uvicorn api.main:app` de verdad contra los artefactos reales
(`model.joblib` generado en la QA de #30, `clusters.joblib` de #27,
`zonas_bogota.geojson` de #5) — los 5 archivos que necesita ya existían
localmente. Respuesta real confirmada:

```
GET /health
{"status":"ok","modelo":"xgboost","anios":[2018..2025],"tipos":[11 códigos],"n_zonas":20}

GET /zonas-riesgo?anio=2025&tipo=HP
FeatureCollection, 20 features. properties de la primera:
{"cod_localidad":"01","localidad_nombre":"USAQUEN","cod_dane_mpio":"11001",
 "cluster":0,"nombre_perfil":"Perfil de bajo incidente relativo",
 "nivel_riesgo":"medio","probabilidad_riesgo":0.4354,"riesgo_predicho":0,
 "anio":2025,"tipo_delito":"HP","tipo_delito_nombre":"Hurto Personas"}
```

Esto **no coincide** con lo que el dashboard usaba desde #33
(`riesgo_alto` 0/1, `conteo_siedco`) — el contrato real de #20 usa
`nivel_riesgo` (3 niveles: bajo/medio/alto, ya calculado por
`api/state.py::_nivel_riesgo()` a partir de `probabilidad_riesgo` y el
umbral del modelo) y no expone `conteo_siedco` en absoluto. La capa de
riesgo del mapa debe rediseñarse sobre estos campos reales.

## Decisión: retirar los fixtures de riesgo/tipología, no la geometría ni NUSE

`app/data/riesgo_por_zona.json` y `app/data/tipologia_zonas.json` (y las
funciones `_generar_riesgo()`/`_generar_tipologia()` de
`generar_datasets_mapa.py`, #33) quedan **obsoletos**: la API real ahora
sirve geometría + riesgo + cluster en una sola respuesta. Se retiran
(confirmado con el usuario), mismo patrón que #33 retiró el mock de #32.

**Se mantienen** `app/data/geometria_localidades.geojson` (la capa NUSE
sigue necesitando geometría local, ya que NUSE no lo sirve la API — ver
`CLAUDE.md` §4: NUSE no forma parte del contrato de `/zonas-riesgo`) y
`app/data/nuse_por_zona.json` + `app/data/linea_base_zscore.json` (el
reporte ciudadano de #36 sigue usando la línea base local).

## Dónde vive el código

- **`app/data_loader.py`** (edita): `cargar_zonas_riesgo(anio: int,
  tipo_delito: str) -> dict` reemplaza su cuerpo por
  `requests.get(f"{API_BASE_URL}/zonas-riesgo", params={"anio": anio,
  "tipo": tipo_delito}, timeout=10)`, valida `response.raise_for_status()`
  y devuelve `response.json()`. Decorada con `@st.cache_data(ttl=300)`
  (5 min — cachea entre interacciones del sidebar, pero no indefinidamente,
  para que un reinicio de la API con un modelo nuevo se refleje sin tener
  que reiniciar todo el dashboard). Si la petición falla (API caída,
  timeout, JSON inválido), se relanza como una excepción clara
  (`RuntimeError` con mensaje legible) que `streamlit_app.py` atrapa y
  muestra con `st.error`, sin tumbar la app.
  `API_BASE_URL` viene de una variable de entorno (`ALERTA_API_URL`,
  default `"http://localhost:8000"`) — mismo patrón que usará la app móvil
  para apuntar a la IP de LAN (`CLAUDE.md` §4).
  `cargar_densidad_nuse()`, `cargar_linea_base()` y `_cargar_geometria()`
  (privada, para NUSE) **no cambian** — siguen leyendo fixtures locales.
- **`app/data/generar_datasets_mapa.py`** (edita): se eliminan
  `_generar_riesgo()`, `_generar_tipologia()`, sus constantes de ruta y su
  llamada en `run()`. Quedan `_generar_geometria()`, `_generar_nuse()`,
  `_generar_linea_base()`.
- **Eliminar:** `app/data/riesgo_por_zona.json`,
  `app/data/tipologia_zonas.json`.
- **`app/streamlit_app.py`** (edita): la capa de riesgo pasa de 2 colores
  (`riesgo_alto` 0/1) a **3 colores reales** por `nivel_riesgo`
  (bajo=verde, medio=amarillo, alto=rojo — mismo estilo de colores que la
  capa de tipología ya usa, 3 tonos). Tooltip actualizado a
  `nivel_riesgo`, `probabilidad_riesgo`, `tipo_delito_nombre` (campos
  reales de la API). Envuelve la llamada a `cargar_zonas_riesgo()` en un
  `try/except` que muestra `st.error()` con un mensaje claro
  ("¿Está corriendo la API en `{API_BASE_URL}`?") si la API no responde,
  en vez de dejar que la excepción tumbe toda la app.
- **`app/requirements.txt`** (edita): + `requests==2.34.2` (ya instalado
  en el venv compartido, dependencia real de Integrante 1 en el
  `requirements.txt` raíz).
- **`app/README.md`** (edita): documenta cómo levantar API + dashboard
  juntos para la demo, la variable `ALERTA_API_URL`, y quita las secciones
  que describían el mock de riesgo/tipología (ya no aplican).

## Prueba end-to-end (criterio 3)

Se hace levantando **ambos procesos**: `uvicorn api.main:app` (puerto
8000) y `streamlit run app/streamlit_app.py` (puerto 8501) al mismo
tiempo, y confirmando que una petición HTTP real a la API con un
`anio`/`tipo` específico devuelve el mismo `nivel_riesgo`/
`probabilidad_riesgo` que aparece en la respuesta de
`cargar_zonas_riesgo()` invocada por el dashboard — no basta con que
ambos arranquen por separado sin errores.

## Fuera de alcance

Cambiar el contrato de la API (#20 ya está cerrado, cualquier cambio de
campos se coordinaría con Integrante 2 aparte). Geofencing / consumo desde
la app móvil (#40, de Integrante 4). El modo demo con ubicación simulada
(trabajo futuro de la app móvil, no de este issue).
