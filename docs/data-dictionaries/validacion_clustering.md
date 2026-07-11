# Validación interna del clustering — K-Means (Issue #28)

**Responsable:** Integrante 3 (Clustering) · **Estado:** validado contra el
modelo final de #27 · **Fecha:** 2026-07-11

Este documento valida que la segmentación de #27 (`k=3`, `n_init=10,
random_state=42`) es estable y no arbitraria. Generado corriendo
`python models/clustering/validate.py` contra `clusters.joblib` y
`features_zona.parquet` (#27) y `data/03_primary/dataset_analitico.parquet`
(#9). Los artefactos serializados no se versionan en git (regla global
`*.parquet`/`*.joblib` de `.gitignore`) — los números de este documento se
regeneran corriendo el script.

---

## 1. Silhouette por cluster

| Cluster | n | Nombre | silhouette medio | silhouette mín |
|---|---|---|---|---|
| 0 | 12 | Perfil de bajo incidente relativo | **0.498** | 0.387 |
| 1 | 2  | Perfil de alto impacto generalizado | 0.249 | 0.219 |
| 2 | 6  | Perfil hurto de bienes / ingreso alto | 0.219 | 0.037 |

El cluster grande (bajo incidente, 12 zonas) es el más cohesivo. Los otros
dos son más débiles — esperable con clusters pequeños (2 y 6 zonas) sobre 13
features: una zona del cluster "hurto de bienes" tiene silhouette casi cero
(0.037), en el límite de estar mal clasificada. Se documenta tal cual, sin
suavizar el resultado: el silhouette global de #27 (0.389) resume estos tres
valores, pero esconde que no todos los clusters son igual de sólidos.

## 2. Estabilidad ante semillas

10 semillas (`0..9`) reentrenadas y comparadas contra el modelo de
referencia (`random_state=42`) con Adjusted Rand Index (ARI: 1.0 =
partición idéntica, 0.0 = tan parecida como al azar):

| semilla | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| ARI | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

**ARI = 1.0 en las 10 semillas.** La partición es completamente estable: no
depende de la inicialización aleatoria de K-Means. Resultado fuerte a favor
de que la segmentación no es un artefacto de la semilla `random_state=42`
elegida en #27.

## 3. Por qué la tipología aporta más que ordenar zonas por conteo

Baseline trivial: cortar las 20 zonas en 3 terciles (`pd.qcut`) por el
conteo total de `conteo_siedco` (solo train, sin fuga — suma de todos los
tipos de delito y años), y comparar contra los clusters reales de K-Means
con ARI.

**ARI (K-Means real vs. terciles por conteo total) = 0.031** — prácticamente
sin relación entre las dos particiones. El crosstab lo confirma:

| perfil K-Means \ tercil conteo | bajo (0) | medio (1) | alto (2) |
|---|---|---|---|
| Alto impacto generalizado | 1 | 1 | 0 |
| Bajo incidente relativo | 4 | 2 | 6 |
| Hurto de bienes / ingreso alto | 2 | 3 | 1 |

**Ejemplo concreto: Candelaria** (perfil "alto impacto generalizado" en
K-Means) cae en el tercil **bajo** de conteo total. Es una localidad
pequeña en población con tasas por 100k habitantes muy altas, pero pocos
incidentes en términos absolutos — ordenar solo por conteo total la
escondería junto a zonas de bajo riesgo real, exactamente el error que la
tipología evita.

**Argumento:** el conteo total es una sola cifra cruda que mezcla volumen
delictivo con tamaño poblacional y no distingue tipo de delito. La
tipología de K-Means usa 13 features (11 tasas de delito por 100k, tasa de
llamadas NUSE, `ipm_nbi`), todas normalizadas por población y estandarizadas
— por eso separa, por ejemplo, "alto impacto generalizado" (alto en *todo*)
de "hurto de bienes / ingreso alto" (alto solo en delitos patrimoniales,
bajo en violencia), una distinción que un ranking de una sola dimensión no
puede capturar. Ver `clustering_perfiles.md` para la lectura completa de
cada perfil.

## 4. Conclusión

Los 3 criterios de aceptación de #28 quedan cubiertos: silhouette por
cluster reportado (con sus debilidades documentadas, no ocultas),
estabilidad perfecta ante 10 semillas distintas, y un argumento cuantitativo
(ARI=0.031) + cualitativo (Candelaria) de por qué la tipología no es
equivalente a ordenar zonas por volumen. No se encontraron motivos para
reentrenar o ajustar el modelo final de #27.
