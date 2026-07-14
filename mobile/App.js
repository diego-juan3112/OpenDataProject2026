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
