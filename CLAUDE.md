# Alerta Ciudadana — Documento maestro del proyecto

Este archivo es la **única fuente de verdad** del proyecto. Define qué se
construye, con qué datos, con qué arquitectura, bajo qué metodología y bajo qué
restricciones. Cualquier decisión de desarrollo se traza contra este documento.

Reto **"Seguridad Ciudadana y Justicia"** — convocatoria de innovación con datos
abiertos. Equipo de **4 estudiantes de ingeniería de software**, Universidad de
Caldas. Metodología **CRISP-ML(Q)**.

---

## 1. Qué es Alerta Ciudadana

**Alerta Ciudadana** es un sistema de analítica predictiva de seguridad ciudadana
para **Bogotá**, construido sobre datos abiertos oficiales de Colombia. Convierte
el histórico oficial de criminalidad en una **alerta accionable en el momento**:
estima el riesgo por zona (localidad) y tipo de delito, y avisa al ciudadano
cuando entra a una zona de riesgo alto.

El proyecto tiene **dos entregables de producto** que consumen **el mismo modelo
y los mismos datos** a través de una **API ligera de un solo endpoint**:

1. **Dashboard analítico (Streamlit).** Panel donde se exploran los resultados del
   análisis: mapa de riesgo por zona, tipología de zonas por perfil delictivo, y
   una demo de reporte ciudadano con detección de anomalías por z-score.

2. **App móvil nativa (Expo / React Native).** Lee la ubicación del dispositivo en
   tiempo real y dispara una **notificación local** cuando el usuario entra a una
   zona de riesgo alto. Es la **pieza central de la propuesta de valor**: lleva el
   análisis estático al bolsillo del ciudadano como una alerta geolocalizada en el
   momento, en la línea de los productos de seguridad pública que inspiran el reto.

No hay backend pesado ni base de datos persistente. El estado del reporte
ciudadano vive en sesión/memoria, no en una BD productiva. La autoridad de
inferencia es la API: ambos clientes son consumidores delgados del mismo contrato
de datos.

