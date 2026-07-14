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
