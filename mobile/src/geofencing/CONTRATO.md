# Contrato geofencing — Issue #21

**Entrega:** Integrante 2 · **Consume:** Integrante 4 (app Expo, issues #39–#40)

## Qué es

Capa de datos del móvil: pide `GET /zonas-riesgo`, cachea el GeoJSON y resuelve
**en qué localidad está el usuario** + su nivel de riesgo.

## API pública

```js
import { ZonasCache, riesgoDeCoordenada } from "./geofencing";

const cache = new ZonasCache({
  baseUrl: "http://192.168.x.x:8000", // IP LAN del portátil con la API
  anio: 2025,
  tipo: "HP",
  ttlMs: 5 * 60 * 1000, // refresco cada 5 min
});

await cache.refresh(); // o { force: true }

// Coordenadas de expo-location (lat, lon)
const r = riesgoDeCoordenada(4.6533, -74.0836, cache.geojson);
// {
//   cod_localidad: "01",
//   localidad_nombre: "USAQUEN",
//   nivel_riesgo: "bajo" | "medio" | "alto" | null,
//   probabilidad_riesgo: 0.43,
//   cluster: 0,
//   nombre_perfil: "...",
//   fueraDeBogota: false
// }
```

## Comportamiento acordado

| Caso | Resultado |
|---|---|
| Punto dentro de una localidad | `fueraDeBogota: false` + campos de zona |
| Punto fuera de Bogotá / mar / otro depto | `fueraDeBogota: true`, resto `null` — **no lanza** |
| API caída en el primer `refresh` | `geojson === null`, `lastError` con mensaje |
| API caída con cache previo | Devuelve **último GeoJSON conocido** |
| `lat`/`lon` inválidos | Equivalente a fuera de Bogotá |

## Uso sugerido para notificaciones (#40)

```js
const r = riesgoDeCoordenada(lat, lon, cache.geojson);
if (!r.fueraDeBogota && r.nivel_riesgo === "alto") {
  // disparar notificación local (anti-rebote: solo en transición)
}
```

## Archivos

| Archivo | Rol |
|---|---|
| `riesgoDeCoordenada.js` | point-in-polygon + lectura de properties |
| `zonasCache.js` | fetch + TTL + fallback offline |
| `index.js` | re-exports |

Referencia Python de verificación: `tests/test_geofencing.py` (misma lógica con Shapely).
