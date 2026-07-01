# data-engineering — Pipeline de datos (Integrante 1)

Ingesta, limpieza y cruce de las fuentes abiertas → el **dataset analítico
unificado** que consume todo el proyecto. Fases 1–2 de CRISP-ML(Q).

## Entregables (Semana 1 · SYNC-1)

- `data/processed/dataset_analitico.parquet` — una fila por
  (localidad × año × tipo de delito) con conteo + contexto.
- `data/processed/zonas_bogota.geojson` — geometría de las 20 localidades
  (EPSG:4326) con código y atributos de riesgo/cluster (estos se adjuntan cuando
  existan los modelos).
- `docs/data-dictionaries/` — un `.md` por fuente (columnas, tipos, calidad).

## Estructura

```
data-engineering/
├── config.py            # rutas, URLs verificadas, CRS, llaves, tipología SIEDCO
├── utils.py             # descarga idempotente + unzip
├── ingest_siedco.py     # #3  SIEDCO (delito por localidad, anual) → interim
├── ingest_nuse.py       # #4  NUSE / Línea 123 (localidad+UPZ, mensual) → interim
├── ingest_divipola.py   # #5  geometría de localidades (EPSG:4326) → interim
├── ingest_datosgov.py   #     Policía Nacional vía API datos.gov.co → interim
├── ingest_dane.py       # #6  contexto DANE/SDP (población + IPM) → interim
├── clean_normalize.py   # #7  reglas de limpieza consolidadas → *_clean.parquet
├── join_sources.py      # #8  cruce TABULAR por código de localidad (no spatial:
│                        #     NUSE no tiene lat/lon) + validación
├── build_dataset.py     # #9  script maestro → los 2 entregables + verificación
├── notebooks/           # EDA + ejemplo_dataset_analitico.ipynb (cómo usar la salida)
└── requirements.txt
```

## Cómo correr

```bash
# 1) entorno (una vez)
python -m venv ../.venv
../.venv/Scripts/pip install -r requirements.txt

# 2) ingestas (idempotentes; usar --force para re-descargar)
../.venv/Scripts/python ingest_siedco.py      # -> data/interim/siedco_delitos.parquet
../.venv/Scripts/python ingest_nuse.py        # -> data/interim/nuse_incidentes.parquet (112 MB)
../.venv/Scripts/python ingest_divipola.py    # -> data/interim/localidades.geojson
../.venv/Scripts/python ingest_datosgov.py    # -> data/interim/datosgov_policia.parquet (API)
../.venv/Scripts/python ingest_dane.py        # -> data/interim/dane_contexto.parquet

# 3) dataset final (limpia + cruza + marca split + escribe los 2 entregables)
../.venv/Scripts/python build_dataset.py      # -> data/processed/{dataset_analitico.parquet, zonas_bogota.geojson}
```

## Reglas del pipeline (no se recortan)

1. Cruzar **siempre por código** de localidad (2 díg.), nunca por nombre.
2. **Mismo CRS** antes de cualquier operación espacial (origen EPSG:4686 → web 4326).
3. **Cero microdatos personales**; contexto DANE siempre agregado por zona.
4. **Reproducible**: cada script corre de cero sin intervención manual.
5. `data/` **no se versiona** (ver `.gitignore`).

## Fuentes y hallazgos

Ver el inventario validado y los diccionarios en
[`../docs/data-dictionaries/`](../docs/data-dictionaries/README.md). Resumen: 4
fuentes abiertas (SIEDCO, NUSE, geometría de localidades, microdatos Policía por
API de datos.gov.co); NUSE es agregado (no punto), no existe franja horaria en
dato abierto, y el grano del predictivo es anual (train ≤2024 / test 2025).
