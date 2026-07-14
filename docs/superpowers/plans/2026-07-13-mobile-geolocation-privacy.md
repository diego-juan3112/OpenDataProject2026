# Geolocalización en tiempo real + permisos + privacidad opt-in (Issue #39) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar la ubicación hardcodeada de `MapaScreen` por la posición
real del GPS (o una coordenada de "modo demo"), detrás de un flujo de
consentimiento opt-in de privacidad en la tab Perfil, sin romper la app si el
permiso se deniega.

**Architecture:** Un reducer puro (`ubicacionReducer.js`) modela las
transiciones de estado; un servicio (`ubicacionService.js`) envuelve las
llamadas reales a `expo-location`; un Context de React
(`UbicacionContext.jsx`) los conecta con `useReducer` + efectos y expone
`useUbicacion()` a `PerfilScreen` y `MapaScreen`.

**Tech Stack:** Expo SDK 57, React Navigation (ya instalado), `expo-location`
(ya instalado), Jest + `jest-expo` (nuevo, primer test runner de `mobile/`).

## Global Constraints

- El consentimiento vive **solo en la tab Perfil** — no hay modal bloqueante al abrir la app.
- El consentimiento y todo el estado de ubicación son **solo de sesión** (en memoria, sin `AsyncStorage`).
- El chip de `MapaScreen` muestra **coordenadas crudas**, no la zona/nivel de riesgo resuelto — resolver la coordenada a zona real es la Issue #40, no esta.
- El "modo demo" de esta issue es **una sola coordenada fija** — la ruta simulada completa que cruza a zona de riesgo alto es la Issue #41.
- Dispositivo objetivo: **Android únicamente** (`CLAUDE.md` §4) — no se agrega configuración específica de iOS.
- Primer test runner de `mobile/`: `jest` + `jest-expo` + `babel-preset-expo`.

---

## Task 1: Test tooling + `ubicacionReducer` (lógica pura, sin I/O)

**Files:**
- Modify: `mobile/package.json`
- Create: `mobile/babel.config.js`
- Create: `mobile/src/context/ubicacionReducer.js`
- Test: `mobile/src/context/ubicacionReducer.test.js`

**Interfaces:**
- Produces: `ESTADO_INICIAL` (objeto), `ubicacionReducer(estado, accion) -> nuevoEstado` — usados por `UbicacionContext.jsx` en el Task 3.

- [ ] **Step 1: Agregar devDependencies y scripts de test a `package.json`**

Edita `mobile/package.json` (queda así completo):

```json
{
  "name": "alerta-ciudadana-mobile",
  "version": "0.1.0",
  "main": "index.js",
  "dependencies": {
    "@react-navigation/bottom-tabs": "^7.18.8",
    "@react-navigation/native": "^7.3.8",
    "expo": "~57.0.4",
    "expo-location": "~57.0.2",
    "expo-notifications": "~57.0.3",
    "expo-status-bar": "~57.0.0",
    "react": "19.2.3",
    "react-native": "0.86.0",
    "react-native-maps": "1.27.2",
    "react-native-safe-area-context": "~5.7.0",
    "react-native-screens": "4.25.2"
  },
  "devDependencies": {
    "babel-preset-expo": "~57.0.0",
    "jest": "^29.7.0",
    "jest-expo": "~57.0.0"
  },
  "scripts": {
    "start": "expo start",
    "android": "expo start --android",
    "ios": "expo start --ios",
    "web": "expo start --web",
    "test": "jest"
  },
  "jest": {
    "preset": "jest-expo"
  },
  "private": true
}
```

- [ ] **Step 2: Crear `babel.config.js`**

```js
module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
  };
};
```

- [ ] **Step 3: Instalar dependencias**

Run: `cd mobile && npm install`
Expected: instala sin errores. **Si `npm install` reporta un conflicto de
peer dependencies** entre `jest` y `jest-expo`, correr
`npm view jest-expo@57 peerDependencies` para ver el rango exacto de `jest`
que espera esa versión de `jest-expo`, ajustar la versión de `"jest"` en
`package.json` a ese rango, y repetir `npm install`.

