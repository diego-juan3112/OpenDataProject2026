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
