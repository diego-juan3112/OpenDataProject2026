// notificacionesService.js
//
// Envuelve expo-notifications (Issue #40): configurar el handler de primer
// plano, pedir permiso y disparar la notificación local de "zona de riesgo
// alto". Aislado para poder mockear expo-notifications en tests y para que
// AlertaRiesgoContext sea el único consumidor.

import * as Notifications from 'expo-notifications';

// Muestra la notificación aunque la app esté en primer plano (Issue #40,
// criterio 3). En SDK 54 los campos son shouldShowBanner/shouldShowList;
// se incluye shouldShowAlert por compatibilidad con handlers previos.
export function configurarHandler() {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
      shouldShowAlert: true,
    }),
  });
}

// Pide el permiso de notificaciones (idempotente: no re-pregunta si ya está).
export async function pedirPermisoNotificaciones() {
  const actual = await Notifications.getPermissionsAsync();
  let status = actual.status;
  if (status !== 'granted') {
    const pedido = await Notifications.requestPermissionsAsync();
    status = pedido.status;
  }
  return status === 'granted' ? 'concedido' : 'denegado';
}

// Dispara la notificación local inmediata al entrar a una zona de riesgo alto.
export async function dispararAlertaZonaAlta(zona) {
  const nombre = zona?.localidad_nombre ?? 'una zona de riesgo alto';
  return Notifications.scheduleNotificationAsync({
    content: {
      title: '⚠️ Zona de riesgo ALTO',
      body: `Estás entrando a ${nombre}. Mantente alerta y evita exhibir objetos de valor.`,
      sound: true,
    },
    trigger: null, // inmediata
  });
}
