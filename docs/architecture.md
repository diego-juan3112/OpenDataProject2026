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

## Framework móvil — Expo (React Native) (Issue #37)

**Framework elegido: Expo (React Native)**, JavaScript (template `blank`).

**Justificación:**
- Camino más corto de "cero a APK instalable" sin experiencia previa en mobile:
  **Expo Go** permite probar en un dispositivo físico real escaneando un QR, sin
  compilar nativo en cada cambio.
- La API ya está en FastAPI (JSON) — React Native consume JSON nativo sin adaptadores.
- `expo-location` y `expo-notifications` son los paquetes estándar para GPS y
  notificaciones locales, con buena documentación y compatibles con Expo Go en
  desarrollo (issues #39, #40).
- Si en el checkpoint de contingencia (PWA) se decide cambiar de cliente, la lógica
  de negocio en JavaScript es reutilizable. El endpoint `/ruta-segura` no cambia.

**Proyecto:** `mobile/` (Expo SDK). Convive con el módulo de geofencing entregado
por Integrante 2 en `mobile/src/geofencing/` (Issue #21), que el cliente enchufa a
`expo-location`. Cómo correr y apuntar a la API: `mobile/README.md`.
