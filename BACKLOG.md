# BACKLOG — Alerta Ciudadana

Backlog completo de issues repartido entre los 4 integrantes, calibrado para
**2.5 semanas** de trabajo en equipo académico (part-time). Cada integrante
tiene **11–12 issues** con carga comparable.

> **Cómo usar este archivo:** cada bloque `###` es un issue listo para copiarse a
> GitHub Issues (o crearse con `gh issue create`). La numeración `#N` es global y
> se usa en los campos *Depende de* / *Bloquea a*.

---

## ⚠️ Recorte de alcance acordado (leer antes de empezar)

El alcance literal de `CLAUDE.md` ("nacional" + app en tiempo real + NLP + GenAI)
es de **2–3 meses**, no 2–3 semanas. Para entregar algo demostrable y defendible,
el equipo acordó estos **recortes explícitos**:

| Aspecto | CLAUDE.md (ideal) | Compromiso para la entrega |
|---|---|---|
| Geografía | Nacional, drill-down depto→municipio | **Solo Bogotá** (PoC; única ciudad con NUSE/C4) |
| Reporte ciudadano | Tiempo real + push notifications | **Form-based MVP** (sin push del SO ni feed en vivo) |
| IA obligatoria | Predictivo + Anomalías + NLP + GenAI | **Predictivo + Anomalías** |
| NLP / GenAI | Módulos del sistema | **Nice-to-have NO bloqueantes** |

Estos recortes están marcados en los issues afectados. El alcance nacional, push
real y NLP/GenAI quedan documentados como **trabajo futuro** en el informe (suma
puntos en "Impacto y escalabilidad").

---

## Leyenda

- **[DATOS]** Integrante 1 · **[PRED]** Integrante 2 · **[ANOM]** Integrante 3 · **[APP]** Integrante 4
- 🟢 puede empezar día 1 (sin bloqueo) · 🟡 bloqueado por dependencia · 🔵 cierre/entrega

---

# 🟦 INTEGRANTE 1 — DATOS (Fase 2: Data Engineering)

### [DATOS] #1 — Validar y cerrar inventario de datasets (Fase 1)

**Asignado a:** Integrante 1 (Datos)
**Fase CRISP-ML:** 1
**Estimación:** 0.5 día
**Depende de:** ninguno 🟢
**Bloquea a:** #3, #4, #5, #6

**Descripción:**
Verificar en datos.gov.co la disponibilidad, vigencia y formato exacto de cada
fuente para Bogotá (SIEDCO, NUSE C4, DIVIPOLA, DANE). Confirmar URLs y fecha de
última actualización. Cerrar la Fase 1 como validación, no como construcción.

**Criterios de aceptación:**
- [ ] Tabla en `docs/business-understanding.md` con cada dataset: nombre, entidad, URL, fecha de última actualización, formato, granularidad.
- [ ] Cada fuente marcada como "disponible y usable" o "descartada" (con razón).
- [ ] Rango temporal real del histórico SIEDCO para Bogotá documentado.

**Notas técnicas:**
Ver tabla de fuentes en `CLAUDE.md §2`. Si una fuente no existe/no es usable para
Bogotá, proponer reemplazo y notificar al equipo de inmediato (afecta modelado).

---

### [DATOS] #2 — Setup del módulo de datos y estructura `data/`

**Asignado a:** Integrante 1 (Datos)
**Fase CRISP-ML:** 2
**Estimación:** 0.5 día
**Depende de:** ninguno 🟢
**Bloquea a:** #3, #4, #5, #6

**Descripción:**
Preparar `data-engineering/`: `requirements.txt` del pipeline, estructura de
scripts, y convención de carpetas `data/raw → interim → processed`. Definir
formato de intercambio del dataset final (Parquet).

**Criterios de aceptación:**
- [ ] `data-engineering/requirements.txt` con pandas, geopandas, pyarrow, etc.
- [ ] README corto en `data-engineering/` explicando el flujo del pipeline.
- [ ] `.gitignore` confirmado: `data/raw|interim|processed` no se versionan.

---

### [DATOS] #3 — Ingesta SIEDCO (delitos seguridad y convivencia, Bogotá)

**Asignado a:** Integrante 1 (Datos)
**Fase CRISP-ML:** 2
**Estimación:** 1 día
**Depende de:** #1, #2
**Bloquea a:** #7, #8

**Descripción:**
Descargar y cargar el dataset núcleo (hurtos, homicidios, lesiones, violencia
intrafamiliar, delitos sexuales, etc.) filtrado a Bogotá. Script reproducible que
guarda en `data/raw/` y carga a DataFrame.

**Criterios de aceptación:**
- [ ] Script `data-engineering/ingest_siedco.py` reproducible (descarga o lee de `data/raw/`).
- [ ] Datos filtrados a Bogotá, con conteo de filas y rango de fechas reportados.
- [ ] Columnas clave identificadas: fecha/hora, tipo de delito, código municipio, modalidad, lugar.

**Notas técnicas:**
Cruzar por **código DANE de municipio**, nunca por nombre de texto libre (ver `CLAUDE.md §4.2`).

---

### [DATOS] #4 — Ingesta NUSE C4 Línea 123 (Bogotá)