- [ ] **Step 4: Escribir el test (falla porque `ubicacionReducer.js` no existe)**

Crear `mobile/src/context/ubicacionReducer.test.js`:

```js
import { ESTADO_INICIAL, ubicacionReducer } from './ubicacionReducer';

describe('ubicacionReducer', () => {
  test('ACEPTAR_CONSENTIMIENTO marca el consentimiento como aceptado', () => {
    const resultado = ubicacionReducer(ESTADO_INICIAL, { type: 'ACEPTAR_CONSENTIMIENTO' });
    expect(resultado.consentimiento).toBe('aceptado');
  });

  test('RECHAZAR_CONSENTIMIENTO marca consentimiento rechazado y permiso denegado', () => {
    const resultado = ubicacionReducer(ESTADO_INICIAL, { type: 'RECHAZAR_CONSENTIMIENTO' });
    expect(resultado.consentimiento).toBe('rechazado');
    expect(resultado.permiso).toBe('denegado');
  });

  test('PERMISO_CONCEDIDO marca permiso concedido y limpia error previo', () => {
    const estadoConError = { ...ESTADO_INICIAL, error: 'algo previo' };
    const resultado = ubicacionReducer(estadoConError, { type: 'PERMISO_CONCEDIDO' });
    expect(resultado.permiso).toBe('concedido');
    expect(resultado.error).toBeNull();
  });

  test('PERMISO_DENEGADO marca permiso denegado con mensaje claro', () => {
    const resultado = ubicacionReducer(ESTADO_INICIAL, { type: 'PERMISO_DENEGADO' });
    expect(resultado.permiso).toBe('denegado');
    expect(resultado.error).toBe('No se concedió el permiso de ubicación.');
  });

  test('POSICION_ACTUALIZADA guarda la posicion y limpia error', () => {
    const estadoConError = { ...ESTADO_INICIAL, error: 'algo previo' };
    const posicion = { lat: 4.65, lon: -74.08, precision: 10 };
    const resultado = ubicacionReducer(estadoConError, {
      type: 'POSICION_ACTUALIZADA',
      payload: posicion,
    });
    expect(resultado.posicion).toEqual(posicion);
    expect(resultado.error).toBeNull();
  });

  test('ERROR_GPS sin modo demo borra la posicion', () => {
    const estado = { ...ESTADO_INICIAL, posicion: { lat: 1, lon: 2, precision: 5 }, modoDemo: false };
    const resultado = ubicacionReducer(estado, { type: 'ERROR_GPS', payload: 'GPS apagado' });
    expect(resultado.error).toBe('GPS apagado');
    expect(resultado.posicion).toBeNull();
  });

  test('ERROR_GPS con modo demo activo conserva la posicion demo', () => {
    const posicionDemo = { lat: 4.6492, lon: -74.0628, precision: null };
    const estado = { ...ESTADO_INICIAL, posicion: posicionDemo, modoDemo: true };
    const resultado = ubicacionReducer(estado, { type: 'ERROR_GPS', payload: 'GPS apagado' });
    expect(resultado.error).toBe('GPS apagado');
    expect(resultado.posicion).toEqual(posicionDemo);
  });

  test('ACTIVAR_MODO_DEMO fija la posicion demo recibida como payload', () => {
    const posicionDemo = { lat: 4.6492, lon: -74.0628, precision: null };
    const resultado = ubicacionReducer(ESTADO_INICIAL, {
      type: 'ACTIVAR_MODO_DEMO',
      payload: posicionDemo,
    });
    expect(resultado.modoDemo).toBe(true);
    expect(resultado.posicion).toEqual(posicionDemo);
    expect(resultado.error).toBeNull();
  });

  test('DESACTIVAR_MODO_DEMO limpia la posicion y el flag', () => {
    const estado = {
      ...ESTADO_INICIAL,
      modoDemo: true,
      posicion: { lat: 4.6492, lon: -74.0628, precision: null },
    };
    const resultado = ubicacionReducer(estado, { type: 'DESACTIVAR_MODO_DEMO' });
    expect(resultado.modoDemo).toBe(false);
    expect(resultado.posicion).toBeNull();
  });
});
```

