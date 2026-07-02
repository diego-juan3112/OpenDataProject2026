# Estructura del proyecto — Alerta Ciudadana

Mapa de referencia del repositorio: **qué hay, dónde está y para qué sirve cada
carpeta, script, notebook y documento**. Refleja el estado real en disco tras la
refactorización a la estructura estándar de la competencia *"Datos al Ecosistema"*
(nivel **Intermedio-ia**).

> **Fecha de corte:** 2026-07-02 · **Frente activo:** Datos + andamiaje ML
> (Integrante 1). Las piezas de modelado, API y clientes (Integrantes 2–4) están
> como *scaffold* o pendientes.

---

## 1. Qué se hizo en esta refactorización

1. **Migración a la estructura de competencia.** El pipeline pasó de la carpeta
   plana `data-engineering/` a la separación estándar `src/` (módulos) +
   `pipelines/` (orquestador) + `notebooks/` + `tests/`.
2. **Renombrado de módulos** al vocabulario del estándar, ajustando los `import`
   internos para no romper el pipeline:
   - `clean_normalize.py` → `src/data_cleaning.py`
   - `join_sources.py` → `src/pipeline_integration.py`
   - `build_dataset.py` → `pipelines/pipeline_ml.py`
3. **Ciclo de vida de datos por capas numeradas:** `data/raw|interim|processed`
   → `data/01_raw | 02_intermediate | 03_primary | 04_model_output`. Las rutas se
   actualizaron en `src/config.py`.
4. **Archivos nuevos del estándar:** `LICENSE` (MIT), `environment.yml`,
   `Changelog.md`, `.github/workflows/ci.yml`, andamiaje de `docs/`, `src/`
   (placeholders de modelado), `notebooks/` (5 scaffolds) y `reports/`.
5. **Limpieza de obsoletos:** se eliminaron artefactos de compilación
   (`__pycache__/`), y —fuera de alcance de "esta parte del proyecto"— las
   carpetas de cliente (`api/`, `app/`, `mobile/`), `CRONOGRAMA.md`,
   `docs/AVANCE.md` y los README de `models/`.
6. **Documentación reconciliada:** todos los `.md` que referenciaban las rutas o
   nombres viejos se actualizaron a la estructura nueva.

---

## 2. Árbol actual (estado real en disco)

> `data/` y los artefactos de modelo **no se versionan** (ver `.gitignore`); solo
> se conservan los `.gitkeep` que preservan las carpetas. Se omiten `.venv/`,
> `.git/` y `__pycache__/`.

