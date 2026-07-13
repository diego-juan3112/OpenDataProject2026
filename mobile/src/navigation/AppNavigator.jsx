import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';

import { COLORES } from '../config';
import MapaScreen from '../screens/MapaScreen';
import RutaSeguraScreen from '../screens/RutaSeguraScreen';
import AlertasScreen from '../screens/AlertasScreen';
import PerfilScreen from '../screens/PerfilScreen';

const Tab = createBottomTabNavigator();

// Navegación de 4 tabs (Mapa, Rutas, Alertas, Perfil). Se usan componentes
// nombrados (no funciones inline en `component=`) para evitar remount en cada
// render, el anti-patrón que advierte React Navigation.
export default function AppNavigator() {
  return (
    <Tab.Navigator
      screenOptions={{
        tabBarStyle: { backgroundColor: COLORES.tarjeta, borderTopColor: COLORES.borde },
        tabBarActiveTintColor: COLORES.acento,
        tabBarInactiveTintColor: COLORES.textoSecund,
        headerStyle: { backgroundColor: COLORES.fondo },
        headerTintColor: COLORES.textoPrinc,
      }}
    >
      <Tab.Screen name="Mapa" component={MapaScreen} />
      <Tab.Screen name="Rutas" component={RutaSeguraScreen} options={{ title: 'Ruta Segura' }} />
      <Tab.Screen name="Alertas" component={AlertasScreen} />
      <Tab.Screen name="Perfil" component={PerfilScreen} />
    </Tab.Navigator>
  );
}