- [ ] **Step 5: Correr el test y verificar que falla**

Run: `cd mobile && npx jest src/context/ubicacionReducer.test.js`
Expected: FAIL — `Cannot find module './ubicacionReducer'`

- [ ] **Step 6: Implementar `ubicacionReducer.js`**

Crear `mobile/src/context/ubicacionReducer.js`:

```js
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
```

- [ ] **Step 7: Correr el test y verificar que pasa**

Run: `cd mobile && npx jest src/context/ubicacionReducer.test.js`
Expected: PASS — 9 tests

- [ ] **Step 8: Commit**

```bash
git add mobile/package.json mobile/package-lock.json mobile/babel.config.js mobile/src/context/ubicacionReducer.js mobile/src/context/ubicacionReducer.test.js
git commit -m "test(mobile): agrega jest + ubicacionReducer puro (issue #39)"
```

---

## Task 2: `ubicacionService` (envuelve `expo-location`)

**Files:**
- Create: `mobile/src/services/ubicacionService.js`
- Test: `mobile/src/services/ubicacionService.test.js`

**Interfaces:**
- Consumes: `expo-location` (`requestForegroundPermissionsAsync`, `watchPositionAsync`, `Accuracy`).
- Produces: `pedirPermiso() -> Promise<'concedido'|'denegado'>`, `suscribirPosicion(onUpdate, onError) -> Promise<{remove: Function}|null>`, `COORDENADA_DEMO` (objeto `{lat, lon, precision}`) — usados por `UbicacionContext.jsx` en el Task 3.

- [ ] **Step 1: Escribir el test (falla porque `ubicacionService.js` no existe)**

Crear `mobile/src/services/ubicacionService.test.js`:

```js
jest.mock('expo-location', () => ({
  requestForegroundPermissionsAsync: jest.fn(),
  watchPositionAsync: jest.fn(),
  Accuracy: { Balanced: 3 },
}));

import * as Location from 'expo-location';
import { pedirPermiso, suscribirPosicion, COORDENADA_DEMO } from './ubicacionService';

beforeEach(() => {
  jest.clearAllMocks();
});

describe('pedirPermiso', () => {
  test('mapea "granted" a "concedido"', async () => {
    Location.requestForegroundPermissionsAsync.mockResolvedValue({ status: 'granted' });
    await expect(pedirPermiso()).resolves.toBe('concedido');
  });

  test('mapea cualquier otro status a "denegado"', async () => {
    Location.requestForegroundPermissionsAsync.mockResolvedValue({ status: 'denied' });
    await expect(pedirPermiso()).resolves.toBe('denegado');
  });
});

describe('suscribirPosicion', () => {
  test('llama watchPositionAsync con las opciones esperadas y reenvia coords', async () => {
    let callbackCapturado;
    Location.watchPositionAsync.mockImplementation((opciones, callback) => {
      callbackCapturado = callback;
      return Promise.resolve({ remove: jest.fn() });
    });

    const onUpdate = jest.fn();
    const onError = jest.fn();
    const suscripcion = await suscribirPosicion(onUpdate, onError);

    expect(Location.watchPositionAsync).toHaveBeenCalledWith(
      { accuracy: Location.Accuracy.Balanced, timeInterval: 5000, distanceInterval: 15 },
      expect.any(Function),
    );

    callbackCapturado({ coords: { latitude: 4.65, longitude: -74.08, accuracy: 12 } });
    expect(onUpdate).toHaveBeenCalledWith({ lat: 4.65, lon: -74.08, precision: 12 });
    expect(suscripcion.remove).toBeInstanceOf(Function);
    expect(onError).not.toHaveBeenCalled();
  });

  test('si watchPositionAsync rechaza, llama onError y devuelve null', async () => {
    Location.watchPositionAsync.mockRejectedValue(new Error('GPS apagado'));
    const onUpdate = jest.fn();
    const onError = jest.fn();

    const resultado = await suscribirPosicion(onUpdate, onError);

    expect(resultado).toBeNull();
    expect(onError).toHaveBeenCalledWith('GPS apagado');
  });
});

test('COORDENADA_DEMO es una coordenada valida dentro de Bogota', () => {
  expect(COORDENADA_DEMO.lat).toBeCloseTo(4.6492, 2);
  expect(COORDENADA_DEMO.lon).toBeCloseTo(-74.0628, 2);
});
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd mobile && npx jest src/services/ubicacionService.test.js`
Expected: FAIL — `Cannot find module './ubicacionService'`

