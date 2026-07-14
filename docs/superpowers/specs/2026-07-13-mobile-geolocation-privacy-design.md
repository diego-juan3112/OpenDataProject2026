# Diseño — Geolocalización en tiempo real + permisos + privacidad opt-in (Issue [APP] #39)

**Fecha:** 2026-07-13 · **Pista:** 4 — App móvil (Integrante 4) · **Fase CRISP-ML:** 5

## Contexto

Issue #39 depende de #38 (completo: scaffold de 4 tabs + `MapaScreen` con
polígonos de riesgo desde un mock, `expo-location`/`expo-notifications` ya
instalados en `package.json` desde #37) y bloquea a #40 (notificación al
entrar a zona de riesgo alto) y #41 (modo demo con ruta simulada completa).

Dos puntos ya dejados como placeholder por el scaffold anterior marcan dónde
debe vivir este trabajo:
- `MapaScreen.jsx` tiene `ZONA_ACTUAL = { nombre: 'Chapinero', nivel: 'MEDIO' }`
  hardcodeado, con el comentario `// Ubicación actual hardcodeada (el GPS
  real llega en #39)`.
- `PerfilScreen.jsx` es un placeholder con el comentario `// Aviso de
  privacidad / consentimiento opt-in + modo demo (Issues #39, #51)`.

**Criterios de aceptación (del backlog):**
1. La app solicita permiso de ubicación con aviso de privacidad opt-in (Ley
   1581/2012). **No se recorta.**
2. Muestra la posición actual y la actualiza periódicamente en primer plano.
3. Manejo del caso "permiso denegado" sin romper (mensaje claro + modo demo
   disponible).

## Decisiones acordadas con el usuario

- El flujo de consentimiento vive **solo en la tab Perfil** (no un modal
  bloqueante al abrir la app) — coincide con el placeholder ya dejado ahí.
