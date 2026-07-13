# Arquitectura — Alerta Ciudadana
<!-- Diagrama de integración de fuentes y flujo de datos -->
<!-- Completar con el diagrama de CLAUDE.md §4 -->

## OpenRouteService (ORS) — Motor de routing

**Rol:** cálculo de rutas navegables entre dos puntos de Bogotá.
La API de ORS devuelve hasta N rutas alternativas con su geometría
(polyline codificada) y resumen (distancia, duración).

**Plan:** gratuito (sin tarjeta de crédito requerida)
**Endpoint usado:** `POST https://api.openrouteservice.org/v2/directions/driving-car/json`

**Límites del plan gratuito (verificados 2026-07-06):**
| Límite | Valor |
|---|---|
| Requests por día | 2.000 |
| Requests por minuto | 40 |
| Rutas alternativas por request | Hasta 3 |
| `avoid_polygons` área máx. por polígono | 200 km² |
| Distancia máx. con avoid areas | 150 km |

> Los cupos por día/minuto son los publicados por ORS para el endpoint de
> *directions* del plan gratuito; los límites de `avoid_polygons` y distancia
> están verificados en `diseño_tecnico_ruta_segura.md` §PARTE 2. Las localidades
> de Bogotá promedian ~30 km² (bajo el tope de 200 km²) y la ciudad mide ~33 km
> norte-sur (bajo el tope de 150 km), así que ambos usos caben en el plan gratuito.

**Cómo se integra:**
1. El endpoint `/ruta-segura` del backend llama a ORS con origen/destino.
2. ORS devuelve 2 rutas con geometría en polyline codificada.
3. El backend decodifica la geometría, hace spatial join con las
   localidades de Bogotá, y calcula el score de riesgo de cada ruta.
4. El resultado (rutas + scores) se devuelve al cliente móvil.

**Cliente en el repo:** `src/routing_client.py` (`get_routes`, `decodificar_ruta`).
**Credencial:** `ORS_API_KEY` en `.env` (nunca en el repositorio); se lee vía
`config.ORS_API_KEY`. Conectividad verificada 2026-07-06 (Chapinero → La
Candelaria: 2 rutas, 5.8 km / 11.2 min y 5.2 km / 12.0 min).
