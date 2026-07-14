// src/config.js
// URL de la API backend. Se lee de la variable de entorno EXPO_PUBLIC_API_BASE_URL
// (definida en mobile/.env, NO versionado — cada quien pone su IP de LAN o túnel).
// Fallback a localhost solo para que el bundle no rompa; desde un teléfono físico
// hay que apuntar a la IP de LAN del PC (ver mobile/.env.example).
export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Paleta de colores del sistema de diseño (compartida con el backend).
export const COLORES = {
  fondo:        "#0D1117",
  tarjeta:      "#161B22",
  borde:        "#21262D",
  riesgoBajo:   "#17D05B",
  riesgoMedio:  "#F5A623",
  riesgoAlto:   "#E05252",
  acento:       "#C89B3C",
  azul:         "#1D428A",
  textoPrinc:   "#E6EDF3",
  textoSecund:  "#8B949E",
  denuncia:     "#A78BFA",
};
