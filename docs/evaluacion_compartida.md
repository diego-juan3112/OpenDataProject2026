# Sección compartida de evaluación

Documento vivo del informe final. Cada integrante aporta métricas de su modelo
y un compañero deja la QA cruzada (Fase 4 CRISP-ML).

---

## A. Modelo predictivo de riesgo (Integrante 2)

| Ítem | Valor |
|---|---|
| Algoritmo final | XGBoost (`n_estimators=300`, `max_depth=5`, `learning_rate=0.05`) |
| Target | `riesgo_alto` (P75 de `conteo_siedco` por tipo, umbral de train) |
| Split | train ≤2024 / test 2025 (sin K-fold aleatorio) |
| Balanceo | `scale_pos_weight` (equivalente a class_weight balanced) |
| Umbral de decisión | **0.560** (máx. F1 en val 2024) |
| Recall (test, clase riesgo) | **0.968** |
| Precision (test, clase riesgo) | **0.536** |
| F1 (test, clase riesgo) | **0.690** |
| Matriz [[TN,FP],[FN,TP]] | [[163, 26], [1, 30]] |

Detalle de error por localidad/tipo y robustez: `models/predictivo/ROBUSTEZ.md`.

### Comentario cruzado de Integrante 3 (Issue #30)

> *Pendiente — Int. 3 completa esta casilla al cerrar #30.*

---

## B. Clustering de tipología de zonas (Integrante 3)

| Ítem | Valor |
|---|---|
| Algoritmo | K-Means |
| k | **3** (codo + interpretabilidad; no silhouette máximo) |
| Silhouette global | 0.389 |
| Estabilidad (ARI vs semillas) | **1.0** (10 semillas) |
| ARI vs terciles por conteo | **0.031** (tipología ≠ ranking de volumen) |
| Perfiles | Alto impacto generalizado · Hurto de bienes / ingreso alto · Bajo incidente relativo |

Fuente: `docs/data-dictionaries/clustering_perfiles.md`, `validacion_clustering.md`.

### Comentario cruzado de Integrante 2 (Issue #23)

> El clustering k=3 es estable (ARI=1.0 ante semillas), sin fuga temporal
> detectable, y produce tipología accionable que aporta más que ordenar por
> conteo. Se acepta para producción en la API `/zonas-riesgo`. Hallazgo
> accionable: comunicar la incertidumbre de los clusters pequeños (silhouette
> débil en “hurto de bienes”) y evitar políticas punitivas basadas solo en la
> etiqueta de perfil.

Texto completo: `models/clustering/qa_cruzada.md`.

---

## C. Trazabilidad a criterios de la convocatoria

| Criterio | Evidencia |
|---|---|
| Tecnologías emergentes / IA (20) | RF/XGBoost + K-Means en producción vía API |
| Rigor técnico (15) | Split temporal, métricas recall/F1, QA cruzada, anti-fuga |
| Innovación (15) | Tipología ≠ heatmap de conteo; predictivo + alerta geolocalizada |
