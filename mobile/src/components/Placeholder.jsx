import { Text, View } from 'react-native';

import { COLORES } from '../config';

// Placeholder de pantalla mientras se implementan las issues #38–#42 / #49–#51.
export default function Placeholder({ nombre }) {
  return (
    <View
      style={{
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: COLORES.fondo,
      }}
    >
      <Text style={{ color: COLORES.textoPrinc, fontSize: 18 }}>
        {nombre} — próximamente
      </Text>
    </View>
  );
}
