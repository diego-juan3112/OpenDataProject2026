# Alerta Ciudadana 🚨

Sistema predictivo de seguridad ciudadana para **Bogotá**, construido con datos
abiertos oficiales de Colombia bajo la metodología **CRISP-ML(Q)**. Reto
**"Seguridad Ciudadana y Justicia"** — Universidad de Caldas.

> **Documento maestro del proyecto:** [`CLAUDE.md`](./CLAUDE.md) (qué es, fuentes,
> arquitectura, metodología y restricciones). Léelo antes de empezar.

---

## ¿Qué es?

Alerta Ciudadana convierte el histórico oficial de criminalidad en una **alerta
geolocalizada accionable**. Tiene **dos clientes** que consumen **el mismo modelo
y los mismos datos** a través de una **API ligera de un solo endpoint**
(`GET /zonas-riesgo`):

1. **Dashboard analítico (Streamlit).** Mapa de riesgo por zona, tipología de
   zonas por perfil delictivo y demo de reporte ciudadano con detección de
   anomalías por z-score.
2. **App móvil nativa (Expo / React Native).** Lee el GPS en tiempo real y dispara
   una **notificación local** cuando el usuario entra a una zona de riesgo alto.
   Es la pieza central de la propuesta: la alerta en el momento.

No hay base de datos persistente: el reporte ciudadano vive en sesión. La API es la
única autoridad de inferencia; ambos clientes son consumidores delgados.

### El mapa es una composición de capas

El dato abierto de SIEDCO es de **tipo polígono por localidad** (EPSG:4686), no
coordenada-punto del hecho. Por la naturaleza del dato, el mapa se compone en capas:

| Capa | Fuente | Representación |
|---|---|---|
| **Coroplético** (fondo estadístico oficial) | SIEDCO | Polígonos por localidad coloreados por riesgo |
| **Densidad por UPZ** (señal operativa complementaria) | NUSE / Línea 123 | Agregado por UPZ × mes × tipo (el dato abierto no trae lat/lon por incidente) |
| **Reportes ciudadanos** | App (simulado, en sesión) | Puntos individuales sobre las capas anteriores |

### Alcance

| Decisión | Detalle |
|---|---|
| **Geografía** | Bogotá (única ciudad con datos NUSE/C4 Línea 123) |
| **Clientes** | Dashboard Streamlit + app móvil Expo, ambos sobre `GET /zonas-riesgo` |
| **Estado del reporte** | Simulado en sesión (sin BD persistente) |
| **IA obligatoria** | Predictivo (RF/Gradient Boosting) + clustering de zonas (K-Means) + flag z-score |
| **IA nice-to-have** | NLP de reportes / resumen GenAI (no bloqueantes) |

---

## Stack técnico

| Capa | Tecnología | Por qué |
|---|---|---|
| Pipeline de datos | Python · pandas · **GeoPandas** · pyarrow | Cruce SIEDCO ↔ DIVIPOLA por **código DANE** (no por nombre) |
| Modelado | scikit-learn · XGBoost · joblib | RF/Gradient Boosting (predictivo) + K-Means (tipología de zonas) |
| API | **FastAPI** + uvicorn | Un endpoint `GET /zonas-riesgo` → GeoJSON con riesgo + cluster, carga `.joblib` en memoria |
| Dashboard | **Streamlit** + **Folium** (`streamlit-folium`) | Mapa coroplético + puntos + reporte simulado, un solo comando |
| App móvil | **Expo (React Native)** · `expo-location` · `expo-notifications` | GPS en tiempo real + notificación local; APK con `eas build` |

---

## Estructura del repositorio

```
OpenDataProject2026/
├── CLAUDE.md                 # Documento maestro
├── README.md                 # Este archivo
├── BACKLOG.md                # Issues por integrante
├── CRONOGRAMA.md             # Semanas, dependencias y sincronizaciones
├── DEFINITION_OF_DONE.md     # DoD a nivel proyecto
├── requirements.txt          # Dependencias Python (environment.yml para Conda)
├── docs/                     # Planteamiento, metodología, fuentes, diccionarios, validación
├── data/                     # 01_raw / 02_intermediate (gitignored) · 03_primary (versionado)
├── src/                      # Integrante 1 — pipeline: config, ingestas, limpieza, cruce
├── pipelines/                # Integrante 1 — pipeline_ml.py (orquestador extremo a extremo)
├── notebooks/                # EDA y experimentación
├── tests/                    # Calidad de datos e inferencia
├── reports/                  # Figuras y reporte final
├── RECURSOS/                 # Presentación y material visual
├── models/
│   ├── predictivo/           # Integrante 2 — RF/Gradient Boosting
│   └── clustering/           # Integrante 3 — K-Means (tipología de zonas)
├── api/                      # Integrante 2 — FastAPI: GET /zonas-riesgo
├── app/                      # Integrante 3 — dashboard Streamlit
└── mobile/                   # Integrante 4 — app Expo / React Native
```

