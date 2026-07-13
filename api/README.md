# API — Alerta Ciudadana (Issue #20)

API ligera en **FastAPI** que sirve el contrato único del sistema:
`GET /zonas-riesgo` → GeoJSON con riesgo predictivo + tipología de clusters.

Lo consumen el **dashboard Streamlit** (Int. 3) y la **app móvil Expo** (Int. 4).

---

## Cómo levantar

Desde la raíz del repo, con el venv activo y los artefactos generados:

```bash
# 1) Datos + modelos (si aún no existen en disco)
python pipelines/pipeline_ml.py
python models/predictivo/train.py
python models/clustering/build_features.py
python models/clustering/train.py

# 2) API — IMPORTANTE: --host 0.0.0.0 para que el teléfono físico
#    alcance la API por IP de LAN (misma Wi-Fi). 
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

- Docs interactivas (Swagger): http://localhost:8000/docs  
- Desde el móvil: `http://<IP-LAN-de-tu-PC>:8000/zonas-riesgo?anio=2025&tipo=HP`  
  (ej. `http://192.168.1.20:8000/...`)

---

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/zonas-riesgo` | GeoJSON de las 20 localidades con riesgo + cluster |
| `GET` | `/health` | Estado, años y tipos disponibles |
| `GET` | `/docs` | Swagger UI |

### Query params de `/zonas-riesgo`

| Param | Default | Ejemplo | Notas |
|---|---|---|---|
| `anio` | `2025` | `2024` | Entero 2018–2025 |
| `tipo` | `HP` | `hurto_personas` o `HP` | Código SIEDCO **o** slug |

Códigos SIEDCO: `H`, `LP`, `HP`, `HR`, `HA`, `HB`, `HC`, `HCE`, `HM`, `DS`, `VI`.

Ejemplos:

```text
GET /zonas-riesgo?anio=2025&tipo=HP
GET /zonas-riesgo?anio=2025&tipo=hurto_personas
GET /zonas-riesgo?anio=2024&tipo=VI
```

---

## Esquema de respuesta (GeoJSON)

`FeatureCollection` con **exactamente 20** `Feature` (una por localidad).

Cada `properties` incluye:

| Campo | Tipo | Origen |
|---|---|---|
| `cod_localidad` | string `"01"`…`"20"` | DIVIPOLA / geometría |
| `localidad_nombre` | string | geometría |
| `cod_dane_mpio` | string | `"11001"` (Bogotá) |
| `cluster` | int | K-Means (#27) |
| `nombre_perfil` | string | tipología interpretable |
| `nivel_riesgo` | `"bajo"` \| `"medio"` \| `"alto"` | modelo predictivo |
| `probabilidad_riesgo` | float 0–1 | `predict_proba` |
| `riesgo_predicho` | 0 \| 1 | umbral del artefacto |
| `anio` | int | query param |
| `tipo_delito` | string | código SIEDCO resuelto |
| `tipo_delito_nombre` | string | nombre legible |

`geometry`: polígono/multipolígono de la localidad (EPSG:4326).

Ejemplo mínimo de una feature:

```json
{
  "type": "Feature",
  "properties": {
    "cod_localidad": "01",
    "localidad_nombre": "USAQUEN",
    "cod_dane_mpio": "11001",
    "cluster": 2,
    "nombre_perfil": "Perfil de bajo incidente relativo",
    "nivel_riesgo": "bajo",
    "probabilidad_riesgo": 0.4354,
    "riesgo_predicho": 0,
    "anio": 2025,
    "tipo_delito": "HP",
    "tipo_delito_nombre": "Hurto Personas"
  },
  "geometry": { "type": "Polygon", "coordinates": [ ... ] }
}
```

---

## Diseño técnico

- Modelos (`model.joblib`, `clusters.joblib`) y predicciones se cargan **una sola vez** al arranque (`lifespan`), no por request.
- Geometría: `data/03_primary/zonas_bogota.geojson`.
- Tipología: `models/clustering/zona_cluster.parquet`.
- Sin base de datos: solo lectura de artefactos en disco.

---

## Errores

| Código | Cuándo |
|---|---|
| `422` | `anio` o `tipo` inválidos (detalle con valores válidos) |
| `404` | Combinación sin filas de predicción |
| `503` | Arranque incompleto |

---

## Contrato con Int. 3 e Int. 4

Este README define el shape acordado (compatible con el mock de #32).  
Cualquier cambio de campos debe coordinarse antes de tocar dashboard/móvil.
