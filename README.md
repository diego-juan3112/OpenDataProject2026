# Alerta Ciudadana 🚨

Sistema predictivo de seguridad ciudadana para Colombia, construido con datos
abiertos oficiales bajo la metodología **CRISP-ML(Q)**. Reto **"Seguridad
Ciudadana y Justicia"** — Universidad de Caldas.

> **Contexto completo del proyecto:** ver [`CLAUDE.md`](./CLAUDE.md) (problema de
> negocio, fuentes de datos, metodología, criterios de evaluación). **Léelo antes
> de empezar.**

---

## ¿Qué es?

Una app web que combina:

1. **Mapa de riesgo predictivo** — modelo ML que estima la probabilidad de
   incidentes por zona, franja horaria y tipo de delito, entrenado sobre
   históricos oficiales (SIEDCO / Policía Nacional).
2. **Canal de reporte ciudadano** — formulario in-app donde los usuarios reportan
   incidentes (tipo, ubicación en mapa, hora, descripción) que se cruzan contra
   el histórico para detectar anomalías.
3. **Detección de anomalías** — identifica picos atípicos en reportes/series
   respecto a lo esperado para una zona–franja horaria.

### Alcance comprometido (PoC)

| Decisión | Compromiso para la entrega |
|---|---|
| **Geografía** | **Bogotá** (única ciudad con datos NUSE/C4 línea 123 — el componente más cercano a "tiempo real") |
| **Reporte ciudadano** | Form-based MVP (sin push del SO ni feed en vivo) |
| **IA obligatoria** | Modelo predictivo de riesgo + detección de anomalías |
| **IA nice-to-have** | NLP de reportes / resumen GenAI (NO bloqueantes) |

---

## Stack técnico

| Capa | Tecnología | Por qué |
|---|---|---|
| Pipeline de datos | Python · pandas · **GeoPandas** | Cruce SIEDCO ↔ DIVIPOLA por **código DANE** (no por nombre) |
| Modelado | scikit-learn · XGBoost · joblib | Random Forest/XGBoost (predictivo) + Isolation Forest/z-score (anomalías) |
| Backend/API | **FastAPI** + SQLite (dev) / PostgreSQL (prod) | Rápido de desarrollar, buena integración con modelos `joblib` |
| Frontend | **Leaflet.js** + Jinja/estático | Mapa de calor interactivo + formulario de reporte sin SPA pesada |

---

## Estructura del repositorio

```
OpenDataProject2026/
├── CLAUDE.md                 # Contexto del proyecto (Fase 1)
├── README.md                 # Este archivo
├── BACKLOG.md                # Issues por integrante
├── CRONOGRAMA.md             # Semanas, dependencias y puntos de sincronización
├── DEFINITION_OF_DONE.md     # DoD a nivel proyecto
├── docs/                     # BU/DU, diccionarios de datos, arquitectura
├── data/                     # raw / interim / processed (gitignored)
├── data-engineering/         # Integrante 1 — pipeline + EDA
├── models/
│   ├── predictivo/           # Integrante 2
│   └── anomalias/            # Integrante 3
└── app/
    ├── backend/              # Integrante 4 — FastAPI
    └── frontend/             # Integrante 4 — Leaflet
```

---

## Cómo correr el proyecto (referencia futura)

> Estos comandos se irán completando a medida que cada pista entregue su parte.

```bash
# 1) Entorno
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2) Pipeline de datos (Integrante 1) — genera data/processed/dataset_analitico.parquet
python data-engineering/build_dataset.py

# 3) Entrenar modelos (Integrantes 2 y 3) — genera models/**/*.joblib
python models/predictivo/train.py
python models/anomalias/train.py

# 4) Levantar la app (Integrante 4)
uvicorn app.backend.main:app --reload
# Frontend disponible en http://localhost:8000
```

---

## Equipo y pistas de trabajo

| # | Pista | Responsabilidad principal |
|---|---|---|
| 1 | **Datos** | Fase 2 — ingesta, limpieza, cruce de fuentes, dataset unificado |
| 2 | **Predictivo** | Fase 3a — modelo de riesgo zona–tiempo–delito |
| 3 | **Anomalías / NLP** | Fase 3b — detección de anomalías (+ NLP nice-to-have) |
| 4 | **Despliegue** | Fase 5 — backend/API + frontend con mapa interactivo |

La **Fase 4 (QA)** es cruzada: los integrantes 2 y 3 evalúan el modelo del otro.
Ver [`BACKLOG.md`](./BACKLOG.md) para el detalle de issues y
[`CRONOGRAMA.md`](./CRONOGRAMA.md) para el plan semanal.
