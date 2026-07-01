# mobile — App móvil (Integrante 4)

**Estado:** pendiente (arranca Semana 2). **Expo / React Native**, objetivo
**Android**. Es la pieza central de la propuesta de valor: lleva el análisis al
bolsillo del ciudadano como una alerta geolocalizada.

## Flujo

1. Lee la ubicación del dispositivo en tiempo real (`expo-location`).
2. Consulta periódicamente `GET /zonas-riesgo` de `../api/`.
3. Dispara una **notificación local** (`expo-notifications`) al entrar a una zona
   de riesgo alto.
4. **Modo demo**: ubicación simulada para disparar la alerta de forma confiable
   en la presentación.

Alcance realista: notificación **local y en primer plano** + modo demo. Geofencing
en segundo plano y push vía servidor (FCM/APNs) quedan como trabajo futuro.

## Plan de contingencia (Plan B)

Si al final de la Semana 2 la app nativa no tiene GPS + notificación funcionando
en un dispositivo físico, se reemplaza por una **PWA instalable** (GPS +
Notification API del navegador). El endpoint `/zonas-riesgo` **no cambia**.

## Cómo correr (cuando exista)

```bash
npm install
npx expo start          # abrir en Expo Go sobre un dispositivo físico
# build instalable:  eas build -p android
```
