# Diseño — Capas del mapa: coroplético de riesgo + puntos NUSE + tipología (Issue [CLUST] #33)

**Fecha:** 2026-07-11 · **Pista:** 3 — Clustering + Dashboard (Integrante 3) · **Fase CRISP-ML:** 5

## Contexto

Issue #33 depende de #5 (geometría real de localidades, completo), #27
(K-Means real, completo) y #32 (scaffold del dashboard con mock, completo) y
bloquea a #34 (integrar la API real). A diferencia de #32 (donde nada real
existía aún para "riesgo"), hoy sí hay una señal de riesgo real
(`riesgo_alto`, calculada en #10 dentro de `dataset_analitico.parquet`) y una
tipología real (#27), así que este issue reemplaza el mock del scaffold por
las 3 capas reales, en vez de seguir mostrando datos inventados.

**Criterios de aceptación (del backlog):**
1. Coroplético colorea las localidades por riesgo, con selector de año/tipo
   de delito y leyenda + tooltip por localidad.
2. Capa de densidad NUSE activable, coloreada por volumen de llamadas por
   localidad/UPZ (sin puntos, porque el dato es agregado).
3. Capa de tipología que colorea las zonas por cluster con la etiqueta de
   perfil (#27) y tooltip en lenguaje no técnico.

## Hallazgo real que reencuadra el criterio 2: no existe geometría de UPZ

`CLAUDE.md` describe la capa NUSE como "resolución más fina que la
localidad" (UPZ), pero se verificó que **ningún archivo del pipeline (ni
`data/02_intermediate/`, ni `data/03_primary/`) contiene geometría de UPZ** —
solo la de localidad (20 polígonos, de #5). La issue #5 (ya cerrada) nunca
ingirió límites de UPZ, aunque el documento maestro asumía que existirían.
Sin polígonos no hay coroplético real a nivel UPZ.

**Decisión (confirmada con el usuario):** la capa NUSE se agrega a nivel
**localidad** (mismos 20 polígonos que las otras 2 capas), sumando los
incidentes de todas las UPZ de cada localidad. Sigue siendo dato real y
filtrable por año — solo a menor resolución de la originalmente prevista. Se
documenta la limitación honestamente en el código/README; ingerir geometría
real de UPZ queda como trabajo futuro para Integrante 1 (fuera de alcance de
#33).

## Calidad de datos verificada en `nuse_incidentes.parquet` (763,074 filas)

- **Códigos de localidad inválidos**: `"99"` (SIN LOCALIZACIÓN, 7,128 filas)
  y `"-0"` (basura, 13 filas) — 7,141 filas en total (0.94%) no corresponden
  a ninguna de las 20 localidades reales. Se excluyen antes de agregar.
- **Cero estructural real**: tras excluir los códigos inválidos y agregar por
  `(cod_localidad, anio)`, quedan 159 combinaciones en vez de las 160
  esperadas (20 × 8 años) — **Sumapaz (`cod_localidad="20"`) no tiene ningún
  incidente NUSE registrado en 2018**. Mismo patrón ya documentado en el
  pipeline real (`pipeline_integration.py`: "una combinación localidad-año
  ausente en NUSE es un cero estructural, no un dato faltante") — se rellena
  con `conteo_nuse=0`, no se descarta la localidad.

## Decisión de diseño: separar geometría de atributos, todo real y commiteado

En #32 el mock horneaba geometría + un único escenario de riesgo en un solo
archivo estático. Aquí, con 3 capas reales y un selector de año/tipo que debe
funcionar de verdad, eso no escala: se separa la **geometría** (no cambia
nunca) de los **atributos** (varían por año/tipo), y el mapa combina ambos en
tiempo de render según la selección del usuario — mismo patrón que un SIG
real. Los 4 archivos resultantes son pequeños (miles de filas, no millones)
y se generan una sola vez con datos reales, luego se commitean:

```
app/data/
├── generar_datasets_mapa.py       # regenera los 4 archivos desde data/ y models/ reales
├── geometria_localidades.geojson  # 20 polígonos reales (simplificados, ~50KB, mismo patrón que #32)
├── riesgo_por_zona.json           # real: 1760 filas (20 localidades x 8 años x 11 tipos)
├── tipologia_zonas.json           # real: 20 filas (de zona_cluster.parquet, #27)
└── nuse_por_zona.json             # real: 160 filas (20 localidades x 8 años, con el cero estructural de Sumapaz)
```

JSON plano (lista de dicts), no parquet — así `app/requirements.txt` sigue
sin necesitar `pandas`/`geopandas` en tiempo de ejecución (esas librerías
solo las usa el generador, que corre en el venv raíz, igual que
`generar_mock.py` en #32). Verificado con datos reales: `riesgo_alto` tiene
416 casos "alto" de 1760 filas totales (~23.6%, consistente con el umbral
P75 de #10); para el corte real `anio=2025, tipo_delito="HP"` (Hurto
Personas), 3 de 20 localidades salen en riesgo alto (Kennedy, Engativá,
Suba).

**Reemplaza y retira el mock de #32**: se elimina `app/mock_data/`
(generador + fixture) — ya no lo usa nada, el propio `app/README.md` de #32
documentaba que #34 (no #33) sería quien reemplazara el mock, pero como
ahora ya existen los datos reales que #32 fabricaba, tiene más sentido
reemplazarlo aquí que mantener dos fuentes de "riesgo" (una inventada, una
real) coexistiendo.

## Dónde vive el código

- **`app/data/generar_datasets_mapa.py`** (nuevo, orquestador — mismo patrón
  que `generar_mock.py` de #32): lee `data/03_primary/dataset_analitico.parquet`
  (`cod_localidad, anio, tipo_delito, riesgo_alto, conteo_siedco`),
  `models/clustering/zona_cluster.parquet` (#27), `data/02_intermediate/nuse_incidentes.parquet`
  (excluye códigos inválidos, agrega por localidad-año, rellena cero
  estructural) y `data/03_primary/zonas_bogota.geojson` (simplifica y
  corrige el mismo mojibake de "ANTONIO NARIÑO" que #32 ya corrigió — mismo
  bug, mismo parche local, documentado igual). Escribe los 4 archivos de
  arriba con verificación de forma (assert de shapes/conteos).
- **`app/data_loader.py`** (edita — reemplaza la función de #32):
  - `cargar_zonas_riesgo(anio: int, tipo_delito: str) -> dict` (GeoJSON):
    combina `geometria_localidades.geojson` + el slice de `riesgo_por_zona.json`
    para `(anio, tipo_delito)` + `tipologia_zonas.json` completo (no varía
    por año/tipo). Mismo nombre y misma forma que tendrá el contrato real de
    `GET /zonas-riesgo` (#20, ver `CLAUDE.md` §4) — **única función que #34
    reemplaza**, ahora parametrizada de verdad (en #32 no tomaba parámetros
    porque el mock era estático).
  - `cargar_densidad_nuse(anio: int) -> dict` (GeoJSON): geometría +
    `conteo_nuse` de `nuse_por_zona.json` para ese año. NUSE **no** forma
    parte del contrato de `/zonas-riesgo` según `CLAUDE.md` (es una capa
    propia del dashboard) — se queda local para siempre, `#34` no la toca.
  - Ambas decoradas con `@st.cache_data`.
- **`app/streamlit_app.py`** (edita): los selectores de año/tipo del sidebar
  (ya existían en #32, sin efecto) ahora alimentan `cargar_zonas_riesgo`.
  3 capas Folium con `folium.LayerControl()`:
  1. **Riesgo** (activa por defecto): 2 colores por `riesgo_alto`
     (rojo=alto, verde=no), leyenda fija, tooltip con `localidad_nombre`,
     `conteo_siedco` y una aclaración de que es un indicador estadístico
     histórico (percentil 75), no la probabilidad del modelo predictivo
     (#19, aún no implementado).
  2. **Densidad NUSE** (togglable, oculta por defecto): escala continua
     (colormap secuencial) por `conteo_nuse`, tooltip con el conteo y nota
     de que es a nivel localidad (no UPZ, ver limitación arriba).
  3. **Tipología** (togglable): color categórico por `nombre_perfil` (3
     perfiles de #27), tooltip en lenguaje no técnico (una frase por
     perfil, no el nombre técnico de la columna).
- **`app/mock_data/`** (eliminado por completo: `generar_mock.py` +
  `zonas_riesgo_mock.geojson`).
- **`app/README.md`** (edita): quita la sección "Estado (Issue #32 —
  scaffold)" sobre el mock, documenta las 3 capas reales, la limitación de
  UPZ→localidad en NUSE, y cómo regenerar `app/data/*.json` con
  `generar_datasets_mapa.py`.

## Fuera de alcance

Ingerir geometría real de UPZ (trabajo futuro de Integrante 1, no de esta
issue). Conectar con la API real (#34) — sigue usando datos locales
commiteados, no `GET /zonas-riesgo` real. El reporte ciudadano (#36).
