# Fuentes de datos — Alerta Ciudadana

**Responsable:** Integrante 1 (Datos) · **Validado contra los datos reales** (no
contra la descripción del portal). URLs verificadas en `src/config.py`.

## Inventario final (verificado 2026-06-30)

| Fuente | Entidad | URL | Última actualización | Formato | Granularidad | Rol en el proyecto |
|---|---|---|---|---|---|---|
| **SIEDCO — Delito de Alto Impacto** | Sec. Seguridad, Convivencia y Justicia de Bogotá | [dataset](https://datosabiertos.bogota.gov.co/dataset/7b270013-42ca-436b-9c1e-3bcb7d280c6b) | 2026-06-30 (datos 2018–2025) | GeoJSON (polígono) | Localidad × año | **Backbone del modelo** (`conteo_siedco`) |
| **NUSE C4 — Línea 123** | Sec. Seguridad, Convivencia y Justicia de Bogotá | [dataset](https://datosabiertos.bogota.gov.co/dataset/9bdf518e-b756-4865-983f-0521111fbcd1) | 2026-05-31 (datos a 31-may-2026) | CSV | Localidad × UPZ × mes | Señal complementaria (`conteo_nuse`, densidad por UPZ) |
| **Geometría de localidades** | Catastro / IDECA (portal Bogotá) | [dataset](https://datosabiertos.bogota.gov.co/dataset/856cb657-8ca3-4ee8-857f-37211173b1f8) | Estático (límites vigentes) | SHP (+GPKG) | Localidad (20) | Base del mapa (`zonas_bogota.geojson`) |
| **Microdatos Policía Nacional** | Policía Nacional de Colombia | [4rxi-8m8d](https://www.datos.gov.co/resource/4rxi-8m8d) · [vuyt-mqpw](https://www.datos.gov.co/resource/vuyt-mqpw) | 2026-06-30 (datos 2018–2025) | **API Socrata (datos.gov.co)** | Municipio (Bogotá) | Validación cruzada de SIEDCO |
| **Contexto DANE/SDP** | DANE (Censo 2018) + Secretaría Distrital de Planeación | [población](https://datosabiertos.bogota.gov.co/dataset/85bf790d-84d1-4eda-bd6f-40af62e71d95) · [IPM/hábitat](https://datosabiertos.bogota.gov.co/dataset/66617126-7606-4851-835f-c1ecfab65b8c) | Población proy. 2018–2035 · IPM Censo 2018 | CSV + XLSX | Localidad (20) | Features de contexto (`poblacion`, `ipm_nbi`) |

> **Nota sobre "Última actualización":** es la fecha de verificación del recurso en
> el portal (2026-06-30) y el rango de datos que efectivamente sirve cada archivo.
> NUSE trae datos hasta el 31-may-2026 (según el nombre del recurso). Diccionario
> por fuente en [`data-dictionaries/`](data-dictionaries/).

### URLs de descarga verificadas (copiar/pegar — reproducibles)

```
SIEDCO (GeoJSON):   https://datosabiertos.bogota.gov.co/dataset/7b270013-42ca-436b-9c1e-3bcb7d280c6b/resource/fc846aa6-68a9-456a-bdd3-f0284e162bd4/download/dai_geojson.zip
NUSE (CSV):         https://datosabiertos.bogota.gov.co/dataset/9bdf518e-b756-4865-983f-0521111fbcd1/resource/30d65a8b-d0ed-4e95-977e-0d7cc2ea89ef/download/llamadastramitadas-c4-bogota_numerounicodeseguridadyemergencias-nuse_linea-123-a-31mayo2026.csv
Localidades (SHP):  https://datosabiertos.bogota.gov.co/dataset/856cb657-8ca3-4ee8-857f-37211173b1f8/resource/30916322-7509-4cb4-8241-6be2b5109248/download/loca.zip
Policía hurto:      https://www.datos.gov.co/resource/4rxi-8m8d.json   (filtro cod_muni='11001')
Policía VIF:        https://www.datos.gov.co/resource/vuyt-mqpw.json   (filtro codigo_dane='11001000')
Población (CSV):    https://datosabiertos.bogota.gov.co/dataset/85bf790d-84d1-4eda-bd6f-40af62e71d95/resource/37e58cb3-c870-4608-8c37-ce45db0eb7c1/download/osb_demografia-poblacion-localidad.csv
IPM/Hábitat (XLSX): https://datosabiertos.bogota.gov.co/dataset/66617126-7606-4851-835f-c1ecfab65b8c/resource/bb1e5ef3-c191-476d-943d-b33406e5e45c/download/indicadores-calidad-de-vida-habitat-en-cifras-en-las-localidades.xlsx
```

## Hallazgos de validación (SIEDCO vs. Policía Nacional — hurto a personas)

Triangulación de dos fuentes oficiales **independientes** para el mismo delito en
Bogotá (fuente: [`data-dictionaries/datosgov_policia.md`](data-dictionaries/datosgov_policia.md)):

| Año | SIEDCO (suma localidades) | Policía Nal. (API) | Diferencia |
|---|---|---|---|
| 2018–2024 | — | — | **≤ 0.7 %** (coincidencia casi perfecta ✅) |
| 2025 | 101.894 | 123.017 | **−17.2 %** (año no consolidado ⚠️) |

**Conclusión:** las cifras 2018–2024 quedan **validadas de forma cruzada** por dos
fuentes oficiales independientes con diferencia ≤0.7%. El 2025 aún no está
consolidado en el archivo anual de SIEDCO → **se entrena con años ≤2024 y se evalúa
2025** con esa salvedad (coherente con el split sin fuga).

## Decisiones de diseño derivadas del dato real

1. **Sin franja horaria.** Ninguna fuente abierta publica la hora del hecho (SIEDCO
   anual, NUSE mensual, microdatos Policía con `fecha_hecho` sin hora). La variable
   objetivo se redefinió de *zona–franja–tipo* a **zona (localidad) – año – tipo de
   delito**. La franja horaria pasa a trabajo futuro.
2. **NUSE como densidad por zona, no puntos.** El dato abierto de NUSE viene
   **agregado por localidad/UPZ × mes × tipo**, sin lat/lon por incidente. La "capa
   de puntos / tiempo real" se reencuadró a **capa de densidad por UPZ**.
3. **Split temporal 2018–2024 / 2025.** SIEDCO es anual; la validación
   espacio-temporal **entrena con años ≤2024 y evalúa 2025** (nunca K-fold
   aleatorio). 2026-YTD se reserva como validación futura.
4. **IPM como porcentaje (no conteo).** La fuente de pobreza es un *conteo* de
   personas pobres por el IPM (Censo 2018); el ingest lo convierte a **incidencia**
   (`personas_pobres / población 2018`) para hacerlo comparable entre localidades de
   distinto tamaño. Es una variable estructural (mismo valor en todos los años).
5. **Sumapaz como caso especial.** La Encuesta Multipropósito **no cubre Sumapaz**
   (cod 20, rural) → `ipm_nbi` nulo en sus 88 filas. **No se imputa en silencio**:
   se documenta y la decisión de imputación se deja a Integrante 2 como *feature*
   (ver [`variable_objetivo.md`](data-dictionaries/variable_objetivo.md)). La
   variable objetivo `riesgo_alto` no depende de `ipm_nbi`.

## Llave de cruce (Restricción del proyecto)

Todas las fuentes se cruzan por el **código de localidad de Bogotá** (2 dígitos,
`"01"`–`"20"`, string con cero a la izquierda), **nunca por nombre** (los nombres
varían entre fuentes: tildes, capitalización, `"Suba"` vs `"USAQUEN"`). El código
DIVIPOLA nacional de Bogotá (`11001`) se conserva en la geometría para escalar a más
municipios, pero el cruce intraurbano es por código de localidad.

## Trazabilidad a criterios de evaluación

- **Uso de datos abiertos (20 pts):** el proyecto integra **cinco fuentes oficiales**
  y consume `datos.gov.co` de **dos formas distintas**, no solo bajando un CSV:
  (1) **descarga directa** de datasets del portal distrital federados en datos.gov.co
  (SIEDCO en GeoJSON, NUSE en CSV, geometrías, contexto DANE/SDP), y (2) **consumo por
  el API nativo Socrata (SoQL)** de datos.gov.co para los microdatos de la Policía
  Nacional, filtrando por `cod_muni='11001'` directamente en el servidor. Todo el
  cruce es por **código DANE de localidad** (nunca por texto libre), lo que deja la
  arquitectura lista para escalar a más municipios. El pipeline es **reproducible de
  punta a punta** (`python pipelines/pipeline_ml.py`); cada URL está verificada en
  `src/config.py`.

- **Análisis y rigor técnico (15 pts):** las cifras se **validan por triangulación**
  entre dos fuentes oficiales independientes (SIEDCO vs. Policía Nacional: diferencia
  **≤0.7% en hurto a personas 2018–2024**), lo que sustenta la calidad del dato antes
  de modelar. El diseño usa un **split espacio-temporal sin fuga** (train 2018–2024,
  test 2025; nunca aleatorio) y una **variable objetivo por percentil dentro de cada
  tipo de delito** (#10) para que delitos de escalas incomparables (homicidio vs.
  hurto) sean comparables. La métrica de evaluación es **recall y F1 de la clase de
  riesgo alto** (no *accuracy* global, engañosa bajo desbalance ~3:1). Y el EDA de
  calidad (#11) documenta explícitamente los **sesgos de sobre-vigilancia**
  (`corr(SIEDCO, NUSE)=0.92`; subregistro en el sur pobre) y de **estigmatización**
  (la pobreza predice violencia interpersonal, no hurto de bienes), condicionando el
  uso responsable del modelo.

## Cómo se descargan / reproducen

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
python src/ingest_siedco.py      # -> data/02_intermediate/siedco_delitos.parquet
python src/ingest_nuse.py        # -> data/02_intermediate/nuse_incidentes.parquet (descarga ~112 MB)
python src/ingest_divipola.py    # -> data/02_intermediate/localidades.geojson
python src/ingest_datosgov.py    # -> data/02_intermediate/datosgov_policia.parquet (API datos.gov.co)
python pipelines/pipeline_ml.py  # -> data/03_primary/dataset_analitico.parquet + zonas_bogota.geojson
```

Cada script de ingesta es **idempotente**: si el crudo ya existe en `data/01_raw/`,
no lo vuelve a descargar (usar `--force` para re-descargar). El reporte de calidad
por fuente (filas originales → tras limpieza + razón de cada descarte) está en
[`data-dictionaries/reporte_calidad.md`](data-dictionaries/reporte_calidad.md).
