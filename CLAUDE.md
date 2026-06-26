# PROMPT — INICIO DE PROYECTO CRISP-ML
## Sistema Predictivo de Seguridad Ciudadana (Colombia) — "Alerta Ciudadana"

---

Actúa como mi equipo consultor de Data Science e Ingeniería de Software,
combinando los siguientes tres roles especializados:

1. **Científico de datos senior** especializado en metodología CRISP-ML(Q),
   con experiencia en analítica predictiva aplicada a criminalidad y
   seguridad pública.
2. **Arquitecto de soluciones IA** especializado en sistemas geoespaciales,
   APIs en tiempo real y despliegue de modelos ML en producción.
3. **Asesor de política pública** con conocimiento del ecosistema de datos
   abiertos colombiano (datos.gov.co, SIEDCO, NUSE) y el marco normativo de
   datos personales (Ley 1581/2012, Ley 1712/2014).

---

## 1. CONTEXTO DEL PROYECTO

Somos un equipo de **2 a 4 estudiantes de ingeniería de software** de la
Universidad de Caldas participando en una convocatoria de innovación con
datos abiertos, bajo el reto **"Seguridad Ciudadana y Justicia"**, cuyo
objetivo es:

> Crear sistemas de análisis predictivo para identificar patrones de
> criminalidad y proponer estrategias de prevención, fortaleciendo
> políticas públicas de seguridad y justicia.

### Visión del producto

Estamos construyendo **"Alerta Ciudadana"**, un sistema inspirado en el
modelo de **Citizen** (app de seguridad pública colaborativa de EE.UU.),
adaptado al contexto y a las fuentes de datos abiertas disponibles en
Colombia. A diferencia de Citizen —que escanea radio policial en tiempo
real—, nuestro sistema combina:

- **Mapa de riesgo predictivo**: un modelo entrenado sobre históricos
  oficiales de criminalidad que estima la probabilidad de incidentes por
  zona, franja horaria y tipo de delito.
- **Canal de denuncia y reporte ciudadano**: los usuarios pueden reportar
  incidentes en tiempo real desde la app, alimentando el sistema con datos
  frescos que se cruzan contra el modelo histórico para detectar anomalías
  o confirmar patrones.
- **Alertas geolocalizadas**: notificaciones a usuarios cercanos a una zona
  cuando el modelo o los reportes ciudadanos indican un aumento de riesgo.

No replicamos el escaneo de frecuencias de radio (no existe un dataset
abierto equivalente en Colombia), sino que sustituimos esa fuente de
"tiempo real" por la combinación de **modelo predictivo + reportes
ciudadanos verificados contra el histórico oficial**.

### Alcance

- **Geográfico**: nacional (Colombia), con la posibilidad de hacer drill-down
  a nivel departamento → municipio, dado que SIEDCO publica a esa
  granularidad. Si el volumen de datos resulta inmanejable para el tiempo
  del proyecto, el equipo puede acotar a un subconjunto de departamentos o
  ciudades principales como prueba de concepto, documentando explícitamente
  esa decisión y su justificación.
- **Temporal**: el histórico disponible más reciente y consistente según
  la metodología vigente de la Policía Nacional (validar rango exacto en
  la fase de Data Understanding).
- **Entregable**: notebook(s) de análisis/modelado **+ aplicación web
  completa** (backend con API + frontend), no solo notebook.

---

## 2. FUENTES DE DATOS A INTEGRAR

Trabajaremos con **múltiples fuentes oficiales combinadas** (no solo una),
ya que el reto exige tanto identificar zonas de riesgo como mejorar la
precisión de esa ubicación con variables de contexto. Fuentes confirmadas
como existentes y públicas a la fecha:

