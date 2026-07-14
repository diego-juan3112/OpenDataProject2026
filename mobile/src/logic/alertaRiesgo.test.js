import { evaluarTransicion } from './alertaRiesgo';
import { riesgoDeCoordenada } from '../geofencing';
import { RUTA_DEMO } from '../services/ubicacionService';
import zonasMock from '../data/zonas_mock.json';

describe('evaluarTransicion — anti-rebote (#40)', () => {
  test('dispara al ENTRAR a alto desde otro nivel', () => {
    expect(evaluarTransicion('bajo', 'alto').debeNotificar).toBe(true);
    expect(evaluarTransicion('medio', 'alto').debeNotificar).toBe(true);
    expect(evaluarTransicion(null, 'alto').debeNotificar).toBe(true);
  });

  test('NO re-dispara mientras se permanece en alto', () => {
    expect(evaluarTransicion('alto', 'alto').debeNotificar).toBe(false);
  });

  test('no dispara al salir de alto ni entre niveles bajos', () => {
    expect(evaluarTransicion('alto', 'medio').debeNotificar).toBe(false);
    expect(evaluarTransicion('alto', 'bajo').debeNotificar).toBe(false);
    expect(evaluarTransicion('bajo', 'medio').debeNotificar).toBe(false);
  });

  test('se re-arma al salir y volver a entrar', () => {
    // alto -> medio (sale) -> alto (re-entra): solo el re-ingreso dispara
    expect(evaluarTransicion('alto', 'medio').debeNotificar).toBe(false);
    expect(evaluarTransicion('medio', 'alto').debeNotificar).toBe(true);
  });

  test('es case-insensitive', () => {
    expect(evaluarTransicion('BAJO', 'ALTO').debeNotificar).toBe(true);
    expect(evaluarTransicion('Alto', 'Alto').debeNotificar).toBe(false);
  });
});

describe('ruta demo (#41) — cruza a zona de riesgo alto', () => {
  const niveles = RUTA_DEMO.map(
    (p) => riesgoDeCoordenada(p.lat, p.lon, zonasMock).nivel_riesgo,
  );

  test('empieza en zona NO alta y termina en zona alta', () => {
    expect(niveles[0]).not.toBe('alto');
    expect(niveles[niveles.length - 1]).toBe('alto');
  });

  test('recorrer la ruta dispara exactamente una alerta', () => {
    let previo = null;
    let disparos = 0;
    for (const nivel of niveles) {
      if (evaluarTransicion(previo, nivel).debeNotificar) disparos += 1;
      previo = nivel;
    }
    expect(disparos).toBe(1);
  });
});
