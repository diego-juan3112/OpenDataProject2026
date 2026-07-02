# DEFINITION OF DONE — Alerta Ciudadana

Checklist única a nivel de **proyecto completo** (no por issue). El proyecto está
listo para entregarse cuando **todos** los ítems están marcados. Cada sección está
mapeada a los 6 criterios de evaluación de la convocatoria (`CLAUDE.md §6`).

> Revisar en equipo en el **SYNC-6** (fin de Semana 3), antes de entregar.

---

## 1. Funcionalidad mínima demostrable (núcleo intocable)

- [ ] La **API ligera `GET /zonas-riesgo`** levanta (`uvicorn api.main:app`) y devuelve un GeoJSON con riesgo + cluster por zona, cargando los `.joblib` en memoria.
- [ ] El **dashboard corre con un solo comando** (`streamlit run app/streamlit_app.py`) y **consume la API real** (no mock).
- [ ] El **mapa coroplético** muestra las localidades de Bogotá coloreadas por nivel de riesgo desde la API.
- [ ] La **capa de puntos NUSE** (o densidad por zona si no hay lat/lon) está visible sobre el coroplético.
- [ ] La **tipología de zonas (clustering)** se muestra como capa/leyenda con perfiles nombrados.
- [ ] El **reporte ciudadano simulado** acepta un reporte (tipo, ubicación, hora, descripción), lo dibuja en el mapa y dispara el **flag z-score** contra el histórico de la zona.
- [ ] La **app móvil está instalada y corriendo en al menos un dispositivo físico real** (no solo emulador).
- [ ] La app **lee el GPS en tiempo real** y **dispara la notificación local** al entrar a una zona de riesgo alto, **verificado en modo demo** de forma reproducible.
- [ ] El **endpoint `/zonas-riesgo` es consumido por ambos clientes** (dashboard y app móvil) **sin datos mock en la entrega final**.

> Si en el checkpoint (`CRONOGRAMA.md` SYNC-4) se activó el plan B, "app móvil"
> equivale a la **PWA instalable**, que debe cumplir los mismos ítems de GPS +
> notificación + consumo de la API real en un dispositivo físico.

## 2. Uso de datos abiertos *(criterio: 20 pts)*

