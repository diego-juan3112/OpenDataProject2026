# Inventario validado de fuentes — Alerta Ciudadana

**Responsable:** Integrante 1 (Datos) · **Validado:** 2026-06-30 (Issue #1)

Las tres fuentes oficiales fueron **verificadas contra los datos reales** (no
contra las descripciones del portal). Todas son descargables por script desde
`datosabiertos.bogota.gov.co` (CKAN) → el pipeline es reproducible (Regla 4).

| Fuente | Diccionario | Grano espacial | Grano temporal | Consumo | Estado |
|---|---|---|---|---|---|
| SIEDCO — Delito de Alto Impacto | [`siedco.md`](data-dictionaries/siedco.md) | Localidad (20) | **Anual** 2018–2025 | GeoJSON, portal Bogotá (federado en datos.gov.co) | ✅ |
| NUSE — C4 / Línea 123 | [`nuse.md`](data-dictionaries/nuse.md) | Localidad + UPZ | Mensual 2015–2026 | CSV, portal Bogotá (federado en datos.gov.co) | ✅ |
| Localidad — geometría | [`localidad.md`](data-dictionaries/localidad.md) | Localidad (20) | Estático | SHP, portal Bogotá | ✅ |
| Policía Nacional — hurto / VIF | [`datosgov_policia.md`](data-dictionaries/datosgov_policia.md) | Municipio (Bogotá) | Diario→anual 2018–2025 | **API nativo de datos.gov.co (Socrata)** | ✅ |
| Contexto DANE/SDP — población + IPM | [`dane_contexto.md`](data-dictionaries/dane_contexto.md) | Localidad (20) | Población anual 2018–2025 · IPM Censo 2018 | CSV + XLSX, portal Bogotá | ✅ |

**Limpieza y trazabilidad:** el reporte de calidad por fuente (filas originales →
tras limpieza + razón de cada descarte) está en
[`reporte_calidad.md`](data-dictionaries/reporte_calidad.md) (Issue #7).

> **Sobre "Uso de datos abiertos" (criterio de 20 pts):** el proyecto consume
> `datos.gov.co` de las dos formas: (1) datasets **catalogados/federados** ahí cuyo
> archivo sirve el portal distrital (SIEDCO, NUSE), y (2) un dataset consumido
> **directamente por el API oficial de datos.gov.co** (microdatos Policía), que
> además **valida por triangulación** las cifras de SIEDCO (coincidencia ≤0.7 % en
> hurto a personas 2018–2024). Trazabilidad de cada fuente en su diccionario.

## Llave de cruce (Regla 1)

Todas las fuentes se cruzan por el **código de localidad de Bogotá** (2 dígitos,
`01`–`20`), normalizado como string con cero a la izquierda. **Nunca** por nombre:
los nombres varían entre fuentes (p. ej. SIEDCO `"Suba"` vs. SHP `"USAQUEN"`, con y
sin tildes, distinta capitalización). El código DIVIPOLA nacional de Bogotá es
`11001` (municipio); se conserva en la geometría para permitir escalar a más
municipios, pero el cruce intraurbano es por código de localidad.

## Hallazgos de validación que ajustaron el diseño

Documentados también en la *Nota de validación de fuentes* de `CLAUDE.md` §1:

1. **NUSE no es punto georreferenciado**, sino agregado por localidad/UPZ × mes ×
   tipo. La "capa de puntos / tiempo real" se reencuadró a **densidad por UPZ**.
2. **No existe franja horaria** en ninguna fuente abierta (SIEDCO anual, NUSE
   mensual, microdatos Policía con fecha sin hora). Variable objetivo redefinida a
   **zona (localidad) – año – tipo de delito**.
3. **SIEDCO es anual**; la validación espacio-temporal del predictivo entrena con
   años ≤2024 y evalúa 2025 (2026-YTD reservado como validación futura).

## Cómo se descargan / reproducen

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
python src/ingest_siedco.py      # -> data/02_intermediate/siedco_delitos.parquet
python src/ingest_nuse.py        # -> data/02_intermediate/nuse_incidentes.parquet  (descarga 112 MB)
python src/ingest_divipola.py    # -> data/02_intermediate/localidades.geojson
python src/ingest_datosgov.py    # -> data/02_intermediate/datosgov_policia.parquet (API datos.gov.co)
```

Cada script es idempotente: si el archivo crudo ya existe en `data/01_raw/`, no lo
vuelve a descargar (usar `--force` para re-descargar).
