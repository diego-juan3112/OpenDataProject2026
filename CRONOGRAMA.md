# CRONOGRAMA — Alerta Ciudadana (2.5 semanas)

Plan semanal con ejecución en paralelo por integrante y **puntos de sincronización
obligatoria** del equipo completo. Los `#N` refieren a issues de [`BACKLOG.md`](./BACKLOG.md).

> **Premisa crítica:** el cuello de botella es el **dataset unificado (#9)**.
> Hasta que exista, Integrantes 2, 3 y 4 trabajan con datos crudos / mocks. El
> éxito del cronograma depende de cumplir el sync point de fin de Semana 1.

---

## Vista de alto nivel

| | Integrante 1 (Datos) | Integrante 2 (Predictivo) | Integrante 3 (Anomalías) | Integrante 4 (Despliegue) |
|---|---|---|---|---|
| **Semana 1** | #1 #2 #3 #4 #5 #6 #7 #8 **#9** | #12 (EDA crudo) #13 | #22 (EDA crudo) | #32 #33 (scaffold + mock) |
| **Semana 2** | #10 #11 | #14 #15 #16 #17 #18 #19 | #23 #24 #25 #26 #27 | #34 #35 #36 #37 |
| **Semana 2.5** | #43 (cierre) | #20 (QA cruz.) #21 #44 | #28 (QA cruz.) #30 #31 #45 / #29* | #38 #39 #40 #41 #42 #46 |

`*#29 (NLP)` = nice-to-have, solo si sobra tiempo.

---

## 🔴 Puntos de sincronización obligatoria

| Sync | Cuándo | Qué debe estar listo | Desbloquea |
|---|---|---|---|
| **SYNC-0: Kickoff** | Inicio Semana 1 | Estructura repo + contrato de taxonomía de delitos (Int.1↔2↔3) + unidad espacial (#5) | Que todos arranquen alineados |
| **SYNC-1: Dataset 🎯** | **Fin Semana 1** | `data/processed/dataset_analitico.parquet` (#9) entregado y documentado | Modelado serio de Int.2 (#16,#17) e Int.3 (#23–#25) |
| **SYNC-2: Contrato API** | Mitad Semana 1 | Contrato input/output de `/predict` y `/anomalias` (#33) acordado con Int.2 e Int.3 | Que #19/#27 entreguen el formato correcto sin retrabajo |
| **SYNC-3: Modelos `joblib`** | Fin Semana 2 | `model.joblib` predictivo (#19) y anomalías (#27) entregados a Despliegue | Integración real en la app (#38) + QA cruzada (#20,#28) |
| **SYNC-4: Integración E2E** | Inicio Semana 2.5 | App con modelos reales corriendo end-to-end (#38) | Demo, deploy y cierre (#41,#42,#46) |
| **SYNC-5: DoD review** | Fin Semana 2.5 | Checklist de `DEFINITION_OF_DONE.md` revisada en equipo | Entrega |

---

## Detalle por semana

### 🗓️ Semana 1 — Datos manda, el resto adelanta en paralelo

**Objetivo:** llegar al dataset unificado (#9) sin que nadie quede ocioso.

- **Int.1 (Datos):** ruta crítica. #1→#2 (setup) → ingestas #3–#6 en paralelo lógico → limpieza #7 → cruce #8 → **dataset #9**. Es la semana más cargada de Int.1; los demás deben proteger su foco.
- **Int.2 (Predictivo):** #12 (EDA sobre crudos de #3/#4) + #13 (protocolo de validación anti-fuga, no necesita el dataset final). **No esperar bloqueado.**
- **Int.3 (Anomalías):** #22 (EDA de series temporales sobre crudos). Forma la definición de "anomalía".
- **Int.4 (Despliegue):** #32 (scaffold FastAPI + mapa vacío) + #33 (contrato API + mock). Construye casi toda la app contra el mock sin depender de nadie.

> ⚠️ Si #9 se retrasa, **todo el cronograma se corre**. Si al día 4 de Semana 1 el
> cruce (#8) está en riesgo, recortar: menos fuentes de contexto DANE (#6 es la
> más prescindible) antes que sacrificar SIEDCO/NUSE.

### 🗓️ Semana 2 — Modelado en serio + app contra mock

**Objetivo:** modelos entrenados y serializados; app funcional contra el mock.

- **Int.1:** #10 (target + desbalance, con Int.2) y #11 (EDA de calidad + nota de sesgo). Pasa a rol de soporte/QA de datos.
- **Int.2:** #14→#15→#16→#17→#18→**#19**. Cierra modelo final y lo serializa.
- **Int.3:** #23→#24/#25→#26→**#27**. Cierra detector y lo serializa.
- **Int.4:** #34 (/predict) #35 (reportes+BD) #36 (mapa calor) #37 (formulario). App completa contra mock.

> Fin de Semana 2 = **SYNC-3**: ambos `.joblib` entregados a Despliegue.

### 🗓️ Semana 2.5 — Integración, QA cruzada, cierre y entrega

**Objetivo:** todo integrado, evaluado y empaquetado.

- **Int.4:** #38 (integrar modelos reales) → #39 (monitoring) #40 (usabilidad+privacidad) #41 (deploy) #42 (README) → #46 (demo/pitch/video).
- **Int.2:** #20 (QA cruzada del modelo de anomalías) + #21 (model card) + #44 (informe).
- **Int.3:** #28 (QA cruzada del modelo predictivo) + #30 #31 + #45 (informe+ética). #29 (NLP) **solo si sobra tiempo.**
- **Int.1:** #43 (sección de datos + diccionario consolidado).

> Fin = **SYNC-5**: revisión conjunta de la Definition of Done.

---

## Plan de contingencia (si vamos retrasados)

Recortar en este orden, **sin tocar el núcleo demostrable** (mapa de riesgo +
reporte ciudadano + 1 detector de anomalías):

1. **#29 NLP** — eliminar (ya es nice-to-have).
2. **#41 hosting público** — quedarse con demo local.
3. **#6/#15 features de contexto DANE** — usar solo features temporales/espaciales.
4. **#25 Isolation Forest** — quedarse solo con z-score (#24), más simple y rápido.
5. **#17 XGBoost** — quedarse con Random Forest (#16) si el tuning no rinde.

Lo que **NO se recorta**: dataset unificado (#9), un modelo predictivo funcional,
un detector de anomalías, la app con mapa + formulario, la QA cruzada (#20/#28) y
la discusión ética (#45). Esos cinco son lo que sostiene la evaluación.
