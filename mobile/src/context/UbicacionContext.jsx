// UbicacionContext.jsx
//
// Conecta ubicacionReducer (estado puro) con ubicacionService (efectos
// reales sobre expo-location) y lo expone a PerfilScreen y MapaScreen via
// useUbicacion(). Todo el estado vive en memoria (useReducer): se resetea
// al cerrar la app, no hay AsyncStorage (issue #39, decisión de diseño).

import { createContext, useCallback, useContext, useEffect, useReducer, useRef } from 'react';

import { ESTADO_INICIAL, ubicacionReducer } from './ubicacionReducer';
import { COORDENADA_DEMO, pedirPermiso, suscribirPosicion } from '../services/ubicacionService';

const UbicacionContext = createContext(null);

export function UbicacionProvider({ children }) {
  const [estado, dispatch] = useReducer(ubicacionReducer, ESTADO_INICIAL);
  const suscripcionRef = useRef(null);

  const detenerSuscripcion = useCallback(() => {
    if (suscripcionRef.current) {
      suscripcionRef.current.remove();
      suscripcionRef.current = null;
    }
  }, []);

  const aceptarConsentimiento = useCallback(async () => {
    dispatch({ type: 'ACEPTAR_CONSENTIMIENTO' });
    const resultado = await pedirPermiso();
    if (resultado === 'concedido') {
      dispatch({ type: 'PERMISO_CONCEDIDO' });
      const suscripcion = await suscribirPosicion(
        (posicion) => dispatch({ type: 'POSICION_ACTUALIZADA', payload: posicion }),
        (mensaje) => dispatch({ type: 'ERROR_GPS', payload: mensaje }),
      );
      suscripcionRef.current = suscripcion;
    } else {
      dispatch({ type: 'PERMISO_DENEGADO' });
    }
  }, []);

  const rechazarConsentimiento = useCallback(() => {
    dispatch({ type: 'RECHAZAR_CONSENTIMIENTO' });
  }, []);

  const activarModoDemo = useCallback(() => {
    detenerSuscripcion();
    dispatch({ type: 'ACTIVAR_MODO_DEMO', payload: COORDENADA_DEMO });
  }, [detenerSuscripcion]);

  const desactivarModoDemo = useCallback(() => {
    dispatch({ type: 'DESACTIVAR_MODO_DEMO' });
  }, []);

  // Cancela la suscripción de GPS al desmontar el provider (cierre de la app).
  useEffect(() => detenerSuscripcion, [detenerSuscripcion]);

  const valor = {
    ...estado,
    aceptarConsentimiento,
    rechazarConsentimiento,
    activarModoDemo,
    desactivarModoDemo,
  };

  return <UbicacionContext.Provider value={valor}>{children}</UbicacionContext.Provider>;
}

export function useUbicacion() {
  const contexto = useContext(UbicacionContext);
  if (!contexto) {
    throw new Error('useUbicacion debe usarse dentro de UbicacionProvider');
  }
  return contexto;
}
