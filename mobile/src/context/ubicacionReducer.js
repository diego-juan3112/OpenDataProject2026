// ubicacionReducer.js
//
// Reducer puro (sin I/O, sin expo-location) para el estado de ubicación de
// la app: consentimiento de privacidad (#39), permiso del SO, última
// posición conocida y modo demo. UbicacionContext.jsx lo conecta a
// useReducer y a los efectos reales (ver ubicacionService.js).

export const ESTADO_INICIAL = {
  consentimiento: 'sin-decidir', // 'sin-decidir' | 'aceptado' | 'rechazado'
  permiso: 'sin-preguntar', // 'sin-preguntar' | 'concedido' | 'denegado'
  posicion: null, // { lat: number, lon: number, precision: number|null } | null
  modoDemo: false,
  error: null, // string | null
};

export function ubicacionReducer(estado, accion) {
  switch (accion.type) {
    case 'ACEPTAR_CONSENTIMIENTO':
      return { ...estado, consentimiento: 'aceptado' };

    case 'RECHAZAR_CONSENTIMIENTO':
      return { ...estado, consentimiento: 'rechazado', permiso: 'denegado' };

    case 'PERMISO_CONCEDIDO':
      return { ...estado, permiso: 'concedido', error: null };

    case 'PERMISO_DENEGADO':
      return {
        ...estado,
        permiso: 'denegado',
        error: 'No se concedió el permiso de ubicación.',
      };

    case 'POSICION_ACTUALIZADA':
      return { ...estado, posicion: accion.payload, error: null };

    case 'ERROR_GPS':
      return {
        ...estado,
        error: accion.payload,
        posicion: estado.modoDemo ? estado.posicion : null,
      };

    case 'ACTIVAR_MODO_DEMO':
      return { ...estado, modoDemo: true, posicion: accion.payload, error: null };

    case 'DESACTIVAR_MODO_DEMO':
      return { ...estado, modoDemo: false, posicion: null };

    default:
      return estado;
  }
}