- [ ] Lista final de datasets de datos.gov.co documentada con URL y fecha de última actualización (#1, #12).
- [ ] Mínimo **3 fuentes oficiales** efectivamente integradas (SIEDCO + NUSE + DIVIPOLA/DANE).
- [ ] Cruce de fuentes hecho por **código DANE**, no por nombre de texto libre.
- [ ] Diccionario de datos real publicado en `docs/data-dictionaries/`.
- [ ] **Documentada la naturaleza geográfica de cada fuente** (SIEDCO = polígono por localidad; NUSE = punto/dirección donde exista).

## 3. Análisis y rigor técnico *(criterio: 15 pts)*

- [ ] Dataset analítico unificado (zona–tiempo–delito) reproducible desde script (#9).
- [ ] Validación **espacio-temporal sin fuga** documentada en el predictivo (no K-fold aleatorio) (#14).
- [ ] **Validación interna del clustering** documentada (elbow/silhouette, estabilidad) (#28).
- [ ] Métricas del predictivo alineadas al objetivo: **recall / F1 sobre clase de riesgo alto**, no solo accuracy (#17–#19, #22).
- [ ] **Manejo explícito del desbalance** documentado (class_weight / SMOTE) (#10).
- [ ] **QA cruzada** ejecutada en la sección compartida de evaluación: Int. 2 revisó el clustering (#23) e Int. 3 revisó el predictivo (#30); comentarios documentados.

## 4. Uso de tecnologías emergentes / IA *(criterio: 20 pts)*

- [ ] **Modelo predictivo** entrenado, versionado (`model.joblib`) y con métricas en la sección compartida de evaluación (#24).
- [ ] **Clustering K-Means** entrenado, versionado (`clusters.joblib`) y con tipología de zonas interpretada (#27); métricas en la sección compartida (#35).
- [ ] El predictivo supera de forma clara su baseline (#15).
- [ ] El clustering aporta más que ordenar zonas por conteo (argumentado en #28).
- [ ] La **app móvil con alerta geolocalizada** funciona sobre la inferencia real servida por la API (no reglas hardcodeadas).
- [ ] (Nice-to-have, no bloqueante) NLP de reportes documentado como hecho o como trabajo futuro. **Ver riesgo abierto: si la convocatoria lo exige como mínimo, deja de ser opcional.**

## 5. Impacto y escalabilidad *(criterio: 20 pts)*

- [ ] Diseño de **monitoring & model drift** y plan de re-entrenamiento documentado (#44, `docs/monitoring.md`).
- [ ] **Un único contrato (`/zonas-riesgo`) sirve a dos clientes** (dashboard + móvil): demuestra que la arquitectura escala a más clientes sin rediseño.
- [ ] Trabajo futuro explícito en el informe: escalar a nacional, push real en segundo plano (FCM/APNs), BD persistente para reportes, NLP/GenAI.
- [ ] Discusión de cómo los reportes ciudadanos retroalimentan el modelo en el tiempo.
- [ ] Arquitectura permite añadir más ciudades sin rediseño (cruce por código DANE ya lo soporta).

## 6. Diseño, comunicación y usabilidad *(criterio: 10 pts)*

- [ ] QA de usabilidad aplicado en el dashboard: navegación clara, estados de carga/error (#36).
- [ ] **Aviso de privacidad / consentimiento opt-in** presente en el **reporte ciudadano simulado** (Ley 1581/2012) (#36). *(No se recorta.)*
- [ ] **Aviso de privacidad / consentimiento opt-in** presente en el **permiso de geolocalización de la app móvil** (#39). *(No se recorta.)*
- [ ] `README.md` raíz permite a un tercero correr API, dashboard y app móvil sin ayuda.
- [ ] Demo en vivo (dashboard + app disparando la alerta) + pitch deck + video corto listos (#44).

## 7. Innovación y ética *(criterio: innovación 15 pts + requisito ético)*

- [ ] Diferenciador narrado: predictivo + tipología de zonas + **alerta geolocalizada en el móvil** + reporte ciudadano verificado contra histórico (flag z-score) — vs. un simple dashboard.
- [ ] **Discusión ética** escrita: sesgo de sobre-vigilancia, estigmatización de barrios, uso responsable (#35, #11). *(No se recorta.)*
- [ ] **Auditoría de sesgo** ejecutada sobre predictivo y clustering: ¿replican sobre-vigilancia histórica? (#31).
- [ ] Confirmado: **cero microdatos personales identificables**; solo agregados anonimizados + reportes/GPS opt-in.

## 8. Trazabilidad y cierre

- [ ] Cada entregable mapeado a ≥1 criterio de evaluación (`CLAUDE.md §6`).
- [ ] **Informe final consolidado** integra las secciones de los 4 + la sección compartida de evaluación de modelos (#12, #24, #35, #44).
- [ ] Repositorio limpio: sin datasets pesados versionados, `.gitignore` respetado, READMEs por módulo (`src/`, `api/`, `app/`, `mobile/`).
- [ ] Las 6 fases CRISP-ML(Q) tienen evidencia documentada (de Business Understanding a Monitoring).

---

### Regla de oro

Si hay que recortar, se conserva el **núcleo de la Sección 1** + las Secciones 2, 3
y 7. Un proyecto con menos features pero con rigor, datos abiertos reales, una alerta
geolocalizada funcional y discusión ética puntúa más que uno ambicioso a medio
terminar. Ver el plan de contingencia en [`CRONOGRAMA.md`](./CRONOGRAMA.md).
