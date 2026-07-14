import { StyleSheet, Text, View, FlatList } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { COLORES } from '../config';
import { colorPorNivel } from '../services/zonasService';
import { useAlertaRiesgo } from '../context/AlertaRiesgoContext';
import { useUbicacion } from '../context/UbicacionContext';

// Alertas de zona de riesgo alto (Issue #40): estado del permiso de
// notificaciones, zona/nivel actual e historial de alertas disparadas.
export default function AlertasScreen() {
  const { permisoNotif, zonaActual, nivelActual, historial, zonasCargadas } = useAlertaRiesgo();
  const { posicion, permiso } = useUbicacion();

  const hora = (d) =>
    new Date(d).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  return (
    <View style={styles.contenedor}>
      <Text style={styles.titulo}>Alertas de riesgo</Text>

      {/* Estado del permiso de notificaciones */}
      <View style={styles.tarjeta}>
        <View style={styles.fila}>
          <Ionicons
            name={permisoNotif === 'concedido' ? 'notifications' : 'notifications-off'}
            size={16}
            color={permisoNotif === 'concedido' ? COLORES.riesgoBajo : COLORES.textoSecund}
          />
          <Text style={styles.texto}>
            Notificaciones: {permisoNotif === 'concedido' ? 'activas' : 'sin permiso'}
          </Text>
        </View>
        {permisoNotif !== 'concedido' && (
          <Text style={styles.textoSecund}>
            Concede el permiso de notificaciones para recibir el aviso al entrar a una zona de riesgo alto.
          </Text>
        )}
      </View>

      {/* Zona / nivel actual */}
      <View style={styles.tarjeta}>
        <Text style={styles.subtitulo}>Tu zona ahora</Text>
        {!posicion ? (
          <Text style={styles.textoSecund}>
            Ubicación desactivada. Actívala (o usa el modo demo) en la tab Perfil.
          </Text>
        ) : !zonasCargadas ? (
          <Text style={styles.textoSecund}>Cargando zonas de riesgo…</Text>
        ) : zonaActual && !zonaActual.fueraDeBogota ? (
          <View style={styles.fila}>
            <View style={[styles.punto, { backgroundColor: colorPorNivel(nivelActual) }]} />
            <Text style={styles.texto}>
              {zonaActual.localidad_nombre} · Riesgo {(nivelActual ?? '—').toUpperCase()}
            </Text>
          </View>
        ) : (
          <Text style={styles.textoSecund}>Estás fuera de las localidades de Bogotá.</Text>
        )}
      </View>

      {/* Historial de alertas disparadas */}
      <Text style={styles.subtitulo}>Historial de alertas</Text>
      {historial.length === 0 ? (
        <Text style={styles.textoSecund}>
          Aún no se ha disparado ninguna alerta. Entra (o simula con el modo demo) a una zona de riesgo alto.
        </Text>
      ) : (
        <FlatList
          data={historial}
          keyExtractor={(item, i) => `${item.hora}-${i}`}
          renderItem={({ item }) => (
            <View style={styles.itemAlerta}>
              <Ionicons name="warning" size={16} color={COLORES.riesgoAlto} />
              <Text style={styles.texto}>
                {item.nombre} · <Text style={styles.textoSecund}>{hora(item.hora)}</Text>
              </Text>
            </View>
          )}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  contenedor: { flex: 1, backgroundColor: COLORES.fondo, padding: 16 },
  titulo: { color: COLORES.textoPrinc, fontSize: 20, fontWeight: 'bold', marginBottom: 16 },
  subtitulo: { color: COLORES.textoPrinc, fontSize: 15, fontWeight: '600', marginBottom: 8, marginTop: 4 },
  tarjeta: {
    backgroundColor: COLORES.tarjeta,
    borderColor: COLORES.borde,
    borderWidth: 1,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  fila: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  texto: { color: COLORES.textoPrinc, fontSize: 14 },
  textoSecund: { color: COLORES.textoSecund, fontSize: 13, marginTop: 6 },
  punto: { width: 12, height: 12, borderRadius: 6 },
  itemAlerta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 10,
    borderBottomColor: COLORES.borde,
    borderBottomWidth: 1,
  },
});
