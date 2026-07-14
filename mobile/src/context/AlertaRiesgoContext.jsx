// AlertaRiesgoContext.jsx
//
// Conecta la posición (UbicacionContext, #39) con la capa de geofencing (#21)
// y dispara la notificación local al entrar a una zona de riesgo alto (#40).
// Se monta UNA vez (en App.js), por encima de la navegación, para que la
// alerta funcione en cualquier tab mientras la app está en primer plano.

import { createContext, useContext, useEffect, useRef, useState } from 'react';

import { riesgoDeCoordenada } from '../geofencing';
import { fetchZonas } from '../services/zonasService';
import {
  configurarHandler,
  dispararAlertaZonaAlta,
  pedirPermisoNotificaciones,
} from '../services/notificacionesService';
import { evaluarTransicion } from '../logic/alertaRiesgo';
import { useUbicacion } from './UbicacionContext';

const AlertaRiesgoContext = createContext(null);

export function AlertaRiesgoProvider({ children }) {
  const { posicion } = useUbicacion();
  const [geojson, setGeojson] = useState(null);
  const [zonaActual, setZonaActual] = useState(null);
  const [permisoNotif, setPermisoNotif] = useState('sin-preguntar');
  const [historial, setHistorial] = useState([]); // [{ nombre, hora }]
  const nivelPrevioRef = useRef(null); // nivel de la lectura anterior (anti-rebote)

  // Setup único: handler de primer plano + permiso de notificaciones + zonas.
  useEffect(() => {
    configurarHandler();
    pedirPermisoNotificaciones().then(setPermisoNotif).catch(() => setPermisoNotif('denegado'));
    fetchZonas().then(setGeojson).catch(() => setGeojson(null));
  }, []);

  // Cada cambio de posición: resolver zona y disparar alerta en la transición a alto.
  useEffect(() => {
    if (!posicion || !geojson) return;
    const zona = riesgoDeCoordenada(posicion.lat, posicion.lon, geojson);
    setZonaActual(zona);

    const nivel = zona.nivel_riesgo ?? null;
    const { debeNotificar } = evaluarTransicion(nivelPrevioRef.current, nivel);
    if (debeNotificar) {
      dispararAlertaZonaAlta(zona).catch(() => {});
      setHistorial((prev) =>
        [{ nombre: zona.localidad_nombre ?? 'Zona de riesgo alto', hora: new Date() }, ...prev].slice(0, 20),
      );
    }
    nivelPrevioRef.current = nivel;
  }, [posicion, geojson]);

  const valor = {
    zonaActual,
    nivelActual: zonaActual?.nivel_riesgo ?? null,
    permisoNotif,
    historial,
    zonasCargadas: geojson != null,
  };

  return <AlertaRiesgoContext.Provider value={valor}>{children}</AlertaRiesgoContext.Provider>;
}

export function useAlertaRiesgo() {
  const contexto = useContext(AlertaRiesgoContext);
  if (!contexto) {
    throw new Error('useAlertaRiesgo debe usarse dentro de AlertaRiesgoProvider');
  }
  return contexto;
}