**Asignado a:** Integrante 1 (Datos)
**Fase CRISP-ML:** 2
**Estimación:** 1 día
**Depende de:** #1, #2
**Bloquea a:** #7, #8

**Descripción:**
Cargar incidentes tramitados C4 (línea 123) georreferenciados de Bogotá. Es la
fuente más cercana a un "feed en tiempo real" y aporta lat/lon a nivel incidente.

**Criterios de aceptación:**
- [ ] Script `data-engineering/ingest_nuse.py` reproducible.
- [ ] Coordenadas (lat/lon) validadas dentro del bounding box de Bogotá.
- [ ] Tipos de incidente mapeados/normalizados a categorías comparables con SIEDCO.

---

### [DATOS] #5 — Ingesta DIVIPOLA + geometrías de Bogotá

**Asignado a:** Integrante 1 (Datos)
**Fase CRISP-ML:** 2
**Estimación:** 1 día
**Depende de:** #1, #2
**Bloquea a:** #8

**Descripción:**
Obtener códigos DIVIPOLA (DANE) y geometrías de Bogotá a nivel localidad (y barrio
si está disponible) en GeoJSON/Shapefile, para definir las "zonas" del modelo.

**Criterios de aceptación:**
- [ ] GeoDataFrame de localidades/UPZ de Bogotá cargado con GeoPandas.
- [ ] Cada zona con su código DANE y geometría válida (sin geometrías nulas/inválidas).
- [ ] Definida la unidad espacial del proyecto (localidad vs UPZ vs grid) y justificada.

**Notas técnicas:**
La unidad espacial elegida será la "zona" del dataset zona–tiempo–delito. Decidir
con Integrantes 2 y 3 (granularidad vs. volumen de datos por celda).

---

### [DATOS] #6 — Ingesta variables demográficas/socioeconómicas DANE

**Asignado a:** Integrante 1 (Datos)
**Fase CRISP-ML:** 2
**Estimación:** 1 día
**Depende de:** #1, #2
**Bloquea a:** #9

**Descripción:**
Cargar variables de contexto por zona (densidad poblacional, NBI/pobreza
multidimensional) **agregadas y anonimizadas** para enriquecer el modelo. Nunca
microdatos identificables (ver `CLAUDE.md §2`).

**Criterios de aceptación:**
- [ ] Variables de contexto unidas a la unidad espacial por código DANE.
- [ ] Confirmado que todo es agregado a nivel zona (cero datos personales).
- [ ] Documentado el año/fuente de cada variable socioeconómica.

---

### [DATOS] #7 — Limpieza, normalización y diccionario de datos real

**Asignado a:** Integrante 1 (Datos)
**Fase CRISP-ML:** 2
**Estimación:** 1.5 días
**Depende de:** #3, #4
**Bloquea a:** #8, #9

**Descripción:**
Limpiar cada fuente: tipos de datos, nulos, duplicados, normalización de
categorías de delito entre SIEDCO y NUSE, parsing de fecha/hora a franjas
horarias. Documentar el diccionario de datos real por fuente.

**Criterios de aceptación:**
- [ ] Reporte de calidad por fuente (% nulos, duplicados, valores fuera de rango).
- [ ] Categorías de delito unificadas en una taxonomía común documentada.
- [ ] Franja horaria derivada (ej. madrugada/mañana/tarde/noche) y día de semana.
- [ ] `docs/data-dictionaries/` con un `.md` por fuente (columna, tipo, descripción, dominio).

**Notas técnicas:**
Esta taxonomía común de delitos la consumen Integrantes 2 y 3. Acordarla con ellos antes de cerrar.

---

### [DATOS] #8 — Cruce geográfico de fuentes por código DANE

**Asignado a:** Integrante 1 (Datos)
**Fase CRISP-ML:** 2
**Estimación:** 1.5 días
**Depende de:** #5, #7
**Bloquea a:** #9

**Descripción:**
Unir SIEDCO, NUSE y contexto DANE a la unidad espacial (spatial join de los
incidentes georreferenciados de NUSE; join por código para SIEDCO). Garantizar
que cada incidente quede asignado a una zona.

**Criterios de aceptación:**
- [ ] Spatial join NUSE→zona con GeoPandas; % de incidentes sin zona asignada reportado y <5%.
- [ ] Join SIEDCO→zona por código DANE sin pérdida de filas no justificada.
- [ ] Tabla de validación: conteos por zona coherentes (sin zonas vacías inesperadas).

**Notas técnicas:**
Usar el mismo CRS en todas las geometrías antes del join (ej. EPSG:4326 → proyectar a métrico si se calculan áreas).

---

### [DATOS] #9 — Construir dataset analítico unificado (zona–tiempo–delito) 🎯

**Asignado a:** Integrante 1 (Datos)
**Fase CRISP-ML:** 2
**Estimación:** 2 días
**Depende de:** #6, #8
**Bloquea a:** #13, #15, #16, #23, #24, #25 (**ENTREGABLE CLAVE — fin Semana 1**)

**Descripción:**
Construir la tabla analítica final: una fila por **(zona × franja temporal × tipo
de delito)** con conteo de incidentes + variables de contexto. Este es el insumo
que desbloquea el modelado serio de Integrantes 2 y 3.

