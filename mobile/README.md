# mobile/ — App Alerta Ciudadana (Expo / React Native)

**Integrante 4** · Issues #37–#44, #49–#51 · Expo SDK (JavaScript, template `blank`)

App móvil que consume la API de Alerta Ciudadana: mapa de riesgo por localidad,
comparativa de rutas (Ruta Más Segura), alerta local al entrar a zona de riesgo
alto y modo demo. Cliente delgado del contrato `/zonas-riesgo` y `/api/v1/ruta-segura`.

## Prerrequisitos
- Node.js >= 18 (verificado con v24)
- Expo Go instalado en el teléfono Android (Play Store)
- La API backend corriendo (ver `README.md` de la raíz)

## Cómo correr en desarrollo

```bash
cd mobile
npm install
npx expo start          # escanear el QR con Expo Go
# Si hay problemas de red (el teléfono no ve el QR / la LAN):
npx expo start --tunnel
```

El teléfono debe estar en la **misma red Wi-Fi** que el computador.

## Cómo apuntar a la API

Editar `src/config.js` → `API_BASE_URL`:
- **IP de LAN** (misma Wi-Fi): `http://192.168.x.x:8000`
  Obtener la IP del backend con `ipconfig` (Windows) o `ifconfig` (Mac/Linux).
  Es dinámica: cambia si cambia la red — actualízala aquí cuando toque.
- **Túnel ngrok** (útil para la demo, URL estable): `https://xxxx.ngrok.io`
  Ejecutar `ngrok http 8000` en el computador del backend.

## Estructura

```
mobile/
├── App.js                     # punto de entrada (NavigationContainer)
├── app.json                   # config Expo (dark mode, íconos, package Android)
├── index.js                   # registerRootComponent
├── assets/                    # íconos y splash
└── src/
    ├── config.js              # API_BASE_URL + paleta COLORES
    ├── navigation/
    │   └── AppNavigator.jsx   # 4 tabs: Mapa · Rutas · Alertas · Perfil
    ├── screens/               # una pantalla por tab (placeholders → #38–#42, #49–#51)
    ├── components/            # componentes reutilizables (Placeholder)
    └── geofencing/            # capa de datos de Int. 2 (Issue #21) — ver abajo
```

## Módulo de geofencing (Issue #21 — entregado por Integrante 2)

`src/geofencing/` es la capa de datos que pide `GET /zonas-riesgo`, cachea el
GeoJSON y resuelve en qué localidad está el usuario + su nivel de riesgo. La app
(issues #39–#40) lo enchufa a `expo-location`. Contrato y API pública en
[`src/geofencing/CONTRATO.md`](src/geofencing/CONTRATO.md):

```js
import { ZonasCache, riesgoDeCoordenada } from './src/geofencing';
```

## Build instalable (APK) — Issue #42

```bash
npm install -g eas-cli
eas login
eas build -p android --profile preview
```

## Privacidad y ubicación (Issue #39)

La app pide el permiso de ubicación **solo desde la tab Perfil**, después de
mostrar un aviso de privacidad explícito (Ley 1581 de 2012) — no hay ningún
permiso pedido al abrir la app. El consentimiento y la posición viven solo en
memoria (`UbicacionContext`, sin `AsyncStorage`): se resetean al cerrar la
app.

Si el permiso se deniega (o el dispositivo no tiene GPS disponible), la tab
Perfil ofrece un switch de **"modo demo"** que fija una coordenada simulada de
Bogotá — sin ruta ni animación (eso llega en la Issue #41). El chip de
`MapaScreen` muestra la coordenada cruda (real o demo); resolverla a
localidad/nivel de riesgo real es la Issue #40.

### Tests

Primer test runner de `mobile/` (`jest` + `jest-expo`), cubre el reducer
puro de ubicación y el servicio sobre `expo-location` (mockeado) — sin tests
de renderizado de pantallas ni del diálogo nativo de permisos, que se
verifican a mano:

```bash
cd mobile
npm test
```

### Checklist de verificación manual en dispositivo físico

1. Abrir la tab **Perfil** sin haber concedido el permiso antes: debe verse
   el aviso de privacidad con los dos botones.
2. Tocar **"Aceptar y activar ubicación"**: el SO debe pedir el permiso de
   ubicación; al concederlo, Perfil debe mostrar "Ubicación activa" y, tras
   unos segundos, coordenadas reales.
3. Ir a la tab **Mapa**: el chip debe mostrar las mismas coordenadas
   (`· GPS activo`) y actualizarse al moverte.
4. Denegar el permiso (probar en una segunda instalación o revocándolo desde
   Ajustes del sistema y reabriendo la app): Perfil debe mostrar el mensaje
   de error claro, sin que la app se rompa.
5. Activar el switch **"Modo demo"**: el chip de Mapa debe cambiar a la
   coordenada fija con `· Modo demo`, y desactivarlo debe volver a
   "Ubicación desactivada" (si no hay permiso real) o a la posición GPS (si
   sí lo hay).
