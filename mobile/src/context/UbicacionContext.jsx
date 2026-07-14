// UbicacionContext.jsx
//
// Conecta ubicacionReducer (estado puro) con ubicacionService (efectos
// reales sobre expo-location) y lo expone a PerfilScreen y MapaScreen via
// useUbicacion(). Todo el estado vive en memoria (useReducer): se resetea
// al cerrar la app, no hay AsyncStorage (issue #39, decisión de diseño).

import { createContext, useCallback, useContext, useEffect, useReducer, useRef } from 'react';

import { ESTADO_INICIAL, ubicacionReducer } from './ubicacionReducer';
import { RUTA_DEMO, pedirPermiso, suscribirPosicion } from '../services/ubicacionService';

const UbicacionContext = createContext(null);

// Intervalo entre puntos de la ruta demo (ms).
const PASO_DEMO_MS = 2500;

export function UbicacionProvider({ children }) {
  const [estado, dispatch] = useReducer(ubicacionReducer, ESTADO_INICIAL);
  const suscripcionRef = useRef(null);
  const demoTimerRef = useRef(null);

  const detenerSuscripcion = useCallback(() => {
    if (suscripcionRef.current) {
      suscripcionRef.current.remove();
      suscripcionRef.current = null;
    }
  }, []);

  const detenerDemo = useCallback(() => {
    if (demoTimerRef.current) {
      clearInterval(demoTimerRef.current);
      demoTimerRef.current = null;
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
    detenerDemo();
    // Reproduce la ruta simulada (#41): un punto cada PASO_DEMO_MS, de zona
    // segura a zona alta. Cada ACTIVAR_MODO_DEMO mantiene modoDemo=true y
    // actualiza la posición → AlertaRiesgoContext dispara la alerta al cruzar.
    let i = 0;
    dispatch({ type: 'ACTIVAR_MODO_DEMO', payload: RUTA_DEMO[0] });
    demoTimerRef.current = setInterval(() => {
      i += 1;
      if (i >= RUTA_DEMO.length) {
        detenerDemo(); // se queda en la última coordenada (zona alta)
        return;
      }
      dispatch({ type: 'ACTIVAR_MODO_DEMO', payload: RUTA_DEMO[i] });
    }, PASO_DEMO_MS);
  }, [detenerSuscripcion, detenerDemo]);

  const desactivarModoDemo = useCallback(async () => {
    detenerDemo();
    dispatch({ type: 'DESACTIVAR_MODO_DEMO' });
    // Si el permiso ya estaba concedido, retoma el GPS real en vez de dejar
    // al usuario sin posición hasta reabrir la app.
    if (estado.permiso === 'concedido') {
      const suscripcion = await suscribirPosicion(
        (posicion) => dispatch({ type: 'POSICION_ACTUALIZADA', payload: posicion }),
        (mensaje) => dispatch({ type: 'ERROR_GPS', payload: mensaje }),
      );
      suscripcionRef.current = suscripcion;
    }
  }, [estado.permiso]);

  // Cancela la suscripción de GPS y el timer de la demo al desmontar el provider.
  useEffect(() => {
    return () => {
      detenerSuscripcion();
      detenerDemo();
    };
  }, [detenerSuscripcion, detenerDemo]);

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
