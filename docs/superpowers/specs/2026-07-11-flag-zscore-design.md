# Diseño — Función `flag_zscore()` para el reporte ciudadano (Issue [CLUST] #29)

**Fecha:** 2026-07-11 · **Pista:** 3 — Clustering + Dashboard (Integrante 3) · **Fase CRISP-ML:** 4

## Contexto

Issue #29 depende de #26 (línea base histórica media/desviación por
localidad-tipo, completo: `calcular_linea_base` en `src/feature_engineering.py`,
serializada en `models/clustering/linea_base_zscore.parquet`) y bloquea a #36
(formulario de reporte ciudadano simulado en el dashboard). Es la pieza de
detección de anomalías del proyecto: cuando llega un reporte ciudadano
simulado (localidad, tipo de delito, conteo reciente), se compara contra el
histórico y se marca si el patrón es atípico — el diferenciador "reporte
verificado contra el histórico" de CLAUDE.md §3.3.

**Criterios de aceptación (del backlog):**
1. `flag_zscore(localidad, tipo_delito, conteo)` documentada y testeada con
   casos límite.
2. Acordada con la vista de reporte del dashboard (#36).
3. Sin fuga: usa solo la línea base histórica de #26.

## Desviación de la firma literal del backlog (justificada)

El backlog escribe la firma como `flag_zscore(localidad, tipo_delito, conteo)`
(3 argumentos), pero comparar contra el histórico requiere la tabla de línea
base de #26. Todo el código existente del proyecto (`models/clustering/
clustering.py`, `src/feature_engineering.py`) sigue el patrón de **funciones
puras que reciben los datos como parámetro, sin I/O**, para ser testeables con
datos sintéticos y no depender de que `data/`/`models/*/*.parquet` existan en
CI. Se añade `linea_base` como 4º parámetro explícito, manteniendo el mismo
patrón. `localidad` se nombra `cod_localidad` (nunca por nombre de texto,
restricción global del proyecto — CLAUDE.md §2/§7).

## Hallazgo real verificado antes del diseño

Se inspeccionó `models/clustering/linea_base_zscore.parquet` (real, de #26):
220 filas (20 localidades × 11 tipos de delito), columnas `cod_localidad,
tipo_delito, media, desviacion` (`media`/`desviacion` en `float64`). El caso
límite `desviacion == 0` documentado en #26 existe de verdad: **Sumapaz
(`cod_localidad="20"`) tiene 4 combinaciones con `media=0.0` y
`desviacion=0.0`** (tipos `HA, HB, HCE, HR` — conteo histórico cero en los 7
años de train). El diseño de abajo cubre explícitamente este caso.

## Dónde vive el código

- **`src/flag_zscore.py`** (nuevo, módulo dedicado — no se agrega a
  `feature_engineering.py` porque no es feature engineering de entrenamiento,
  es detección de anomalías en tiempo de reporte, consumida por el dashboard):

  ```python
  UMBRAL_Z = 2.0  # |z| > 2 ~ 95%, estándar para un flag simple de anomalía

  def flag_zscore(
      cod_localidad: str,
      tipo_delito: str,
      conteo: float,
      linea_base: pd.DataFrame,
  ) -> dict:
      fila = linea_base[
          (linea_base["cod_localidad"] == cod_localidad)
          & (linea_base["tipo_delito"] == tipo_delito)
      ]
      if fila.empty:
          raise ValueError(
              f"No hay linea base para cod_localidad={cod_localidad!r}, "
              f"tipo_delito={tipo_delito!r}."
          )

      media = fila["media"].iloc[0]
      desviacion = fila["desviacion"].iloc[0]

      if desviacion == 0:
          return {"es_atipico": conteo != media, "z_score": None,
                  "media": media, "desviacion": desviacion}

      z_score = (conteo - media) / desviacion
      return {"es_atipico": abs(z_score) > UMBRAL_Z, "z_score": z_score,
              "media": media, "desviacion": desviacion}
  ```

  Comportamiento en los 3 casos:
  1. **Normal** (`desviacion > 0`): `z_score = (conteo - media) / desviacion`;
     `es_atipico = abs(z_score) > 2.0`. Verificado con una fila real
     (`cod_localidad="01", tipo_delito="DS"`, media≈296.43, desviacion≈67.63):
     conteo=400 → z≈1.53 (no atípico); conteo=450 → z≈2.27 (atípico).
  2. **`desviacion == 0`** (histórico perfectamente constante, p. ej. Sumapaz):
     `z_score = None` (la fórmula no aplica, se evita `ZeroDivisionError`
     silencioso); `es_atipico = (conteo != media)` — cualquier desviación del
     valor constante es significativa.
  3. **Combo `(cod_localidad, tipo_delito)` no existe en `linea_base`**:
     `ValueError` explícito — falla rápido en vez de devolver un resultado
     engañoso (p. ej. `es_atipico=False` por defecto).

- **`tests/test_flag_zscore.py`** (nuevo, datos sintéticos — `linea_base` se
  construye en memoria, no se lee el parquet real): casos normal-no-atípico,
  normal-atípico, `desviacion==0` con conteo igual a la media (no atípico),
  `desviacion==0` con conteo distinto (atípico, mismo escenario real de
  Sumapaz), y combo inexistente (`ValueError`).

## Sin fuga

`linea_base` ya es train-only por construcción (`calcular_linea_base` en #26
filtra `split == "train"` antes de calcular media/desviación). `flag_zscore`
en sí no toca `split` — solo consume la tabla ya filtrada, así que no hay
superficie de fuga adicional que introducir aquí.

## Fuera de alcance

La integración real con el formulario del dashboard (leer el clic en el mapa,
mostrar el resultado en la UI, el checkbox de consentimiento opt-in) es #36,
bloqueada por esta issue — aquí solo se entrega la función pura + sus tests.
No se decide todavía el umbral final de producción (`UMBRAL_Z = 2.0` es un
valor razonable documentado, ajustable si #36 o QA cruzada piden otro).
