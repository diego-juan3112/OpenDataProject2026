# Diccionario de datos — Microdatos Policía Nacional (API datos.gov.co)

- **Entidad:** Policía Nacional de Colombia.
- **Portal / consumo:** **API oficial de `datos.gov.co`** (Socrata SoQL). A
  diferencia de SIEDCO/NUSE (federados, archivo servido por el portal de Bogotá),
  estos se **consultan y filtran directamente por el API** de datos.gov.co →
  evidencia de "Uso de datos abiertos".
- **Datasets usados (verificado 2026-06-30):**
  | Delito | ID | Columna filtro Bogotá | Fecha |
  |---|---|---|---|
  | Hurto a personas | `4rxi-8m8d` | `cod_muni = '11001'` | `fecha_hecho` (calendar_date) |
  | Violencia intrafamiliar | `vuyt-mqpw` | `codigo_dane = '11001000'` | `fecha_hecho` (texto DD/MM/YYYY) |
- **Naturaleza:** nivel-registro agregado por **municipio** (Bogotá = un solo
  polígono). **No** se desagrega por localidad → no es el backbone del dataset
  analítico; su rol es **triangulación/validación** de SIEDCO y **estacionalidad**
  mensual a nivel ciudad.

## Columnas de origen (API)

| Columna | Descripción |
|---|---|
| `fecha_hecho` | Fecha del hecho (día). Sin hora → no permite franja horaria. |
| `cod_depto`, `departamento` | Departamento (11 / Bogotá D.C.). |
| `cod_muni` / `codigo_dane`, `municipio` | Municipio (Bogotá). Llave DANE. |
| `cantidad` | Nº de casos del registro. |
| `tipo_de_hurto`, `genero`, `grupo_etario`, `armas_medios` | Presentes en algunos datasets; no se usan (agregación por año). |

## Salida normalizada (`data/02_intermediate/datosgov_policia.parquet`)

| Columna | Tipo | Descripción |
|---|---|---|
| `delito` | str | `hurto_personas` \| `violencia_intrafamiliar` |
| `anio` | int | 2018–2025 |
| `subtipo` | str | `TOTAL` (o subtipo cuando el dataset lo trae) |
| `cantidad` | int | Casos agregados Bogotá-año |
| `fuente` | str | `datos.gov.co/<id>` (trazabilidad) |

## Triangulación con SIEDCO (validación de calidad)

Hurto a personas, Bogotá, comparando SIEDCO (suma de localidades) vs. Policía
nacional (API):

| Año | SIEDCO | Policía Nal. | Dif. |
|---|---|---|---|
| 2018–2024 | — | — | **≤ 0.7 %** (coincidencia casi perfecta ✅) |
| 2025 | 101.894 | 123.017 | **−17.2 %** (año no consolidado ⚠️) |

**Conclusión:** las cifras 2018–2024 quedan validadas de forma cruzada por dos
fuentes oficiales independientes. El 2025 aún no está consolidado en el archivo
anual de SIEDCO → se entrena con años ≤2024 y se evalúa 2025 con esa salvedad.

## Notas de calidad

- La columna de código de municipio **cambia entre datasets** (`cod_muni`=11001 de
  5 díg. vs. `codigo_dane`=11001000 de 8 díg.) — capturado en `config.DATOSGOV_DATASETS`.
- El dataset `d4fr-sbn2` ("Hurto por Modalidades") **fue descartado**: solo cubre
  modalidades nicho (piratería terrestre, entidades financieras, abigeato), no
  hurto urbano a personas.
- Sin hora en `fecha_hecho` → confirma la ausencia de franja horaria en dato abierto.
