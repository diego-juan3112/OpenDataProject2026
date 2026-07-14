# mobile/ — App Alerta Ciudadana (Expo / React Native)

**Integrante 4** · Issues #37–#44, #49–#51 · **Expo SDK 54** (JavaScript, template `blank`)

App móvil que consume la API de Alerta Ciudadana: mapa de riesgo por localidad,
alerta local al entrar a zona de riesgo alto y modo demo. Cliente delgado del
contrato `/zonas-riesgo`.

> **El proyecto va en Expo SDK 54** porque es la versión de **Expo Go** disponible
> en la Play Store del equipo. No lo subas a un SDK mayor sin que todos tengan un
> Expo Go compatible: un desajuste rompe el bundling (error de codegen). Si tras un
> `git pull` cambian las versiones, **borra `node_modules` y reinstala**
> (`Remove-Item -Recurse -Force node_modules; npm install`), y arranca con caché
> limpia: `npx expo start -c`.

## Prerrequisitos
- Node.js >= 18 (verificado con v24)
- **Expo Go 54** instalado en el teléfono Android (Play Store)
- La API backend corriendo — opcional: por defecto el mapa usa datos mock (ver `README.md` de la raíz)

## Cómo correr en desarrollo

```bash
cd mobile
npm install
npx expo start          # escanear el QR con Expo Go
# Si hay problemas de red (el teléfono no ve el QR / la LAN):
npx expo start --tunnel
```

El teléfono debe estar en la **misma red Wi-Fi** que el computador.

## Cómo apuntar a la API (`.env`)

La URL de la API y el modo mock se leen de **`mobile/.env`** (no versionado).
Copia la plantilla y ajústala:

```bash
cp .env.example .env     # Windows: copy .env.example .env
```

`mobile/.env`:
```
EXPO_PUBLIC_API_BASE_URL=http://192.168.x.x:8000   # IP de LAN del PC (ipconfig → Wi-Fi), puerto 8000
EXPO_PUBLIC_USAR_MOCK=false                        # false = API real · true = mock
```

- **IP de LAN** (misma Wi-Fi): la del adaptador **Wi-Fi** en `ipconfig`/`ifconfig`
  (no la de adaptadores virtuales tipo `192.168.56.x`). Es dinámica: si cambia la
  red, actualiza el `.env`.
- **Túnel ngrok** (URL estable para la demo): `ngrok http 8000` en el PC y pon
  `https://xxxx.ngrok.io` en `EXPO_PUBLIC_API_BASE_URL`.
- Tras editar el `.env`, reinicia con caché limpia: `npx expo start -c`.

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

## Consumir la API real + build instalable (APK) — Issue #42

Por defecto (sin `.env`) el mapa usa datos de prueba (mock). Para consumir la
**API real**, configura `mobile/.env` (ver *"Cómo apuntar a la API"* arriba):

1. Levanta la API en la LAN (ver `README.md` raíz) y anota su IP (`ipconfig`).
2. En `mobile/.env`: `EXPO_PUBLIC_API_BASE_URL=http://<IP-LAN>:8000` y
   `EXPO_PUBLIC_USAR_MOCK=false`.
3. Reinicia con caché limpia: `npx expo start -c`. Con eso el mapa, el chip y las
   alertas usan `GET /zonas-riesgo` real (mismo shape que el mock, nada más cambia).

**Build APK instalable** (requiere una cuenta Expo; el build corre en la nube de
EAS, perfil `preview` definido en `eas.json`):

```bash
npm install -g eas-cli
eas login
eas build -p android --profile preview
```

Al terminar, EAS entrega un enlace para descargar e instalar el APK en el
teléfono (o `eas build:run -p android` para instalarlo por USB).

## Privacidad y ubicación (Issue #39)

La app pide el permiso de ubicación **solo desde la tab Perfil**, después de
mostrar un aviso de privacidad explícito (Ley 1581 de 2012) — no hay ningún
permiso pedido al abrir la app. El consentimiento y la posición viven solo en
memoria (`UbicacionContext`, sin `AsyncStorage`): se resetean al cerrar la
app.

Si el permiso se deniega (o el dispositivo no tiene GPS disponible), la tab
Perfil ofrece un switch de **"modo demo"** (ver abajo). El chip de `MapaScreen`
muestra la **localidad y el nivel de riesgo** resueltos por el geofencing (#21).

## Alertas y modo demo (Issues #40–#41)

**Alerta local (#40).** `AlertaRiesgoProvider` observa la posición (GPS o demo),
la resuelve a localidad con el geofencing (#21) y, **al entrar a una zona de
riesgo alto**, dispara una notificación local (`expo-notifications`). Es
anti-rebote: solo notifica en la **transición** a "alto" y se re-arma al salir
(lógica pura en `src/logic/alertaRiesgo.js`, testeada). La tab **Alertas**
muestra el estado del permiso, tu zona/nivel actual y el historial de alertas.

**Modo demo (#41) — guion para la presentación:**

1. (Opcional) Concede notificaciones la primera vez que abras la tab **Alertas**.
2. Ve a **Perfil** y activa el switch **"Modo demo (recorrido simulado)"**.
3. La app reproduce una ruta **Usaquén (bajo) → Chapinero (medio) → Kennedy
   (alto)**, un punto cada ~2,5 s. El chip de **Mapa** va cambiando de nivel.
4. Al cruzar a **Kennedy (riesgo alto)** salta la **notificación local**
   "⚠️ Zona de riesgo ALTO" y aparece en el historial de **Alertas**.
5. Desactiva el switch para volver al GPS real (o a "ubicación desactivada").

No depende de moverse físicamente ni de la red → la alerta se dispara de forma
reproducible en la demo en vivo.

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
5. Activar el switch **"Modo demo"**: el chip de Mapa debe recorrer las zonas
   (bajo → medio → alto); al llegar a **Kennedy** debe **saltar la notificación
   local** de riesgo alto y registrarse en la tab **Alertas**. Desactivarlo
   vuelve al GPS real (si hay permiso) o a "ubicación desactivada".
6. Permanecer en la zona alta: **no** debe repetir la notificación (anti-rebote).