- [ ] **Step 3: Implementar `ubicacionService.js`**

Crear `mobile/src/services/ubicacionService.js`:

```js
// ubicacionService.js
//
// Envuelve expo-location: pedir permiso y suscribirse a la posición en
// primer plano. UbicacionContext.jsx es el único consumidor — no importa
// React ni el reducer, para poder mockear expo-location sin renderizar nada.

import * as Location from 'expo-location';

// Coordenada fija provisional (Chapinero) para el "modo demo" de esta issue.
// La Issue #41 la reemplaza por la ruta simulada real, coordinada con
// Integrante 3 a partir del modelo/tipología de zonas.
export const COORDENADA_DEMO = { lat: 4.6492, lon: -74.0628, precision: null };

export async function pedirPermiso() {
  const { status } = await Location.requestForegroundPermissionsAsync();
  return status === 'granted' ? 'concedido' : 'denegado';
}

// Muestreo periódico en primer plano (issue #39, criterio 2): cada 5s o cada
// 15m de desplazamiento, lo que ocurra primero.
export async function suscribirPosicion(onUpdate, onError) {
  try {
    return await Location.watchPositionAsync(
      { accuracy: Location.Accuracy.Balanced, timeInterval: 5000, distanceInterval: 15 },
      (loc) => {
        onUpdate({
          lat: loc.coords.latitude,
          lon: loc.coords.longitude,
          precision: loc.coords.accuracy ?? null,
        });
      },
    );
  } catch (err) {
    onError(err instanceof Error ? err.message : String(err));
    return null;
  }
}
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `cd mobile && npx jest src/services/ubicacionService.test.js`
Expected: PASS — 5 tests

- [ ] **Step 5: Commit**

```bash
git add mobile/src/services/ubicacionService.js mobile/src/services/ubicacionService.test.js
git commit -m "feat(mobile): agrega ubicacionService sobre expo-location (issue #39)"
```

---

## Task 3: `UbicacionContext` (conecta reducer + servicio, expone `useUbicacion()`)

**Files:**
- Modify: `mobile/package.json` (agrega `react-test-renderer`)
- Create: `mobile/src/context/UbicacionContext.jsx`
- Test: `mobile/src/context/UbicacionContext.test.jsx`

**Interfaces:**
- Consumes: `ubicacionReducer`, `ESTADO_INICIAL` (Task 1); `pedirPermiso`, `suscribirPosicion`, `COORDENADA_DEMO` (Task 2).
- Produces: `UbicacionProvider` (componente), `useUbicacion()` hook devolviendo `{ consentimiento, permiso, posicion, modoDemo, error, aceptarConsentimiento(), rechazarConsentimiento(), activarModoDemo(), desactivarModoDemo() }` — usado por `PerfilScreen.jsx` (Task 4) y `MapaScreen.jsx` (Task 5).

- [ ] **Step 1: Agregar `react-test-renderer` a `package.json` e instalar**

En `mobile/package.json`, dentro de `"devDependencies"`, agregar (junto a las
del Task 1):

```json
    "react-test-renderer": "19.2.3"
