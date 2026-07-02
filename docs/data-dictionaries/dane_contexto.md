# Diccionario — Contexto socioeconómico DANE/SDP (`dane_contexto.parquet`)

**Responsable:** Integrante 1 (Datos) · **Issue #6** · Grano: **localidad × año**

Variables de contexto (features de fondo) para el modelo predictivo y el
clustering. **Ambas variables son agregadas a nivel localidad — cero microdatos
personales** (Regla 3; Ley 1581/2012).

## Esquema

| Columna | Tipo | Descripción |
|---|---|---|
| `cod_localidad` | str(2) | Código de localidad `01`–`20` (llave de cruce). |
| `anio` | int | 2018–2025. |
| `poblacion` | int | Población proyectada total de la localidad ese año. |
| `personas_pobres_ipm` | float | Personas pobres por el IPM (Censo DANE 2018). Conteo; **estático** (se difunde a todos los años). |
| `ipm_pct` | float | Incidencia de pobreza multidimensional = `100 · personas_pobres_ipm / poblacion(2018)`. Feature comparable entre localidades. |

## Fuentes

| Variable | Dataset (portal Bogotá) | Entidad | Año | Grano |
|---|---|---|---|---|
| `poblacion` | *Población en Bogotá D.C. 2005–2035* (`piramide-poblacional-bogota-d-c`), CSV `osb_demografia-poblacion-localidad.csv` | Observatorio SDP (base Censo DANE 2018) | 2018–2025 | Localidad × año (agregado desde sexo/edad) |
| `personas_pobres_ipm` / `ipm_pct` | *Hábitat en cifras en las localidades — Indicadores Calidad de Vida* (`habitat-en-cifras-...`), XLSX, indicador "Personas pobres por el índice de Pobreza Multidimensional - IPM Censo" | SDP / **Censo DANE 2018** | 2018 | Localidad |

## Decisiones y advertencias

- **El IPM de origen es un CONTEO de personas pobres**, no una tasa. Se convierte
  a incidencia (`ipm_pct`) dividiendo por la población 2018 de la misma localidad,
  para que sea comparable entre localidades de tamaños muy distintos.
- **IPM es una variable estructural de 2018**: se difunde estática a 2018–2025.
  No hay serie anual de IPM por localidad en el dato abierto.
- **Sumapaz (`20`) no tiene IPM** (`ipm_pct` nulo): no está cubierta por la
  Encuesta Multipropósito / el indicador de Hábitat (solo 19 localidades). Sí
  tiene población. El consumidor debe imputar o excluir Sumapaz para features que
  usen `ipm_pct`.
- **El IPM viene por NOMBRE de localidad** (la fuente no trae código). Se mapea a
  `cod_localidad` con un diccionario explícito nombre-normalizado → código
  (`NOMBRE_A_CODIGO` en `ingest_dane.py`); si alguna localidad no mapea, el
  ingest falla en vez de cruzar por texto libre (Regla 1).

## Reproducción

```bash
python src/ingest_dane.py   # -> data/02_intermediate/dane_contexto.parquet
```
