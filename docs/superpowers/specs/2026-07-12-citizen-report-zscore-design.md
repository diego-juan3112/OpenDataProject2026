# Diseño — Reporte ciudadano simulado + flag z-score (Issue [CLUST] #36)

**Fecha:** 2026-07-12 · **Pista:** 3 — Clustering + Dashboard (Integrante 3, con Int. 4) · **Fase CRISP-ML:** 4–5

## Contexto

Issue #36 depende de #29 (`flag_zscore()`, completo) y #32 (scaffold del
dashboard, completo — y #33 ya agregó la geometría real de localidades que
esta issue reutiliza). No bloquea a nada más. Es el diferenciador
"reporte verificado contra el histórico" de CLAUDE.md §3.3: un formulario
que agrega un reporte ciudadano simulado (sin BD, `st.session_state`), lo
dibuja en el mapa, y lo evalúa contra la línea base histórica real con
`flag_zscore()`.

**Criterios de aceptación (del backlog):**
1. El formulario añade un punto a la sesión y lo renderiza en el mapa.
2. El reporte dispara el flag z-score y muestra resultado interpretable.
3. Validación de input (rechaza coords fuera de Bogotá; campos requeridos;
   no rompe ante input ruidoso/faltante).
4. Checkbox de consentimiento opt-in + enlace al aviso de privacidad (Ley
   1581/2012). **No se recorta.**

## Decisión de diseño: cada reporte se evalúa solo, con `conteo=1`

