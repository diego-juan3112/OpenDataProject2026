import { NavigationContainer } from '@react-navigation/native';
import { StatusBar } from 'expo-status-bar';

import AppNavigator from './src/navigation/AppNavigator';
import { UbicacionProvider } from './src/context/UbicacionContext';
import { AlertaRiesgoProvider } from './src/context/AlertaRiesgoContext';

// Punto de entrada. UbicacionProvider (#39) comparte permiso/posición entre
// tabs; AlertaRiesgoProvider (#40) observa esa posición y dispara la
// notificación local al entrar a zona de riesgo alto — montado sobre la
// navegación para que funcione en cualquier tab.
export default function App() {
  return (
    <UbicacionProvider>
      <AlertaRiesgoProvider>
        <NavigationContainer>
          <StatusBar style="light" />
          <AppNavigator />
        </NavigationContainer>
      </AlertaRiesgoProvider>
    </UbicacionProvider>
  );
}
