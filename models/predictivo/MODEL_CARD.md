# Model card — Predictivo de riesgo (Issue #21 parcial / soporte #24)

## Model details
- **Nombre:** Alerta Ciudadana — riesgo alto por localidad × año × tipo
- **Versión:** artefact `models/predictivo/model.joblib`
- **Tipo:** clasificación binaria (XGBoost)
- **Dueño:** Integrante 2

## Intended use
Estimar si una celda (localidad, año, tipo de delito) cae en riesgo alto para
alimentar el mapa coroplético y alertas geolocalizadas en Bogotá.

## Out of scope
Micropredicción hora a hora, identificación de personas, decisiones judiciales
o policiales automatizadas sin revisión humana.

## Training data
`dataset_analitico.parquet` (SIEDCO + NUSE + DANE), train 2018–2024.

## Evaluation
Test 2025: recall 0.968 · precision 0.536 · F1 0.690 · umbral 0.560.
Ver `metrics.json`, `ROBUSTEZ.md`, `VALIDACION.md`.

## Ethical considerations
Riesgo de estigmatización territorial y de reproducir sesgo de vigilancia.
Usar como insumo de prevención/comunicación, no como veredicto sobre barrios.
