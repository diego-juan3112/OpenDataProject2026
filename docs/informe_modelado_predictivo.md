# Modelado predictivo de riesgo — sección de informe (Issue #24)

**Autor:** Integrante 2 · **Fase CRISP-ML:** 3–4 · **Trazabilidad:** Uso de
tecnologías emergentes / IA · Análisis y rigor técnico

---

## 1. Pregunta analítica

> Dada una celda **localidad × año × tipo de delito** en Bogotá, ¿pertenece al
> cuartil superior de incidencia registrada (riesgo alto) respecto al histórico
> del mismo tipo de delito?

La etiqueta `riesgo_alto` la define Integrante 1 (P75 estricto de `conteo_siedco`
por tipo, umbrales aprendidos solo en train). El modelo **no recalcula** el
target; predice esa etiqueta con información disponible sin fuga.

## 2. Datos y protocolo anti-fuga

- Dataset: `data/03_primary/dataset_analitico.parquet` (1.760 filas =
  20 localidades × 8 años × 11 tipos).
- **Train:** 2018–2024 (1.540) · **Test:** 2025 (220).
- Tuning interno: fit ≤2023, validación = 2024.
- **No** se usa K-fold aleatorio: mezclaría pasado y futuro.

Ver `models/predictivo/VALIDACION.md`.

## 3. Features

Se excluye a propósito `conteo_siedco` del mismo año (el target es función de
esa variable → fuga de etiqueta). Features usadas:

| Grupo | Variables |
|---|---|
| Temporal | `anio` |
| Contexto | `poblacion`, `ipm_nbi` (Sumapaz imputado con mediana train), `tasa_nuse_100k` |
| Rezagos | `lag_1/2/3`, `roll_mean_3` de conteos pasados |
| Categóricas | `cod_localidad`, `tipo_delito` (One-Hot) |

Detalle: `models/predictivo/FEATURES.md` y `DECISIONES.md`.

## 4. Modelos y selección

| Modelo | Recall | Precision | F1 (test 2025) |
|---|---|---|---|
| Baseline mayoría | 0.00 | 0.00 | 0.00 |
| Baseline zona histórica | 0.94 | 0.54 | 0.68 |
| Random Forest | 0.97 | 0.54 | 0.69 |
| **XGBoost final @ umbral 0.56** | **0.97** | **0.54** | **0.69** |

El ganador en validación 2024 fue XGBoost; se reentrenó en todo train y se
calibró el umbral maximizando F1 de la clase riesgo alto. El modelo supera al
mejor baseline en F1. Artefacto: `models/predictivo/model.joblib` +
`predict.py`.

## 5. Evaluación profunda (#22)

- **Recall alto (0.97):** 30/31 positivos de 2025 detectados (1 FN).
- **Precision moderada (0.54):** 26 falsos positivos — el sistema prefiere
  alertar de más que de menos (alineado a seguridad ciudadana).
- Curva PR y degradación ante nulos/ruido: `models/predictivo/ROBUSTEZ.md`.
- Fallos se concentran en algunas combinaciones localidad–tipo con frontera
  cercana al P75; el baseline histórico ya es fuerte porque el riesgo es
  persistente año a año.

## 6. Despliegue

El modelo se sirve en `GET /zonas-riesgo` (Issue #20) junto al clustering de
Int. 3. El móvil resuelve geofencing con `riesgoDeCoordenada` (#21).

## 7. Limitaciones y ética

1. Los datos miden **delito registrado**, no victimización real (sesgo de
   vigilancia / subregistro — ver handoff Int. 1).
2. Grano anual: no hay franja horaria en el dato abierto.
3. Solo Bogotá; escalar a otras ciudades exige el mismo cruce por código DANE.
4. El mapa no debe usarse para estigmatizar barrios ni para decisiones
   punitivas sin contexto.

## 8. QA cruzada recibida / emitida

- **Emitida (#23):** validación del clustering — aceptado con hallazgo sobre
  silhouette débil en clusters pequeños (`models/clustering/qa_cruzada.md`).
- **Recibida (#30):** pendiente de Integrante 3 en
  `docs/evaluacion_compartida.md`.

## 9. Criterios de evaluación cubiertos

| Criterio convocatoria | Cómo aporta esta sección |
|---|---|
| Tecnologías emergentes / IA (20) | XGBoost en producción + API |
| Rigor técnico (15) | Split temporal, recall/F1, anti-fuga, robustez |
| Impacto / escalabilidad (20) | Contrato estable para dashboard y móvil |