> **Nota de validación de fuentes (Integrante 1 · #1 · 2026-06-30).** Tras
> inspeccionar los datos reales en datos abiertos, se ajustan tres supuestos de
> diseño a lo que las fuentes abiertas efectivamente permiten. Los cambios se
> documentan como parte del rigor técnico (no se "arreglan" en silencio):
>
> 1. **NUSE no es punto georreferenciado.** El dataset abierto de NUSE/Línea 123
>    viene **agregado por localidad y UPZ × mes × tipo** (sin lat/lon por
>    incidente). Por tanto la "capa de puntos / tiempo real" se reencuadra como
>    **capa de densidad por UPZ** (resolución más fina que la localidad de
>    SIEDCO). La única capa de puntos real queda en los reportes ciudadanos
>    simulados.
> 2. **No existe franja horaria en el dato abierto.** Ni SIEDCO (anual por
>    localidad) ni NUSE (mensual) ni los microdatos de la Policía (fecha, sin
>    hora) publican hora del hecho. La variable objetivo se redefine de
>    *zona–franja horaria–tipo* a **zona (localidad) – año – tipo de delito**. La
>    franja horaria pasa a trabajo futuro (requiere microdato con hora, no
>    disponible en abierto).
> 3. **Grano temporal del predictivo = año.** SIEDCO abierto es anual por
>    localidad. La validación espacio-temporal sin fuga se mantiene: **entrenar
>    con años ≤2024, evaluar 2025**; 2026-YTD se reserva como validación futura.

### Naturaleza del mapa: una composición de capas

El mapa **no** es un único mapa de calor de puntos exactos, porque el dato abierto
no es de punto exacto. SIEDCO publica la criminalidad como **polígono por
localidad** (EPSG:4686), no como coordenada del hecho. La consecuencia directa de
la naturaleza del dato es que el mapa se construye en **tres capas**:

1. **Coroplético (fondo estadístico oficial)** — polígonos por localidad de Bogotá,
   coloreados por nivel de riesgo del modelo, alimentado por **SIEDCO**.
2. **Densidad por UPZ** — alimentado por **NUSE / Línea 123**, agregado por UPZ
   (Unidad de Planeamiento Zonal), resolución más fina que la localidad. No es
   punto exacto: el dato abierto de NUSE viene agregado, no georreferenciado por
   incidente (ver Nota de validación arriba).
3. **Reportes ciudadanos** — puntos individuales (simulados, en sesión) sobre las
   capas anteriores.

Distinguir entre **dato administrativo agregado por localidad** (SIEDCO, polígono
anual) y **dato operativo agregado por UPZ** (NUSE, densidad mensual) es una
decisión de diseño fundamentada en la estructura real de las fuentes, y suma en
"Análisis y rigor técnico".

### Alcance geográfico: Bogotá

El sistema cubre **Bogotá únicamente**. Es la ciudad con datos NUSE/C4 (Línea 123)
disponibles como dato abierto y con la desagregación intraurbana (localidad y UPZ)
que el producto necesita. Acotar a Bogotá es una **decisión de alcance**, no una
limitación: concentra el esfuerzo donde existen las fuentes con granularidad de
zona (SIEDCO por localidad, NUSE por UPZ).

### Lo que NO se construye (y por qué, en términos del proyecto)

- **Sin base de datos persistente.** Los reportes ciudadanos son una simulación de
  sesión, suficiente para demostrar el flujo de detección de anomalías sin la
  complejidad operativa de un sistema transaccional en producción.
- **Sin NLP ni sistema de recomendación obligatorios.** Son mejoras declaradas como
  trabajo futuro; el sistema cumple su propuesta con el predictivo + el clustering.
- **Sin hosting público de tienda de aplicaciones.** El dashboard corre localmente
  y la app móvil se instala desde un build de desarrollo (APK / build de Expo),
  no desde Google Play / App Store.

---

## 2. Fuentes de datos

El sistema integra **un mínimo de tres fuentes oficiales y públicas**, cruzadas
por **código DANE** (nunca por nombre de texto libre). El cruce por código es lo
que permite unir fuentes heterogéneas sin ambigüedad y lo que deja la arquitectura
lista para escalar a más ciudades.

| Fuente | Entidad | Qué aporta | Naturaleza geográfica |
|---|---|---|---|
| **SIEDCO / "Delito de Alto Impacto"** | Policía Nacional / Secretaría de Seguridad de Bogotá, vía datos.gov.co | Núcleo del análisis: hurtos, homicidios, lesiones, violencia intrafamiliar, delitos sexuales, etc., por tiempo, modalidad y lugar | **Polígono por localidad** (EPSG:4686). No contiene coordenada-punto del hecho. |
| **NUSE / Línea 123 (C4)** | Secretaría de Seguridad, Convivencia y Justicia de Bogotá | Volumen de llamadas de emergencia (RIÑA, RUIDO, ACCIDENTE, MALTRATO, etc.); sostiene la capa de densidad por UPZ como señal complementaria (taxonomía distinta a los delitos SIEDCO) | **Agregado por localidad y UPZ × mes × tipo** (EPSG no aplica: sin geometría propia; se ubica por código de localidad/UPZ). Verificado: no trae lat/lon por incidente. |
| **DIVIPOLA + variables demográficas (DANE)** | DANE | Códigos oficiales para cruzar las fuentes y geometrías de localidades; variables de contexto (densidad poblacional, NBI/pobreza) | Códigos + geometrías de localidad. |

El equipo verifica disponibilidad, vigencia y formato exacto de cada dataset en
datos.gov.co antes de comprometerlo, y documenta el diccionario de datos real de
cada fuente seleccionada.

### Sobre los "datos de las personas"

El enriquecimiento con datos de personas se hace **exclusivamente con datos
agregados y anonimizados** a nivel zona (variables demográficas por localidad,
nunca microdatos identificables de individuos) y con los reportes ciudadanos
generados **dentro de la propia app**, siempre opt-in y con aviso de privacidad.
No se usan bases de datos personales de terceros. Este punto es una restricción
legal y ética del proyecto (Ley 1581/2012, Ley 1712/2014).

---

## 3. Componentes de Inteligencia Artificial

1. **Modelo predictivo de riesgo (Random Forest / Gradient Boosting).** Estima el
   nivel de riesgo por **zona (localidad) – año – tipo de delito** (la franja
   horaria no existe en el dato abierto; ver Nota de validación en §1). Se entrena
   con **manejo explícito del desbalance de clases** (class_weight / SMOTE) y se
   valida con un esquema **espacio-temporal sin fuga de información** (entrenar con
   años ≤2024, evaluar 2025; nunca K-fold aleatorio).

2. **Clustering de zonas (K-Means).** Agrupa las localidades de Bogotá por **perfil
   delictivo** (mezcla de tipos de delito, señal de NUSE y contexto
   socioeconómico; la franja horaria no existe en el dato abierto, ver Nota de
   validación) y produce una **tipología interpretable de zonas** (p. ej.
   "perfil hurto-alto", "perfil violencia-intrafamiliar", "perfil de bajo
   incidente"). No es un ranking por conteo: es una segmentación accionable que
   colorea y etiqueta el mapa coroplético. El nivel intermedio de la convocatoria
   nombra literalmente clustering, su validación interna es directa
   (elbow / silhouette) y el resultado es un insight comunicable a planeación.

3. **Detección de anomalías por z-score.** Cuando llega un reporte ciudadano
   simulado, se compara la **frecuencia reciente** de esa zona–tipo de delito contra
   su **línea base histórica** (media/desviación de los conteos anuales) y se marca
   si el patrón es atípico. Es un chequeo
   estadístico que vive dentro del cliente (dashboard), no un modelo con ciclo de
   vida propio; preserva el diferenciador "reporte verificado contra el histórico".

4. **NLP / IA generativa (nice-to-have, no bloqueante).** Clasificación del texto
   libre de los reportes en tipo de delito + extracción de entidades, y/o resumen
   automático en lenguaje natural ("esta semana en tu localidad…"). Solo si el
   tiempo lo permite tras cerrar lo obligatorio.

> **Riesgo abierto a verificar contra el texto oficial:** si la convocatoria
> exigiera NLP / sistemas de recomendación como **mínimo** (no como sugerencia),
> el NLP pasa de nice-to-have a obligatorio y se recorta otro frente para
> garantizarlo. Confirmar antes de la Semana 2.

---

## 4. Arquitectura técnica

```
                         ┌─────────────────────────┐
                         │   Datos abiertos (3+)    │
                         │  SIEDCO · NUSE · DANE    │
                         └────────────┬─────────────┘
                                      │ ingesta + limpieza + cruce por código DANE
                                      ▼
                         ┌─────────────────────────┐
                         │ dataset_analitico.parquet│
                         │  zonas_bogota.geojson    │
                         └────────────┬─────────────┘
                          ┌───────────┴───────────┐
                          ▼                       ▼
              ┌───────────────────┐   ┌───────────────────────┐
              │ Modelo predictivo  │   │  Clustering K-Means    │
              │ (RF/Grad.Boosting) │   │  (tipología de zonas)  │
              │ → model.joblib     │   │  → clusters.joblib     │
              └─────────┬──────────┘   └───────────┬────────────┘
                        └───────────┬───────────────┘
                                    ▼
                      ┌───────────────────────────┐
                      │   API ligera (1 endpoint)  │
                      │   GET /zonas-riesgo        │
                      │   → GeoJSON con riesgo,    │
                      │     cluster y metadatos     │
                      │   (FastAPI mínimo)         │
                      └─────────────┬───────────────┘
                       ┌────────────┴────────────┐
                       ▼                         ▼
          ┌─────────────────────┐   ┌─────────────────────────┐
          │ Dashboard Streamlit  │   │   App móvil (Expo/RN)    │
          │ - mapa coroplético   │   │   - lee GPS en tiempo    │
          │ - capa NUSE          │   │     real                  │
          │ - tipología clusters │   │   - consulta /zonas-     │
          │ - reporte simulado + │   │     riesgo periódicamente│
          │   flag z-score       │   │   - dispara notificación  │
          └─────────────────────┘   │     local al entrar a     │
                                     │     zona de riesgo alto   │
                                     │   - modo demo: ubicación  │
                                     │     simulada para la      │
                                     │     presentación en vivo  │
                                     └───────────────────────────┘
```

### Contrato de datos: `GET /zonas-riesgo`

Único endpoint del sistema. Devuelve un **GeoJSON** de las localidades de Bogotá,
cada una con: geometría, **nivel/probabilidad de riesgo** (modelo predictivo),
**cluster + nombre de perfil** (clustering) y metadatos (código DANE, año y tipo de
delito consultados). Tanto el dashboard como la app móvil consumen este mismo contrato; el
contrato no cambia según el cliente. Se sirve con **FastAPI** (un solo endpoint,
sin BD), cargando `model.joblib` y `clusters.joblib` en memoria.

### Framework móvil: Expo (React Native)

Se elige **Expo (React Native)** como única tecnología móvil. Es el camino más
corto de "cero a APK instalable" para un equipo sin experiencia nativa previa:
`expo-location` y `expo-notifications` corren en **Expo Go** sobre un dispositivo
físico real sin compilar nativo en cada cambio, y `eas build -p android` produce un
APK instalable. El dispositivo objetivo del entregable es **Android**.

**Alcance realista de la alerta:** la notificación es **local y en primer plano**
(app abierta → muestreo de GPS → notificación al entrar a zona de riesgo alto),
más un **modo demo** con ubicación simulada para disparar la alerta de forma
confiable en la presentación. El geofencing en segundo plano (app cerrada) y el
push real vía servidor (FCM/APNs) quedan como trabajo futuro.

**Alcanzabilidad de la API desde el dispositivo físico:** el teléfono no alcanza
`localhost`; consume la API por **IP de LAN** (misma Wi-Fi) o por **túnel**
(p. ej. ngrok / túnel de Expo). Esto se documenta y se prueba como parte del
entregable.

### Plan de contingencia: PWA instalable

Si en el **punto de control de mitad de proyecto** (a más tardar fin de Semana 2)
la app nativa no tiene la geolocalización y la notificación local funcionando en un
dispositivo físico real, se reemplaza el cliente móvil por una **PWA instalable**
(mismo flujo de GPS + Notification API del navegador, instalable vía "Agregar a
pantalla de inicio"). **El endpoint `/zonas-riesgo` no cambia**: solo cambia el
cliente que lo consume. El plan B se declara desde el inicio para activarlo sin
perder tiempo decidiéndolo bajo presión.

---

## 5. Metodología CRISP-ML(Q)

1. **Business & Data Understanding.** Problema de negocio medible, KPIs (recall/F1
   sobre la clase de riesgo alto, no accuracy global, dado el desbalance esperado),
   stakeholders (ciudadanía, policía, planeación), riesgos legales/éticos (sesgo
   geográfico, estigmatización de barrios, uso indebido de datos) e inventario
   validado de fuentes con su diccionario de datos.

2. **Data Engineering.** Limpieza, normalización de unidades geográficas entre
   fuentes (cruce por código DANE), tratamiento de series temporales, construcción
   del **dataset analítico unificado** a nivel zona (localidad) – año – tipo de
   delito, y manejo explícito del desbalance de clases.

3. **Model Engineering.** Entrenamiento de los dos modelos formales —predictivo
   (RF/Gradient Boosting) y clustering (K-Means)— con justificación de cada
   elección, **validación espacio-temporal sin fuga** en el predictivo y validación
   interna (elbow/silhouette) en el clustering, con hiperparámetros documentados.

4. **Quality Assurance / Evaluación.** Métricas alineadas al objetivo
   (recall/F1 de la clase de riesgo alto), verificación de que el modelo no replique
   sesgos de sobre-vigilancia histórica, y pruebas de robustez ante datos faltantes
   o ruidosos. La QA es **cruzada**: nadie evalúa su propio modelo.

5. **Deployment.** API ligera `/zonas-riesgo` + dos clientes (dashboard Streamlit y
   app móvil Expo). El dashboard corre con un comando; la app se instala en un
   dispositivo físico real desde un build de desarrollo.

6. **Monitoring & Maintenance.** Cómo se detectaría model drift (cambios en los
   patrones delictivos que degraden el modelo) y cómo se incorporarían los nuevos
   reportes ciudadanos al re-entrenamiento periódico.

---

## 6. Criterios de éxito (100 puntos)

| Criterio | Peso |
|---|---|
| Innovación y creatividad | 15 |
| Uso de datos abiertos | 20 |
| Análisis y rigor técnico | 15 |
| Uso de tecnologías emergentes / IA | 20 |
| Impacto y escalabilidad | 20 |
| Diseño, comunicación y usabilidad | 10 |

Cada entregable de cada fase se traza explícitamente a uno o más de estos criterios
(ver `DEFINITION_OF_DONE.md`).

---

## 7. Restricciones que no se recortan

Bajo ninguna circunstancia se eliminan:

- Las **3 fuentes oficiales** de datos y su **cruce por código DANE**.
- El **manejo explícito del desbalance de clases** en el predictivo.
- La **validación espacio-temporal sin fuga de información**.
- La **discusión ética** sobre sesgo de sobre-vigilancia y estigmatización de zonas,
  con auditoría de sesgo sobre ambos modelos.
- El **aviso de privacidad / consentimiento opt-in**, tanto en el reporte ciudadano
  simulado como en el permiso de geolocalización de la app móvil.

---

## 8. Estructura del repositorio

```
OpenDataProject2026/
├── CLAUDE.md                 # Documento maestro (este archivo)
├── README.md                 # Cómo correr cada pieza
├── BACKLOG.md                # Issues por integrante
├── CRONOGRAMA.md             # Semanas, dependencias y sincronizaciones
├── DEFINITION_OF_DONE.md     # DoD a nivel proyecto
├── LICENSE · Changelog.md    # Licencia MIT y registro de cambios
├── requirements.txt          # Dependencias Python (environment.yml para Conda)
├── docs/                     # Planteamiento, metodología, fuentes, diccionarios, validación
├── data/                     # 01_raw / 02_intermediate / 03_primary / 04_model_output (gitignored)
├── src/                      # Pipeline de datos: config, ingestas, limpieza, cruce (Integrante 1)
├── pipelines/                # pipeline_ml.py — orquestador extremo a extremo (Integrante 1)
├── notebooks/                # EDA y experimentación (scaffolds 01–05 + ejemplo)
├── tests/                    # Calidad de datos e inferencia
├── reports/                  # Figuras y reporte final
├── RECURSOS/                 # Presentación y material visual de la entrega
├── models/
│   ├── predictivo/           # RF/Gradient Boosting (Integrante 2)
│   └── clustering/           # K-Means (Integrante 3)
├── api/                      # API ligera FastAPI — GET /zonas-riesgo (Integrante 2)
├── app/                      # Dashboard Streamlit (Integrante 3)
└── mobile/                   # App móvil Expo / React Native (Integrante 4)
```

---

## 9. Equipo y pistas de trabajo

| # | Pista | Responsabilidad principal | Fase CRISP-ML |
|---|---|---|---|
| 1 | **Datos** | Ingesta, limpieza, cruce por DANE, dataset unificado + GeoJSON de zonas | 1–2 |
| 2 | **Predictivo + API** | Modelo de riesgo (RF/GB) + API `/zonas-riesgo` + capa de datos del móvil | 3a + 5 |
| 3 | **Clustering + Dashboard** | Tipología de zonas (K-Means) + ética/sesgo + dashboard Streamlit | 3b + 5 |
| 4 | **App móvil** | Cliente Expo: GPS + notificación local + modo demo + build en dispositivo | 5 |

La **Fase 4 (QA)** es cruzada y se consolida en una **sección compartida de
evaluación** del informe: cada responsable reporta sus métricas y un compañero deja
un comentario corto de validación. Ver `BACKLOG.md` (issues) y `CRONOGRAMA.md`
(plan semanal y puntos de sincronización).

---

## 10. Guía operativa para agentes de código

### Estado real de implementación (no confundir con la arquitectura objetivo de §4)

- **Completo:** `src/` (ingestas, limpieza, cruce) + `pipelines/pipeline_ml.py` —
  Issues #1–#12 (Integrante 1). El handoff detallado está en
  `docs/HANDOFF_INT1.md` (contrato de columnas, decisiones pendientes, sesgos
  identificados en los datos — léelo antes de tocar el dataset analítico).
- **Scaffold / placeholder:** `src/feature_engineering.py` (solo expone la
  variable objetivo `riesgo_alto`), `src/model_training.py`,
  `src/model_evaluation.py`, la mayoría de `notebooks/*` (excepto el EDA #11 y
  `ejemplo_dataset_analitico.ipynb`), y la mayoría de `docs/*.md` fuera de
  `fuentes_datos.md`, `data_dictionary.md` y `data-dictionaries/`.
- **No existen aún en disco:** `api/`, `app/`, `mobile/`,
  `models/predictivo/`, `models/clustering/`. Los comandos de `README.md` para
  esas piezas (`uvicorn`, `streamlit run`, `expo start`) documentan el plan de
  arquitectura, no algo ejecutable hoy — verifica con `ls`/`Glob` antes de
  asumir que un archivo de esas carpetas existe.
- `tests/` está vacío (solo `.gitkeep`) pero `.github/workflows/ci.yml` corre
  `pytest tests/ -v`; cualquier trabajo en `src/`/`pipelines/` debería venir
  con sus pruebas en `tests/`.
- `CRONOGRAMA.md` se referencia desde README/BACKLOG pero no existe en el
  repo (ver nota de seguimiento en `ESTRUCTURA.md` §5).

### Comandos

```bash
# Entorno (una vez, desde la raíz). Alternativa Conda: environment.yml
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # Unix

# Ingesta de fuentes crudas (idempotente; usar --force para re-descargar).
# NUSE descarga ~112 MB.
python src/ingest_siedco.py
python src/ingest_nuse.py
python src/ingest_divipola.py
python src/ingest_datosgov.py
python src/ingest_dane.py

# Pipeline completo -> data/03_primary/{dataset_analitico.parquet, zonas_bogota.geojson}
python pipelines/pipeline_ml.py

# Lo que corre CI (.github/workflows/ci.yml)
python -m compileall src pipelines tests
pytest tests/ -v
```

No hay linter/formatter configurado (no hay `ruff`, `flake8` ni `black` en
`requirements.txt` ni en CI).

### Arquitectura del pipeline de datos (leer antes de tocar `src/`)

- `src/config.py` es la única fuente de verdad de rutas, URLs CKAN, CRS y la
  llave de cruce (`cod_localidad`, string de 2 dígitos con cero a la
  izquierda). No hardcodear rutas ni URLs en otro módulo.
- Los datos fluyen por capas numeradas — `data/01_raw` → `02_intermediate` →
  `03_primary` → `04_model_output` — ninguna versionada en git (solo
  `.gitkeep`); hay que regenerarlas corriendo el pipeline.
- El cruce entre fuentes es siempre **tabular** (no spatial join: NUSE no trae
  lat/lon por incidente) y siempre por `cod_localidad`, nunca por nombre de
  texto (los nombres de SIEDCO vienen con mojibake latin-1; el nombre
  canónico sale de la geometría en `ingest_divipola.py`).
- `src/pipeline_integration.py`: SIEDCO es la *spine* (1.760 filas = 20
  localidades × 8 años × 11 tipos de delito); NUSE y el contexto DANE se
  pegan con left join por (`cod_localidad`, `anio`). Una combinación
  localidad-año ausente en NUSE es un **cero estructural**, no un dato
  faltante.
- `pipelines/pipeline_ml.py` orquesta `data_cleaning.run()` →
  `pipeline_integration.run()` → `feature_engineering.add_target_riesgo_alto()`
  → split espacio-temporal (`train` = años ≤2024, `test` = 2025) → escribe y
  **verifica** (asserts) los dos entregables. `COLS_FINAL` en ese archivo es
  el contrato de columnas con Integrantes 2 y 3 — cambiarlo rompe aguas
  abajo.
- La variable objetivo `riesgo_alto` (percentil 75 de `conteo_siedco` por
  tipo de delito, umbral aprendido **solo** con `train`) ya viene calculada
  en `dataset_analitico.parquet`; no se recalcula en otros módulos (ver
  `src/feature_engineering.py`).
- `Sumapaz` (`cod_localidad` = `"20"`) tiene `ipm_nbi` nulo (sin Encuesta
  Multipropósito). Es una decisión abierta para quien consuma el dataset
  (imputar vs. excluir) — documentada en
  `docs/data-dictionaries/variable_objetivo.md` y `docs/HANDOFF_INT1.md`.
