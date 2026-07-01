# app — Dashboard analítico (Integrante 3)

**Estado:** pendiente (arranca Semana 2). **Streamlit** (un solo app Python; sin
backend ni frontend separados — la inferencia vive en `../api/`).

## Qué muestra

- **Mapa coroplético** por localidad, coloreado por nivel de riesgo del modelo.
- **Capa de densidad por UPZ** (NUSE) como señal complementaria.
- **Tipología de zonas** (clusters de perfil delictivo) que etiqueta el mapa.
- **Demo de reporte ciudadano** con **detección de anomalías por z-score**:
  compara la frecuencia reciente de la zona contra su línea base histórica y
  marca lo atípico. Este chequeo estadístico vive **aquí, en el cliente**, no es
  un modelo con ciclo de vida propio (por eso no hay carpeta en `../models/`).

Consume el mismo contrato `GET /zonas-riesgo` de `../api/`.

## Cómo correr (cuando exista)

```bash
streamlit run app.py
```
