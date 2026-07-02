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
├── data/                     # 01_raw / 02_intermediate / 03_primary / 04_model_output (gitignored)
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

## Cómo correr el proyecto

> Los comandos se completan a medida que cada pista entrega su parte. El orden de
> arranque para una demo completa es: **pipeline → modelos → API → (dashboard | app)**.

### 0) Entorno Python

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 1) Pipeline de datos (Integrante 1)

Genera `data/03_primary/dataset_analitico.parquet` y `data/03_primary/zonas_bogota.geojson`.

```bash
python pipelines/pipeline_ml.py
```

### 2) Entrenar modelos (Integrantes 2 y 3)

Genera `models/predictivo/model.joblib` y `models/clustering/clusters.joblib`.

```bash
python models/predictivo/train.py
python models/clustering/train.py
```

### 3) Levantar la API ligera (Integrante 2)

Carga los modelos en memoria y expone el único endpoint del sistema.

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
# Contrato:  GET http://localhost:8000/zonas-riesgo  → GeoJSON (riesgo + cluster por zona)
```

> `--host 0.0.0.0` permite que el dispositivo móvil físico alcance la API por la
> IP de LAN del portátil (misma Wi-Fi).

### 4a) Dashboard (Integrante 3)

```bash
streamlit run app/streamlit_app.py
# Dashboard en http://localhost:8501  (consume la API en el puerto 8000)
```

### 4b) App móvil en dispositivo físico real (Integrante 4)

```bash
cd mobile
npm install
npx expo start
```

1. Escanea el QR con **Expo Go** desde un teléfono **Android** en la misma Wi-Fi.
2. Configura la URL de la API con la **IP de LAN** del portátil (p. ej.
   `http://192.168.x.x:8000`) o un **túnel** (`npx expo start --tunnel` / ngrok).
3. Concede el permiso de ubicación (aviso de privacidad opt-in) y activa el
   **modo demo** para disparar la alerta con una ubicación simulada en la
   presentación.

Para un APK instalable: `eas build -p android --profile preview`.

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
