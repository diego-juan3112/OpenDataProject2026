# Diseño — EDA para perfilado de zonas (Issue [CLUST] #25)

**Fecha:** 2026-07-09 · **Pista:** 3 — Clustering + Dashboard (Integrante 3) · **Fase CRISP-ML:** 3

## Contexto

El issue #25 del backlog pide un notebook exploratorio que sirva de insumo para
el clustering formal de #27 (K-Means sobre perfiles de zona). Su dependencia
original ("usa crudos de #3/#4") quedó obsoleta: el dataset analítico
consolidado ya existe (`data/03_primary/dataset_analitico.parquet`, Integrante
1 completó #1–#12), así que este EDA parte directamente de ese consolidado.

**Criterios de aceptación (del backlog):**
1. Notebook con perfiles delictivos por localidad (proporción de cada tipo de delito).
2. Tendencia por año identificada (¿sube o baja cada tipo de delito por localidad?).
3. Hipótesis preliminar de cuántos perfiles distintos podrían existir.

## Decisión: notebook nuevo

`notebooks/06_eda_perfilado_clustering.ipynb`. El scaffold
`03_analisis_descriptivo.ipynb` es genérico (evolución, ranking, correlaciones
con DANE) y no tiene dueño claro; un notebook nuevo y explícitamente nombrado
evita choque de alcance con quien eventualmente llene el 03.

## Alcance

**Fuente de datos:** `data/03_primary/dataset_analitico.parquet` completo
(2018–2025). Igual que `01_EDA_exploracion_datos.ipynb`, un EDA describe el
histórico completo porque no aprende parámetros de modelo — la validación
espacio-temporal sin fuga se respeta más adelante, en el modelado formal de
#27 (que sí debe restringirse a `split == "train"`).

**Estilo:** reutilizar la paleta y configuración de matplotlib/seaborn
(`COLORES`, `sns.set_style`) de `01_EDA_exploracion_datos.ipynb` para
consistencia visual entre notebooks del proyecto.

### Sección 1 — Perfiles delictivos por localidad (criterio 1)

- Tabla `localidad × tipo_delito` con la **proporción** de cada tipo dentro
  del total de esa localidad (`conteo_siedco` normalizado por fila, no por
  columna) — compara composición, no volumen.
- Heatmap de la matriz de proporciones.
- Párrafo de interpretación señalando localidades con perfiles marcadamente
  distintos, apoyado en el hallazgo ya documentado en `docs/HANDOFF_INT1.md`
  (pobreza ↔ más violencia interpersonal, no ↔ más hurto de bienes).

### Sección 2 — Tendencia por año por localidad-tipo (criterio 2)

- Para cada combinación `(localidad, tipo_delito)`: pendiente de regresión
  lineal simple de `conteo_siedco` contra `anio` → clasificación **sube /
  baja / estable** sobre un umbral simple de la pendiente relativa.
- Tabla resumen + heatmap `localidad × tipo` coloreado por dirección de
  tendencia.
- Nota explícita sobre el valle de 2020 (COVID) para no confundirlo con una
  tendencia estructural (mismo tratamiento que en el notebook 01).

### Sección 3 — Hipótesis preliminar de perfiles (criterio 3)

- Sobre la matriz de proporciones de la Sección 1: heatmap ordenado +
  **dendrograma** (`scipy.cluster.hierarchy`, linkage sobre proporciones
  estandarizadas) para leer visualmente en cuántos grupos parecen separarse
  las 20 localidades.
- Párrafo de hipótesis en lenguaje natural (p. ej. "se observan
  preliminarmente entre 3 y 5 grupos: uno dominado por hurto en zonas
  comerciales, otro por violencia interpersonal en zonas periféricas...").
- Se deja explícito que el método formal (K-Means, features estandarizadas
  con NUSE/IPM, elbow + silhouette cuantitativos) es alcance de #27.

## Fuera de alcance

Estandarización formal de features, K-Means, elbow/silhouette cuantitativo,
asignación final de cluster por localidad, nombres de perfil interpretable —
todo eso pertenece a #27 (features + clustering) y #28 (validación interna).

## Testing / verificación

No aplica suite de `pytest` (es un notebook exploratorio, no código de
pipeline). Verificación manual: el notebook debe correr de punta a punta sin
errores contra el parquet ya generado y producir las 3 salidas de los
criterios de aceptación.