---

## Cómo correr el proyecto (empezar desde cero)

> **El repo ya incluye los datos procesados y los modelos entrenados** (~3 MB,
> versionados). No necesitas descargar las fuentes crudas ni entrenar nada:
> clona, instala dependencias y arranca. Ver [Gestión de datos](#gestión-de-datos).

### Requisitos

| Herramienta | Versión | Para qué |
|---|---|---|
| **Python** | 3.11+ (probado en 3.13) | Pipeline, API, dashboard |
| **Node.js** | >= 18 (probado en v24) | App móvil |
| **Expo Go** | **54** (Play Store, Android) | Correr la app en tu teléfono |

### 0) Entorno Python (una vez, desde la raíz del repo)

```bash
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 1) API ligera (Integrante 2)

Carga los modelos (ya incluidos en el repo) y expone el endpoint del sistema.

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
# GET http://localhost:8000/zonas-riesgo   → GeoJSON (riesgo + cluster por zona)
# Swagger interactivo: http://localhost:8000/docs
```

> `--host 0.0.0.0` permite que el teléfono físico alcance la API por la **IP de
> LAN** del portátil (misma Wi-Fi).

### 2) Dashboard Streamlit (Integrante 3)

```bash
pip install -r app/requirements.txt
streamlit run app/streamlit_app.py
# Dashboard en http://localhost:8501  (consume la API del puerto 8000)
```

### 3) App móvil en un teléfono real (Integrante 4)

```bash
cd mobile
npm install
npx expo start                      # si el teléfono no ve el QR: npx expo start --tunnel
```

1. Escanea el QR con **Expo Go 54** desde un **Android** en la misma Wi-Fi.
2. Apunta la app a la API: edita `mobile/src/config.js` → `API_BASE_URL` con la
   **IP de LAN** del portátil (p. ej. `http://192.168.x.x:8000`; obtén la IP con
   `ipconfig`). Por defecto el mapa usa datos de prueba (mock) y no necesita la API.
3. Concede el permiso de ubicación (aviso de privacidad opt-in) y usa el **modo
   demo** para simular la ubicación en la presentación.

Para un APK instalable: `eas build -p android --profile preview`.

### (Opcional) Regenerar datos y modelos desde cero

Solo si quieres reconstruirlos (descarga las fuentes abiertas, ~112 MB de NUSE):

```bash
python pipelines/pipeline_ml.py     # regenera el dataset analítico + GeoJSON de zonas
python models/predictivo/train.py   # re-entrena el modelo predictivo
# Los scripts de cada modelo viven en models/ (ver models/predictivo/ y models/clustering/).
```

---

## Gestión de datos

El proyecto separa lo **pesado/crudo** (no se versiona) de los **artefactos
derivados pequeños** (sí se versionan), para que cualquiera pueda clonar y correr
sin descargar fuentes ni re-entrenar:

| Qué | Dónde | ¿En git? |
|---|---|---|
| Fuentes crudas y limpias (incluye NUSE ~112 MB) | `data/01_raw`, `data/02_intermediate` | ❌ ignorado (se descarga/regenera) |
| **Dataset analítico + geometría de zonas** | `data/03_primary/{dataset_analitico.parquet, zonas_bogota.geojson}` | ✅ versionado (~2.5 MB) |
| **Modelos entrenados** | `models/predictivo/model.joblib`, `models/clustering/*.joblib`/`*.parquet` | ✅ versionado (<1 MB) |
| Fixtures del dashboard | `app/data/*` | ✅ versionado |

Las excepciones que "des-ignoran" esos archivos están al final de `.gitignore`.
Al clonar el repo ya vienen incluidos → la API, el dashboard y el mock del móvil
funcionan de inmediato. Solo hace falta regenerarlos si cambian las fuentes o el
modelado (ver *(Opcional) Regenerar…* arriba).

---

## Equipo y pistas de trabajo

| # | Pista | Responsabilidad principal |
|---|---|---|
| 1 | **Datos** | Ingesta, limpieza, cruce por DANE, dataset unificado + GeoJSON de zonas |
| 2 | **Predictivo + API** | Modelo de riesgo (RF/GB) + API `/zonas-riesgo` + capa de datos del móvil |
| 3 | **Clustering + Dashboard** | Tipología de zonas (K-Means) + ética/sesgo + dashboard Streamlit |
| 4 | **App móvil** | Cliente Expo: GPS + notificación local + modo demo + build en dispositivo físico |

La **Fase 4 (QA)** es cruzada: cada quien reporta sus métricas y un compañero deja
un comentario de validación (nadie evalúa su propio modelo). Ver
[`BACKLOG.md`](./BACKLOG.md) y [`CRONOGRAMA.md`](./CRONOGRAMA.md).
