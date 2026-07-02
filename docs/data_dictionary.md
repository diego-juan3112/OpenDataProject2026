# Diccionario de datos — Alerta Ciudadana

Las variables del dataset analítico consolidado
(`data/03_primary/dataset_analitico.parquet`) y de cada fuente están
documentadas por fuente en [`data-dictionaries/`](data-dictionaries/):

| Fuente / tabla | Diccionario |
|---|---|
| SIEDCO — Delito de Alto Impacto | [`data-dictionaries/siedco.md`](data-dictionaries/siedco.md) |
| NUSE — C4 / Línea 123 | [`data-dictionaries/nuse.md`](data-dictionaries/nuse.md) |
| Localidad — geometría oficial | [`data-dictionaries/localidad.md`](data-dictionaries/localidad.md) |
| Policía Nacional (API datos.gov.co) | [`data-dictionaries/datosgov_policia.md`](data-dictionaries/datosgov_policia.md) |
| Contexto DANE/SDP (población + IPM) | [`data-dictionaries/dane_contexto.md`](data-dictionaries/dane_contexto.md) |
| Reporte de calidad (Issue #7) | [`data-dictionaries/reporte_calidad.md`](data-dictionaries/reporte_calidad.md) |

Columnas del consolidado (contrato con los Integrantes 2 y 3): `cod_localidad`,
`localidad_nombre`, `anio`, `tipo_delito`, `tipo_delito_nombre`, `conteo_siedco`,
`conteo_nuse`, `poblacion`, `ipm_nbi`, `split`.
