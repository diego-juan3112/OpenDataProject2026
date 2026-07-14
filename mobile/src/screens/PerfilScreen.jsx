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