```

Run: `cd mobile && npm install`
Expected: instala sin errores (misma versión que `"react": "19.2.3"` en dependencies).

- [ ] **Step 2: Escribir el test (falla porque `UbicacionContext.jsx` no existe)**

Crear `mobile/src/context/UbicacionContext.test.jsx`:

```jsx
import { create, act } from 'react-test-renderer';

import { UbicacionProvider, useUbicacion } from './UbicacionContext';
import * as ubicacionService from '../services/ubicacionService';

jest.mock('../services/ubicacionService', () => ({
  pedirPermiso: jest.fn(),
  suscribirPosicion: jest.fn(),
  COORDENADA_DEMO: { lat: 4.6492, lon: -74.0628, precision: null },
}));

let valorActual;
function Consumidor() {
  valorActual = useUbicacion();
  return null;
}

function montar() {
  let raiz;
  act(() => {
    raiz = create(
      <UbicacionProvider>
        <Consumidor />
      </UbicacionProvider>,
    );
  });
  return raiz;
}

beforeEach(() => {
  jest.clearAllMocks();
});

test('estado inicial es sin-decidir / sin-preguntar', () => {
  montar();
  expect(valorActual.consentimiento).toBe('sin-decidir');
  expect(valorActual.permiso).toBe('sin-preguntar');
  expect(valorActual.posicion).toBeNull();
});

test('aceptarConsentimiento con permiso concedido suscribe la posicion', async () => {
  ubicacionService.pedirPermiso.mockResolvedValue('concedido');
  const remove = jest.fn();
  ubicacionService.suscribirPosicion.mockResolvedValue({ remove });

  montar();
  await act(async () => {
    await valorActual.aceptarConsentimiento();
  });

  expect(valorActual.consentimiento).toBe('aceptado');
  expect(valorActual.permiso).toBe('concedido');
  expect(ubicacionService.suscribirPosicion).toHaveBeenCalledTimes(1);
});

test('aceptarConsentimiento con permiso denegado no suscribe nada', async () => {
  ubicacionService.pedirPermiso.mockResolvedValue('denegado');

  montar();
  await act(async () => {
    await valorActual.aceptarConsentimiento();
  });

  expect(valorActual.permiso).toBe('denegado');
  expect(ubicacionService.suscribirPosicion).not.toHaveBeenCalled();
});

test('rechazarConsentimiento marca permiso denegado sin llamar al servicio', () => {
  montar();
  act(() => {
    valorActual.rechazarConsentimiento();
  });

  expect(valorActual.consentimiento).toBe('rechazado');
  expect(valorActual.permiso).toBe('denegado');
  expect(ubicacionService.pedirPermiso).not.toHaveBeenCalled();
});

test('activarModoDemo fija la posicion demo y detiene la suscripcion GPS activa', async () => {
  ubicacionService.pedirPermiso.mockResolvedValue('concedido');
  const remove = jest.fn();
  ubicacionService.suscribirPosicion.mockResolvedValue({ remove });

  montar();
  await act(async () => {
    await valorActual.aceptarConsentimiento();
  });

  act(() => {
    valorActual.activarModoDemo();
  });

  expect(remove).toHaveBeenCalledTimes(1);
  expect(valorActual.modoDemo).toBe(true);
  expect(valorActual.posicion).toEqual({ lat: 4.6492, lon: -74.0628, precision: null });
});

test('desactivarModoDemo limpia la posicion', async () => {
  ubicacionService.pedirPermiso.mockResolvedValue('denegado');

  montar();
  await act(async () => {
    await valorActual.aceptarConsentimiento();
  });

  act(() => {
    valorActual.activarModoDemo();
  });
  expect(valorActual.posicion).not.toBeNull();

  act(() => {
    valorActual.desactivarModoDemo();
  });
  expect(valorActual.modoDemo).toBe(false);
  expect(valorActual.posicion).toBeNull();
});

