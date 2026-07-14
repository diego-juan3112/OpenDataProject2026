// alertaRiesgo.js
//
// Núcleo PURO de la alerta de riesgo (Issue #40): decide si hay que disparar la
// notificación local dada la transición de nivel de riesgo. Sin expo, sin React
// → 100% testeable. La regla anti-rebote vive aquí: solo se notifica en la
// TRANSICIÓN a "alto" (no mientras se permanece en la zona), y se re-arma al salir.

const NIVEL_ALTO = 'alto';

/**
 * @param {string|null} nivelPrevio  nivel de la lectura anterior ('bajo'|'medio'|'alto'|null)
 * @param {string|null} nivelActual  nivel de la lectura actual
 * @returns {{ debeNotificar: boolean }}
 */
export function evaluarTransicion(nivelPrevio, nivelActual) {
  const norm = (n) => (n == null ? null : String(n).toLowerCase());
  const previo = norm(nivelPrevio);
  const actual = norm(nivelActual);
  // Notificar solo al ENTRAR a "alto" desde un nivel distinto (o sin nivel).
  const debeNotificar = actual === NIVEL_ALTO && previo !== NIVEL_ALTO;
  return { debeNotificar };
}
