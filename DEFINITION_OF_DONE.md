# DEFINITION OF DONE — Alerta Ciudadana

Checklist única a nivel de **proyecto completo** (no por issue). El proyecto está
listo para entregarse cuando **todos** los ítems están marcados. Cada sección está
mapeada a los 6 criterios de evaluación de la convocatoria (`CLAUDE.md §5`).

> Revisar en equipo en el **SYNC-5** (fin de Semana 2.5), antes de entregar.

---

## 1. Funcionalidad mínima demostrable (núcleo intocable)

- [ ] La app corre end-to-end con un solo comando documentado (dataset → modelo → API → mapa).
- [ ] El **mapa de riesgo** muestra zonas de Bogotá coloreadas por nivel de riesgo desde el modelo real (no mock).
- [ ] El **canal de reporte ciudadano** acepta un reporte (tipo, ubicación, hora, descripción), lo persiste y lo muestra en el mapa.
- [ ] El **detector de anomalías** está integrado y devuelve resultado para una zona/periodo.
- [ ] No quedan endpoints sirviendo datos mock en la demo final.

## 2. Uso de datos abiertos *(criterio: 20 pts)*

- [ ] Lista final de datasets de datos.gov.co documentada con URL y fecha de última actualización (#1, #43).
- [ ] Mínimo **3 fuentes oficiales** efectivamente integradas (SIEDCO + NUSE + DIVIPOLA/DANE).
- [ ] Cruce de fuentes hecho por **código DANE**, no por nombre de texto libre.
- [ ] Diccionario de datos real publicado en `docs/data-dictionaries/`.

## 3. Análisis y rigor técnico *(criterio: 15 pts)*

- [ ] Dataset analítico unificado (zona–tiempo–delito) reproducible desde script (#9).
- [ ] Validación **espacio-temporal sin fuga** documentada (no K-fold aleatorio) (#13).
- [ ] Métricas reportadas alineadas al objetivo: **recall / F1 sobre clase de riesgo alto**, no solo accuracy (#16–#18).
- [ ] Manejo explícito del desbalance documentado (class_weight / SMOTE) (#10).
- [ ] **QA cruzada** ejecutada: Int.2 evaluó anomalías (#20) e Int.3 evaluó predictivo (#28); hallazgos documentados.

## 4. Uso de tecnologías emergentes / IA *(criterio: 20 pts)*

- [ ] Modelo predictivo entrenado, versionado (`model.joblib`) y con **model card** (#21).
- [ ] Detector de anomalías entrenado, versionado y con **model card** (#31).
- [ ] Ambos modelos superan de forma clara su baseline correspondiente.
- [ ] (Nice-to-have, no bloqueante) NLP de reportes documentado como hecho o como trabajo futuro (#29).

## 5. Impacto y escalabilidad *(criterio: 20 pts)*

- [ ] Diseño de **monitoring & model drift** y plan de re-entrenamiento documentado (#39).
- [ ] Trabajo futuro explícito en el informe: escalar a nacional, push real, NLP/GenAI.
- [ ] Discusión de cómo los reportes ciudadanos retroalimentan el modelo en el tiempo.
- [ ] Arquitectura permite añadir más ciudades sin rediseño (cruce por código DANE ya lo soporta).

## 6. Diseño, comunicación y usabilidad *(criterio: 10 pts)*

- [ ] QA de usabilidad aplicado: navegación clara, estados de carga/error (#40).
- [ ] **Aviso de privacidad / consentimiento opt-in** presente en el formulario (Ley 1581/2012) (#40).
- [ ] `README.md` raíz permite a un tercero correr el proyecto sin ayuda.
- [ ] Demo en vivo + pitch deck + video corto listos (#46).

## 7. Innovación y ética *(criterio: innovación 15 pts + requisito ético)*

- [ ] Diferenciador narrado: predictivo + reporte ciudadano verificado contra histórico (vs. solo dashboard).
- [ ] **Discusión ética** escrita: sesgo de sobre-vigilancia, estigmatización de barrios, uso responsable (#45, #11).
- [ ] Confirmado: **cero microdatos personales identificables**; solo agregados anonimizados + reportes opt-in.

## 8. Trazabilidad y cierre

- [ ] Cada entregable mapeado a ≥1 criterio de evaluación (`CLAUDE.md §5`).
- [ ] Informe final consolidado integra las secciones de los 4 integrantes (#43–#46).
- [ ] Repositorio limpio: sin datasets pesados versionados, `.gitignore` respetado, READMEs por módulo.
- [ ] Las 6 fases CRISP-ML(Q) tienen evidencia documentada (de Business Understanding a Monitoring).

---

### Regla de oro

Si hay que recortar, se conserva el **núcleo de la Sección 1** + las Secciones 2,
3 y 7. Un proyecto con menos features pero con rigor, datos abiertos reales y
discusión ética puntúa más que uno ambicioso a medio terminar. Ver el plan de
contingencia en [`CRONOGRAMA.md`](./CRONOGRAMA.md).
