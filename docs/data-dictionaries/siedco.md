# Diccionario de datos — SIEDCO / Delito de Alto Impacto. Bogotá D.C.

- **Entidad:** Secretaría Distrital de Seguridad, Convivencia y Justicia (SDSCJ) /
  Policía Nacional, vía datos abiertos Bogotá.
- **Dataset:** `delito-de-alto-impacto-bogota-d-c` (federado en datos.gov.co como
  `t26q-43fj`).
- **Recurso usado:** GeoJSON "enero–diciembre (2018–2025) Localidad" (`dai_geojson.zip`
  → `DAILoc.geojson`).
- **Naturaleza:** polígono por localidad, **EPSG:4686** (MAGNA-SIRGAS). Conteos
  **anuales**. No hay mes, no hay franja horaria, no hay coordenada del hecho.
- **Actualización verificada:** 2026-06-26.

## Estructura

Formato **ancho**: 21 features (20 localidades + 1 `"Sin Localización"`), 116
columnas. Cada tipo de delito tiene una columna por año con el patrón
`CM<PREFIJO><AA>CONT` (el prefijo `HCE` se trunca a `...CON` por el límite de 10
caracteres de nombre de campo tipo shapefile).

### Columnas de identidad / geometría

| Columna | Alias oficial | Tipo | Notas |
|---|---|---|---|
| `CMIULOCAL` | Código Localidad | str | Llave de cruce (2 díg., `01`–`20`; `99`=Sin Localización) |
| `CMNOMLOCAL` | Nombre Localidad | str | **No usar para cruzar** (texto libre) |
| `CMMES` | Mes | str | Etiqueta de corte, p. ej. `"Ene-Dic (2024vs2025)"` |
| `geometry` | — | Polygon | EPSG:4686 |
| `SHAPE_AREA`, `SHAPE_LEN` | — | float | Métricas de geometría (no analíticas) |

### Tipos de delito (prefijo → etiqueta oficial)

| Prefijo | Tipo de delito | | Prefijo | Tipo de delito |
|---|---|---|---|---|
| `H`  | Homicidios | | `HC`  | Hurto Comercio |
| `LP` | Lesiones Personales | | `HCE` | Hurto Celulares |
| `HP` | Hurto Personas | | `HM`  | Hurto Motocicletas |
| `HR` | Hurto Residencias | | `DS`  | Delitos Sexuales |
| `HA` | Hurto Automotores | | `VI`  | Violencia Intrafamiliar |
| `HB` | Hurto Bicicletas | | | |

Años disponibles por tipo: `18`–`26` (se usan 2018–2025). Columnas derivadas
`*VAR` (variación %) y `*TOTAL` (total ciudad, **no** por localidad) se descartan.

## Salida normalizada (`data/interim/siedco_delitos.parquet`)

Formato **largo**, 1.760 filas = 20 localidades × 11 tipos × 8 años.

| Columna | Tipo | Descripción |
|---|---|---|
| `cod_localidad` | str(2) | Código de localidad, cero a la izquierda |
| `localidad_nombre` | str | Nombre (referencia, no cruce) |
| `anio` | int | 2018–2025 |
| `cod_delito` | str | Prefijo SIEDCO (`H`, `HP`, …) |
| `tipo_delito` | str | Etiqueta oficial |
| `conteo` | int | Nº de casos en la localidad-año-tipo |

## Notas de calidad

- **Fila `99 = "Sin Localización"`** presente en el origen → se descarta en la
  ingesta (no es una de las 20 localidades) y se reporta en consola.
- **Sin mes ni hora**: el dato es anual. Limita el grano temporal del modelo a año.
- Los nombres traen tildes y capitalización mixta (`"Fontibón"`, `"Los Mártires"`);
  el archivo viene en UTF-8 en el GeoJSON, pero difiere de otras fuentes → cruce
  por código.
- Total de casos 2018–2025 (suma de conteos): **2.135.884**. Delito dominante:
  Hurto a Personas (localidades grandes: Suba, Kennedy, Engativá).