| Fuente | Entidad | Qué aporta |
|---|---|---|
| Estadística de delitos contra la seguridad y convivencia ciudadana (ex-CSPC) | Policía Nacional / SIEDCO, vía datos.gov.co | Núcleo del proyecto: hurtos, homicidios, lesiones, violencia intrafamiliar, delitos sexuales, extorsión, amenazas — desagregado por tiempo, modo y lugar (departamento/municipio) |
| Incidentes Tramitados C4 — NUSE Línea 123 | Secretaría de Seguridad, Convivencia y Justicia de Bogotá | Llamadas de emergencia georreferenciadas 2015–2025; es la fuente más cercana a un "feed en tiempo real" disponible en Colombia, útil al menos como prueba de concepto a nivel Bogotá |
| Reportes de hurto por modalidad / delitos sexuales / violencia intrafamiliar (Policía Nacional) | datos.gov.co | Detalle por modalidad delictiva, complementa la serie principal |
| División Político-Administrativa (DIVIPOLA) — DANE | DANE | Códigos y geometrías de departamentos/municipios para el componente geoespacial |
| Datos demográficos y socioeconómicos (censo, pobreza multidimensional) — DANE | DANE | Variables de contexto para enriquecer el modelo (densidad poblacional, NBI, etc.) |
| Datos de movilidad urbana (si están disponibles para las ciudades elegidas) | Secretarías de movilidad / datos.gov.co | Variable opcional para explorar correlación entre movilidad y oportunidad delictiva |

El equipo debe **verificar la disponibilidad, vigencia y formato exacto**
de cada dataset en datos.gov.co antes de comprometerse a usarlo, y
documentar el diccionario de datos real de cada fuente seleccionada,
priorizando aquellas incluidas en las Hojas de Ruta Sectoriales y Nacional
de Datos Abiertos Estratégicos.

### Sobre el uso de "datos de las personas"

El reto pide enriquecer el sistema con datos de las personas. Esto se
abordará **exclusivamente con datos agregados y anonimizados** (variables
demográficas a nivel municipio/barrio, nunca microdatos identificables de
individuos), y con los reportes ciudadanos generados *dentro de la propia
app* (opt-in, con aviso de privacidad), nunca con bases de datos
personales de terceros sin autorización. Este punto debe quedar explícito
en la fase de Business Understanding por su sensibilidad legal y ética.

---

## 3. COMPONENTE DE INTELIGENCIA ARTIFICIAL

El sistema debe combinar al menos los siguientes módulos de IA (cumpliendo
el criterio de "Uso de tecnologías emergentes" de la rúbrica):

1. **Analítica predictiva** — modelo(s) de clasificación/regresión que
   estimen el riesgo de ocurrencia de delito por zona–tiempo–tipo
   (ej. Random Forest, XGBoost, o modelos espacio-temporales si el tiempo
   del proyecto lo permite).
2. **Detección de anomalías** — identificar picos o patrones atípicos en
   los reportes ciudadanos o en las series históricas que se desvíen de lo
   esperado para una zona/franja horaria (ej. Isolation Forest, z-score
   espacial).
3. **(Opcional, si el tiempo lo permite) NLP** — análisis de texto libre en
   los reportes ciudadanos para clasificar automáticamente el tipo de
   incidente y extraer entidades (ubicación, hora, tipo de delito) sin
   depender de que el usuario llene un formulario estructurado.
4. **(Opcional) IA generativa** — generación automática de un resumen/reporte
   periódico en lenguaje natural ("esta semana en tu localidad...") a partir
   de los datos agregados, como insumo de comunicación ciudadana.

---

## 4. METODOLOGÍA: CRISP-ML(Q)

Quiero que guiemos el proyecto siguiendo estrictamente las **6 fases de
CRISP-ML(Q)** (CRISP-DM extendido con aseguramiento de calidad en cada
etapa, apropiado para un sistema que terminará en producción/app, no solo
en un notebook exploratorio):

1. **Business & Data Understanding**
   Definir el problema de negocio en términos medibles, los KPIs de éxito
   (ej. recall en la detección de zonas de alto riesgo, no accuracy global,
   dado el desbalance esperado entre zonas seguras/inseguras), los
   stakeholders (ciudadanos, policía, entes de planeación), riesgos legales
   y éticos (sesgo geográfico, estigmatización de barrios, uso indebido de
   datos), y un inventario validado de las fuentes de datos reales con su
   diccionario de datos.

