import { NavigationContainer } from '@react-navigation/native';
import { StatusBar } from 'expo-status-bar';

import AppNavigator from './src/navigation/AppNavigator';

// Punto de entrada. La navegación (4 tabs) vive en src/navigation/AppNavigator.
// Las pantallas son placeholders; se implementan en las issues #38–#42 y #49–#51.
export default function App() {
  return (
    <NavigationContainer>
      <StatusBar style="light" />
      <AppNavigator />
    </NavigationContainer>
  );
}
