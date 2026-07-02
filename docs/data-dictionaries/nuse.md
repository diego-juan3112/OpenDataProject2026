# Diccionario de datos — NUSE / Incidentes C4 · Línea 123. Bogotá D.C.

- **Entidad:** Secretaría Distrital de Seguridad, Convivencia y Justicia (SDSCJ).
- **Dataset:** `incidentes` (federado en datos.gov.co como `2rem-xdf7`).
- **Recurso usado:** CSV "Llamadas Tramitadas C4 … enero 2015 – mayo 2026".
- **Naturaleza:** CSV **agregado** por localidad/UPZ × mes × tipo de incidente.
  **No es nivel-incidente y no trae lat/lon.** ~112 MB, encoding **latin-1**,
  separador `;`.
- **Actualización verificada:** 2026-06-26.
- **Rol:** señal complementaria (volumen de llamadas de emergencia) + capa de
  densidad por UPZ. Su taxonomía (RIÑA, RUIDO, ACCIDENTE…) **no** coincide con los
  delitos de SIEDCO; no se mezclan como el mismo `tipo_delito`.

## Columnas del CSV original

| Columna | Tipo | Descripción |
|---|---|---|
| `ID` | str | Identificador compuesto (año+mes+localidad+incidencia) |
| `ANIO` | int | Año |
| `MES` | int | Mes (1–12) |
| `TIPO_INCIDENTE` | str | Código del tipo de incidente |
| `TIPO_DETALLE` | str | Descripción del incidente (RIÑA, RUIDO, …) |
| `COD_LOCALIDAD` | str | Código de localidad — **llave de cruce** |
| `LOCALIDAD` | str | Nombre de localidad (no cruzar) |
| `COD_UPZ` | str | Código de UPZ (Unidad de Planeamiento Zonal) |
| `UPZ` | str | Nombre de UPZ |
| `CANT_INCIDENTES` | int | Nº de llamadas tramitadas del grupo |

> ⚠️ **El diccionario oficial `definicioncampos.csv` está desactualizado**: lista
> `COD_INCIDENTE/INCIDENTE` y omite `TIPO_DETALLE`, `COD_UPZ`, `UPZ`, que sí están
> en el CSV real. Se documenta el CSV real, no el diccionario del portal.

## Salida normalizada (`data/02_intermediate/nuse_incidentes.parquet`)

Recorte 2018–2025, 763.074 filas. Grano nativo (localidad × UPZ × año × mes × tipo).

| Columna | Tipo | Descripción |
|---|---|---|
| `cod_localidad` | str(2) | Código de localidad, cero a la izquierda |
| `localidad_nombre` | str | Nombre (referencia) |
| `cod_upz`, `upz_nombre` | str | UPZ (grano fino para la capa de densidad) |
| `anio`, `mes` | int | Periodo |
| `cod_incidente`, `tipo_incidente` | str | Tipo de llamada |
| `cant_incidentes` | int | Nº de llamadas tramitadas |

## Notas de calidad

- **`COD_LOCALIDAD = 99` → "SIN LOCALIZACION":** 149.930 incidentes en 2018–2025
  no ubicables por localidad. Se marca en la ingesta; se decide su tratamiento en
  el cruce (#8) — no se imputan a ninguna localidad.
- **Código basura `-0` (nombre `-`):** 22 incidentes en una fila malformada. Se
  descarta al cruzar por no estar en `01`–`20`.
- **20 localidades reales presentes** (`01`–`20`), coinciden con SIEDCO ✅.
- **Sumapaz (`20`)** tiene solo 488 llamadas (zona rural muy dispersa): posible
  outlier de bajo conteo para el modelo.
- **UPZ:** 125 códigos (incluye `UPZ999` = sin localización).
- Total llamadas tramitadas 2018–2025: **20.996.584**. Top tipos: RIÑA (3,53 M),
  RUIDO (2,19 M), ACCIDENTE DE TRÁNSITO (1,38 M).