```
OpenDataProject2026/                    ( = Intermedio-ia/ en la entrega)
│
├── CLAUDE.md                           # Documento maestro (fuente de verdad del proyecto)
├── README.md                           # Guía principal: qué es, stack, cómo correr
├── ESTRUCTURA.md                       # Este archivo: mapa de carpetas y funciones
├── BACKLOG.md                          # Issues por integrante (plan de 3 semanas)
├── DEFINITION_OF_DONE.md               # Definición de "hecho" a nivel proyecto
├── Changelog.md                        # Registro cronológico de versiones/cambios
├── LICENSE                             # Licencia MIT
├── requirements.txt                    # Dependencias Python (pip)
├── environment.yml                     # Entorno Conda equivalente
├── .gitignore                          # Exclusiones (datos, modelos, temporales)
│
├── .github/
│   └── workflows/
│       └── ci.yml                      # CI GitHub Actions: compila src/ y corre pytest
│
├── src/                                # Código fuente modular del pipeline (Integrante 1)
│   ├── __init__.py                     # Marca src/ como paquete importable
│   ├── config.py                       # Config central: rutas, URLs, CRS, llaves, tipología
│   ├── utils.py                        # Utilidades: descarga idempotente + descompresión
│   ├── ingest_siedco.py                # #3  Ingesta SIEDCO (delitos por localidad, anual)
│   ├── ingest_nuse.py                  # #4  Ingesta NUSE / Línea 123 (localidad+UPZ, mensual)
│   ├── ingest_divipola.py              # #5  Geometría de las 20 localidades → EPSG:4326
│   ├── ingest_datosgov.py              #     Microdatos Policía vía API datos.gov.co (Socrata)
│   ├── ingest_dane.py                  # #6  Contexto DANE/SDP (población + IPM)
│   ├── data_cleaning.py                # #7  Limpieza consolidada → *_clean.parquet + reporte
│   ├── pipeline_integration.py         # #8  Cruce por código de localidad + validación
│   ├── feature_engineering.py          #     [placeholder] features del predictivo/clustering
│   ├── model_training.py               #     [placeholder] entrenamiento RF/GB + K-Means
│   ├── model_evaluation.py             #     [placeholder] métricas, matrices, auditoría sesgo
│   └── README.md                       # Guía del pipeline de datos
│
├── pipelines/
│   └── pipeline_ml.py                  # #9  Orquestador maestro → los 2 entregables + verificación
│
├── notebooks/                          # Experimentación y análisis exploratorio
│   ├── 01_EDA_exploracion_datos.ipynb  #     [scaffold] EDA de calidad
│   ├── 02_limpieza_transformacion.ipynb#     [scaffold] documenta reglas de limpieza
│   ├── 03_analisis_descriptivo.ipynb   #     [scaffold] descriptivos del consolidado
│   ├── 04_modelo_predictivo.ipynb      #     [scaffold] experimentación del predictivo
│   ├── 05_reportes_automaticos.ipynb   #     [scaffold] figuras/reportes
│   └── ejemplo_dataset_analitico.ipynb # Ejemplo REAL: cómo cargar y usar el dataset final
│
├── docs/                               # Documentación técnica para evaluación
│   ├── fuentes_datos.md                # Inventario validado de las fuentes abiertas (REAL)
│   ├── data_dictionary.md              # Índice del consolidado + enlaces a diccionarios (REAL)
│   ├── architecture.md                 # [placeholder] diagrama de arquitectura/flujo
│   ├── planteamiento_problema.md       # [placeholder] definición del problema
│   ├── marco_metodologico.md           # [placeholder] CRISP-ML(Q) aplicado
│   ├── validacion_guide.md             # [placeholder] guía de reproducción para pares
│   ├── conclusiones.md                 # [placeholder] hallazgos y próximos pasos
│   └── data-dictionaries/              # Diccionario de datos por fuente (REAL)
│       ├── siedco.md                   #   SIEDCO — delito de alto impacto
│       ├── nuse.md                     #   NUSE — Línea 123
│       ├── localidad.md                #   Geometría oficial de localidades
│       ├── datosgov_policia.md         #   Microdatos Policía (API datos.gov.co)
│       ├── dane_contexto.md            #   Contexto socioeconómico DANE/SDP
│       └── reporte_calidad.md          #   Trazabilidad de limpieza (generado por el pipeline)
│
├── data/                               # Ciclo de vida de los datos (gitignored salvo .gitkeep)
│   ├── 01_raw/                         # Fuentes originales descargadas tal cual
│   │   ├── siedco/                     #   dai_geojson.zip, DAILoc.geojson
│   │   ├── nuse/                       #   nuse_c4_linea123.csv + metadatos
│   │   ├── localidad/                  #   shapefile Loca.* + loca.zip
│   │   └── dane/                       #   población CSV + calidad de vida XLSX
│   ├── 02_intermediate/               # Limpio, tipado, despivoteado por fuente
│   │                                  #   siedco_delitos/nuse_incidentes/localidades/
│   │                                  #   dane_contexto + *_clean.parquet
│   ├── 03_primary/                    # Consolidado final (ENTREGABLE Semana 1 / SYNC-1)
│   │   ├── dataset_analitico.parquet  #   1 fila por (localidad × año × tipo de delito)
│   │   └── zonas_bogota.geojson       #   20 polígonos, EPSG:4326
│   └── 04_model_output/               # Predicciones/salidas de modelo (vacío por ahora)
│
├── models/                             # Artefactos de modelos entrenados (vacío; Integrantes 2–3)
├── tests/                              # Pruebas de calidad de datos e inferencia (vacío)
├── reports/
│   └── figures/                        # Figuras generadas (vacío por ahora)
└── RECURSOS/                           # Presentación y material visual de la entrega (vacío)
```

---

## 3. Función de cada elemento

### 3.1 Documentos raíz (gobernanza del proyecto)

| Archivo | Función |
|---|---|
| `CLAUDE.md` | **Fuente de verdad**: qué se construye, fuentes, arquitectura, metodología CRISP-ML(Q), criterios de éxito y restricciones que no se recortan. |
| `README.md` | Puerta de entrada: descripción, stack técnico, estructura y **cómo correr** cada pieza. |
| `ESTRUCTURA.md` | Este documento: mapa navegable de carpetas y función de cada archivo. |
| `BACKLOG.md` | Backlog de issues `#N` repartido entre los 4 integrantes (3 semanas). |
| `DEFINITION_OF_DONE.md` | Criterios de "hecho" a nivel proyecto y por entregable. |
| `Changelog.md` | Registro cronológico de cambios y versiones. |
| `LICENSE` | Licencia MIT (abierta). |
| `requirements.txt` / `environment.yml` | Dependencias del proyecto (pip / Conda). |
| `.gitignore` | Excluye datos pesados, modelos serializados, entornos y temporales. |
| `.github/workflows/ci.yml` | Integración continua: compila `src/`, `pipelines/` y corre `pytest`. |

### 3.2 `src/` — Pipeline de datos modular (Fases 1–2 de CRISP-ML(Q))

