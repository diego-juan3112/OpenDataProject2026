# Auditoría de sesgo — predictivo + clustering (Issue #31)

**Autor:** Integrante 3 · **Fecha:** 2026-07-13 · **Alcance:** ambos modelos
(predictivo de Integrante 2, clustering propio) — **la discusión de
sesgo/estigmatización no se recorta** (`CLAUDE.md` §7).

Pregunta central: ¿las zonas de "alto riesgo" (predictivo) y los clusters
"peligrosos" (clustering) coinciden con zonas **históricamente más
patrulladas/registradas**, y no necesariamente con más delito real?

Método: se comparó la intensidad de registro policial (SIEDCO,
`conteo_siedco`) contra un proxy **independiente** — las llamadas
ciudadanas al 123 (NUSE, `conteo_nuse`), que no dependen de la discreción
policial de registrar un hecho — y contra contexto socioeconómico
(`ipm_nbi`, población). Datos: `data/03_primary/dataset_analitico.parquet`,
solo `split == "train"` (2018–2024), agregado por localidad.

---

## 1. Comparación: intensidad de registro vs. proxies independientes

| localidad | tasa SIEDCO /100k | tasa NUSE /100k | ipm_nbi | veces `riesgo_alto`=1 (de ~88) |
|---|---|---|---|---|
| Candelaria | **118,631** | 81,451 | 6.12 | **0** |
| Los Mártires | **113,298** | 88,890 | 8.54 | 5 |
| Santa Fe | 84,858 | 61,294 | 11.06 | 6 |
| Teusaquillo | 60,703 | 52,466 | 0.68 | 6 |
| Barrios Unidos | 50,978 | 58,482 | 2.20 | 0 |
| Engativá | 22,901 | 34,011 | 3.76 | 60 |
| Usaquén | 21,460 | 30,407 | 2.42 | 22 |
| Kennedy | 20,377 | 31,106 | 5.38 | **75** |
| Suba | 16,968 | 28,017 | 4.01 | **74** |
| Ciudad Bolívar | 17,214 | 28,703 | 11.62 | 41 |

(tabla completa de 20 localidades corrida en vivo antes de escribir este
documento; se muestran las filas más ilustrativas)

**Correlaciones (20 localidades, train):**
- Tasa SIEDCO/100k vs. tasa NUSE/100k: **r = 0.938** (muy fuerte).
- Tasa SIEDCO/100k vs. `ipm_nbi` (pobreza): **r = −0.052** (prácticamente nula).
- Tasa NUSE/100k vs. `ipm_nbi`: **r = −0.089** (prácticamente nula).
- Veces `riesgo_alto=1` vs. población: **r = 0.943** (muy fuerte).
- Veces `riesgo_alto=1` vs. tasa SIEDCO/100k (la tasa *real* de delito por
  habitante): **r = −0.371** (negativa).

**Lectura:** SIEDCO y NUSE — dos canales de registro **independientes**
(policial vs. ciudadano) — coinciden fuertemente (r=0.94). Esto es
**evidencia en contra** de que el conteo policial sea, en el agregado, un
artefacto puro de vigilancia diferencial: si lo fuera, esperaríamos que
NUSE (que no depende de la discreción policial) no corroborara el mismo
patrón, y sí lo corrobora. Tampoco hay correlación relevante con pobreza
(`ipm_nbi`) — las zonas de mayor tasa de delito **no** son las más pobres
(Candelaria ipm_nbi=6.1, Los Mártires=8.5, frente a Usme=13.95 o Ciudad
Bolívar=11.6 con tasas mucho más bajas).

