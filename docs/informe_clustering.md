# Clustering de tipología de zonas + discusión ética — sección de informe (Issue #35)

**Autor:** Integrante 3 · **Fase CRISP-ML:** 3–4 · **Trazabilidad:** Innovación
y creatividad · Uso de tecnologías emergentes / IA · Impacto y escalabilidad ·
Discusión ética (restricción no recortable, `CLAUDE.md` §7)

---

## 1. Pregunta analítica

> Dadas las 20 localidades de Bogotá, ¿qué agrupaciones naturales existen por
> **perfil delictivo** (mezcla de tipos de delito, señal de llamadas NUSE y
> contexto socioeconómico), más allá de ordenar las zonas por un solo número
> de volumen total?

El clustering no es un ranking: es una segmentación no supervisada (K-Means)
que produce una **tipología interpretable**, insumo directo de `GET
/zonas-riesgo` (#20) junto al modelo predictivo de Integrante 2.

## 2. Método

- **Algoritmo:** K-Means sobre 13 features de zona (#26): 11 tasas de tipo de
  delito por 100k habitantes, tasa de llamadas NUSE por 100k y `ipm_nbi`,
  todas estandarizadas.
- **k=3**, elegido por **codo + interpretabilidad**, no por silhouette
  máximo — el silhouette más alto corresponde a k=2 (0.492) pero produce un
  corte binario poco útil como tipología (ver justificación completa en
  `docs/data-dictionaries/clustering_perfiles.md` §2).
- **Parámetros reproducibles:** `k=3, n_init=10, random_state=42`, rango
  explorado `k=2..7`, guardados dentro de `clusters.joblib`.

Generado con `python models/clustering/build_features.py` seguido de `python
models/clustering/train.py`. Detalle completo:
`docs/data-dictionaries/clustering_perfiles.md`.

## 3. Validación interna (#28)

| Chequeo | Resultado |
|---|---|
| Silhouette global | 0.389 |
| Silhouette por cluster | 0.498 (bajo incidente, 12 zonas) · 0.249 (alto impacto, 2 zonas) · 0.219 (hurto de bienes, 6 zonas) |
| Estabilidad ante semillas (ARI, 10 semillas 0–9) | **1.0** — partición idéntica en todas |
| ARI vs. terciles por conteo total (baseline trivial) | **0.031** — la tipología no equivale a ordenar por volumen |

Se documenta sin suavizar que los clusters pequeños son menos cohesivos (una
zona del cluster "hurto de bienes" tiene silhouette ≈0.037, al límite de
estar mal clasificada). Detalle completo, incluyendo el crosstab contra el
baseline de terciles y el ejemplo de Candelaria:
`docs/data-dictionaries/validacion_clustering.md`.

## 4. Tipología accionable

| Perfil | n zonas | Localidades | Lectura para planeación |
|---|---|---|---|
| **Alto impacto generalizado** | 2 | Candelaria, Los Mártires | Tasas altas en *todos* los tipos de delito; requieren atención transversal, no focalizada en un solo tipo. |
| **Hurto de bienes / ingreso alto** | 6 | Antonio Nariño, Barrios Unidos, Chapinero, Puente Aranda, Santa Fe, Teusaquillo | Alto solo en delitos patrimoniales, bajo en violencia interpersonal; el foco es prevención situacional del hurto, no violencia social. |
| **Bajo incidente relativo** | 12 | Bosa, Ciudad Bolívar, Engativá, Fontibón, Kennedy, Rafael Uribe Uribe, San Cristóbal, Suba, Sumapaz, Tunjuelito, Usaquén, Usme | Tasas por debajo del promedio en casi todos los tipos; grupo heterogéneo en lo socioeconómico, homogéneo solo en tasa relativa baja. |

Regla de nombrado (por centroides, no por índice de cluster) e implementación:
`models/clustering/clustering.py::nombrar_clusters`. Lectura completa por
perfil (1 párrafo cada uno): `docs/data-dictionaries/clustering_perfiles.md`
§4.

## 5. Despliegue

El cluster + `nombre_perfil` se sirve junto al riesgo predictivo en `GET
/zonas-riesgo` (#20). El dashboard lo consume como capa de tipología
independiente, con tooltip en lenguaje no técnico (#33/#34). El móvil no
consume el cluster directamente hoy — `riesgoDeCoordenada` (#21) solo resuelve
`nivel_riesgo`; exponer la tipología en el cliente móvil queda como trabajo
futuro.

## 6. Discusión ética — auditoría de sesgo (#31)

La discusión de sesgo/estigmatización **no se recorta** (`CLAUDE.md` §7). La
auditoría comparó la intensidad de registro (SIEDCO) contra un proxy
independiente (llamadas NUSE al 123) y contexto socioeconómico (`ipm_nbi`,
población), y encontró:

1. **Sesgo de escala poblacional (predictivo).** `riesgo_alto` se define
   sobre conteo crudo, no tasa per cápita: Candelaria tiene la tasa de
   delito por habitante más alta de Bogotá (confirmada por NUSE) y **nunca**
   fue clasificada `riesgo_alto`, mientras Kennedy (tasa 6× menor) lo fue 75
   veces. La correlación entre frecuencia de `riesgo_alto` y tasa real por
   habitante es **negativa** (r=−0.371).
2. **Inconsistencia entre predictivo y clustering.** El clustering (basado en
   tasas, no conteo crudo) sí identifica correctamente a Candelaria y Los
   Mártires como "alto impacto generalizado" — en el mismo mapa, un usuario
   vería contradicción entre la capa de riesgo y la de tipología para la
   misma localidad si no se aclara la diferencia en el dashboard.
3. **Zona comercial/tránsito vs. riesgo para residentes.** Las localidades de
   mayor tasa por habitante son también centros comerciales/turísticos con
   alta afluencia flotante; una tasa "por habitante residente" puede
   sobreestimar el riesgo percibido para quien vive ahí.

**Recomendaciones de uso responsable** (no usar `riesgo_alto` para asignar
recursos policiales de forma automática; no presentar riesgo y tipología como
una sola señal; no usar el mapa para vivienda/seguros/estigmatización de
barrios; no tratar el perfil de cluster como veredicto fijo; no leer "alto
riesgo" céntrico como riesgo proporcional para residentes). Texto completo,
con tablas de correlación y evidencia: `docs/auditoria_sesgo.md`.

## 7. QA cruzada recibida / emitida

- **Recibida (#23, de Integrante 2):** el clustering se acepta para
  producción — estable (ARI=1.0), sin fuga temporal detectable, tipología
  accionable — con el hallazgo de comunicar la incertidumbre de los clusters
  pequeños y evitar políticas punitivas basadas solo en la etiqueta de
  perfil. Texto completo: `models/clustering/qa_cruzada.md`.
- **Emitida (#30, a Integrante 2):** revisión del predictivo — sin fuga
  temporal clásica, métrica correcta, con el hallazgo de que el modelo apenas
  supera al baseline histórico y de un sesgo de escala poblacional no
  documentado en `MODEL_CARD.md` (ver también §6 arriba). Texto completo:
  `models/predictivo/qa_cruzada.md`.

## 8. Métricas en la sección compartida

Las métricas de clustering (silhouette, ARI, tamaños de cluster) y el
comentario cruzado de Integrante 2 (#23) ya están consolidados en
`docs/evaluacion_compartida.md` §B, junto a la auditoría de sesgo en §D — no
se duplican en esta sección.

## 9. Criterios de evaluación cubiertos

| Criterio convocatoria | Cómo aporta esta sección |
|---|---|
| Innovación y creatividad (15) | Tipología interpretable de 3 perfiles, no un ranking de conteo — ARI=0.031 contra el baseline trivial lo confirma cuantitativamente. |
| Uso de tecnologías emergentes / IA (20) | K-Means en producción vía `GET /zonas-riesgo`, validado internamente (codo, silhouette, estabilidad ante semillas). |
| Impacto y escalabilidad (20) | Contrato estable (`cluster` + `nombre_perfil`) consumido por dashboard y disponible para el móvil; mismo pipeline reproducible con `train.py`. |
| Análisis y rigor técnico / ética (restricción §7) | Auditoría de sesgo con evidencia cuantitativa (correlaciones, casos concretos) y 5 recomendaciones explícitas de uso responsable — no se recorta. |