`flag_zscore()` compara un conteo contra la línea base **histórica anual**
(media/desviación de `conteo_siedco` por localidad-tipo, #26). Un reporte
ciudadano es 1 solo caso — no es comparable en escala a un promedio anual.
Se decidió (confirmado con el usuario) evaluar cada reporte de forma
independiente con `conteo=1` en el momento de enviarlo, en vez de acumular
un conteo de sesión, y mostrar el resultado con contexto honesto en vez de
una alerta genérica de "peligro". Verificado con datos reales:

- **Caso común** (`cod_localidad="01"` Usaquén, `tipo_delito="DS"`, media
  histórica real ≈296.4, desviación ≈67.6): `flag_zscore("01", "DS", 1,
  linea_base)` → `es_atipico=True`, `z_score≈-4.37`. Es **atípico por
  debajo** del promedio — 1 caso siempre lo será frente a un promedio anual
  de cientos. La UI debe explicar esto, no presentarlo como una alerta de
  riesgo.
- **Caso con historial nulo** (`cod_localidad="20"` Sumapaz,
  `tipo_delito="HA"`, media=0.0, desviación=0.0 — nunca hubo un caso en 7
  años de train): `flag_zscore("20", "HA", 1, linea_base)` →
  `es_atipico=True`, `z_score=None` (rama de `desviacion==0` de #29). Este
  **sí** es una señal genuina: "esto nunca había pasado aquí" — se resalta
  distinto en la UI que el caso común.

## Nuevo fixture real: `app/data/linea_base_zscore.json`

Extiende `app/data/generar_datasets_mapa.py` (#33) con una función más,
`_generar_linea_base()`, que llama a `calcular_linea_base()` (ya existente
en `src/feature_engineering.py`, #26) sobre `dataset_analitico.parquet` y
serializa las 220 filas (20 localidades × 11 tipos) reales a JSON —
commiteado, mismo patrón que los otros 4 archivos de `app/data/`.

## Decisión de diseño: reutilizar `src/flag_zscore.py` real, no reimplementar

`flag_zscore()` recibe `linea_base` como `pd.DataFrame`. `app/` hoy no tiene
`pandas` como dependencia (se mantuvo liviano en #32/#33, solo JSON plano).
Se decidió (confirmado con el usuario) **agregar `pandas` a
`app/requirements.txt`** y reutilizar la función real de #29 tal cual
(construyendo un `DataFrame` pequeño desde el fixture JSON antes de
llamarla), en vez de duplicar la lógica de z-score sin pandas. `pandas` ya
está instalado en el venv compartido — no hay costo real de instalación,
y evita mantener dos implementaciones de la misma fórmula.

## Ubicación por clic → localidad real: `app/localidad_lookup.py`

`shapely` (ya instalado como dependencia transitiva de `geopandas` en el
venv compartido, se agrega explícito a `app/requirements.txt`) hace el
point-in-polygon contra la geometría real de #33
(`app/data/geometria_localidades.geojson`). `ubicar_localidad(lat, lon,
geometria) -> str | None` devuelve `None` si el clic cae fuera de las 20
localidades — satisface el criterio "rechaza coords fuera de Bogotá".
Verificado con un punto real dentro de Usaquén (`lat=4.7452,
lon=-74.0279`, punto representativo real del polígono de la localidad
"01").

## Dónde vive el código

- **`app/data/generar_datasets_mapa.py`** (edita, #33 → #36): +
  `_generar_linea_base()`, + `app/data/linea_base_zscore.json` (220 filas).
- **`app/localidad_lookup.py`** (nuevo): `ubicar_localidad(lat, lon,
  geometria) -> str | None`, función pura (recibe la geometría ya cargada
  como parámetro, no lee archivos — mismo patrón de pureza que
  `models/clustering/clustering.py`), testeable contra la geometría real
  commiteada (igual que `tests/test_data_loader.py` en #33).
- **`app/reporte_ciudadano.py`** (nuevo):
  - `construir_reporte(cod_localidad, tipo_delito, descripcion, lat, lon,
    linea_base: list[dict]) -> dict` — función pura que arma el
    `DataFrame` y llama a `flag_zscore()` real (#29), devuelve un dict
    listo para `st.session_state` (datos del reporte + resultado del flag).
    Testeable con datos sintéticos de línea base (mismo patrón que
    `tests/test_flag_zscore.py`, #29).
  - Una función de UI (acoplada a Streamlit, sin test unitario, verificada
    por smoke test — mismo tratamiento que `streamlit_app.py`) que
    renderiza: el aviso de privacidad + checkbox de consentimiento
    (Ley 1581/2012, opt-in, bloquea el envío si no está marcado), el
    formulario (tipo de delito, descripción, ubicación tomada del último
    clic en el mapa), la validación (ubicación fuera de Bogotá, campos
    vacíos, clic aún no registrado), y el resultado interpretable tras
    enviar (distingue el caso común del caso de historial nulo, como se
    describe arriba).
- **`app/streamlit_app.py`** (edita): agrega un marcador
  (`folium.Marker`, ícono FontAwesome vía `prefix="fa"` — **sin emojis**,
  `triangle-exclamation` en rojo si `es_atipico`, `circle-check` en verde
  si no) por cada reporte en `st.session_state.reportes`, y llama a la
  función de UI del formulario después de renderizar el mapa (necesita el
  clic devuelto por `st_folium()` de la corrida anterior).
- **`app/requirements.txt`** (edita): + `pandas`, + `shapely` (versiones
  reales instaladas, no adivinadas — se capturan al implementar).

## Sin emojis (instrucción del usuario, aplica a todo el trabajo de UI)

Marcadores del mapa: `folium.Icon` con íconos FontAwesome
(`prefix="fa"`), no emoji. Encabezados/botones de Streamlit: shortcodes
`:material/...:` (soportados desde Streamlit 1.31+; confirmado en la
versión instalada, 1.59.1), no caracteres emoji.

## Fuera de alcance

Persistencia real (sigue en `st.session_state`, se pierde al cerrar
sesión — decisión de alcance ya fijada en CLAUDE.md §1, no de esta issue).
Sincronizar el patrón de aviso de privacidad con la app móvil de
Integrante 4 (aún no existe `mobile/`) — se documenta el texto usado aquí
para que Integrante 4 lo reutilice cuando llegue a su issue, pero no hay
nada que sincronizar todavía.
