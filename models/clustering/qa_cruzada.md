# QA cruzada — Clustering (Issue #23)

**Revisor:** Integrante 2 (Predictivo) · **Objeto:** modelo K-Means de Integrante 3  
**Fecha:** 2026-07-12 · **Artefactos revisados:** `clustering_perfiles.md`,
`validacion_clustering.md`, `models/clustering/train.py`, `validate.py`,
`features_zona` (solo train).

> Nadie evalúa su propio modelo. Esta es la validación cruzada del clustering
> para la sección compartida de evaluación del informe.

---

## 1. ¿El k=3 se sostiene?

**Sí, con matices documentados (no ocultos).**

- El silhouette máximo está en **k=2** (0.492), pero produce un corte binario
  poco útil como tipología. Int. 3 elige **k=3 por codo de inercia +
  interpretabilidad** — decisión explícita y defendible.
- Los tres perfiles resultantes son **distintos y nombrables** (alto impacto
  generalizado / hurto de bienes / bajo incidente), no etiquetas arbitrarias.
- Hallazgo accionable: los clusters pequeños (alto impacto n=2, hurto n=6)
  tienen silhouette más débil (0.25 y 0.22). El perfil “hurto de bienes” tiene
  una zona con silhouette ≈ 0.037 (límite de mal clasificación). **No invalida
  k=3**, pero el informe debe presentar esos perfiles como *tendencias*, no
  como fronteras rígidas.

## 2. ¿Hay fuga temporal en las features?

**No se observó fuga.**

- `construir_features_zona` y `calcular_linea_base` filtran `split == train`
  (años ≤2024). El test 2025 no entra al ajuste del K-Means ni a la línea base
  del z-score.
- Las tasas se construyen con promedios anuales del histórico de train;
  `ipm_nbi` de Sumapaz se imputa con mediana de train (misma política que el
  predictivo).
- Confirmación: el contrato anti-fuga del predictivo (lags sin `conteo_siedco`
  del mismo año) es independiente; el clustering no usa la etiqueta
  `riesgo_alto`, así que no hay fuga de etiqueta hacia la tipología.

## 3. ¿La tipología es interpretable?

**Sí.**

- El contraste con terciles por conteo total (ARI ≈ 0.03) demuestra que K-Means
  **no** es un ranking disfrazado: Candelaria queda en “alto impacto” por tasas
  por 100k pese a conteo absoluto bajo — lectura útil para planeación.
- Estabilidad ante semillas: ARI = 1.0 en 10 semillas → la partición no es un
  accidente de `random_state=42`.

## 4. Comentario de validación (para la sección compartida)

> **Validación cruzada (Int. 2):** El clustering k=3 es estable (ARI=1.0 ante
> semillas), sin fuga temporal detectable, y produce tipología accionable que
> aporta más que ordenar por conteo. Se acepta para producción en la API
> `/zonas-riesgo`. Hallazgo accionable: comunicar la incertidumbre de los
> clusters pequeños (silhouette débil en “hurto de bienes”) y evitar políticas
> punitivas basadas solo en la etiqueta de perfil.

---

## Checklist de aceptación #23

- [x] Comentario de validación cruzada escrito
- [x] Al menos 1 hallazgo accionable con evidencia (silhouette débil / zona límite
  en perfil hurto de bienes; y/o ARI vs terciles = 0.03)
