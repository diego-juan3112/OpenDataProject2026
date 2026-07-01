# api — API ligera de inferencia (Integrante 2)

**Estado:** pendiente (arranca Semana 2, tras el dataset analítico de #9).

FastAPI mínimo, **un solo endpoint**, sin base de datos. Carga `model.joblib`
(predictivo) y `clusters.joblib` (clustering) en memoria y sirve el contrato de
datos que consumen **el dashboard y la app móvil por igual**.

## Contrato: `GET /zonas-riesgo`

Devuelve un **GeoJSON** de las 20 localidades de Bogotá; cada feature con:

- `geometry` (polígono, EPSG:4326)
- `cod_localidad`, `localidad_nombre`, `cod_dane_mpio`
- `riesgo` / `probabilidad` (modelo predictivo)
- `cluster` + `perfil` (clustering)
- metadatos de la consulta (tipo de delito, año)

El contrato **no cambia** según el cliente.

## Alcanzabilidad desde el dispositivo físico

El teléfono no alcanza `localhost`: se consume por **IP de LAN** (misma Wi-Fi) o
por **túnel** (ngrok / túnel de Expo). Se documenta y prueba como parte del
entregable.
