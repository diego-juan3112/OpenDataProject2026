# BACKLOG — Alerta Ciudadana

Backlog completo de issues repartido entre los **4 integrantes**, calibrado para
**3 semanas** de trabajo en equipo académico (part-time). La carga objetivo es de
**~11–13 días-persona** por integrante.

> **Cómo usar este archivo:** cada bloque `###` es un issue listo para copiarse a
> GitHub Issues (o crearse con `gh issue create`). La numeración `#N` es global y
> se usa en los campos *Depende de* / *Bloquea a*.

## Leyenda

- **[DATOS]** Integrante 1 · **[PRED]** Integrante 2 · **[CLUST]** Integrante 3 · **[APP]** Integrante 4
- 🟢 puede empezar día 1 (sin bloqueo) · 🟡 bloqueado por dependencia · 🔵 cierre/entrega
- 🤝 sync point entre integrantes · 🎯 entregable clave · 🔴 decisión bloqueante

## Reparto de pistas

| Pista | Integrante | Frente |
|---|---|---|
| **Datos** | Int. 1 | Pipeline: ingesta → limpieza → cruce DANE → dataset unificado + GeoJSON de zonas |
| **Predictivo + API** | Int. 2 | Modelo RF/GB · API `/zonas-riesgo` · capa de datos/geofencing del móvil |
| **Clustering + Dashboard** | Int. 3 | K-Means (tipología) · ética/sesgo · dashboard Streamlit |
| **App móvil** | Int. 4 | Cliente Expo: GPS · notificación local · modo demo · build en dispositivo físico |

La app móvil es trabajo nuevo y significativo, por eso se reparte entre **dos
integrantes**: Int. 2 sostiene la **API + la capa de datos/geofencing** que el
cliente consume, e Int. 4 construye la **UI + GPS + notificaciones + modo demo +
build en dispositivo**. El dashboard, más liviano porque la inferencia vive en la
API, lo lleva Int. 3 junto al clustering.

---

# 🟦 INTEGRANTE 1 — DATOS (Fase 1–2)

### [DATOS] #1 — Validar y cerrar inventario de datasets (Fase 1)

**Asignado a:** Integrante 1 · **Fase:** 1 · **Estimación:** 0.5 día
**Depende de:** ninguno 🟢 · **Bloquea a:** #3, #4, #5, #6

**Descripción:** Verificar en datos.gov.co disponibilidad, vigencia y formato exacto
de cada fuente para Bogotá (SIEDCO, NUSE C4, DIVIPOLA, DANE). Confirmar URLs y fecha
de última actualización.

**Criterios de aceptación:**
- [ ] Tabla en `docs/business-understanding.md`: nombre, entidad, URL, fecha, formato, granularidad.
- [ ] Cada fuente marcada "disponible y usable" o "descartada" (con razón).
- [ ] Confirmado el tipo de geometría de SIEDCO (polígono por localidad, EPSG:4686) y la granularidad real de NUSE.
- [ ] Rango temporal real del histórico SIEDCO para Bogotá documentado.

---

### [DATOS] #2 — Setup del módulo de datos y estructura `data/`

**Asignado a:** Integrante 1 · **Fase:** 2 · **Estimación:** 0.5 día
**Depende de:** ninguno 🟢 · **Bloquea a:** #3, #4, #5, #6

**Descripción:** Preparar `src/`: `requirements.txt` del pipeline, estructura de
scripts y convención `data/01_raw → 02_intermediate → 03_primary`. Formato de
intercambio final: Parquet.

**Criterios de aceptación:**
- [ ] `requirements.txt` (raíz) con pandas, geopandas, pyarrow, etc.
- [ ] README corto del flujo del pipeline en `src/`.
- [ ] `.gitignore` confirmado: `data/01_raw|02_intermediate|03_primary|04_model_output` no se versionan.

---

### [DATOS] #3 — Ingesta SIEDCO (delitos de alto impacto, Bogotá)

**Asignado a:** Integrante 1 · **Fase:** 2 · **Estimación:** 1 día
**Depende de:** #1, #2 · **Bloquea a:** #7, #8

**Descripción:** Descargar y cargar el dataset núcleo (hurtos, homicidios, lesiones,
violencia intrafamiliar, delitos sexuales, etc.) filtrado a Bogotá. Script reproducible.

**Criterios de aceptación:**
- [ ] `src/ingest_siedco.py` reproducible (descarga o lee de `data/01_raw/`).
- [ ] Datos filtrados a Bogotá, con conteo de filas y rango de fechas reportados.
- [ ] Columnas clave: fecha/hora, tipo de delito, código DANE / localidad, modalidad.

**Notas técnicas:** Cruzar por **código DANE**, nunca por nombre de texto libre.

---

### [DATOS] #4 — Ingesta NUSE C4 Línea 123 (Bogotá)

**Asignado a:** Integrante 1 · **Fase:** 2 · **Estimación:** 1 día
**Depende de:** #1, #2 · **Bloquea a:** #7, #8

**Descripción:** Cargar las llamadas de emergencia de la Línea 123 (C4) de Bogotá.
El dato abierto **viene agregado por localidad y UPZ × mes × tipo** (verificado: no
trae la ubicación exacta de cada llamada). Sostiene la **capa de densidad por UPZ**
del mapa, no una capa de puntos.

**Criterios de aceptación:**
- [ ] `src/ingest_nuse.py` reproducible.
- [ ] Confirmado que el dato es agregado por localidad/UPZ (sin lat/lon por incidente) y documentado.
- [ ] Conteo de llamadas por localidad, UPZ, mes y tipo, con tipos normalizados a categorías comparables con SIEDCO.

---

### [DATOS] #5 — Ingesta DIVIPOLA + geometrías de Bogotá → `zonas_bogota.geojson` 🎯

**Asignado a:** Integrante 1 · **Fase:** 2 · **Estimación:** 1 día
**Depende de:** #1, #2 · **Bloquea a:** #8, #21, #28, #35

**Descripción:** Obtener códigos DIVIPOLA (DANE) y geometrías de Bogotá a nivel
localidad en GeoJSON. **Exportar `data/03_primary/zonas_bogota.geojson`**: es el
insumo geográfico que consumen la API y el dashboard.

**Criterios de aceptación:**
- [ ] GeoDataFrame de localidades de Bogotá cargado con GeoPandas (EPSG documentado).
- [ ] Cada zona con su código DANE y geometría válida (sin geometrías nulas/inválidas).
- [ ] `zonas_bogota.geojson` exportado y entregado al equipo de API/dashboard.
- [ ] Unidad espacial del proyecto (localidad) definida y justificada con Int. 2 e Int. 3.

