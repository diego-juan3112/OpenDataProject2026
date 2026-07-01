# models/clustering — Tipología de zonas (Integrante 3)

**Estado:** pendiente (Semana 2, tras el dataset analítico #9). Fase 3b de
CRISP-ML(Q).

K-Means que agrupa las 20 localidades por **perfil delictivo** (mezcla de tipos
de delito y contexto socioeconómico) y produce una **tipología interpretable**
(p. ej. "perfil hurto", "perfil violencia-intrafamiliar", "perfil bajo incidente").
No es un ranking por conteo: es una segmentación accionable que colorea y etiqueta
el mapa coroplético.

## Restricciones

- **Validación interna**: elbow / silhouette, con hiperparámetros documentados.
- **Auditoría de sesgo**: no estigmatizar zonas; la tipología describe perfiles,
  no juicios.

Artefacto de salida: `clusters.joblib` (lo carga `../../api/`).
