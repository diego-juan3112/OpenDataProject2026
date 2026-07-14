// src/services/zonasService.js
//
// Capa de datos que abstrae el origen del GeoJSON de zonas (mock vs API real).
// MapaScreen lo consume sin saber de dónde vienen los datos.
//
// El shape es el contrato de GET /zonas-riesgo (ver src/geofencing/CONTRATO.md):
// FeatureCollection cuyas features tienen properties.nivel_riesgo EN MINÚSCULAS
// ("bajo" | "medio" | "alto"). No hay un campo numérico `riesgo`; el continuo
// es `probabilidad_riesgo` (0–1).

import { ZonasCache } from '../geofencing';
import { API_BASE_URL } from '../config';

// Cambiar a false cuando la API esté disponible en la sesión (misma Wi-Fi).
export const USAR_MOCK = true;

// Cache real reutilizando el módulo de geofencing (#21): fetch + TTL + fallback
// offline. Se instancia una vez a nivel de módulo.
const cacheReal = new ZonasCache({ baseUrl: API_BASE_URL, anio: 2025, tipo: 'HP' });

export async function fetchZonas() {
  if (USAR_MOCK) {
    // Simular latencia de red para probar el estado de carga.
    await new Promise((r) => setTimeout(r, 800));
    return require('../data/zonas_mock.json');
  }
  // Producción: reutiliza ZonasCache (mismo GET /zonas-riesgo + fallback).
  const geojson = await cacheReal.refresh({ force: true });
  if (!geojson) {
    throw new Error(cacheReal.lastError || 'No se pudo cargar /zonas-riesgo');
  }
  return geojson;
}

// Color por nivel de riesgo. Case-insensitive para aceptar tanto el contrato
// real ("bajo"/"medio"/"alto") como valores en mayúsculas.
const COLORES_RIESGO = {
  bajo: '#17D05B',
  medio: '#F5A623',
  alto: '#E05252',
  desconocido: '#8B949E',
};

export function colorPorNivel(nivel) {
  const key = (nivel ?? '').toString().toLowerCase();
  return COLORES_RIESGO[key] ?? COLORES_RIESGO.desconocido;
}
