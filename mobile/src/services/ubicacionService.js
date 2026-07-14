// ubicacionService.js
//
// Envuelve expo-location: pedir permiso y suscribirse a la posición en
// primer plano. UbicacionContext.jsx es el único consumidor — no importa
// React ni el reducer, para poder mockear expo-location sin renderizar nada.

import * as Location from 'expo-location';

// Ruta simulada del "modo demo" (Issue #41): recorre de una zona segura a una
// de riesgo alto para disparar la alerta de forma reproducible en la
// presentación, sin depender de moverse físicamente. Los puntos se eligen a
// partir del modelo/tipología (Int. 3): Kennedy es la localidad de mayor score.
//   Usaquén (bajo) → Chapinero (medio) → Kennedy (ALTO → dispara la alerta).
// UbicacionContext reproduce estos puntos uno por uno; al cruzar a "alto",
// AlertaRiesgoContext dispara la notificación local (#40).
export const RUTA_DEMO = [
  { lat: 4.70, lon: -74.03, precision: null }, // Usaquén — bajo (inicio seguro)
  { lat: 4.66, lon: -74.05, precision: null }, // en tránsito
  { lat: 4.65, lon: -74.06, precision: null }, // Chapinero — medio
  { lat: 4.64, lon: -74.10, precision: null }, // en tránsito
  { lat: 4.63, lon: -74.15, precision: null }, // Kennedy — ALTO → alerta
];

// Primer punto de la ruta (compatibilidad con quien importe la coord. inicial).
export const COORDENADA_DEMO = RUTA_DEMO[0];

export async function pedirPermiso() {
  const { status } = await Location.requestForegroundPermissionsAsync();
  return status === 'granted' ? 'concedido' : 'denegado';
}

// Muestreo periódico en primer plano (issue #39, criterio 2): cada 5s o cada
// 15m de desplazamiento, lo que ocurra primero.
export async function suscribirPosicion(onUpdate, onError) {
  try {
    return await Location.watchPositionAsync(
      { accuracy: Location.Accuracy.Balanced, timeInterval: 5000, distanceInterval: 15 },
      (loc) => {
        onUpdate({
          lat: loc.coords.latitude,
          lon: loc.coords.longitude,
          precision: loc.coords.accuracy ?? null,
        });
      },
    );
  } catch (err) {
    onError(err instanceof Error ? err.message : String(err));
    return null;
  }
}
