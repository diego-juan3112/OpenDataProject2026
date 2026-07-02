# Reporte de calidad — limpieza consolidada (Issue #7)

Generado por `src/data_cleaning.py`. Filas negativas = descartes.

| Fuente | Paso | Δ filas | Razón |
|---|---|---:|---|
| SIEDCO | filas originales | +1,760 |  |
| SIEDCO | filas finales | +1,760 | 11 tipos de delito · 20 localidades · 2018–2025 |
| NUSE | filas originales | +763,074 | 20,996,584 incidentes |
| NUSE | descartar cod=99 (Sin Localización) | -7,128 | 149,930 incidentes = 0.71% del total sin localidad |
| NUSE | descartar filas basura | -13 | códigos inválidos: ['-0'] |
| NUSE | Sumapaz (20) CONSERVADO — posible outlier | +0 | solo 488 incidentes en toda la serie |
| NUSE | filas finales | +755,933 | 20,846,632 incidentes · 20 localidades · taxonomía NUSE (138 tipos, separada de SIEDCO) |