**Criterios de aceptación:**
- [ ] `data/processed/dataset_analitico.parquet` generado por `build_dataset.py` reproducible.
- [ ] Esquema documentado: claves (zona, periodo, tipo_delito), features de contexto, target.
- [ ] Sin fuga temporal en la construcción (no usar info del futuro en una fila pasada).
- [ ] Entregado al equipo con un notebook de ejemplo de carga + descripción de columnas.

**Notas técnicas:**
**Este es el sync point de fin de Semana 1.** Avisar al equipo en cuanto esté listo.

---

### [DATOS] #10 — Definir variable objetivo y manejo de desbalance

**Asignado a:** Integrante 1 (Datos)
**Fase CRISP-ML:** 2–3
**Estimación:** 1 día
**Depende de:** #9
**Bloquea a:** #14

**Descripción:**
Definir cómo se etiqueta "riesgo alto" (umbral de conteo / percentil por zona), y
caracterizar el desbalance de clases. Proponer estrategia (class_weight, SMOTE) en
conjunto con Integrante 2.

**Criterios de aceptación:**
- [ ] Definición de la clase objetivo documentada y justificada (con `CLAUDE.md §4.2`).
- [ ] Distribución de clases reportada (ratio de desbalance).
- [ ] Recomendación de técnica de balanceo acordada con Integrante 2.

---

### [DATOS] #11 — EDA de calidad de datos + apoyo QA (Fase 4)

**Asignado a:** Integrante 1 (Datos)
**Fase CRISP-ML:** 4
**Estimación:** 1 día
**Depende de:** #9
**Bloquea a:** ninguno

**Descripción:**
Notebook de EDA de calidad: distribuciones, mapas de cobertura por zona, posibles
sesgos de vigilancia (zonas con más registros por más policía, no más delito).
Insumo para la discusión ética de Fase 4.

**Criterios de aceptación:**
- [ ] `data-engineering/notebooks/eda_calidad.ipynb` con visualizaciones clave.
- [ ] Identificadas al menos 2 limitaciones/sesgos potenciales de los datos.
- [ ] Nota escrita sobre sesgo de sobre-vigilancia para el informe ético (`CLAUDE.md §4.4`).

---

# 🟩 INTEGRANTE 2 — MODELO PREDICTIVO (Fase 3a)

### [PRED] #12 — EDA exploratorio sobre datos crudos (en paralelo) 🟢

