# CRONOGRAMA — Alerta Ciudadana (3 semanas)

Plan de 3 semanas con ejecución en paralelo por integrante y **puntos de
sincronización obligatoria** del equipo completo. Los `#N` refieren a issues de
[`BACKLOG.md`](./BACKLOG.md). "Día 1" es el inicio acordado del sprint.

> **Premisa crítica 1 — Datos manda:** el cuello de botella es el **dataset
> unificado (#9)**. Hasta que exista, Integrantes 2, 3 y 4 trabajan con datos crudos
> o mocks. El cronograma depende de cumplir SYNC-1 al final de la Semana 1.

> **Premisa crítica 2 — La app móvil arranca el Día 1:** el frente móvil es el de
> mayor riesgo técnico, así que la **decisión de framework (#37) es de los primeros
> días** y la app se construye contra mocks en paralelo, no se deja para el final.

---

## Vista de alto nivel

| | Int. 1 (Datos) | Int. 2 (Predictivo + API) | Int. 3 (Clustering + Dashboard) | Int. 4 (App móvil) |
|---|---|---|---|---|
| **Semana 1** | #1 #2 #3 #4 #5 #6 #7 #8 **#9** | #13 #14 #15 #16 | #25 #26 #32 | **#37** #38 |
| **Semana 2** | #10 #11 | #17 #18 #19 #20 #21 | #27 #28 #33 | #39 #40 #41 · **#43 (checkpoint PWA)** |
| **Semana 3** | #12 (cierre) | #22 #23 #24 | #29 #30 #31 #34 #35 #36 | #42 #44 |

---

## 🔴 Puntos de sincronización obligatoria

| Sync | Cuándo | Qué debe estar listo | Desbloquea |
|---|---|---|---|
| **SYNC-0: Kickoff** | Día 1 | Estructura repo · taxonomía de delitos (Int.1↔2↔3) · unidad espacial (#5) · **decisión de framework móvil (#37)** | Que todos arranquen alineados |
| **SYNC-1: Dataset 🎯** | **Fin Semana 1** | `dataset_analitico.parquet` (#9) + `zonas_bogota.geojson` (#5) | Modelado (#17,#18,#27) + capas reales del dashboard |
| **SYNC-2: Contrato `/zonas-riesgo`** | Mitad Semana 1 | Esquema del GeoJSON del endpoint (#20) acordado entre Int.2, Int.3 e Int.4 | Que dashboard (#32) y móvil (#38) construyan contra el mismo shape |
| **SYNC-3: Modelos `joblib`** | Fin Semana 2 | `model.joblib` (#19) + `clusters.joblib` (#27) | API real (#20) → integración en ambos clientes |
| **🔴 SYNC-4: Checkpoint PWA** | **Fin Semana 2 (a más tardar Día 10)** | App nativa con GPS + notificación local en **dispositivo físico real** (#39, #40) | Decidir seguir nativa o **activar plan B PWA** (#43) con la Semana 3 íntegra para ejecutar |
| **SYNC-5: Integración E2E** | Inicio Semana 3 | API real consumida por dashboard (#34) y móvil (#42), sin mocks | Demo, informe y cierre (#44) |
| **SYNC-6: DoD review** | Fin Semana 3 | Checklist de `DEFINITION_OF_DONE.md` revisada en equipo | Entrega |

---

## Detalle por semana

### 🗓️ Semana 1 — Datos manda; modelado, dashboard y app arrancan en paralelo

**Objetivo:** llegar al dataset unificado (#9) y dejar la app móvil decidida y en pie.

- **Int. 1 (Datos):** ruta crítica. #1→#2 → ingestas #3–#6 → limpieza #7 → cruce #8 → **dataset #9** (+ `zonas_bogota.geojson` en #5).
- **Int. 2 (Predictivo + API):** #13 (EDA crudos) + #14 (protocolo anti-fuga) + #15 (baseline) + #16 (feature engineering). No espera bloqueado.
- **Int. 3 (Clustering + Dashboard):** #25 (EDA de perfiles) + #26 (features de perfil) + #32 (scaffold del dashboard contra mock). Construye el dashboard sin depender de nadie.
- **Int. 4 (App móvil):** **#37 (decisión de framework, primeros días)** + #38 (pantalla principal contra mock de `/zonas-riesgo`). La app existe y corre en Expo Go desde la Semana 1.

> ⚠️ Si #9 se retrasa, todo se corre. Si al Día 4 el cruce (#8) está en riesgo,
> recortar primero las features de contexto DANE (#6 es lo más prescindible) antes
> que sacrificar SIEDCO o NUSE.

### 🗓️ Semana 2 — Modelos entrenados, API arriba, GPS y notificación en el móvil

**Objetivo:** ambos modelos serializados, la API real respondiendo, y la app móvil
disparando la notificación local en un dispositivo físico.

- **Int. 1:** #10 (target + desbalance, con Int. 2) y #11 (EDA de calidad + nota de sesgo). Pasa a soporte/QA de datos.
- **Int. 2:** #17→#18→#19 (modelo final + `model.joblib`) → **#20 (API `/zonas-riesgo`)** → #21 (capa de datos/geofencing del móvil, con Int. 4).
- **Int. 3:** #27 (K-Means + tipología + `clusters.joblib`) → #28 (validación interna) → #33 (capas del mapa contra mock/real).
- **Int. 4:** #39 (GPS + permisos + privacidad) → #40 (notificación local al entrar a zona alta) → #41 (modo demo). **Cierra la Semana 2 con el checkpoint #43.**

> Fin de Semana 2 = **SYNC-3** (`.joblib` listos) y **🔴 SYNC-4** (checkpoint PWA).

### 🗓️ Semana 3 — Integración real, QA cruzada, ética, demo y cierre

**Objetivo:** todo integrado contra la API real (sin mocks), evaluado, y empaquetado
con foco en el informe y la demo.

- **Int. 1:** #12 (sección de datos + diccionario consolidado).
- **Int. 2:** #22 (análisis de error/robustez) + #23 (QA cruzada del clustering) + #24 (sección predictivo + evaluación compartida).
- **Int. 3:** #29 (flag z-score) + #30 (QA cruzada del predictivo) + #31 (auditoría de sesgo) + #34 (API real en dashboard) + #35 (sección clustering + ética) + #36 (reporte simulado + flag, con Int. 4).
- **Int. 4:** #42 (API real en la app + build instalable en dispositivo físico) + **#44** (monitoring + demo + pitch + video + consolidación del informe).

> Fin = **SYNC-6**: revisión conjunta de la Definition of Done.

---

## 🔴 Decisión de contingencia: PWA (fecha límite dura)

El **checkpoint #43 (SYNC-4) se evalúa a más tardar el Día 10 (fin de Semana 2)**.
Regla de decisión:

- **Si** al fin de Semana 2 la app nativa tiene **GPS + notificación local
  funcionando en un dispositivo físico real** → se continúa con la app nativa.
- **Si no** → se **activa el plan B: PWA instalable** (GPS + Notification API del
  navegador, "Agregar a pantalla de inicio"), que consume **el mismo
  `/zonas-riesgo`**. El contrato de datos no cambia; solo cambia el cliente.

Tomar la decisión ese día deja la **Semana 3 completa** para ejecutar el cliente que
gane, sin comprometer el tiempo de demo. Decidirlo más tarde sí lo comprometería.

---

## ⚠️ Riesgo abierto: NLP / convocatoria

Si se confirmara que el texto oficial exige **NLP / sistemas de recomendación como
mínimo** (no como sugerencia), el NLP de reportes pasa de nice-to-have a obligatorio
y se recorta otro frente para liberarlo (p. ej. la tipología del dashboard como tabla
estática en vez de capa interactiva). Confirmar contra el texto oficial **antes de la
Semana 2**, cuando aún hay margen.

---

## Plan de contingencia general (si vamos retrasados)

Recortar en este orden, **sin tocar el núcleo demostrable** (API `/zonas-riesgo` +
mapa de riesgo + tipología de zonas + un cliente con alerta + reporte simulado):

1. **NLP / GenAI** — ya es nice-to-have, se elimina primero.
2. **Cliente móvil nativo → PWA** (vía #43) si el GPS/notificación no cuaja a tiempo.
3. **Features de contexto DANE (#6/#16)** — usar solo features temporales/espaciales.
4. **Capa de tipología interactiva (#33)** — mostrarla como tabla/leyenda estática.
5. **Gradient Boosting (#18)** — quedarse con Random Forest (#17) si el tuning no rinde.

Lo que **NO se recorta:** dataset unificado (#9), un modelo predictivo funcional, el
clustering K-Means funcional, la API `/zonas-riesgo` consumida por ambos clientes, al
menos un cliente disparando la alerta geolocalizada, la QA cruzada (#23/#30), la
auditoría de sesgo (#31) y la discusión ética (#35). Esos sostienen los criterios de
mayor peso (datos abiertos, IA, impacto, innovación/ética).
