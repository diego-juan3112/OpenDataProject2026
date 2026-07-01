# models/predictivo — Modelo de riesgo (Integrante 2)

**Estado:** pendiente (Semana 2, tras el dataset analítico #9). Fase 3a de
CRISP-ML(Q).

Random Forest / Gradient Boosting que estima el nivel de riesgo por
**localidad × año × tipo de delito** (la franja horaria no existe en el dato
abierto; ver Nota de validación en `CLAUDE.md` §1).

## Restricciones que no se recortan

- **Manejo explícito del desbalance de clases** (class_weight / SMOTE).
- **Validación espacio-temporal sin fuga**: entrenar con años ≤2024, evaluar 2025.
  Nunca K-fold aleatorio.
- **Métrica objetivo**: recall / F1 sobre la clase de riesgo alto (no accuracy).
- **Auditoría de sesgo**: evitar replicar sobre-vigilancia histórica.

Artefacto de salida: `model.joblib` (lo carga `../../api/`).