---

### [DATOS] #6 — Ingesta variables demográficas/socioeconómicas DANE

**Asignado a:** Integrante 1 · **Fase:** 2 · **Estimación:** 1 día
**Depende de:** #1, #2 · **Bloquea a:** #9

**Descripción:** Cargar variables de contexto por zona (densidad poblacional,
NBI/pobreza multidimensional) **agregadas y anonimizadas**. Nunca microdatos.

**Criterios de aceptación:**
- [ ] Variables de contexto unidas a la unidad espacial por código DANE.
- [ ] Confirmado que todo es agregado a nivel zona (cero datos personales).
- [ ] Documentado el año/fuente de cada variable socioeconómica.

---

### [DATOS] #7 — Limpieza, normalización y diccionario de datos real

**Asignado a:** Integrante 1 · **Fase:** 2 · **Estimación:** 1.5 días
**Depende de:** #3, #4 · **Bloquea a:** #8, #9

**Descripción:** Limpiar cada fuente: tipos, nulos, duplicados, normalización de
categorías de delito entre SIEDCO y NUSE, y normalización del **año** (grano temporal
del proyecto). Documentar el diccionario de datos real por fuente.

**Criterios de aceptación:**
- [ ] Reporte de calidad por fuente (% nulos, duplicados, fuera de rango).
- [ ] Taxonomía común de delitos documentada (la consumen Int. 2 e Int. 3).
- [ ] Columna `anio` limpia y consistente entre fuentes (no hay hora en el dato abierto; ver Nota de validación, CLAUDE.md §1).
- [ ] `docs/data-dictionaries/` con un `.md` por fuente (columna, tipo, descripción, dominio).

---

### [DATOS] #8 — Cruce geográfico de fuentes por código DANE

**Asignado a:** Integrante 1 · **Fase:** 2 · **Estimación:** 1.5 días
**Depende de:** #5, #7 · **Bloquea a:** #9

**Descripción:** Unir SIEDCO, NUSE y contexto DANE a la unidad espacial (localidad)
**por código de localidad DANE**, nunca por nombre. Como ninguna fuente trae
coordenada-punto, el cruce es un join por código, no un spatial join.

**Criterios de aceptación:**
- [ ] Join SIEDCO→localidad por código DANE sin pérdida de filas no justificada.
- [ ] Join NUSE→localidad por código DANE (el UPZ se mantiene como detalle para la capa de densidad).
- [ ] Contexto DANE (población, NBI) unido por código de localidad; cero cruces por nombre de texto libre.

---

### [DATOS] #9 — Construir dataset analítico unificado (zona–tiempo–delito) 🎯

**Asignado a:** Integrante 1 · **Fase:** 2 · **Estimación:** 2 días
**Depende de:** #6, #8 · **Bloquea a:** #16, #18, #27, #28 — **ENTREGABLE CLAVE, fin Semana 1 (SYNC-1)**

**Descripción:** Tabla analítica final: una fila por **(localidad × año × tipo de
delito)** con conteo de incidentes (SIEDCO y NUSE) + variables de contexto (población,
NBI). Desbloquea el modelado de Int. 2 (predictivo) e Int. 3 (clustering).

**Criterios de aceptación:**
- [ ] `data/03_primary/dataset_analitico.parquet` generado por `pipelines/pipeline_ml.py` reproducible.
- [ ] Esquema documentado: claves (`cod_localidad`, `anio`, `tipo_delito`), features de contexto (`conteo_siedco`, `conteo_nuse`, `poblacion`, `ipm_nbi`) y marca `split`.
- [ ] Split espacio-temporal marcado sin fuga: `train` = años ≤2024, `test` = 2025.
- [ ] Notebook de ejemplo de carga + descripción de columnas entregado al equipo.

**Notas técnicas:** Avisar al equipo en cuanto esté listo (SYNC-1).

---

### [DATOS] #10 — Definir variable objetivo y manejo de desbalance

**Asignado a:** Integrante 1 (con Int. 2) · **Fase:** 2–3 · **Estimación:** 1 día
**Depende de:** #9 · **Bloquea a:** #17

**Descripción:** Definir cómo se etiqueta "riesgo alto" para cada fila
**(localidad × año × tipo de delito)** — por ejemplo, percentil alto del conteo — y
caracterizar el desbalance. Acordar estrategia (class_weight, SMOTE) con Int. 2.
**El manejo explícito de desbalance no se recorta.**

**Criterios de aceptación:**
- [ ] Definición de la clase objetivo documentada y justificada.
- [ ] Distribución de clases reportada (ratio de desbalance).
- [ ] Técnica de balanceo acordada con Integrante 2.

---

### [DATOS] #11 — EDA de calidad de datos + nota de sesgo (insumo ético)

**Asignado a:** Integrante 1 · **Fase:** 4 · **Estimación:** 1 día
**Depende de:** #9 · **Bloquea a:** #32

