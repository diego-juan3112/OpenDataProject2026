/**
 * riesgoDeCoordenada.js
 *
 * Dada una coordenada GPS y el GeoJSON de GET /zonas-riesgo, determina
 * en qué localidad cae (point-in-polygon) y su nivel de riesgo.
 *
 */

/**
 * @typedef {Object} RiesgoZona
 * @property {string|null} cod_localidad
 * @property {string|null} localidad_nombre
 * @property {'bajo'|'medio'|'alto'|null} nivel_riesgo
 * @property {number|null} probabilidad_riesgo
 * @property {number|null} cluster
 * @property {string|null} nombre_perfil
 * @property {boolean} fueraDeBogota
 */

/**
 * Ray-casting: ¿el punto (lon, lat) está dentro del anillo [ [lon,lat], ... ]?
 * @param {number} lon
 * @param {number} lat
 * @param {number[][]} ring
 */
function puntoEnAnillo(lon, lat, ring) {
  let dentro = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
    const intersect =
      yi > lat !== yj > lat &&
      lon < ((xj - xi) * (lat - yi)) / (yj - yi + Number.EPSILON) + xi;
    if (intersect) dentro = !dentro;
  }
  return dentro;
}

/**
 * @param {number} lon
 * @param {number} lat
 * @param {GeoJSON.Geometry} geometry
 */
function puntoEnGeometria(lon, lat, geometry) {
  if (!geometry) return false;
  if (geometry.type === "Polygon") {
    const [exterior, ...agujeros] = geometry.coordinates;
    if (!puntoEnAnillo(lon, lat, exterior)) return false;
    for (const agujero of agujeros) {
      if (puntoEnAnillo(lon, lat, agujero)) return false;
    }
    return true;
  }
  if (geometry.type === "MultiPolygon") {
    return geometry.coordinates.some((poly) => {
      const [exterior, ...agujeros] = poly;
      if (!puntoEnAnillo(lon, lat, exterior)) return false;
      for (const agujero of agujeros) {
        if (puntoEnAnillo(lon, lat, agujero)) return false;
      }
      return true;
    });
  }
  return false;
}

/**
 * Resuelve zona + riesgo para una coordenada GPS.
 *
 * Convención: lat, lon en WGS84 (como expo-location).
 * GeoJSON de la API usa [lon, lat] internamente — esta función lo traduce.
 *
 * @param {number} lat
 * @param {number} lon
 * @param {GeoJSON.FeatureCollection|null|undefined} geojson
 * @returns {RiesgoZona}
 */
export function riesgoDeCoordenada(lat, lon, geojson) {
  const vacio = {
    cod_localidad: null,
    localidad_nombre: null,
    nivel_riesgo: null,
    probabilidad_riesgo: null,
    cluster: null,
    nombre_perfil: null,
    fueraDeBogota: true,
  };

  if (
    typeof lat !== "number" ||
    typeof lon !== "number" ||
    Number.isNaN(lat) ||
    Number.isNaN(lon) ||
    !geojson ||
    !Array.isArray(geojson.features)
  ) {
    return vacio;
  }

  for (const feature of geojson.features) {
    if (puntoEnGeometria(lon, lat, feature.geometry)) {
      const p = feature.properties || {};
      return {
        cod_localidad: p.cod_localidad ?? null,
        localidad_nombre: p.localidad_nombre ?? null,
        nivel_riesgo: p.nivel_riesgo ?? null,
        probabilidad_riesgo:
          typeof p.probabilidad_riesgo === "number" ? p.probabilidad_riesgo : null,
        cluster: typeof p.cluster === "number" ? p.cluster : null,
        nombre_perfil: p.nombre_perfil ?? null,
        fueraDeBogota: false,
      };
    }
  }

  return vacio;
}

export default riesgoDeCoordenada;
