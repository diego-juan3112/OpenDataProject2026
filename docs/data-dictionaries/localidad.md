# Diccionario de datos — Localidad. Bogotá D.C (geometría)

- **Entidad:** IDECA / Unidad Administrativa Especial de Catastro Distrital.
- **Dataset:** `localidad-bogota-d-c`.
- **Recurso usado:** Shape File `loca.zip` (`loca.shp`). Existe también GeoJSON
  `loca.json` **en formato Esri JSON** (no GeoJSON estándar) y GPKG `loca.gpkg`.
- **Naturaleza:** 20 polígonos de localidad, **EPSG:4686** (MAGNA-SIRGAS).
- **Actualización verificada:** 2022-08-05 (geometría estable, cambia rara vez).

## Columnas del shapefile

| Columna | Tipo | Descripción |
|---|---|---|
| `LocCodigo` | str(2) | Código de localidad — **llave de cruce** (`01`–`20`) |
| `LocNombre` | str | Nombre (MAYÚSCULAS, sin tildes: `USAQUEN`, `SUBA`…) |
| `LocAAdmini` | str | Acto administrativo de creación |
| `LocArea` | float | Área (m²) |
| `SHAPE_Leng`, `SHAPE_Area` | float | Métricas de geometría |
| `geometry` | Polygon | EPSG:4686 |

## Salida normalizada (`data/02_intermediate/localidades.geojson`)

Base geométrica de `zonas_bogota.geojson`. Reproyectada a **EPSG:4326** (WGS84)
para consumo web (API / dashboard / móvil). El riesgo y el cluster se adjuntan
después, en `pipelines/pipeline_ml.py`, una vez existan los modelos.

| Columna | Tipo | Descripción |
|---|---|---|
| `cod_localidad` | str(2) | Código de localidad, cero a la izquierda |
| `localidad_nombre` | str | Nombre de la localidad |
| `cod_dane_mpio` | str | `11001` (Bogotá) — para escalar a otros municipios |
| `geometry` | Polygon (4326) | Límite de la localidad |

## Notas de calidad

- **Nombres divergen de otras fuentes** (mayúsculas/sin tildes) → confirma la
  Regla 1: cruzar por `LocCodigo`, nunca por nombre.
- **CRS de origen EPSG:4686** coincide con SIEDCO → los joins espaciales no
  requieren reproyección entre ambas (Regla 2); solo se reproyecta a 4326 al
  exportar para web.
- **20/20 localidades**, geometrías válidas (`is_valid.all() == True`).
- **Bounding box (lon/lat):** aprox. `[-74.45, 3.73, -73.99, 4.84]` — incluye la
  extensión rural de Sumapaz al sur (lat ≈ 3.73).