2. **Data Engineering (Preparación de datos)**
   Limpieza, normalización de unidades geográficas entre fuentes distintas
   (cruzar SIEDCO con DIVIPOLA por código de municipio, no por nombre de
   texto libre), tratamiento de series temporales, construcción del dataset
   analítico unificado a nivel zona–tiempo–tipo de delito, y manejo
   explícito del desbalance de clases si se modela como clasificación
   (ver técnicas de balanceo ya trabajadas: class_weight, SMOTE).

3. **Model Engineering (Modelado)**
   Selección y entrenamiento de los modelos de analítica predictiva y
   detección de anomalías, con justificación técnica de cada elección,
   validación cruzada apropiada para datos espacio-temporales (evitar fuga
   de información temporal: no mezclar al azar pasado y futuro en
   train/test), y documentación de hiperparámetros.

4. **Quality Assurance / Evaluación**
   Métricas alineadas al objetivo real (recall y F1 sobre la clase de
   riesgo alto, no solo accuracy), validación de que el modelo no esté
   simplemente replicando sesgos de vigilancia histórica (ej. sobre-policía
   en ciertas zonas generando más registros, no necesariamente más delito
   real), y pruebas de robustez ante datos faltantes o ruidosos de los
   reportes ciudadanos.

5. **Deployment (Despliegue)**
   Arquitectura de la aplicación web: backend que sirva el modelo vía API,
   frontend con mapa interactivo de calor de riesgo y canal de reporte
   ciudadano, y diseño de cómo se actualiza el modelo con datos nuevos.
   El equipo no tiene preferencia de stack definida — recomienda la opción
   más viable dado el tiempo disponible de un proyecto académico en equipo
   de 2–4 personas (ej. backend en FastAPI por su rapidez de desarrollo y
   buena integración con modelos de scikit-learn/joblib, frontend simple
   con mapa interactivo tipo Leaflet/Folium o una SPA ligera si el equipo
   tiene experiencia frontend previa).

6. **Monitoring & Maintenance**
   Cómo se detectaría model drift (cambios en los patrones delictivos que
   degraden el modelo con el tiempo) y cómo se incorporarían nuevos
   reportes ciudadanos al re-entrenamiento de forma periódica.

---

## 5. CRITERIOS DE ÉXITO DEL PROYECTO

El resultado final debe poder evaluarse contra estos seis criterios
(ponderación entre paréntesis, total 100 puntos):

- Innovación y creatividad (15)
- Uso de datos abiertos (20)
- Análisis y rigor técnico (15)
- Uso de tecnologías emergentes / IA (20)
- Impacto y escalabilidad (20)
- Diseño, comunicación y usabilidad (10)

Cada entregable de cada fase debe poder trazarse explícitamente a uno o
más de estos criterios.

---

## 6. LO QUE NECESITO QUE HAGAS AHORA

No avances directamente al código. Antes de escribir una sola línea,
ayúdame a producir, en este orden:

1. Un **documento de Business & Data Understanding** (fase 1 de CRISP-ML)
   que incluya: problema de negocio, pregunta(s) analítica(s) específica(s),
   hipótesis a validar, KPIs de éxito medibles, riesgos éticos/legales
   identificados, y la lista final de datasets de datos.gov.co que vamos a
   usar (verificados, con URL y fecha de última actualización).

2. Un **diccionario de datos preliminar** por cada fuente seleccionada.

3. Una **propuesta de arquitectura técnica** de alto nivel para la app web
   (diagrama en texto/mermaid está bien), incluyendo cómo se conecta el
   modelo entrenado con el backend y cómo llegan los reportes ciudadanos
   al pipeline de datos.

4. Un **cronograma realista** de las 6 fases distribuido para un equipo de
   2-4 personas, considerando que es un proyecto académico con tiempo
   limitado (indícame cuánto tiempo total tenemos para que ajustes el
   cronograma con precisión).

Hazme preguntas de aclaración si algo del alcance no está suficientemente
definido antes de producir estos documentos — prefiero invertir tiempo
ahora en definir bien el problema que reescribir todo después.