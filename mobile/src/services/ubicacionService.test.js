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
    expect(typeof suscripcion.remove).toBe('function');
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