- El consentimiento es **solo de sesión** (Context de React en memoria, sin
  `AsyncStorage`): se vuelve a preguntar cada vez que se abre la app. Mismo
  patrón "sin persistencia" que ya usa el reporte ciudadano del dashboard
  (`st.session_state`, #36).
- El chip de `MapaScreen` muestra **coordenadas crudas** (`📍 4.6533,
  -74.0836`), no la zona/nivel de riesgo resuelta — resolver una coordenada a
  zona real es trabajo de #40 ("conectar el GPS de #39 con la capa de
  geofencing de #21"), no de esta issue.
- El "modo demo" de esta issue es **una sola coordenada fija** inyectada por
  un switch en Perfil (sin ruta ni animación) — la ruta simulada completa que
  cruza a una zona de riesgo alto es #41, coordinada con Integrante 3.

## Arquitectura

Un **Context de React** (`UbicacionContext`), montado en `App.js` alrededor
de `NavigationContainer`, compartido entre las tabs `Mapa` y `Perfil`. El
estado se maneja con un **reducer puro** (testeable sin renderizar React ni
mockear `expo-location`), separado de los efectos secundarios (llamadas
reales a `expo-location`), que viven en un **servicio** — mismo patrón de
"capa de datos que abstrae el origen" que ya usa `zonasService.js` (mock vs.
API real; aquí, GPS real vs. coordenada demo).

```
PerfilScreen / MapaScreen
        │  useUbicacion()
        ▼
UbicacionContext.jsx  (useReducer + efectos: pide permiso, suscribe GPS)
        │                                   │
        ▼                                   ▼
ubicacionReducer.js (puro, sin I/O)   ubicacionService.js (envuelve expo-location)
```

## Dónde vive el código

- **`mobile/src/context/ubicacionReducer.js`** (nuevo): estado inicial
  `{ consentimiento: 'sin-decidir', permiso: 'sin-preguntar', posicion: null,
  modoDemo: false, error: null }` y `ubicacionReducer(estado, accion)` puro
  con las transiciones: `ACEPTAR_CONSENTIMIENTO`, `RECHAZAR_CONSENTIMIENTO`
  (implica `permiso: 'denegado'` sin llamar al SO), `PERMISO_CONCEDIDO`,
  `PERMISO_DENEGADO`, `POSICION_ACTUALIZADA` (payload `{lat, lon,
  precision}`), `ERROR_GPS`, `ACTIVAR_MODO_DEMO` (fija `posicion` a la
  coordenada demo), `DESACTIVAR_MODO_DEMO` (limpia `posicion`). Sin
  dependencias de React Native ni `expo-location` — 100% unit-testeable.
- **`mobile/src/services/ubicacionService.js`** (nuevo): `pedirPermiso()`
  llama `Location.requestForegroundPermissionsAsync()` y mapea el `status`
  del SO a `'concedido'|'denegado'`; `suscribirPosicion(onUpdate, onError)`
  llama `Location.watchPositionAsync({ accuracy: Balanced, timeInterval:
  5000, distanceInterval: 15 }, ...)` y devuelve la suscripción (para
  `.remove()` en cleanup); `COORDENADA_DEMO` exporta la coordenada fija
  provisional (Chapinero, mismo punto que el chip hardcodeado actual) con un
  comentario de que #41 la reemplaza por la ruta real coordinada con
  Integrante 3.
- **`mobile/src/context/UbicacionContext.jsx`** (nuevo): `UbicacionProvider`
  con `useReducer(ubicacionReducer, ESTADO_INICIAL)`; expone
  `aceptarConsentimiento()` (dispara `pedirPermiso()` y despacha
  `PERMISO_CONCEDIDO`/`PERMISO_DENEGADO`; si se concede, llama
  `suscribirPosicion()` y guarda la suscripción en un `useRef` para poder
  cancelarla), `rechazarConsentimiento()`, `activarModoDemo()` /
  `desactivarModoDemo()` (cancela la suscripción GPS si estaba activa).
  Hook `useUbicacion()` para consumir el contexto.
- **`mobile/App.js`** (edita): envuelve `NavigationContainer` con
  `<UbicacionProvider>`.
- **`mobile/src/screens/PerfilScreen.jsx`** (reemplaza el placeholder):
  tarjeta de aviso de privacidad en lenguaje claro (qué se usa, para qué —
  avisar al entrar a zona de riesgo alto —, que no se guarda ni se comparte,
  mención a Ley 1581/2012) con botones "Aceptar y activar ubicación" / "No,
  gracias" cuando `consentimiento === 'sin-decidir'`; estado "Ubicación
  activa" + última posición cuando `permiso === 'concedido'`; mensaje claro
  + switch "Modo demo" cuando `permiso === 'denegado'` (el switch queda
  visible siempre, no solo tras un rechazo, para poder probarlo sin
  necesidad de negar el permiso primero).
- **`mobile/src/screens/MapaScreen.jsx`** (edita): quita `ZONA_ACTUAL`
  hardcodeado; el chip lee `useUbicacion()` y muestra `📍 {lat}, {lon} · GPS
  activo` o `· Modo demo` si hay `posicion`, o `📍 Ubicación desactivada ·
  Actívala en Perfil` (con `onPress` que navega a la tab Perfil) si no la
  hay.

## Manejo de errores

- Permiso denegado por el SO → `PERMISO_DENEGADO`, mensaje claro en Perfil,
  la app no se rompe; el switch de modo demo queda como salida.
- `watchPositionAsync` falla en tiempo de ejecución (GPS del dispositivo
  apagado) aunque el permiso esté concedido → `onError` despacha `ERROR_GPS`,
  se muestra el mismo mensaje de "no se pudo obtener tu ubicación" + modo
  demo disponible; si el modo demo ya estaba activo, `posicion` no se borra.
- Cleanup: la suscripción de `watchPositionAsync` se cancela (`.remove()`)
  al desmontar el provider o al activar modo demo, para no seguir
  consumiendo GPS de fondo innecesariamente.

## Testing

Primer test runner para `mobile/` (no existía ninguno para #37/#38):

- Se agregan `jest`, `jest-expo`, `babel-preset-expo` como devDependencies,
  `babel.config.js` (`presets: ['babel-preset-expo']`) y el script
  `"test": "jest"` en `package.json`.
- **`mobile/src/context/ubicacionReducer.test.js`**: cubre las 8
  transiciones del reducer puro, sin mockear `expo-location` ni renderizar
  componentes — incluye el caso `ERROR_GPS` con `modoDemo: true` (la
  posición demo no debe borrarse) y con `modoDemo: false` (sí se borra).
- **`mobile/src/services/ubicacionService.test.js`**: mockea el módulo
  `expo-location` (`jest.mock('expo-location')`) para verificar que
  `pedirPermiso()` mapea `'granted'→'concedido'` y cualquier otro status a
  `'denegado'`, y que `suscribirPosicion()` llama a `watchPositionAsync` con
  las opciones esperadas y reenvía las coordenadas en el shape
  `{lat, lon, precision}`.
- **Fuera de alcance de estos tests:** render de `PerfilScreen`/`MapaScreen`
  (necesitaría `@testing-library/react-native`, no instalado) y el flujo end
  a end del diálogo nativo de permisos, que no se puede simular de forma
  significativa. Se verifica manualmente en un dispositivo físico corriendo
  `npx expo start`: aceptar/rechazar el consentimiento, conceder/denegar el
  permiso del SO, confirmar que el chip de `MapaScreen` se actualiza
  periódicamente, y probar el toggle de modo demo con el permiso denegado.

## Fuera de alcance

Resolver la coordenada a localidad/nivel de riesgo real (#40, usa
`riesgoDeCoordenada` de `src/geofencing/`, ya disponible). Disparar
notificaciones (#40). La ruta de modo demo con varias coordenadas cruzando a
zona de riesgo alto, coordinada con Integrante 3 (#41). Persistencia del
consentimiento entre reinicios de la app (`AsyncStorage`). Soporte iOS (el
dispositivo objetivo del entregable es Android, `CLAUDE.md` §4).