**Descripción:** Notebook de EDA de calidad: distribuciones, cobertura por zona,
posibles sesgos de vigilancia (zonas con más registros por más policía, no más
delito real). Insumo para la auditoría de sesgo (#32).

**Criterios de aceptación:**
- [ ] `notebooks/01_EDA_exploracion_datos.ipynb` con visualizaciones clave.
- [ ] Al menos 2 limitaciones/sesgos potenciales identificados.
- [ ] Nota escrita sobre sesgo de sobre-vigilancia para la auditoría de sesgo.

---

### [DATOS] #12 — Sección de datos del informe + diccionario consolidado

**Asignado a:** Integrante 1 · **Fase:** 1–2 (cierre) 🔵 · **Estimación:** 1 día
**Depende de:** #9, #11 · **Bloquea a:** ninguno

**Criterios de aceptación:**
- [ ] Sección de datos del informe con la lista final de datasets (URLs, fechas).
- [ ] Diccionario de datos consolidado en `docs/`.
- [ ] Trazabilidad explícita a "Uso de datos abiertos" y "Rigor técnico".

---

# 🟩 INTEGRANTE 2 — PREDICTIVO + API (Fase 3a + 5)

### [PRED] #13 — EDA exploratorio sobre datos crudos (en paralelo) 🟢

**Asignado a:** Integrante 2 · **Fase:** 3 · **Estimación:** 1 día
**Depende de:** ninguno (usa crudos de #3/#4) · **Bloquea a:** ninguno

**Criterios de aceptación:**
- [ ] Notebook con distribuciones temporales y espaciales de delitos.
- [ ] Lista de hipótesis de features candidatas.
- [ ] Hallazgos compartidos con Integrante 1.

---

### [PRED] #14 — Protocolo de validación espacio-temporal (anti-fuga) 🟢

**Asignado a:** Integrante 2 · **Fase:** 3 · **Estimación:** 1 día
**Depende de:** #9 (diseño puede empezar antes) · **Bloquea a:** #17, #18

**Descripción:** Split temporal (train=pasado, test=futuro) y/o CV por bloques
temporales. Nada de shuffle aleatorio. **La validación sin fuga no se recorta.**

**Criterios de aceptación:**
- [ ] Documento con las fechas de corte train/val/test.
- [ ] Función reutilizable `temporal_split()` implementada y testeada.
- [ ] Justificación escrita de por qué no se usa K-fold aleatorio.

---

### [PRED] #15 — Modelo baseline

**Asignado a:** Integrante 2 · **Fase:** 3 · **Estimación:** 0.5 día
**Depende de:** #14 · **Bloquea a:** #17

**Criterios de aceptación:**
- [ ] Baseline trivial (mayoría) + baseline por regla ("zona históricamente peligrosa").
- [ ] Evaluados con la métrica objetivo (recall/F1 clase riesgo); registrados como referencia.

---

### [PRED] #16 — Feature engineering

**Asignado a:** Integrante 2 · **Fase:** 3 · **Estimación:** 1.5 días
**Depende de:** #9 · **Bloquea a:** #17, #18

**Criterios de aceptación:**
- [ ] Pipeline de features reproducible (`sklearn` Pipeline/ColumnTransformer).
- [ ] Features de rezago calculadas solo con información pasada (sin fuga).
- [ ] Matriz de features documentada (nombre, tipo, fuente).

---

### [PRED] #17 — Entrenar Random Forest

**Asignado a:** Integrante 2 · **Fase:** 3 · **Estimación:** 1 día
**Depende de:** #10, #14, #15, #16 · **Bloquea a:** #19

**Criterios de aceptación:**
- [ ] RF entrenado con `class_weight`/SMOTE según #10.
- [ ] Métricas: recall, F1 y matriz de confusión sobre la clase de riesgo alto.
- [ ] Importancia de features reportada.

---

### [PRED] #18 — Entrenar Gradient Boosting (XGBoost) + comparación

**Asignado a:** Integrante 2 · **Fase:** 3 · **Estimación:** 1 día
**Depende de:** #14, #16 · **Bloquea a:** #19

**Criterios de aceptación:**
- [ ] XGBoost entrenado y evaluado con la misma métrica objetivo.
- [ ] Tabla comparativa baseline vs RF vs XGBoost.
- [ ] Recomendación preliminar de modelo ganador justificada.

---

### [PRED] #19 — Tuning + selección del modelo final + `model.joblib`

**Asignado a:** Integrante 2 · **Fase:** 3 · **Estimación:** 1.5 días
**Depende de:** #17, #18 · **Bloquea a:** #21, #23

**Descripción:** Búsqueda de hiperparámetros con validación temporal, selección del
modelo final y serialización a `models/predictivo/model.joblib` con su función de
inferencia `predict.py`.

**Criterios de aceptación:**
- [ ] Búsqueda de hiperparámetros con validación temporal (no aleatoria); hiperparámetros documentados.
- [ ] Modelo final supera de forma clara los baselines en la métrica objetivo.
- [ ] `models/predictivo/model.joblib` + `predict.py` con función de inferencia y ejemplo end-to-end.

---

### [PRED] #20 — API ligera `GET /zonas-riesgo` (FastAPI) 🎯🤝

**Asignado a:** Integrante 2 · **Fase:** 5 · **Estimación:** 1.5 días
**Depende de:** #5, #19, #27 · **Bloquea a:** #28 (dashboard real), #34 (móvil real)

**Descripción:** Único endpoint del sistema. Carga `model.joblib` y `clusters.joblib`
en memoria y devuelve un **GeoJSON** de las localidades de Bogotá con: geometría,
nivel/probabilidad de riesgo (predictivo), cluster + nombre de perfil (clustering) y
metadatos (código DANE, año y tipo consultados). **Mismo contrato para ambos clientes.**

**Criterios de aceptación:**
- [ ] `uvicorn api.main:app` levanta y responde `GET /zonas-riesgo` con GeoJSON válido.
- [ ] Soporta parámetros de año y tipo de delito (p. ej. `?anio=2025&tipo=hurto_personas`) y devuelve riesgo + cluster por localidad.
- [ ] Modelos cargados una sola vez al arranque (no por request).
- [ ] `--host 0.0.0.0` documentado para acceso desde dispositivo físico por IP de LAN.
- [ ] Esquema de respuesta documentado en `api/README.md` (acordado con Int. 3 y Int. 4).

---

### [PRED] #21 — Capa de datos y geofencing del móvil 🤝

**Asignado a:** Integrante 2 (con Int. 4) · **Fase:** 5 · **Estimación:** 1.5 días
**Depende de:** #20 · **Bloquea a:** #32 (móvil notificación)

**Descripción:** Lógica que consume `/zonas-riesgo` desde el cliente móvil, cachea
el GeoJSON y resuelve **geofencing**: dada una coordenada GPS, determinar en qué
localidad cae (point-in-polygon) y su nivel de riesgo. Es el "cerebro" de datos que
Int. 4 conecta a la UI.

**Criterios de aceptación:**
- [ ] Función `riesgoDeCoordenada(lat, lon)` que devuelve zona + nivel de riesgo a partir del GeoJSON de la API.
- [ ] Manejo de coordenada fuera de Bogotá (sin zona) sin romper.
- [ ] Cacheo del GeoJSON con refresco periódico configurable; tolerante a API caída (último valor conocido).
- [ ] Contrato de la función acordado y entregado a Int. 4 (#31, #32).

---

### [PRED] #22 — Análisis de error y robustez del predictivo

**Asignado a:** Integrante 2 · **Fase:** 4 · **Estimación:** 1 día
**Depende de:** #19 · **Bloquea a:** #24

**Descripción:** Profundizar la evaluación: error por localidad y por tipo de delito,
curva precision-recall, calibración de probabilidades y robustez ante features
faltantes/ruidosas (escenario de datos imperfectos en producción).

**Criterios de aceptación:**
- [ ] Desglose de recall/F1 por localidad y por tipo de delito (¿dónde falla el modelo?).
- [ ] Curva precision-recall y umbral de decisión justificado para "riesgo alto".
- [ ] Prueba de degradación con features faltantes/ruidosas documentada.

---

### [PRED] #23 — QA cruzada: revisar el clustering (Int. 3) 🔁

**Asignado a:** Integrante 2 · **Fase:** 4 · **Estimación:** 0.5 día
**Depende de:** #27 · **Bloquea a:** #24, #38

**Descripción:** **QA cruzada (nadie evalúa su propio modelo).** Revisión corta del
clustering de Int. 3 para la sección compartida de evaluación: ¿el k elegido se
sostiene?, ¿las features tienen fuga?, ¿la tipología es interpretable? Deja un
comentario de validación.

**Criterios de aceptación:**
- [ ] Comentario de validación cruzada del clustering en la sección compartida del informe.
- [ ] Al menos 1 hallazgo accionable o confirmación de validez con evidencia.

---

### [PRED] #24 — Sección de modelado predictivo + evaluación compartida

**Asignado a:** Integrante 2 · **Fase:** 3–4 (cierre) 🔵 · **Estimación:** 1 día
**Depende de:** #22, #23 · **Bloquea a:** ninguno

**Criterios de aceptación:**
- [ ] Sección redactada con métricas (recall/F1 de clase riesgo), decisiones y limitaciones.
- [ ] Métricas del predictivo en la sección compartida de evaluación + comentario cruzado de Int. 3 (#39).
- [ ] Trazabilidad a "Tecnologías emergentes / IA" y "Rigor técnico".

---

## 🧭 Feature: Ruta Más Segura — issues de API (Int. 2)

> Feature nueva sobre el mismo modelo/datos: la app pide dos rutas alternativas
> a OpenRouteService y la API las evalúa por el riesgo de las localidades que
> atraviesan. Diseño técnico completo (arquitectura, código de referencia,
> esquema del endpoint) en `diseño_tecnico_ruta_segura.md`. No reproducir el
> código aquí: citar la sección correspondiente del diseño.

### [PRED] #45 — Setup ORS: API key, wrapper y prueba de conectividad 🟢

**Asignado a:** Integrante 2 · **Fase:** 5 · **Estimación:** 0.5 día
**Depende de:** ninguno 🟢 · **Bloquea a:** #46, #47

**Descripción:** Crear cuenta en OpenRouteService, obtener API key, añadirla al
`.env` del proyecto y escribir la función `get_routes()` en
`src/routing_client.py`. Verificar con un request de prueba entre dos puntos
conocidos de Bogotá que ORS devuelve rutas válidas. Documentar los límites del
plan gratuito en `docs/architecture.md`. Código de referencia:
`diseño_tecnico_ruta_segura.md` §PARTE 2.

**Criterios de aceptación:**
- [ ] `ORS_API_KEY` en `.env` (nunca commiteada — verificar `.gitignore`).
- [ ] `src/routing_client.py` con `get_routes(origen_lon, origen_lat, destino_lon, destino_lat)` implementado.
- [ ] Test manual: request entre Chapinero y La Candelaria devuelve 2 rutas con `summary.distance` y `summary.duration` válidos.
- [ ] Límites del plan gratuito documentados en `docs/architecture.md`.
- [ ] `polyline` añadido a `requirements.txt`.

**Notas técnicas:** Instalar `openrouteservice` y `polyline`. ORS usa `[lon, lat]`,
no al revés (error frecuente: invertir coordenadas). Endpoint
`POST /v2/directions/{profile}/json`; perfil recomendado para demo `driving-car`.

---

### [PRED] #46 — Función de score de riesgo por localidad

**Asignado a:** Integrante 2 · **Fase:** 3 · **Estimación:** 0.5 día
**Depende de:** #9 · **Bloquea a:** #47

**Descripción:** Implementar `calcular_scores_localidad()` en
`src/model_evaluation.py`. Lee el dataset analítico, aplica pesos por gravedad de
delito y devuelve un diccionario `{cod_localidad: score_0_a_10}` usando datos de
2024 (último año de entrenamiento). Acordar con el equipo si los pesos por tipo
de delito son razonables y documentar la decisión. Código de referencia:
`diseño_tecnico_ruta_segura.md` §PARTE 3, Paso 1.

**Criterios de aceptación:**
- [ ] Función implementada; devuelve dict con exactamente 20 claves (01–20).
- [ ] Scores en rango 0–10, con al menos 3 niveles distintos (no todos iguales).
- [ ] Test: localidades conocidas como problemáticas (Kennedy, Los Mártires) tienen score > 6.
- [ ] Pesos por tipo de delito documentados con justificación en el código.
- [ ] Sumapaz (cod 20) tiene score calculable (`ipm_nbi` nulo no afecta este cálculo).

**Notas técnicas:** Los pesos del diseño son un punto de partida ajustable; lo
importante es que estén documentados y sean defendibles. Considerar normalizar
también por población para no sesgar hacia localidades grandes.

---

### [PRED] #47 — Spatial join: qué localidades cruza una ruta

**Asignado a:** Integrante 2 · **Fase:** 5 · **Estimación:** 0.5 día
**Depende de:** #45, #46, #5 · **Bloquea a:** #48

**Descripción:** Implementar `decodificar_ruta()` y `localidades_de_ruta()` en
`src/routing_client.py`. La primera decodifica la polyline de ORS a puntos
geográficos; la segunda hace el spatial join con los polígonos de localidad
(`zonas_bogota.geojson`, #5) para saber por cuáles pasa la ruta. Verificar con
una ruta conocida que el resultado tiene sentido geográfico. Código de
referencia: `diseño_tecnico_ruta_segura.md` §PARTE 3, Pasos 2–3.

**Criterios de aceptación:**
- [ ] `decodificar_ruta()` devuelve GeoDataFrame en EPSG:4326 con puntos cada ~200 m.
- [ ] `localidades_de_ruta()` devuelve lista de `cod_localidad` en orden de aparición, sin duplicados.
- [ ] Test: ruta Chapinero → Santa Fe devuelve secuencia de localidades geográficamente coherente.
- [ ] Puntos fuera de Bogotá (ruta que sale del bounding box) no generan error — se filtran.
- [ ] Spatial join < 500 ms para rutas típicas de Bogotá.

**Notas técnicas:** `gpd.sjoin(..., predicate="within")`; usar `"intersects"` como
fallback si un punto cae en el borde de dos localidades. Samplear cada 200 m en
vez de usar todos los puntos de la polyline para mantener la performance.

---

### [PRED] #48 — Endpoint `POST /ruta-segura` completo 🎯🤝

**Asignado a:** Integrante 2 · **Fase:** 5 · **Estimación:** 1 día
**Depende de:** #45, #46, #47 · **Bloquea a:** #50 — **SYNC-R (ver nota al cierre de la sección)**

**Descripción:** Implementar el endpoint completo `POST /ruta-segura` en
`api/routers/routing.py` siguiendo el esquema request/response del diseño.
Incluir validación de coordenadas (dentro del bounding box de Bogotá), manejo de
errores de ORS y el startup hook que pre-carga scores y GeoDataFrame en
`app.state`. Código de referencia: `diseño_tecnico_ruta_segura.md` §PARTE 4–5.

**Criterios de aceptación:**
- [ ] `POST /ruta-segura` devuelve el response JSON del esquema definido.
- [ ] Validación: coordenadas fuera de Bogotá devuelven HTTP 422 con mensaje claro.
- [ ] Error de ORS devuelve HTTP 502 con mensaje útil (no stack trace).
- [ ] Sin ruta posible devuelve HTTP 404.
- [ ] Scores y zonas cargados en startup — no en cada request.
- [ ] Tiempo de respuesta end-to-end < 3 s en condiciones normales.
- [ ] Probado manualmente con Swagger UI (`/docs`) antes de entregarlo a Int. 4.

**Notas técnicas:** Incluir `routing.router` en `api/main.py`. La advertencia de
zona de riesgo alto en el origen es opcional para el MVP. El campo
`geometry_geojson` del response debe ser un dict Python (no string JSON) para que
FastAPI lo serialice correctamente.

---

> **SYNC-R: Entrega del endpoint `/ruta-segura`** 🤝
> Al terminar la issue #48, Integrante 2 entrega a Integrante 4 la URL del
> endpoint con un ejemplo de request/response funcionando en Swagger UI
> (`/docs`). Sin esa entrega, la issue #50 no puede completarse.

---

# 🟨 INTEGRANTE 3 — CLUSTERING + DASHBOARD (Fase 3b + 5)

### [CLUST] #25 — EDA para perfilado de zonas (en paralelo) 🟢

**Asignado a:** Integrante 3 · **Fase:** 3 · **Estimación:** 1 día
**Depende de:** ninguno (usa crudos de #3/#4) · **Bloquea a:** ninguno

**Criterios de aceptación:**
- [x] Notebook con perfiles delictivos por localidad (proporción de cada tipo de delito).
- [x] Tendencia por año identificada (¿sube o baja cada tipo de delito por localidad?).
- [x] Hipótesis preliminar de cuántos perfiles distintos podrían existir.

---

### [CLUST] #26 — Features de perfil de zona + línea base z-score

**Asignado a:** Integrante 3 · **Fase:** 3 · **Estimación:** 1 día
**Depende de:** #9 · **Bloquea a:** #27, #36

**Descripción:** Construir el vector de features por localidad para el clustering
(tasas por tipo de delito, señal de NUSE, contexto socioeconómico), estandarizado.
**Y** calcular la **línea base histórica (media/dispersión) por localidad–tipo de
delito** (sobre los conteos anuales) que usará el flag z-score (#36).

**Criterios de aceptación:**
- [x] Matriz localidad × features estandarizada y documentada.
- [x] Línea base (media + desviación) por localidad–tipo de delito, calculada con los conteos anuales del histórico, y guardada.
- [x] Sin fuga: la línea base solo usa histórico, no el reporte que se evaluará.

---

### [CLUST] #27 — Entrenar K-Means + tipología + `clusters.joblib` 🎯

**Asignado a:** Integrante 3 · **Fase:** 3 · **Estimación:** 2 días
**Depende de:** #26 · **Bloquea a:** #20, #23, #28, #37

**Descripción:** Entrenar K-Means sobre las features de perfil de zona, elegir k con
codo + silhouette, **caracterizar e interpretar** cada cluster como tipología
accionable y serializar.

**Criterios de aceptación:**
- [x] Curva de codo + silhouette para un rango de k; k final justificado.
- [x] Cada zona asignada a un cluster; parámetros (k, n_init, random_state) reproducibles.
- [x] Tabla de perfiles por cluster con **nombre interpretable** ("perfil hurto-alto", "perfil violencia-intrafamiliar", etc.) + lectura accionable (1 párrafo por perfil).
- [x] `models/clustering/clusters.joblib` + `models/clustering/zona_cluster.parquet` (zona, cluster, nombre_perfil) para la API y el dashboard.

---

### [CLUST] #28 — Validación interna del clustering

**Asignado a:** Integrante 3 · **Fase:** 3 · **Estimación:** 1 día
**Depende de:** #27 · **Bloquea a:** #39

**Descripción:** Validar que la segmentación es estable y no arbitraria: silhouette
por cluster, estabilidad ante semillas/submuestras, y comparación con una agrupación
trivial (solo por conteo total).

**Criterios de aceptación:**
- [x] Silhouette global y por cluster reportado.
- [x] Prueba de estabilidad (varias semillas / submuestreo) documentada.
- [x] Argumento de por qué la tipología aporta más que ordenar zonas por conteo.

---

### [CLUST] #29 — Función `flag_zscore()` para el reporte ciudadano 🤝

**Asignado a:** Integrante 3 · **Fase:** 4 · **Estimación:** 0.5 día
**Depende de:** #26 · **Bloquea a:** #36

**Descripción:** Entregar la función del flag de anomalía (input: localidad, tipo de
delito, conteo reciente; output: ¿desviación? + score) que el dashboard usa sobre el
reporte ciudadano simulado. Compara el conteo reciente contra la línea base histórica
por localidad–tipo (#26).

**Criterios de aceptación:**
- [x] `flag_zscore(localidad, tipo_delito, conteo)` documentada y testeada con casos límite.
- [x] Acordada con la vista de reporte del dashboard (#36).
- [x] Sin fuga: usa solo la línea base histórica de #26.

---

### [CLUST] #30 — QA cruzada: revisar el predictivo (Int. 2) 🔁

**Asignado a:** Integrante 3 · **Fase:** 4 · **Estimación:** 0.5 día
**Depende de:** #19 · **Bloquea a:** #39

**Descripción:** **QA cruzada.** Revisión corta del predictivo de Int. 2 para la
sección compartida: ¿hay fuga temporal?, ¿la métrica es adecuada?, ¿solo replica
sesgo de vigilancia? Deja un comentario de validación.

**Criterios de aceptación:**
- [ ] Comentario de validación cruzada del predictivo en la sección compartida del informe.
- [ ] Verificación explícita de ausencia de fuga temporal.
- [ ] Al menos 1 hallazgo accionable o confirmación de validez con evidencia.

---

### [CLUST] #31 — Auditoría de sesgo (predictivo + clustering)

**Asignado a:** Integrante 3 · **Fase:** 4 · **Estimación:** 1 día
**Depende de:** #11, #19, #27 · **Bloquea a:** #39

**Descripción:** Auditar si los modelos **replican sesgo de sobre-vigilancia**: ¿las
zonas de "alto riesgo" y los clusters peligrosos coinciden con zonas históricamente
más patrulladas (más registros) y no necesariamente con más delito real? **La
discusión de sesgo/estigmatización no se recorta.**

**Criterios de aceptación:**
- [ ] Comparación entre intensidad de registro y proxys de delito real / contexto.
- [ ] Al menos 2 riesgos de sesgo/estigmatización identificados con evidencia.
- [ ] Recomendaciones de uso responsable (qué NO debe hacerse con el mapa).

---

### [CLUST] #32 — Scaffold del dashboard + consumo de `/zonas-riesgo` (con mock) 🟢

**Asignado a:** Integrante 3 · **Fase:** 5 · **Estimación:** 1 día
**Depende de:** ninguno (mock al inicio) · **Bloquea a:** #33, #34, #36

**Descripción:** Montar `app/streamlit_app.py`, su `requirements.txt`, un mapa Folium
base de Bogotá con `streamlit-folium`, y la función de consumo de la API
(`@st.cache_data`) con un **mock** del GeoJSON de `/zonas-riesgo` para construir todo
sin esperar a la API real.

**Criterios de aceptación:**
- [x] `streamlit run app/streamlit_app.py` levanta y muestra el mapa base de Bogotá.
- [x] Función de carga del GeoJSON (mock con el shape acordado en #20).
- [x] Layout base (sidebar de controles + área de mapa) + README de cómo correr.

---

### [CLUST] #33 — Capas del mapa: coroplético de riesgo + puntos NUSE + tipología

**Asignado a:** Integrante 3 · **Fase:** 5 · **Estimación:** 2 días
**Depende de:** #5, #27, #32 · **Bloquea a:** #34

**Descripción:** Sobre el scaffold, construir las tres capas con selector: (a)
coroplético de localidades coloreado por riesgo, (b) densidad de NUSE por localidad/UPZ
(el dato es agregado, no trae lat/lon), (c) tipología de zonas del clustering (color +
etiqueta de perfil).

**Criterios de aceptación:**
- [x] Coroplético colorea las localidades por riesgo, con selector de año/tipo de delito y leyenda + tooltip por localidad.
- [x] Capa de densidad NUSE activable, coloreada por volumen de llamadas por localidad/UPZ (sin puntos, porque el dato es agregado).
- [x] Capa de tipología que colorea las zonas por cluster con la etiqueta de perfil (#27) y tooltip en lenguaje no técnico.

---

### [CLUST] #34 — Integrar la API real en el dashboard (reemplazar mock) 🤝

**Asignado a:** Integrante 3 · **Fase:** 5 · **Estimación:** 0.5 día
**Depende de:** #20, #33 · **Bloquea a:** #40

**Descripción:** Apuntar el dashboard a la API real `GET /zonas-riesgo` en lugar del
mock. **Sin datos mock en la demo final.**

**Criterios de aceptación:**
- [ ] El mapa de riesgo y la tipología se alimentan del endpoint real.
- [ ] GeoJSON cacheado (`@st.cache_data`), no re-pedido por cada interacción.
- [ ] Prueba end-to-end: API → dashboard lo refleja. Sin mocks.

---

### [CLUST] #35 — Sección de clustering + ética/sesgo del informe

**Asignado a:** Integrante 3 · **Fase:** 3–4 (cierre) 🔵 · **Estimación:** 1 día
**Depende de:** #27, #28, #31 · **Bloquea a:** ninguno

**Criterios de aceptación:**
- [ ] Sección de clustering con método, validación interna y tipología accionable.
- [ ] **Discusión ética** con los hallazgos de la auditoría de sesgo (#31).
- [ ] Métricas del clustering en la sección compartida + comentario cruzado de Int. 2 (#23).
- [ ] Trazabilidad a "Innovación", "Impacto y escalabilidad" y requisito ético.

---

### [CLUST] #36 — Reporte ciudadano simulado en el dashboard + flag z-score (con Int. 4) 🤝

**Asignado a:** Integrante 3 (con Int. 4) · **Fase:** 4–5 · **Estimación:** 1.5 días
**Depende de:** #29, #32 · **Bloquea a:** ninguno

**Descripción:** Formulario que añade un reporte (tipo de delito, ubicación por clic en
el mapa, descripción) a `st.session_state` y lo dibuja como punto, **sin base de datos**.
Aplica el `flag_zscore()` (#29) —que compara por **localidad + tipo de delito** contra
el histórico— y muestra si es una desviación. Incluye el **aviso de privacidad /
consentimiento opt-in**. Comparte con Int. 4 el patrón de aviso de privacidad para
mantenerlo consistente con el permiso de GPS del móvil.

**Criterios de aceptación:**
- [x] El formulario añade un punto a la sesión y lo renderiza en el mapa.
- [x] El reporte dispara el flag z-score y muestra resultado interpretable.
- [x] Validación de input (rechaza coords fuera de Bogotá; campos requeridos; no rompe ante input ruidoso/faltante).
- [x] Checkbox de consentimiento opt-in + enlace al aviso de privacidad (Ley 1581/2012). **No se recorta.**

---

# 🟥 INTEGRANTE 4 — APP MÓVIL (Fase 5–6)

### [APP] #37 — Decisión de framework móvil + setup inicial 🔴🟢

**Asignado a:** Integrante 4 · **Fase:** 5 · **Estimación:** 0.5 día
**Depende de:** ninguno (primeros días) · **Bloquea a:** #38, #39, #40, #41

**Descripción:** **Decisión bloqueante de los primeros días.** Confirmar el framework
móvil (recomendado **Expo / React Native** por el camino más corto a APK instalable y
pruebas en dispositivo real con Expo Go). Dejar `mobile/` inicializado y corriendo.

**Criterios de aceptación:**
- [ ] Framework decidido y registrado (recomendación por defecto: Expo / React Native).
- [ ] `mobile/` inicializado (`npx create-expo-app`), `npm install` ok.
- [ ] `npx expo start` levanta y abre en **Expo Go sobre un teléfono físico** (no solo emulador).
- [ ] README de `mobile/` con cómo correr y cómo apuntar a la API por IP de LAN / túnel.

---

### [APP] #38 — Pantalla principal + consumo de `/zonas-riesgo` (con mock)

**Asignado a:** Integrante 4 · **Fase:** 5 · **Estimación:** 1 día
**Depende de:** #37 · **Bloquea a:** #39, #40

**Descripción:** Pantalla de estado/mapa que muestra el nivel de riesgo de la zona
actual, consumiendo un **mock** del GeoJSON de `/zonas-riesgo` mientras la API real
no esté lista.

**Criterios de aceptación:**
- [ ] Pantalla principal con indicador de "riesgo de tu zona" alimentado por el mock.
- [ ] Estado de carga/error si la API no responde.
- [ ] Estructura de componentes lista para enchufar la capa de datos real (#21).

---

### [APP] #39 — Geolocalización en tiempo real + permisos + privacidad opt-in 🎯

**Asignado a:** Integrante 4 · **Fase:** 5 · **Estimación:** 1.5 días
**Depende de:** #38 · **Bloquea a:** #40, #41

**Descripción:** Leer la ubicación del dispositivo en tiempo real (`expo-location`)
con muestreo periódico en primer plano. Solicitar el permiso de ubicación con un
**aviso de privacidad / consentimiento opt-in** explícito antes de pedirlo.

**Criterios de aceptación:**
- [ ] La app solicita permiso de ubicación con aviso de privacidad opt-in (Ley 1581/2012). **No se recorta.**
- [ ] Muestra la posición actual y la actualiza periódicamente en primer plano.
- [ ] Manejo del caso "permiso denegado" sin romper (mensaje claro + modo demo disponible).

---

### [APP] #40 — Notificación local al entrar a zona de riesgo alto 🎯🤝

**Asignado a:** Integrante 4 · **Fase:** 5 · **Estimación:** 1.5 días
**Depende de:** #21, #39 · **Bloquea a:** #42, #43

**Descripción:** Conectar el GPS (#39) con la capa de geofencing (#21): cuando la
coordenada actual cae en una zona de riesgo alto, disparar una **notificación local**
(`expo-notifications`). Evitar spam (notificar solo en la transición a zona alta).

**Criterios de aceptación:**
- [ ] Al entrar a una zona de riesgo alto, se dispara una notificación local visible.
- [ ] Anti-rebote: no re-notifica mientras se permanece en la misma zona; re-arma al salir.
- [ ] Funciona con la app en primer plano sobre un dispositivo físico real.

---

### [APP] #41 — Modo demo: ubicación simulada que dispara la alerta 🎯

**Asignado a:** Integrante 4 (coords con Int. 3) · **Fase:** 5 · **Estimación:** 1 día
**Depende de:** #40 · **Bloquea a:** #43

**Descripción:** Modo demo con **coordenadas simuladas predefinidas** que recorren de
una zona segura a una de riesgo alto, para disparar la alerta de forma **confiable**
durante la presentación en vivo, sin depender de moverse físicamente. Las
coordenadas de zona alta se eligen con Int. 3 a partir del modelo/tipología.

**Criterios de aceptación:**
- [ ] Toggle "modo demo" que inyecta una ruta de coordenadas simuladas.
- [ ] La ruta cruza a una zona de riesgo alto y dispara la notificación de forma reproducible.
- [ ] Documentado el guion exacto de la demo (qué tocar, qué se verá).

---

### [APP] #42 — Integrar la API real en la app + build instalable en dispositivo físico 🎯🤝

**Asignado a:** Integrante 4 · **Fase:** 5 · **Estimación:** 1.5 días
**Depende de:** #20, #40 · **Bloquea a:** #44

**Descripción:** Reemplazar el mock por la API real (`/zonas-riesgo` por IP de LAN o
túnel) y generar un **build instalable** probado en un **dispositivo físico real**
(Android). **Sin datos mock en la entrega final.**

**Criterios de aceptación:**
- [ ] La app consume la API real; el riesgo mostrado/alertado proviene del endpoint, no de mock.
- [ ] App instalada y corriendo en **al menos un dispositivo físico real** (no solo emulador): Expo Go + `eas build -p android` (APK).
- [ ] Documentado cómo apuntar a la API (IP de LAN / túnel) y cómo instalar el APK.

---

### [APP] #43 — Punto de control: ¿activar contingencia PWA? 🔴🤝

**Asignado a:** Integrante 4 (decisión de equipo) · **Fase:** 5 · **Estimación:** 0.25 día
**Depende de:** #40 · **Bloquea a:** #42 / #44

**Descripción:** **Checkpoint de mitad de proyecto, a más tardar fin de Semana 2.**
Evaluar si la app nativa tiene GPS + notificación local funcionando en un dispositivo
físico real. Si **no**, activar el **plan B (PWA instalable)**: mismo flujo de GPS +
Notification API del navegador, instalable vía "Agregar a pantalla de inicio",
**consumiendo el mismo `/zonas-riesgo`** (el contrato no cambia, solo el cliente).

**Criterios de aceptación:**
- [ ] Decisión registrada (seguir con nativa / activar PWA) con la evidencia que la motivó.
- [ ] Si se activa PWA: plan de tareas de la PWA definido para la Semana 3 sin tocar la API.
- [ ] La decisión se toma a más tardar el último día de la Semana 2.

---

### [APP] #44 — Diseño de Fase 6 (monitoring & drift) + demo + pitch + video + informe consolidado

**Asignado a:** Integrante 4 (consolidación con todos) · **Fase:** 5–6 (cierre) 🔵 · **Estimación:** 2 días
**Depende de:** #34, #42, #35, #24, #12 · **Bloquea a:** ninguno

**Descripción:** Documentar el diseño de **monitoring & model drift** y el plan de
re-entrenamiento; preparar la **demo en vivo** (dashboard + app móvil disparando la
alerta en modo demo) y **consolidar las secciones de los 4** en un solo informe con
la sección compartida de evaluación.

**Criterios de aceptación:**
- [ ] `docs/monitoring.md`: métricas de drift, umbrales, frecuencia/trigger de re-entrenamiento, diagrama del ciclo de vida.
- [ ] Guion de demo que recorre dashboard (coroplético + tipología + reporte con flag) y app móvil (alerta en modo demo).
- [ ] Pitch deck cubriendo los 6 criterios + video corto (2–3 min).
- [ ] **Informe final consolidado** (secciones de los 4 + evaluación compartida).

---

## 🧭 Feature: Ruta Más Segura — issues de app móvil (Int. 4)

> Cliente móvil de la feature Ruta Más Segura: buscar destino, pedir rutas al
> endpoint `POST /ruta-segura` (Int. 2, #48) y compararlas por riesgo en el mapa.
> Diseño técnico y código base de la pantalla en `diseño_tecnico_ruta_segura.md`
> §PARTE 6.

### [APP] #49 — Pantalla de búsqueda de destino

**Asignado a:** Integrante 4 · **Fase:** 5 · **Estimación:** 0.5 día
**Depende de:** #37 · **Bloquea a:** #50

**Descripción:** Crear la pantalla `RutaSeguraScreen` con un campo de búsqueda de
texto (geocoding) y la opción de marcar el destino con long-press en el mapa.
Para el geocoding (convertir "Carrera 7 con 32" a coordenadas) usar la API de
geocoding de ORS (Pelias) — misma API key, sin costo adicional. Código de
referencia: `diseño_tecnico_ruta_segura.md` §PARTE 6.

**Criterios de aceptación:**
- [ ] Campo de texto que acepta dirección o nombre de lugar.
- [ ] Request a ORS Geocoding devuelve coordenadas del lugar buscado.
- [ ] Marcador azul en el mapa cuando el destino está seleccionado.
- [ ] Long-press en el mapa también establece el destino.
- [ ] Botón "Calcular ruta segura" visible solo cuando hay destino seleccionado.
- [ ] Estado de carga visible mientras se espera la respuesta.

**Notas técnicas:** Endpoint de geocoding
`GET https://api.openrouteservice.org/geocode/search?text=...&boundary.country=CO`
(añadir `boundary.country=CO` para limitar a Colombia). Si el geocoding resulta
complejo, el MVP puede ser solo el long-press en el mapa — documentar como
simplificación si se toma esa decisión.

---

### [APP] #50 — Integración del endpoint y visualización de rutas 🤝

**Asignado a:** Integrante 4 · **Fase:** 5 · **Estimación:** 1 día
**Depende de:** #48, #49 · **Bloquea a:** #51

**Descripción:** Conectar `RutaSeguraScreen` con el endpoint `POST /ruta-segura`.
Mostrar ambas rutas en el mapa con colores distintos (verde = segura, rojo =
rápida) y el panel de comparativa debajo del mapa con la información de cada ruta.
Código de referencia: `diseño_tecnico_ruta_segura.md` §PARTE 6.

**Criterios de aceptación:**
- [ ] Request al endpoint con origen (GPS actual) y destino seleccionado.
- [ ] Dos Polylines en el mapa con colores según nivel de riesgo.
- [ ] La ruta recomendada (segura) aparece más gruesa o resaltada por defecto.
- [ ] Panel con tiempo, distancia, nivel de riesgo y localidades de cada ruta.
- [ ] Tap en una ruta (mapa o panel) la selecciona/resalta.
- [ ] Advertencia visible si el origen está en zona de riesgo alto.
- [ ] Estado de error visible si el endpoint falla (mensaje amigable, no crash).

**Notas técnicas:** La `geometry_geojson` viene como
`{type: "LineString", coordinates: [[lon, lat], ...]}`; React Native Maps usa
`{latitude, longitude}`, así que hay que mapear
`coords.map(([lon, lat]) => ({ latitude: lat, longitude: lon }))`. Colores:
BAJO=#17D05B, MEDIO=#F5A623, ALTO=#E05252 (consistentes con el resto de la app).

---

### [APP] #51 — Modo demo de ruta segura para la presentación 🎯

**Asignado a:** Integrante 4 · **Fase:** 5 · **Estimación:** 0.25 día
**Depende de:** #50 · **Bloquea a:** ninguno

**Descripción:** Añadir un "modo demo" para la presentación al jurado que
pre-carga un escenario guionizado: origen en Chapinero (zona media), destino en
Plaza de Bolívar, con las dos rutas ya calculadas. Garantiza que la demo funciona
aunque el GPS del dispositivo no coopere o la red sea lenta en el evento. Código
de referencia: `diseño_tecnico_ruta_segura.md` §PARTE 6.

**Criterios de aceptación:**
- [ ] Un botón oculto (triple tap en el logo o botón discreto en Settings) activa el modo demo.
- [ ] Modo demo muestra el escenario Chapinero → Plaza de Bolívar con rutas pre-calculadas.
- [ ] La ruta segura (verde) pasa visiblemente por zonas distintas a la rápida (roja).
- [ ] El modo demo es indistinguible visualmente del modo real para el jurado.
- [ ] Documentado en `docs/validacion_guide.md` cómo activarlo.

**Notas técnicas:** Guardar el response JSON del modo demo como constante en el
código (`DEMO_RUTA_RESPONSE = {...}`). Con el modo demo activo, en vez de hacer el
fetch al endpoint, devolver ese JSON directamente. Así la demo no depende de red
ni de GPS.

---

## 🔗 Dependencias de la feature Ruta Más Segura

```
Int. 2:  #45 → #46 → #47 → #48 ─┐
                                 ├─► #50 → #51
Int. 4:              #49 ────────┘
```

`#48` es el punto de sincronización **SYNC-R**: sin el endpoint entregado en
Swagger UI, `#50` (integración en el móvil) no puede completarse.

---

## Resumen de carga por integrante

| Integrante | Issues | Estimación aprox. |
|---|---|---|
| 1 — Datos | #1–#12 (12 issues) | ~13 días-persona (ruta crítica, front-loaded) |
| 2 — Predictivo + API | #13–#24, #45–#48 (16 issues) | ~15 días-persona (+2.5 por Ruta Más Segura) |
| 3 — Clustering + Dashboard | #25–#36 (12 issues) | ~12.5 días-persona |
| 4 — App móvil | #37–#44, #49–#51 (11 issues) | ~13.25 días-persona (móvil es el frente de mayor riesgo; +1.75 por Ruta Más Segura) |

> Int. 1 es la ruta crítica: hasta que exista el dataset unificado (#9), los demás
> trabajan con datos crudos o mocks. La app móvil se reparte entre Int. 2 (API +
> datos/geofencing) e Int. 4 (cliente, GPS, notificaciones, build). El NLP
> nice-to-have (no listado) solo se aborda si Int. 3 cierra lo obligatorio con holgura.