**Asignado a:** Integrante 2 (Predictivo)
**Fase CRISP-ML:** 3
**Estimación:** 1 día
**Depende de:** ninguno (usa salidas crudas de #3/#4 apenas existan)
**Bloquea a:** ninguno

**Descripción:**
Mientras el dataset unificado (#9) no esté listo, explorar los datos crudos de
SIEDCO/NUSE para entender distribuciones de delito por hora/zona y formar
hipótesis de features. Trabajo adelantado no bloqueante.

**Criterios de aceptación:**
- [ ] Notebook con distribuciones temporales y espaciales de delitos.
- [ ] Lista de hipótesis de features candidatas para el modelo.
- [ ] Hallazgos compartidos con Integrante 1 (pueden afectar el diseño del dataset).

---

### [PRED] #13 — Protocolo de validación espacio-temporal (anti-fuga) 🟢

**Asignado a:** Integrante 2 (Predictivo)
**Fase CRISP-ML:** 3
**Estimación:** 1 día
**Depende de:** #9 (diseño puede empezar antes)
**Bloquea a:** #16, #17

**Descripción:**
Definir el esquema de validación que evita fuga temporal: split temporal
(train=pasado, test=futuro) y/o validación cruzada por bloques temporales. Nada de
shuffle aleatorio que mezcle pasado y futuro.

**Criterios de aceptación:**
- [ ] Documento que describe el split (fechas de corte train/val/test).
- [ ] Función reutilizable `temporal_split()` implementada y testeada.
- [ ] Justificación escrita de por qué no se usa K-fold aleatorio (ver `CLAUDE.md §4.3`).

---

### [PRED] #14 — Modelo baseline

**Asignado a:** Integrante 2 (Predictivo)
**Fase CRISP-ML:** 3
**Estimación:** 0.5 día
**Depende de:** #10, #13
**Bloquea a:** #16

**Descripción:**
Implementar baselines (clasificador trivial por mayoría + regla simple "zona
históricamente peligrosa"). Sirven como piso de comparación para los modelos reales.

**Criterios de aceptación:**
- [ ] Baseline trivial y baseline por regla evaluados con la métrica objetivo (recall/F1 clase riesgo).
- [ ] Resultados registrados como referencia para comparar RF/XGBoost.

---

### [PRED] #15 — Feature engineering

**Asignado a:** Integrante 2 (Predictivo)
**Fase CRISP-ML:** 3
**Estimación:** 1.5 días
**Depende de:** #9
**Bloquea a:** #16, #17

**Descripción:**
Construir features: temporales (franja, día semana, festivo), espaciales (zona,
vecindad), de contexto (densidad, NBI) y de rezago histórico (delitos pasados en
la zona) cuidando no introducir fuga.

**Criterios de aceptación:**
- [ ] Pipeline de features reproducible (`sklearn` Pipeline/ColumnTransformer).
- [ ] Features de rezago calculadas solo con información pasada (sin fuga).
- [ ] Matriz de features documentada (nombre, tipo, fuente).

---

### [PRED] #16 — Entrenar Random Forest

**Asignado a:** Integrante 2 (Predictivo)
**Fase CRISP-ML:** 3
**Estimación:** 1 día
**Depende de:** #13, #15
**Bloquea a:** #18

**Descripción:**
Entrenar Random Forest sobre el dataset con el split temporal y la estrategia de
balanceo definida. Reportar métricas alineadas al objetivo (recall/F1 de clase
riesgo, no accuracy global).

**Criterios de aceptación:**
- [ ] RF entrenado con `class_weight`/SMOTE según #10.
- [ ] Métricas: recall, F1 y matriz de confusión sobre la clase de riesgo alto.
- [ ] Importancia de features reportada.

---

### [PRED] #17 — Entrenar XGBoost + comparación

**Asignado a:** Integrante 2 (Predictivo)
**Fase CRISP-ML:** 3
**Estimación:** 1 día
**Depende de:** #13, #15
**Bloquea a:** #18

**Descripción:**
Entrenar XGBoost y compararlo con RF y los baselines bajo el mismo protocolo de
validación. Tabla comparativa de modelos.

**Criterios de aceptación:**
- [ ] XGBoost entrenado y evaluado con la misma métrica objetivo.
- [ ] Tabla comparativa baseline vs RF vs XGBoost.
- [ ] Recomendación preliminar de modelo ganador justificada.

---

### [PRED] #18 — Tuning + selección del modelo final

**Asignado a:** Integrante 2 (Predictivo)
**Fase CRISP-ML:** 3
**Estimación:** 1.5 días
**Depende de:** #16, #17
**Bloquea a:** #19, #28

**Descripción:**
Ajuste de hiperparámetros del modelo ganador (búsqueda con validación temporal) y
selección final. Documentar hiperparámetros elegidos.

**Criterios de aceptación:**
- [ ] Búsqueda de hiperparámetros con validación temporal (no aleatoria).
- [ ] Hiperparámetros finales documentados.
- [ ] Modelo final supera de forma clara los baselines en la métrica objetivo.

---

### [PRED] #19 — Serializar modelo + contrato de inferencia para la app 🤝

**Asignado a:** Integrante 2 (Predictivo)
**Fase CRISP-ML:** 3–5
**Estimación:** 0.5 día
**Depende de:** #18
**Bloquea a:** #38 (**sync point: entrega a Despliegue**)

**Descripción:**
Exportar el modelo final a `joblib` y definir con Integrante 4 el contrato de
inferencia: qué entra (zona, periodo, features) y qué sale (probabilidad/nivel de
riesgo). Función `predict()` envuelta y documentada.

**Criterios de aceptación:**
- [ ] `models/predictivo/model.joblib` + `predict.py` con función de inferencia.
- [ ] Contrato input/output documentado y acordado con Integrante 4 (#33).
- [ ] Ejemplo de llamada de inferencia funcionando end-to-end (sin la app).

**Notas técnicas:**
**Sync point Semana 2.** Coordinar el formato con #33 para que la app no tenga que adaptarse después.

---

### [PRED] #20 — QA cruzada: evaluar el modelo de anomalías (Int. 3) 🔁

**Asignado a:** Integrante 2 (Predictivo)
**Fase CRISP-ML:** 4
**Estimación:** 1 día
**Depende de:** #27
**Bloquea a:** ninguno

**Descripción:**
**QA cruzada (nadie evalúa su propio modelo).** Evaluar críticamente el modelo de
detección de anomalías de Integrante 3: validez de la métrica, robustez, casos de
falso positivo/negativo, y reproducibilidad.

**Criterios de aceptación:**
- [ ] Reporte de evaluación independiente del modelo de anomalías.
- [ ] Al menos 2 hallazgos accionables o confirmación de validez con evidencia.
- [ ] Revisión de que no hay fuga de información ni métrica engañosa.

**Notas técnicas:**
QA cruzada definida en `CLAUDE.md §kickoff`. Documentar en `models/anomalias/qa_cruzada.md`.

---

### [PRED] #21 — Documentación del modelo predictivo (model card)

**Asignado a:** Integrante 2 (Predictivo)
**Fase CRISP-ML:** 4
**Estimación:** 0.5 día
**Depende de:** #18
**Bloquea a:** ninguno

**Descripción:**
Model card del predictivo: datos usados, features, métricas, limitaciones, y
advertencia explícita sobre sesgo de vigilancia histórica.

**Criterios de aceptación:**
- [ ] `models/predictivo/MODEL_CARD.md` completo.
- [ ] Sección de limitaciones y riesgos éticos incluida.
- [ ] Métricas finales y hiperparámetros documentados.

---

# 🟨 INTEGRANTE 3 — ANOMALÍAS / NLP (Fase 3b)

### [ANOM] #22 — EDA de series temporales (en paralelo) 🟢

**Asignado a:** Integrante 3 (Anomalías/NLP)
**Fase CRISP-ML:** 3
**Estimación:** 1 día
**Depende de:** ninguno (usa crudos de #3/#4 apenas existan)
**Bloquea a:** ninguno

**Descripción:**
Mientras llega el dataset unificado (#9), explorar las series temporales de
incidentes por zona/franja para entender estacionalidad, tendencias y qué
constituye un "pico atípico". Trabajo adelantado no bloqueante.

**Criterios de aceptación:**
- [ ] Notebook con series temporales por zona y por tipo de delito.
- [ ] Estacionalidad/tendencias identificadas (día, semana, mes).
- [ ] Definición preliminar (cualitativa) de qué es una anomalía en este dominio.

---

### [ANOM] #23 — Definir "comportamiento esperado" por zona–franja

**Asignado a:** Integrante 3 (Anomalías/NLP)
**Fase CRISP-ML:** 3
**Estimación:** 1 día
**Depende de:** #9
**Bloquea a:** #24, #25

**Descripción:**
Establecer la línea base estadística de incidentes esperados por (zona, franja
horaria) contra la cual se mide la desviación. Es el fundamento de la detección de
anomalías.

**Criterios de aceptación:**
- [ ] Baseline esperado (media/mediana + dispersión) por zona–franja calculado.
- [ ] Método documentado y justificado.
- [ ] Validado contra el EDA (#22) para que sea coherente.

---

### [ANOM] #24 — Detección por z-score espacial/temporal

**Asignado a:** Integrante 3 (Anomalías/NLP)
**Fase CRISP-ML:** 3
**Estimación:** 1.5 días
**Depende de:** #23
**Bloquea a:** #26

**Descripción:**
Implementar detección de anomalías por z-score: marcar (zona, franja) cuyo conteo
se desvía significativamente de lo esperado. Método interpretable y barato.

**Criterios de aceptación:**
- [ ] Función que calcula z-score por zona–franja y marca anomalías sobre un umbral.
- [ ] Umbral justificado (ej. |z|>3) y configurable.
- [ ] Ejemplos de anomalías detectadas inspeccionados manualmente.

---

### [ANOM] #25 — Detección con Isolation Forest

**Asignado a:** Integrante 3 (Anomalías/NLP)
**Fase CRISP-ML:** 3
**Estimación:** 1.5 días
**Depende de:** #9
**Bloquea a:** #26

**Descripción:**
Entrenar Isolation Forest multivariado (conteo + contexto + features temporales)
como detector de anomalías complementario al z-score, capturando patrones no
univariados.

**Criterios de aceptación:**
- [ ] Isolation Forest entrenado sobre features de zona–tiempo.
- [ ] Anomalías comparadas con las del z-score (solapamiento/diferencias).
- [ ] Parámetros (contamination, n_estimators) documentados.

---

### [ANOM] #26 — Validación de la detección de anomalías

**Asignado a:** Integrante 3 (Anomalías/NLP)
**Fase CRISP-ML:** 3
**Estimación:** 1 día
**Depende de:** #24, #25
**Bloquea a:** #27

**Descripción:**
Validar los detectores: inyectar anomalías sintéticas conocidas y medir si se
detectan; revisar falsos positivos en datos reales. Sin etiquetas reales, usar
validación semi-sintética.

**Criterios de aceptación:**
- [ ] Conjunto de anomalías sintéticas inyectadas y tasa de detección medida.
- [ ] Análisis cualitativo de falsos positivos en datos reales.
- [ ] Recomendación de cuál detector (o combinación) usar en producción.

---

### [ANOM] #27 — Serializar modelo de anomalías + contrato para la app 🤝

**Asignado a:** Integrante 3 (Anomalías/NLP)
**Fase CRISP-ML:** 3–5
**Estimación:** 0.5 día
**Depende de:** #26
**Bloquea a:** #20, #38

**Descripción:**
Exportar el detector elegido a `joblib` y definir con Integrante 4 cómo la app
consulta anomalías (input: zona/periodo/conteo reciente; output: ¿es anomalía? +
score). Entregar también a Integrante 2 para la QA cruzada (#20).

**Criterios de aceptación:**
- [ ] `models/anomalias/model.joblib` + `detect.py` con función de inferencia.
- [ ] Contrato input/output acordado con Integrante 4 (#33).
- [ ] Ejemplo de detección end-to-end funcionando (sin la app).

---

### [ANOM] #28 — QA cruzada: evaluar el modelo predictivo (Int. 2) 🔁

**Asignado a:** Integrante 3 (Anomalías/NLP)
**Fase CRISP-ML:** 4
**Estimación:** 1 día
**Depende de:** #18
**Bloquea a:** ninguno

**Descripción:**
**QA cruzada (nadie evalúa su propio modelo).** Evaluar críticamente el modelo
predictivo de Integrante 2: validez del split temporal (¿hay fuga?), métrica
adecuada, robustez, y si solo replica sesgo de vigilancia histórica.

**Criterios de aceptación:**
- [ ] Reporte de evaluación independiente del modelo predictivo.
- [ ] Verificación explícita de ausencia de fuga temporal.
- [ ] Al menos 2 hallazgos accionables o confirmación de validez con evidencia.

**Notas técnicas:**
Documentar en `models/predictivo/qa_cruzada.md`. Ver criterio de no replicar sesgo en `CLAUDE.md §4.4`.

---

### [ANOM] #29 — [NICE-TO-HAVE] NLP de reportes ciudadanos

**Asignado a:** Integrante 3 (Anomalías/NLP)
**Fase CRISP-ML:** 3
**Estimación:** 1.5 días (solo si hay tiempo)
**Depende de:** #26, #35
**Bloquea a:** ninguno

**Descripción:**
**NO BLOQUEANTE.** Si el tiempo lo permite, clasificar el texto libre de los
reportes ciudadanos en tipo de delito y extraer entidades (hora/lugar). Solo
empezar tras cerrar lo obligatorio (#26).

**Criterios de aceptación:**
- [ ] Clasificador de texto → tipo de delito con métrica básica reportada.
- [ ] (Opcional) Extracción de entidades de ubicación/hora.
- [ ] Si no se alcanza, queda documentado como "trabajo futuro" sin penalizar la entrega.

**Notas técnicas:**
Recortado a nice-to-have (ver §recorte de alcance). No arriesgar la entrega por esto.

---

### [ANOM] #30 — Pruebas de robustez ante reportes ruidosos/faltantes

**Asignado a:** Integrante 3 (Anomalías/NLP)
**Fase CRISP-ML:** 4
**Estimación:** 1 día
**Depende de:** #27
**Bloquea a:** ninguno

**Descripción:**
Probar cómo se comportan los detectores ante datos faltantes o ruidosos de los
reportes ciudadanos (campos vacíos, ubicaciones imprecisas), según `CLAUDE.md §4.4`.

**Criterios de aceptación:**
- [ ] Escenarios de ruido/faltantes simulados y evaluados.
- [ ] Comportamiento degradado documentado (no rompe, no genera falsos masivos).
- [ ] Recomendaciones de validación de input para la app (insumo para #35).

---

### [ANOM] #31 — Documentación del modelo de anomalías (model card)

**Asignado a:** Integrante 3 (Anomalías/NLP)
**Fase CRISP-ML:** 4
**Estimación:** 0.5 día
**Depende de:** #26
**Bloquea a:** ninguno

**Descripción:**
Model card de anomalías: método, supuestos, métricas de validación, limitaciones.

**Criterios de aceptación:**
- [ ] `models/anomalias/MODEL_CARD.md` completo.
- [ ] Supuestos estadísticos y limitaciones documentados.
- [ ] Guía de interpretación de un "score de anomalía" para usuarios no técnicos.

---

# 🟥 INTEGRANTE 4 — DESPLIEGUE (Fase 5: backend/API + frontend)

### [APP] #32 — Scaffolding de la app (FastAPI + frontend) 🟢

**Asignado a:** Integrante 4 (Despliegue)
**Fase CRISP-ML:** 5
**Estimación:** 1 día
**Depende de:** ninguno (empieza día 1)
**Bloquea a:** #34, #35, #36

**Descripción:**
Montar el esqueleto: proyecto FastAPI en `app/backend`, servidor de estáticos/Jinja
para `app/frontend`, `requirements.txt`, y un endpoint `/health`. Todo corre con
`uvicorn` desde día 1.

**Criterios de aceptación:**
- [ ] `uvicorn app.backend.main:app --reload` levanta y `/health` responde 200.
- [ ] Estructura backend/frontend creada con README de cómo correr.
- [ ] Página frontend base sirve un mapa Leaflet vacío de Bogotá.

---

### [APP] #33 — Definir contrato de API + modelo mock 🤝🟢

**Asignado a:** Integrante 4 (Despliegue)
**Fase CRISP-ML:** 5
**Estimación:** 1 día
**Depende de:** #32
**Bloquea a:** #34, #38

**Descripción:**
Definir el contrato de los endpoints (`/predict`, `/reportes`, `/anomalias`) y
crear un **modelo mock** que devuelve datos falsos con el formato final. Permite
construir toda la app sin esperar a los modelos reales.

**Criterios de aceptación:**
- [ ] Esquemas Pydantic de request/response para cada endpoint.
- [ ] Mock que devuelve respuestas con el shape acordado con #19 y #27.
- [ ] Contrato documentado y validado con Integrantes 2 y 3.

**Notas técnicas:**
Acordar este contrato temprano evita retrabajo cuando lleguen `model.joblib` (#19, #27).

---

### [APP] #34 — Endpoint `/predict` (mapa de riesgo)

**Asignado a:** Integrante 4 (Despliegue)
**Fase CRISP-ML:** 5
**Estimación:** 1 día
**Depende de:** #33
**Bloquea a:** #36

**Descripción:**
Endpoint que devuelve el nivel de riesgo por zona (y franja) para alimentar el mapa
de calor. Inicialmente contra el mock; luego contra el modelo real (#38).

**Criterios de aceptación:**
- [ ] `GET /predict?periodo=...` devuelve riesgo por zona en JSON/GeoJSON.
- [ ] Manejo de errores (parámetros inválidos → 4xx con mensaje claro).
- [ ] Probado con el mock y documentado en OpenAPI (`/docs`).

---

### [APP] #35 — Endpoint de reportes ciudadanos + base de datos

**Asignado a:** Integrante 4 (Despliegue)
**Fase CRISP-ML:** 5
**Estimación:** 1.5 días
**Depende de:** #32
**Bloquea a:** #37, #29

**Descripción:**
CRUD mínimo de reportes ciudadanos: `POST /reportes` (tipo, lat/lon, hora,
descripción) persistido en SQLite, y `GET /reportes` para listarlos. Incluir
validación de input.

**Criterios de aceptación:**
- [ ] `POST /reportes` persiste en BD y valida campos (rechaza coords fuera de Bogotá).
- [ ] `GET /reportes` devuelve reportes recientes.
- [ ] Esquema de BD documentado; coordenadas validadas según recomendaciones de #30.

**Notas técnicas:**
Form-based MVP (sin push). PostgreSQL/PostGIS queda como ruta de producción.

---

### [APP] #36 — Frontend: mapa de calor de riesgo (Leaflet)

**Asignado a:** Integrante 4 (Despliegue)
**Fase CRISP-ML:** 5
**Estimación:** 1.5 días
**Depende de:** #34
**Bloquea a:** ninguno

**Descripción:**
Capa de calor sobre el mapa de Bogotá que consume `/predict` y colorea las zonas
por nivel de riesgo, con selector de franja horaria/tipo de delito.

**Criterios de aceptación:**
- [ ] Mapa Leaflet muestra zonas coloreadas por riesgo desde la API.
- [ ] Control para cambiar franja horaria/tipo de delito y re-consultar.
- [ ] Leyenda de niveles de riesgo y tooltip por zona.

---

### [APP] #37 — Frontend: formulario de reporte ciudadano

**Asignado a:** Integrante 4 (Despliegue)
**Fase CRISP-ML:** 5
**Estimación:** 1 día
**Depende de:** #35
**Bloquea a:** ninguno

**Descripción:**
Formulario para que el usuario reporte un incidente: selección de ubicación en el
mapa, tipo, hora y descripción; envía a `POST /reportes` y muestra los reportes en
el mapa.

**Criterios de aceptación:**
- [ ] Formulario con pin de ubicación en el mapa, envía a la API y confirma éxito/error.
- [ ] Reportes existentes se renderizan como marcadores en el mapa.
- [ ] Incluye checkbox de consentimiento + enlace al aviso de privacidad (ver #40).

---

### [APP] #38 — Integrar modelos reales (reemplazar mock) 🤝

**Asignado a:** Integrante 4 (Despliegue)
**Fase CRISP-ML:** 5
**Estimación:** 1 día
**Depende de:** #19, #27, #34
**Bloquea a:** ninguno (**sync point: integración final**)

**Descripción:**
Cargar `models/predictivo/model.joblib` y `models/anomalias/model.joblib` en el
backend y reemplazar el mock por inferencia real, respetando el contrato de #33.

**Criterios de aceptación:**
- [ ] `/predict` y `/anomalias` responden con inferencia real de los `.joblib`.
- [ ] Latencia razonable (modelo cargado una vez al iniciar, no por request).
- [ ] Prueba end-to-end: dato entra → modelo → mapa lo refleja.

**Notas técnicas:**
**Sync point Semana 2–3.** Depende de que #19 y #27 entreguen el formato acordado.

---

### [APP] #39 — Diseño de Fase 6: monitoring & model drift

**Asignado a:** Integrante 4 (Despliegue)
**Fase CRISP-ML:** 6
**Estimación:** 0.5 día
**Depende de:** ninguno
**Bloquea a:** ninguno

**Descripción:**
Documentar cómo se detectaría drift (cambios en patrones delictivos) y cómo se
re-entrenaría el modelo incorporando nuevos reportes ciudadanos de forma periódica.
Diseño en texto/diagrama, no implementación.

**Criterios de aceptación:**
- [ ] `docs/monitoring.md` con métricas de drift propuestas y umbrales.
- [ ] Flujo de re-entrenamiento periódico descrito (frecuencia, trigger, datos).
- [ ] Diagrama del ciclo de vida del modelo en producción.

---

### [APP] #40 — QA de usabilidad + aviso de privacidad (Ley 1581)

**Asignado a:** Integrante 4 (Despliegue)
**Fase CRISP-ML:** 4–5
**Estimación:** 1 día
**Depende de:** #37
**Bloquea a:** ninguno

**Descripción:**
Revisión de usabilidad de la app y redacción del aviso de privacidad/consentimiento
para los reportes ciudadanos (opt-in), conforme a Ley 1581/2012 (ver `CLAUDE.md §2`).

**Criterios de aceptación:**
- [ ] Checklist de usabilidad aplicado (navegación clara, estados de carga/error).
- [ ] Aviso de privacidad redactado y enlazado desde el formulario.
- [ ] Confirmado que no se recogen datos personales identificables innecesarios.

---

### [APP] #41 — Empaquetado y despliegue (deploy doc + hosting opcional)

**Asignado a:** Integrante 4 (Despliegue)
**Fase CRISP-ML:** 5
**Estimación:** 1 día
**Depende de:** #38
**Bloquea a:** ninguno

**Descripción:**
`Dockerfile`/instrucciones para correr todo end-to-end y, como **nice-to-have**,
desplegar en un free tier (Render/Railway/HF Spaces) para tener una URL pública en
la demo.

**Criterios de aceptación:**
- [ ] App corre con un solo comando documentado (Docker o script).
- [ ] `docs/deploy.md` con pasos reproducibles.
- [ ] (Nice-to-have) URL pública funcionando; si no, demo local documentada.

---

### [APP] #42 — README de la app + flujo end-to-end

**Asignado a:** Integrante 4 (Despliegue)
**Fase CRISP-ML:** 5
**Estimación:** 0.5 día
**Depende de:** #38
**Bloquea a:** ninguno

**Descripción:**
Documentar en `app/` cómo correr backend+frontend, variables de entorno, y el flujo
completo desde dataset → modelo → API → mapa.

**Criterios de aceptación:**
- [ ] `app/README.md` con pasos de instalación y ejecución.
- [ ] Diagrama o lista del flujo de datos end-to-end.
- [ ] Capturas de pantalla de la app funcionando.

---

# 🔵 CIERRE Y ENTREGA FINAL (repartido entre los 4)

### [DATOS] #43 — Sección de datos del informe + diccionario consolidado

**Asignado a:** Integrante 1 (Datos)
**Fase CRISP-ML:** 1–2 (cierre)
**Estimación:** 1 día
**Depende de:** #9, #11
**Bloquea a:** ninguno

**Descripción:**
Redactar la sección del informe sobre fuentes, pipeline y calidad de datos;
consolidar los diccionarios de datos. Trazar a los criterios "Uso de datos
abiertos" y "Rigor técnico".

**Criterios de aceptación:**
- [ ] Sección de datos del informe redactada con la lista final de datasets (URLs, fechas).
- [ ] Diccionario de datos consolidado en `docs/`.
- [ ] Trazabilidad explícita a los criterios de evaluación (`CLAUDE.md §5`).

---

### [PRED] #44 — Sección de modelado predictivo del informe

**Asignado a:** Integrante 2 (Predictivo)
**Fase CRISP-ML:** 3–4 (cierre)
**Estimación:** 1 día
**Depende de:** #21, #28
**Bloquea a:** ninguno

**Descripción:**
Redactar la sección de metodología y resultados del modelo predictivo, incluyendo
la validación espacio-temporal y las conclusiones de la QA cruzada recibida.

**Criterios de aceptación:**
- [ ] Sección redactada con métricas, decisiones y limitaciones.
- [ ] Incorpora hallazgos de la QA cruzada (#28).
- [ ] Trazabilidad a "Uso de tecnologías emergentes / IA" y "Rigor técnico".

---

### [ANOM] #45 — Sección de anomalías + ética/sesgo del informe

**Asignado a:** Integrante 3 (Anomalías/NLP)
**Fase CRISP-ML:** 3–4 (cierre)
**Estimación:** 1 día
**Depende de:** #31, #20
**Bloquea a:** ninguno

**Descripción:**
Redactar la sección de detección de anomalías y la discusión ética (sesgo de
vigilancia, estigmatización de barrios, uso responsable de datos) — diferenciador
clave del proyecto.

**Criterios de aceptación:**
- [ ] Sección de anomalías redactada con método y validación.
- [ ] Discusión ética alineada a `CLAUDE.md §4.4` (sesgo, estigmatización).
- [ ] Trazabilidad a "Innovación" e "Impacto y escalabilidad".

---

### [APP] #46 — Demo en vivo + pitch + video

**Asignado a:** Integrante 4 (Despliegue)
**Fase CRISP-ML:** 5–6 (cierre)
**Estimación:** 1 día
**Depende de:** #41, #42
**Bloquea a:** ninguno

**Descripción:**
Preparar la demostración final: guion de demo en vivo de la app, pitch deck y un
video corto. Coordina la integración de las secciones de los 4 en un solo informe.

**Criterios de aceptación:**
- [ ] Guion de demo que recorre mapa de riesgo + reporte ciudadano + anomalía.
- [ ] Pitch deck cubriendo los 6 criterios de evaluación.
- [ ] Video corto (2–3 min) e informe final consolidado.

---

## Resumen de carga por integrante

| Integrante | Issues | Estimación aprox. |
|---|---|---|
| 1 — Datos | #1–#11, #43 (12 issues) | ~12.5 días-persona |
| 2 — Predictivo | #12–#21, #44 (11 issues) | ~11 días-persona |
| 3 — Anomalías/NLP | #22–#31, #45 (11 issues) | ~11.5 días-persona (NLP excluido del crítico) |
| 4 — Despliegue | #32–#42, #46 (12 issues) | ~12 días-persona |

> Las estimaciones son días-persona de trabajo efectivo, no días de calendario.
> En 2.5 semanas part-time (4 integrantes) son holgura razonable **si** el sync
> point de fin de Semana 1 (dataset #9) se cumple. Ver `CRONOGRAMA.md`.
