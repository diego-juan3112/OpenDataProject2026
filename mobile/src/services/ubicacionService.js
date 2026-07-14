// ubicacionService.js
//
// Envuelve expo-location: pedir permiso y suscribirse a la posición en
// primer plano. UbicacionContext.jsx es el único consumidor — no importa
// React ni el reducer, para poder mockear expo-location sin renderizar nada.

import * as Location from 'expo-location';

// Coordenada fija provisional (Chapinero) para el "modo demo" de esta issue.
// La Issue #41 la reemplaza por la ruta simulada real, coordinada con
// Integrante 3 a partir del modelo/tipología de zonas.
export const COORDENADA_DEMO = { lat: 4.6492, lon: -74.0628, precision: null };

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
