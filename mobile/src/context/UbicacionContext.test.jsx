import { create, act } from 'react-test-renderer';

import { UbicacionProvider, useUbicacion } from './UbicacionContext';
import * as ubicacionService from '../services/ubicacionService';

jest.mock('../services/ubicacionService', () => {
  const ruta = [
    { lat: 4.70, lon: -74.03, precision: null }, // inicio (zona segura)
    { lat: 4.63, lon: -74.15, precision: null }, // fin (zona alta)
  ];
  return {
    pedirPermiso: jest.fn(),
    suscribirPosicion: jest.fn(),
    RUTA_DEMO: ruta,
    COORDENADA_DEMO: ruta[0],
  };
});

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

  const raiz = montar();
  await act(async () => {
    await valorActual.aceptarConsentimiento();
  });

  act(() => {
    valorActual.activarModoDemo();
  });

  expect(remove).toHaveBeenCalledTimes(1);
  expect(valorActual.modoDemo).toBe(true);
  // La ruta demo (#41) arranca en su primer punto (zona segura).
  expect(valorActual.posicion).toEqual(ubicacionService.RUTA_DEMO[0]);

  act(() => raiz.unmount()); // limpia el intervalo de la ruta demo
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

test('desactivarModoDemo retoma el GPS real si el permiso ya estaba concedido', async () => {
  ubicacionService.pedirPermiso.mockResolvedValue('concedido');
  const removeReal = jest.fn();
  const posicionReal = { lat: 4.65, lon: -74.08, precision: 10 };
  ubicacionService.suscribirPosicion.mockImplementation((onUpdate) => {
    onUpdate(posicionReal);
    return Promise.resolve({ remove: removeReal });
  });

  montar();
  await act(async () => {
    await valorActual.aceptarConsentimiento();
  });
  expect(valorActual.posicion).toEqual(posicionReal);

  act(() => {
    valorActual.activarModoDemo();
  });
  expect(valorActual.modoDemo).toBe(true);
  expect(removeReal).toHaveBeenCalledTimes(1);

  await act(async () => {
    await valorActual.desactivarModoDemo();
  });

  expect(valorActual.modoDemo).toBe(false);
  expect(ubicacionService.suscribirPosicion).toHaveBeenCalledTimes(2);
  expect(valorActual.posicion).toEqual(posicionReal);
});

test('useUbicacion fuera del provider lanza un error claro', () => {
  function ConsumidorSuelto() {
    useUbicacion();
    return null;
  }
  const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
  // React 19 test-renderer solo relanza sincronicamente los errores de render
  // no atrapados cuando ocurren dentro de act(); sin act(), el error se
  // reporta via el hook global reportError en vez de propagarse a create().
  expect(() => act(() => create(<ConsumidorSuelto />))).toThrow(
    'useUbicacion debe usarse dentro de UbicacionProvider',
  );
  spy.mockRestore();
});
