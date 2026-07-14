# Changelog — Alerta Ciudadana

Qué se puede hacer o ver en cada versión. Más reciente arriba.

## 0.3.0 — 2026-07-14
- La app móvil corre en el teléfono con **Expo Go 54** y muestra el mapa de riesgo con datos de prueba (mock).
- La app pide ubicación (GPS) con aviso de privacidad opt-in y tiene modo demo.
- Los **datos procesados y los modelos entrenados ya vienen en el repo**: se clona y se corre sin descargar fuentes ni entrenar.

## 0.2.0 — 2026-07-13
- La **API** responde `GET /zonas-riesgo` con las 20 localidades: nivel de riesgo (modelo predictivo) y perfil (clustering).
- El **dashboard** (Streamlit) muestra el mapa de riesgo real, la densidad de llamadas NUSE y el reporte ciudadano con detección de anomalías (z-score).

## 0.1.0 — 2026-07-06
- **Pipeline de datos** completo: dataset analítico unificado (localidad × año × tipo de delito) + geometría de las 20 zonas de Bogotá, a partir de 5 fuentes abiertas oficiales (Issues #1–#12).
