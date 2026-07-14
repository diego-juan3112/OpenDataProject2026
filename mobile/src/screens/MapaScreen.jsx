import { useCallback, useEffect, useLayoutEffect, useState } from 'react';
import {
  ActivityIndicator,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import MapView, { Polygon } from 'react-native-maps';

import { COLORES } from '../config';
import { useUbicacion } from '../context/UbicacionContext';
import { colorPorNivel, fetchZonas, USAR_MOCK } from '../services/zonasService';

// Región inicial: Bogotá.
const REGION_BOGOTA = {
  latitude: 4.65,
  longitude: -74.08,
  latitudeDelta: 0.15,
  longitudeDelta: 0.15,
};


// Extrae los anillos exteriores de un feature (Polygon o MultiPolygon).
function anillosExteriores(feature) {
  const g = feature?.geometry;
  if (!g) return [];
  if (g.type === 'Polygon') return [g.coordinates[0]];
  if (g.type === 'MultiPolygon') return g.coordinates.map((poly) => poly[0]);
  return [];
}

export default function MapaScreen({ navigation }) {
  const [estado, setEstado] = useState('cargando'); // 'cargando' | 'error' | 'listo'
  const [zonas, setZonas] = useState([]);
  const { posicion, modoDemo } = useUbicacion();

  useLayoutEffect(() => {
    navigation?.setOptions?.({
      title: USAR_MOCK ? 'Alerta Ciudadana · Mock' : 'Alerta Ciudadana',
    });
  }, [navigation]);

  const cargar = useCallback(async () => {
    setEstado('cargando');
    try {
      const fc = await fetchZonas();
      setZonas(fc?.features ?? []);
      setEstado('listo');
    } catch (e) {
      console.error('Error cargando zonas:', e);
      setEstado('error');
    }
  }, []);

  useEffect(() => {
    cargar();
  }, [cargar]);

  if (estado === 'cargando') {
    return (
      <View style={styles.centro}>
        <ActivityIndicator size="large" color={COLORES.acento} />
        <Text style={styles.textoSecund}>Cargando mapa de riesgo…</Text>
      </View>
    );
  }

  if (estado === 'error') {
    return (
      <View style={styles.centro}>
        <Text style={styles.textoError}>No se pudo cargar el mapa.</Text>
        <TouchableOpacity style={styles.botonReintentar} onPress={cargar}>
          <Text style={styles.textoBoton}>Reintentar</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.contenedor}>
      <MapView style={styles.mapa} initialRegion={REGION_BOGOTA}>
        {zonas.flatMap((feature, i) =>
          anillosExteriores(feature).map((anillo, j) => (
            <Polygon
              key={`${feature.properties?.cod_localidad ?? i}-${j}`}
              coordinates={anillo.map(([lon, lat]) => ({ latitude: lat, longitude: lon }))}
              fillColor={`${colorPorNivel(feature.properties?.nivel_riesgo)}B3`}
              strokeColor="#21262D"
              strokeWidth={1}
            />
          )),
        )}
      </MapView>

      {/* Chip de posición: GPS real o modo demo (#39). Resolver la
          coordenada a zona/nivel de riesgo real es la Issue #40. */}
      <TouchableOpacity
        style={styles.chip}
        activeOpacity={posicion ? 1 : 0.7}
        onPress={() => !posicion && navigation?.navigate?.('Perfil')}
      >
        <Ionicons name="location-sharp" size={14} color={COLORES.textoPrinc} />
        <Text style={styles.chipTexto}>
          {posicion
            ? `${posicion.lat.toFixed(4)}, ${posicion.lon.toFixed(4)} · ${
                modoDemo ? 'Modo demo' : 'GPS activo'
              }`
            : 'Ubicación desactivada · Actívala en Perfil'}
        </Text>
      </TouchableOpacity>

      {/* FAB de reporte ciudadano (solo visual hasta #42) */}
      <TouchableOpacity style={styles.fab} activeOpacity={0.8}>
        <Ionicons name="megaphone" size={22} color={COLORES.textoPrinc} />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  contenedor: { flex: 1, backgroundColor: COLORES.fondo },
  mapa: { flex: 1 },
  centro: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORES.fondo,
    padding: 24,
  },
  textoSecund: { color: COLORES.textoSecund, marginTop: 12 },
  textoError: { color: COLORES.riesgoAlto, fontSize: 16, marginBottom: 16 },
  botonReintentar: {
    backgroundColor: COLORES.azul,
    paddingVertical: 10,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  textoBoton: { color: COLORES.textoPrinc, fontWeight: 'bold' },
  chip: {
    position: 'absolute',
    left: 16,
    bottom: 24,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: COLORES.tarjeta,
    borderColor: COLORES.borde,
    borderWidth: 1,
    borderRadius: 20,
    paddingVertical: 8,
    paddingHorizontal: 14,
  },
  chipTexto: { color: COLORES.textoPrinc, fontSize: 13, fontWeight: '600' },
  fab: {
    position: 'absolute',
    right: 16,
    bottom: 24,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: COLORES.denuncia,
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 4,
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
  },
});