| Módulo | Rol en el pipeline |
|---|---|
| `config.py` | Config única: rutas de datos, URLs CKAN verificadas, CRS (4686→4326), llave de cruce (`cod_localidad`), ventana temporal (2018–2025) y tipología SIEDCO. |
| `utils.py` | Descarga idempotente (no re-baja lo existente) y descompresión de zips. |
| `ingest_siedco.py` | Descarga el GeoJSON ancho de SIEDCO y lo despivotea a formato largo (localidad × año × tipo). |
| `ingest_nuse.py` | Carga las llamadas de la Línea 123 agregadas por localidad/UPZ × mes × tipo. |
| `ingest_divipola.py` | Lee el shapefile de localidades, valida geometrías y reproyecta a EPSG:4326. |
| `ingest_datosgov.py` | Consume microdatos de la Policía por el **API oficial de datos.gov.co** (Socrata) para triangular SIEDCO. |
| `ingest_dane.py` | Genera el contexto socioeconómico (población proyectada + IPM/pobreza) por localidad. |
| `data_cleaning.py` | Aplica las reglas de limpieza consolidadas y escribe el `reporte_calidad.md`. |
| `pipeline_integration.py` | Cruza todas las fuentes **por código de localidad** (nunca por nombre) y valida; expone `tabla_analitica()` y `tabla_zonas()`. |
| `feature_engineering.py` · `model_training.py` · `model_evaluation.py` | **Placeholders** reservados para el modelado de los Integrantes 2 y 3. |
| `README.md` | Documentación operativa del pipeline (entregables, cómo correr, reglas). |

### 3.3 `pipelines/` — Orquestación

| Archivo | Función |
|---|---|
| `pipeline_ml.py` | Script maestro (Issue #9): corre limpieza → cruce → marca el split espacio-temporal (train ≤2024 / test 2025) → escribe y **verifica** los dos entregables de `data/03_primary/`. |

### 3.4 `data/` — Ciclo de vida por capas

| Capa | Contenido | Se versiona |
|---|---|---|
| `01_raw/` | Fuentes originales descargadas (SIEDCO, NUSE, localidad, DANE). | No (solo `.gitkeep`) |
| `02_intermediate/` | Datos limpios y tipados por fuente. | No |
| `03_primary/` | Consolidado final: `dataset_analitico.parquet` + `zonas_bogota.geojson`. | No |
| `04_model_output/` | Predicciones y resultados de modelo (aún vacío). | No |

### 3.5 `docs/` — Documentación técnica

Contenido **real**: `fuentes_datos.md` (inventario validado), `data_dictionary.md`
(índice del consolidado) y los 6 diccionarios de `data-dictionaries/`. El resto
(`architecture.md`, `planteamiento_problema.md`, `marco_metodologico.md`,
`validacion_guide.md`, `conclusiones.md`) son **placeholders** listos para
completar con el contenido correspondiente de `CLAUDE.md`.

### 3.6 `notebooks/`, `tests/`, `models/`, `reports/`, `RECURSOS/`

- `notebooks/` — 5 scaffolds numerados (solo celda de título/propósito) + el
  notebook **real** `ejemplo_dataset_analitico.ipynb` que muestra cómo consumir
  el dataset.
- `tests/` — reservado para pruebas de calidad de datos e inferencia (vacío).
- `models/` — reservado para artefactos `.pkl` de modelos entrenados (vacío).
- `reports/figures/` — reservado para figuras generadas (vacío).
- `RECURSOS/` — reservado para la presentación y material visual (vacío).

---

## 4. Cómo se reproduce el pipeline

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt

# Ingestas (idempotentes)
python src/ingest_siedco.py
python src/ingest_nuse.py
python src/ingest_divipola.py
python src/ingest_datosgov.py
python src/ingest_dane.py

# Dataset final (limpia + cruza + split + escribe los 2 entregables)
python pipelines/pipeline_ml.py
```

Salidas: `data/03_primary/dataset_analitico.parquet` y
`data/03_primary/zonas_bogota.geojson`.

---

## 5. Estado y notas de seguimiento

- **Completo:** ingesta, limpieza, cruce y dataset analítico unificado (Issues
  #1–#9). Los dos entregables de SYNC-1 existen en `data/03_primary/`.
- **Scaffold / pendiente:** modelado (`src/model_*`, `notebooks/04`), notebooks de
  EDA, docs placeholder, y las carpetas vacías `models/`, `tests/`, `reports/`,
  `RECURSOS/`.
- **Referencias colgantes tras las eliminaciones manuales:** `CLAUDE.md`,
  `README.md`, `DEFINITION_OF_DONE.md` y `BACKLOG.md` aún mencionan
  `CRONOGRAMA.md` y las carpetas `api/`, `app/`, `mobile/` (eliminadas). El
  `ci.yml` corre `pytest tests/` sobre una carpeta sin pruebas. Conviene decidir
  si esas piezas quedan **fuera de alcance de "esta parte"** (y limpiar las
  referencias) o si se reincorporan más adelante.