test('useUbicacion fuera del provider lanza un error claro', () => {
  function ConsumidorSuelto() {
    useUbicacion();
    return null;
  }
  const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
  expect(() => create(<ConsumidorSuelto />)).toThrow(
    'useUbicacion debe usarse dentro de UbicacionProvider',
  );
  spy.mockRestore();
});
```

- [ ] **Step 3: Correr el test y verificar que falla**

Run: `cd mobile && npx jest src/context/UbicacionContext.test.jsx`
Expected: FAIL — `Cannot find module './UbicacionContext'`

- [ ] **Step 4: Implementar `UbicacionContext.jsx`**

Crear `mobile/src/context/UbicacionContext.jsx`:

```jsx
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
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `cd mobile && npx jest src/context/UbicacionContext.test.jsx`
Expected: PASS — 7 tests

- [ ] **Step 6: Correr toda la suite de jest junta**

Run: `cd mobile && npm test`
Expected: PASS — 21 tests (9 reducer + 5 service + 7 context) en 3 suites

- [ ] **Step 7: Commit**

```bash
git add mobile/package.json mobile/package-lock.json mobile/src/context/UbicacionContext.jsx mobile/src/context/UbicacionContext.test.jsx
git commit -m "feat(mobile): agrega UbicacionContext (issue #39)"
```

---

## Task 4: Montar el provider + pantalla de privacidad (`PerfilScreen`)

**Files:**
- Modify: `mobile/App.js`
- Modify: `mobile/src/screens/PerfilScreen.jsx`

**Interfaces:**
- Consumes: `UbicacionProvider`, `useUbicacion()` (Task 3).

- [ ] **Step 1: Envolver la navegación con `UbicacionProvider` en `App.js`**

Reemplazar el contenido de `mobile/App.js` por:

```jsx
import { NavigationContainer } from '@react-navigation/native';
import { StatusBar } from 'expo-status-bar';

import AppNavigator from './src/navigation/AppNavigator';
import { UbicacionProvider } from './src/context/UbicacionContext';

// Punto de entrada. UbicacionProvider (issue #39) comparte el estado de
// permiso/posición entre las tabs Mapa y Perfil. La navegación (4 tabs)
// vive en src/navigation/AppNavigator.
export default function App() {
  return (
    <UbicacionProvider>
      <NavigationContainer>
        <StatusBar style="light" />
        <AppNavigator />
      </NavigationContainer>
    </UbicacionProvider>
  );
}
```

- [ ] **Step 2: Reemplazar el placeholder de `PerfilScreen.jsx`**

Reemplazar el contenido completo de `mobile/src/screens/PerfilScreen.jsx` por:

```jsx
import { StyleSheet, Switch, Text, TouchableOpacity, View } from 'react-native';

import { COLORES } from '../config';
import { useUbicacion } from '../context/UbicacionContext';

// Aviso de privacidad / consentimiento opt-in + estado de ubicación +
// modo demo (Issue #39). El modo demo con ruta simulada completa es #41;
// aquí solo fija una coordenada, ver ubicacionService.js::COORDENADA_DEMO.
export default function PerfilScreen() {
  const {
    consentimiento,
    permiso,
    posicion,
    modoDemo,
    error,
    aceptarConsentimiento,
    rechazarConsentimiento,
    activarModoDemo,
    desactivarModoDemo,
  } = useUbicacion();

  return (
    <View style={styles.contenedor}>
      <Text style={styles.titulo}>Privacidad y ubicación</Text>

      {consentimiento === 'sin-decidir' && (
        <View style={styles.tarjeta}>
          <Text style={styles.texto}>
            Alerta Ciudadana puede usar tu ubicación en tiempo real, solo
            mientras la app está abierta, para avisarte cuando entras a una
            zona de riesgo alto. Tu ubicación no se guarda ni se comparte con
            terceros (Ley 1581 de 2012). Puedes desactivarla cuando quieras.
          </Text>
          <View style={styles.filaBotones}>
            <TouchableOpacity style={styles.botonAceptar} onPress={aceptarConsentimiento}>
              <Text style={styles.textoBotonAceptar}>Aceptar y activar ubicación</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.botonRechazar} onPress={rechazarConsentimiento}>
              <Text style={styles.textoBotonRechazar}>No, gracias</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {permiso === 'concedido' && (
        <View style={styles.tarjeta}>
          <Text style={styles.texto}>📍 Ubicación activa</Text>
          {posicion ? (
            <Text style={styles.textoSecund}>
              {posicion.lat.toFixed(4)}, {posicion.lon.toFixed(4)}
            </Text>
          ) : (
            <Text style={styles.textoSecund}>Esperando la primera lectura del GPS…</Text>
          )}
        </View>
      )}

      {permiso === 'denegado' && (
        <View style={styles.tarjeta}>
          <Text style={styles.textoError}>
            No se pudo activar tu ubicación en tiempo real. Aún puedes ver el
            mapa de riesgo por zona.
          </Text>
        </View>
      )}

      {error && permiso === 'concedido' && (
        <View style={styles.tarjeta}>
          <Text style={styles.textoError}>{error}</Text>
        </View>
      )}

      <View style={styles.tarjeta}>
        <View style={styles.filaSwitch}>
          <Text style={styles.texto}>Modo demo (ubicación simulada)</Text>
          <Switch
            value={modoDemo}
            onValueChange={(valor) => (valor ? activarModoDemo() : desactivarModoDemo())}
            trackColor={{ false: COLORES.borde, true: COLORES.acento }}
          />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  contenedor: { flex: 1, backgroundColor: COLORES.fondo, padding: 16 },
  titulo: { color: COLORES.textoPrinc, fontSize: 20, fontWeight: 'bold', marginBottom: 16 },
  tarjeta: {
    backgroundColor: COLORES.tarjeta,
    borderColor: COLORES.borde,
    borderWidth: 1,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  texto: { color: COLORES.textoPrinc, fontSize: 14, lineHeight: 20 },
  textoSecund: { color: COLORES.textoSecund, fontSize: 13, marginTop: 8 },
  textoError: { color: COLORES.riesgoAlto, fontSize: 14 },
  filaBotones: { flexDirection: 'row', marginTop: 16, gap: 12 },
  botonAceptar: {
    flex: 1,
    backgroundColor: COLORES.azul,
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  textoBotonAceptar: { color: COLORES.textoPrinc, fontWeight: 'bold', fontSize: 13 },
  botonRechazar: {
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    borderColor: COLORES.borde,
    borderWidth: 1,
    alignItems: 'center',
  },
  textoBotonRechazar: { color: COLORES.textoSecund, fontSize: 13 },
  filaSwitch: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
});
```

- [ ] **Step 3: Verificación estática — el bundle compila sin errores**

Run: `cd mobile && npx expo export --platform android --output-dir .expo-export-check`
Expected: termina con `Exported: .expo-export-check` (o similar mensaje de
éxito) y código de salida 0 — sin errores de sintaxis ni de imports. Borrar
la carpeta de salida después: `rm -rf .expo-export-check` (no se versiona).

- [ ] **Step 4: Correr toda la suite de jest (no debería haberse roto nada)**

Run: `cd mobile && npm test`
Expected: PASS — 21 tests

- [ ] **Step 5: Commit**

```bash
git add mobile/App.js mobile/src/screens/PerfilScreen.jsx
git commit -m "feat(mobile): aviso de privacidad opt-in + estado de ubicacion en Perfil (issue #39)"
```

---

## Task 5: Chip de posición real en `MapaScreen`

**Files:**
- Modify: `mobile/src/screens/MapaScreen.jsx`

**Interfaces:**
- Consumes: `useUbicacion()` (Task 3) → `{ posicion, modoDemo }`.

- [ ] **Step 1: Quitar el import y uso de `ZONA_ACTUAL`, agregar `useUbicacion`**