**Pero** la señal que realmente alimenta el modelo predictivo
(`riesgo_alto`, ver hallazgo #1 abajo) **no** es la tasa por habitante, y
ahí sí aparece un sesgo claro y cuantificable.

---

## 2. Riesgo de sesgo #1 — sesgo de escala poblacional (predictivo)

**Evidencia directa de la tabla de arriba:** Candelaria tiene la tasa de
delito por habitante **más alta de las 20 localidades** (118,631/100k,
confirmada de forma independiente por NUSE: 81,451/100k) y sin embargo
**nunca** fue clasificada `riesgo_alto=1` en 8 años × 11 tipos de delito
(~88 combinaciones). Kennedy, con una tasa **~6 veces menor** (20,377/100k),
fue clasificada `riesgo_alto=1` **75 veces** — más que cualquier otra
localidad.

**Causa raíz (confirmada en la QA de #30):** `riesgo_alto` se define sobre
el **conteo crudo** de `conteo_siedco` (percentil 75 por tipo de delito),
no una tasa per cápita. Kennedy (población ≈1.07M) acumula conteos
absolutos altos solo por su tamaño; Candelaria (población ≈17,000) nunca
cruza ese umbral absoluto aunque su tasa por habitante sea la más alta de
la ciudad. La correlación r=−0.371 entre "veces riesgo_alto" y la tasa real
de delito por habitante lo confirma cuantitativamente: el indicador que ve
el ciudadano en el mapa está **inversamente relacionado** con el riesgo real
por habitante en el extremo (localidades pequeñas de alta tasa).

**Riesgo de estigmatización:** el efecto es doble y va en las dos
direcciones. (a) Localidades grandes (Kennedy, Suba, Engativá) quedan
etiquetadas como "alto riesgo" con mucha frecuencia por su tamaño, no
necesariamente porque vivir ahí sea más peligroso por habitante —
estigmatización de zonas populosas y de estrato medio/bajo. (b) Localidades
pequeñas de alta tasa real (Candelaria, Los Mártires — zonas céntricas)
quedan sistemáticamente **invisibilizadas** en el mapa de riesgo, pese a
tener el problema más agudo por habitante.

---

## 3. Riesgo de sesgo #2 — inconsistencia entre predictivo y clustering sobre las mismas zonas

El clustering (Issue #27) usa **tasas por 100k** (no conteo crudo) como
features, y por eso sí detecta correctamente a Candelaria y Los Mártires
como **"Perfil de alto impacto generalizado"** (ver
`docs/data-dictionaries/clustering_perfiles.md`) — el perfil de mayor
intensidad de la tipología.

Esto significa que, en el **mismo mapa** (`GET /zonas-riesgo`, #20, combina
ambas señales), un usuario vería: Candelaria marcada como perfil de
**"alto impacto generalizado"** por la capa de tipología, pero **rara vez o
nunca** en rojo por la capa de riesgo predictivo. Dos modelos entrenados
sobre el mismo dataset, con definiciones distintas de "intensidad"
(conteo crudo vs. tasa), producen lecturas contradictorias sobre la misma
localidad. Sin una aclaración explícita en el dashboard, esa contradicción
se puede leer como "el sistema no sabe lo que dice" o, peor, como que
Candelaria es "segura" porque el predictivo no la marca — reforzando
exactamente la invisibilización del hallazgo #1.

---

## 4. Riesgo de sesgo #3 — delito de zona comercial/tránsito vs. riesgo para residentes

Las localidades con mayor tasa SIEDCO/NUSE por habitante (Candelaria, Los
Mártires, Santa Fe, Teusaquillo) son también los centros
comercial/institucional/turístico de Bogotá, con población residente
pequeña pero enorme afluencia diaria de personas que no viven ahí (oficinas,
comercio, universidades, turismo). Una tasa "por habitante" calculada con
población **residente** en el denominador **sobreestima** el riesgo por
persona cuando la mayoría de los hechos ocurren contra población flotante,
no contra quienes viven en la localidad — y estas zonas centrales también
concentran población en situación de calle y trabajo informal, que puede
verse desproporcionadamente afectada por cualquier respuesta de "alto
riesgo" (mayor presencia policial, desalojos) sin ser la población que el
sistema pretende proteger. No se puede cuantificar sin datos de población
flotante (no disponibles en fuentes abiertas), pero es un supuesto
metodológico que ninguno de los dos modelos declara explícitamente hoy.

---

## 5. Recomendaciones de uso responsable — qué NO debe hacerse con el mapa

1. **No usar `riesgo_alto` del predictivo para asignar recursos policiales
   de forma automática o proporcional.** Sub-representa zonas pequeñas de
   alta tasa real (Candelaria, Los Mártires) y sobre-representa zonas
   grandes de tasa moderada (Kennedy, Suba) — ver hallazgo #1.
2. **No presentar la capa de riesgo y la de tipología como una sola
   señal.** Miden cosas distintas (conteo crudo vs. tasa por 100k) y pueden
   contradecirse en la misma localidad (hallazgo #2) — el dashboard debe
   aclarar esta diferencia en el tooltip/leyenda, no solo en la
   documentación técnica.
3. **No usar el mapa para decisiones de vivienda, seguros, inversión
   inmobiliaria o estigmatización pública de barrios** (ya declarado como
   "out of scope" en `MODEL_CARD.md`; se reitera aquí con evidencia
   concreta de por qué el indicador puede ser engañoso).
4. **No tratar la etiqueta de perfil del clustering como un veredicto
   fijo o exhaustivo** — recomendación ya emitida por Integrante 2 en la QA
   cruzada de #23 (`models/clustering/qa_cruzada.md`), se reitera aquí
   porque aplica igual a esta auditoría más amplia.
5. **No interpretar "alto riesgo" en zonas céntricas como riesgo
   proporcional para sus residentes** sin aclarar que gran parte del
   conteo puede corresponder a población flotante, no residente
   (hallazgo #3).

---

## Checklist de aceptación #31

- [x] Comparación entre intensidad de registro (SIEDCO) y proxys de delito
  real / contexto (NUSE, `ipm_nbi`, población) — con correlaciones reales.
- [x] Al menos 2 riesgos de sesgo/estigmatización identificados con
  evidencia (3 identificados: sesgo de escala poblacional, inconsistencia
  predictivo/clustering, y conflación zona comercial vs. riesgo residente).
- [x] Recomendaciones de uso responsable (5 recomendaciones concretas de
  qué NO hacer con el mapa).
