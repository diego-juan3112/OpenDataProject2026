# Protocolo de validación espacio-temporal (Issue #14)

## Cortes
- **Train:** años <= 2024 (columna `split == 'train'`).
- **Test:** año 2025 (`split == 'test'`).
- **Tuning:** fit <= 2023, validación = 2024.

## Por qué no K-fold aleatorio
Un shuffle mezcla filas de 2018 con 2025: el modelo vería el 'futuro'
durante el entrenamiento (fuga temporal) y las métricas quedarían
infladas. En datos espacio-temporales el corte debe respetar el orden
del tiempo: entrenar en el pasado y evaluar en el futuro.

## Función
`src/model_training.py::temporal_split()` y `temporal_tune_split()`.

## Modelo final
- Familia: **xgboost**
- Hiperparámetros: `{'n_estimators': 300, 'max_depth': 5, 'learning_rate': 0.05}`
- Umbral de decisión: **0.560**
- Test recall=0.968 F1=0.690