En `mobile/src/screens/MapaScreen.jsx`, reemplazar:

```js
import { COLORES } from '../config';
import { colorPorNivel, fetchZonas, USAR_MOCK } from '../services/zonasService';
```

por:

```js
import { COLORES } from '../config';
import { useUbicacion } from '../context/UbicacionContext';
import { colorPorNivel, fetchZonas, USAR_MOCK } from '../services/zonasService';
```

Y eliminar por completo estas dos líneas (ya no se usan):

```js
// Ubicación actual hardcodeada (el GPS real llega en #39).
const ZONA_ACTUAL = { nombre: 'Chapinero', nivel: 'MEDIO' };
```

- [ ] **Step 2: Leer `posicion`/`modoDemo` dentro del componente**

Dentro de `export default function MapaScreen({ navigation }) {`, justo
después de `const [zonas, setZonas] = useState([]);`, agregar:

```js
  const { posicion, modoDemo } = useUbicacion();
```

- [ ] **Step 3: Reemplazar el chip hardcodeado por el chip reactivo**

Reemplazar:

```jsx
      {/* Chip de ubicación (hardcodeado hasta #39) */}
      <View style={styles.chip}>
        <Text style={styles.chipTexto}>
          📍 {ZONA_ACTUAL.nombre} · Riesgo {ZONA_ACTUAL.nivel}
        </Text>
      </View>
```

por:

```jsx
      {/* Chip de posición: GPS real o modo demo (#39). Resolver la
          coordenada a zona/nivel de riesgo real es la Issue #40. */}
      <TouchableOpacity
        style={styles.chip}
        activeOpacity={posicion ? 1 : 0.7}
        onPress={() => !posicion && navigation?.navigate?.('Perfil')}
      >
        <Text style={styles.chipTexto}>
          {posicion
            ? `📍 ${posicion.lat.toFixed(4)}, ${posicion.lon.toFixed(4)} · ${
                modoDemo ? 'Modo demo' : 'GPS activo'
              }`
            : '📍 Ubicación desactivada · Actívala en Perfil'}
        </Text>
      </TouchableOpacity>
```

(`TouchableOpacity` ya está importado en este archivo desde `react-native`,
no hace falta agregar el import.)

- [ ] **Step 4: Verificación estática — el bundle compila sin errores**

Run: `cd mobile && npx expo export --platform android --output-dir .expo-export-check`
Expected: termina en éxito, código de salida 0. Borrar después:
`rm -rf .expo-export-check`.

- [ ] **Step 5: Correr toda la suite de jest (no debería haberse roto nada)**

Run: `cd mobile && npm test`
Expected: PASS — 21 tests

- [ ] **Step 6: Commit**

```bash
git add mobile/src/screens/MapaScreen.jsx
git commit -m "feat(mobile): chip de posicion real en MapaScreen (issue #39)"
```

---

## Task 6: Documentación + checklist de verificación manual en dispositivo

**Files:**
- Modify: `mobile/README.md`

**Interfaces:**
- Ninguna (solo documentación).

- [ ] **Step 1: Agregar sección de privacidad/ubicación y tests al README**

Agregar al final de `mobile/README.md` (después del contenido existente):

```markdown

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
```

- [ ] **Step 2: Commit**

```bash
git add mobile/README.md
git commit -m "docs(mobile): documenta privacidad/ubicacion y checklist manual (issue #39)"
```

---

## Fuera de alcance de este plan

Resolver la coordenada a localidad/nivel de riesgo real y disparar
notificaciones (Issue #40). La ruta de modo demo con varias coordenadas
cruzando a zona de riesgo alto (Issue #41). Persistencia del consentimiento
entre reinicios de la app (`AsyncStorage`). Tests de renderizado de
`PerfilScreen`/`MapaScreen` con `@testing-library/react-native` o del flujo
end-to-end del diálogo nativo de permisos (no simulable de forma
significativa — se cubre con el checklist manual del Task 6).
