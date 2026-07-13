/**
 * zonasCache.js
 *
 * Cachea el GeoJSON de GET /zonas-riesgo con refresco periódico.
 * Si la API cae, conserva el último valor conocido (no rompe la app).
 */

/**
 * @typedef {Object} ZonasCacheOptions
 * @property {string} [baseUrl]  
 * @property {number} [anio]
 * @property {string} [tipo]     
 * @property {number} [ttlMs]    
 * @property {typeof fetch} [fetchImpl]
 */

export class ZonasCache {
  /**
   * @param {ZonasCacheOptions} options
   */
  constructor(options = {}) {
    this.baseUrl = (options.baseUrl || "http://127.0.0.1:8000").replace(/\/$/, "");
    this.anio = options.anio ?? 2025;
    this.tipo = options.tipo ?? "HP";
    this.ttlMs = options.ttlMs ?? 5 * 60 * 1000;
    this.fetchImpl = options.fetchImpl || fetch.bind(globalThis);

    /** @type {GeoJSON.FeatureCollection|null} */
    this._geojson = null;
    /** @type {number} */
    this._fetchedAt = 0;
    /** @type {string|null} */
    this._lastError = null;
  }

  /** Último GeoJSON conocido (puede ser null si nunca hubo éxito). */
  get geojson() {
    return this._geojson;
  }

  get lastError() {
    return this._lastError;
  }

  get isStale() {
    if (!this._geojson) return true;
    return Date.now() - this._fetchedAt > this.ttlMs;
  }

  /**
   * Fuerza o refresca si el TTL venció.
   * Ante fallo de red: NO borra el cache previo.
   * @param {{ force?: boolean }} [opts]
   * @returns {Promise<GeoJSON.FeatureCollection|null>}
   */
  async refresh({ force = false } = {}) {
    if (!force && this._geojson && !this.isStale) {
      return this._geojson;
    }

    const url =
      `${this.baseUrl}/zonas-riesgo` +
      `?anio=${encodeURIComponent(this.anio)}` +
      `&tipo=${encodeURIComponent(this.tipo)}`;

    try {
      const res = await this.fetchImpl(url);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      if (!data || data.type !== "FeatureCollection" || !Array.isArray(data.features)) {
        throw new Error("Respuesta no es un FeatureCollection valido");
      }
      this._geojson = data;
      this._fetchedAt = Date.now();
      this._lastError = null;
      return this._geojson;
    } catch (err) {
      this._lastError = err instanceof Error ? err.message : String(err);
      // Tolerante a API caida: devolver ultimo valor conocido
      return this._geojson;
    }
  }
}

export default ZonasCache;
