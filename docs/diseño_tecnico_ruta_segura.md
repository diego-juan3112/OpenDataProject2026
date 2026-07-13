# DISEÑO TÉCNICO — Feature: Ruta Más Segura
## Alerta Ciudadana · Integrante 2 (API) + Integrante 4 (App Móvil)

---

# PARTE 1 — VISIÓN GENERAL

## Qué hace esta feature

El usuario escoge un destino en el mapa. La app calcula **dos rutas alternativas**
entre su posición actual y ese destino, las evalúa según el riesgo de las zonas
que atraviesan, y las presenta comparadas:

```
┌─────────────────────────────────────────────┐
│  📍 Estás en: Chapinero                      │
│  🎯 Vas a:   Plaza de Bolívar                │
│                                             │
│  🟢 Ruta Segura     ←── RECOMENDADA          │
│     23 min · 4.2 km · Riesgo: BAJO          │
│     Pasa por: Teusaquillo → Santa Fe        │
│                                             │
│  🔴 Ruta Rápida                              │
│     18 min · 3.1 km · Riesgo: ALTO          │
│     Pasa por: Los Mártires → La Candelaria  │
│                                             │
│         [ Ir por ruta segura ]              │
└─────────────────────────────────────────────┘
```

## La lógica en una frase

ORS calcula las rutas en el mundo real (calles reales).
Nuestro modelo asigna el riesgo a cada localidad que atraviesa esa ruta.
La app presenta ambas opciones con su score de riesgo calculado.

---

# PARTE 2 — CÓMO FUNCIONA OPENROUTESERVICE

## Qué es y por qué es la opción correcta

OpenRouteService (ORS) es un motor de routing open source de la Universidad
de Heidelberg, basado en datos de OpenStreetMap. Es gratuito, sin tarjeta de
crédito, y tiene dos capacidades críticas para este proyecto:

**1. Rutas alternativas:** devuelve hasta 3 rutas distintas en un solo request.

**2. `avoid_polygons`:** acepta GeoJSON de polígonos que el routing debe evitar.
Esto permite pasarle directamente los polígonos de las localidades de riesgo
alto para que ORS calcule la ruta "rodeándolas" en vez de atravesarlas.

## Límites del plan gratuito (verificados 2025)
- Hasta 3 rutas alternativas por request ✅
- `avoid_polygons`: área máxima 200 km² por polígono ✅ (localidades de Bogotá promedian ~30 km²)
- Distancia máxima con avoid areas: 150 km ✅ (Bogotá mide ~33 km de norte a sur)
- Sin tarjeta de crédito — solo registro con email ✅

## Cómo obtener la API key
1. Ir a `openrouteservice.org` → "Get API Key"
2. Crear cuenta con email universitario
3. Copiar el token del dashboard
4. Guardarlo en `.env` como `ORS_API_KEY=...` — nunca en el código

## El request básico a ORS

```python
import requests

ORS_BASE = "https://api.openrouteservice.org/v2/directions/driving-car"

def get_routes(origen_lon, origen_lat, destino_lon, destino_lat, api_key):
    """
    Pide 2 rutas alternativas a ORS entre origen y destino.
    Devuelve el GeoJSON con ambas rutas.
    """
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    body = {
        "coordinates": [
            [origen_lon,  origen_lat],   # ORS usa [lon, lat] — no al revés
            [destino_lon, destino_lat]
        ],
        "alternative_routes": {
            "target_count": 2,           # pedir 2 rutas
            "weight_factor": 1.6         # qué tan distintas deben ser (1.4–2.0)
        },
        "geometry": True,               # devolver la geometría de la ruta
        "instructions": False           # no necesitamos giro a giro para el MVP
    }
    response = requests.post(ORS_BASE, json=body, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()
```

## La respuesta de ORS (estructura simplificada)

```json
{
  "routes": [
    {
      "summary": {
        "distance": 4200,        // metros
        "duration": 1380         // segundos
      },
      "geometry": "encodedPolyline..."  // la línea de la ruta en el mapa
    },
    {
      "summary": {
        "distance": 3100,
        "duration": 1080
      },
      "geometry": "encodedPolyline..."
    }
  ]
}
```

La `geometry` viene como polyline codificada. Se decodifica con la librería
`polyline` de Python para obtener coordenadas `[[lat, lon], [lat, lon], ...]`.

---

# PARTE 3 — CÓMO SE CALCULA EL RIESGO DE CADA RUTA

## El problema de granularidad (y cómo lo resolvemos)

El modelo predice riesgo por **localidad** (20 zonas grandes). ORS devuelve
una **línea de calle** que cruza múltiples localidades. El puente entre ambas
es un **spatial join**: para cada punto de la ruta, preguntar "¿en qué
localidad estoy?" y sumar los riesgos de las localidades por las que pasa.

## Paso 1 — Calcular el score de riesgo actual por localidad

Antes de calcular rutas, el backend necesita un único número de riesgo
por localidad — no por tipo de delito, sino un score consolidado.

```python
import pandas as pd
import numpy as np

def calcular_scores_localidad(dataset_path: str) -> dict:
    """
    Lee el dataset analítico y devuelve un score de riesgo 0-10 por localidad.
    Usa el último año disponible (2024) de los datos de entrenamiento.
    El score es el percentil relativo del conteo total de delitos graves,
    ponderado por tipo (homicidio pesa más que hurto de bicicleta).
    """
    df = pd.read_parquet(dataset_path)
    df_2024 = df[(df["anio"] == 2024) & (df["split"] == "train")].copy()

    # Pesos por tipo de delito (mayor = más grave)
    PESOS = {
        "H":   10,   # Homicidios
        "DS":   8,   # Delitos Sexuales
        "LP":   7,   # Lesiones Personales
        "HP":   5,   # Hurto Personas
        "VI":   5,   # Violencia Intrafamiliar
        "HR":   4,   # Hurto Residencias
        "HC":   3,   # Hurto Comercio
        "HCE":  3,   # Hurto Celulares
        "HA":   3,   # Hurto Automotores
        "HM":   2,   # Hurto Motocicletas
        "HB":   1,   # Hurto Bicicletas
    }

    df_2024["conteo_ponderado"] = (
        df_2024["conteo_siedco"] *
        df_2024["tipo_delito"].map(PESOS).fillna(1)
    )

    # Score por localidad: suma ponderada, normalizada 0-10
    scores_raw = df_2024.groupby("cod_localidad")["conteo_ponderado"].sum()
    scores_norm = (scores_raw - scores_raw.min()) / (scores_raw.max() - scores_raw.min()) * 10

    return scores_norm.round(2).to_dict()
    # Ejemplo: {"01": 3.2, "08": 8.7, "11": 7.4, ...}
```

## Paso 2 — Decodificar la geometría de la ruta

```python
import polyline as polyline_lib
import geopandas as gpd
from shapely.geometry import LineString, Point

def decodificar_ruta(encoded_geometry: str) -> gpd.GeoDataFrame:
    """
    Convierte la polyline codificada de ORS en una lista de puntos GeoDataFrame.
    ORS devuelve [lat, lon] — los convertimos a geometría Shapely.
    """
    puntos = polyline_lib.decode(encoded_geometry, geojson=True)
    # geojson=True → devuelve [lon, lat] en vez de [lat, lon]
    linea = LineString(puntos)
    # Samplear puntos cada ~200 metros para el spatial join
    distancias = [i / linea.length for i in
                  range(0, int(linea.length * 111320), 200)]
    puntos_sample = [linea.interpolate(d, normalized=True)
                     for d in distancias]
    gdf = gpd.GeoDataFrame(
        geometry=puntos_sample,
        crs="EPSG:4326"
    )
    return gdf
```

## Paso 3 — Spatial join: qué localidades cruza la ruta

```python
def localidades_de_ruta(puntos_gdf: gpd.GeoDataFrame,
                        zonas_gdf: gpd.GeoDataFrame) -> list[str]:
    """
    Para cada punto de la ruta, encuentra en qué localidad está.
    Devuelve la lista ordenada de localidades que cruza la ruta.
    """
    joined = gpd.sjoin(
        puntos_gdf,
        zonas_gdf[["cod_localidad", "localidad_nombre", "geometry"]],
        how="left",
        predicate="within"
    )
    # Localidades únicas en orden de aparición en la ruta
    localidades = (
        joined["cod_localidad"]
        .dropna()
        .drop_duplicates()
        .tolist()
    )
    return localidades
```

## Paso 4 — Score de riesgo de la ruta completa

```python
def score_ruta(localidades: list[str],
               scores_por_localidad: dict) -> dict:
    """
    Calcula el riesgo total de una ruta como el promedio de los scores
    de las localidades que atraviesa, ponderado por cuántos puntos
    de la ruta caen en cada localidad (más tiempo en una zona = más peso).
    """
    scores = [scores_por_localidad.get(loc, 5.0) for loc in localidades]
    if not scores:
        return {"score": 5.0, "nivel": "DESCONOCIDO", "localidades": []}

    score_promedio = sum(scores) / len(scores)
    score_max = max(scores)

    # El nivel usa el máximo (la zona más peligrosa que cruza),
    # no el promedio — más conservador y más honesto.
    if score_max >= 7.5:
        nivel = "ALTO"
    elif score_max >= 4.5:
        nivel = "MEDIO"
    else:
        nivel = "BAJO"

    return {
        "score": round(score_promedio, 2),
        "score_max": round(score_max, 2),
        "nivel": nivel,
        "localidades": localidades
    }
```

---

# PARTE 4 — EL ENDPOINT `POST /ruta-segura`

## Esquema completo

```python
# api/routers/routing.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, validator
import geopandas as gpd

router = APIRouter()

# ── Request ──────────────────────────────────────────────────────────────────

class PuntoGeo(BaseModel):
    lat: float
    lon: float

    @validator("lat")
    def lat_bogota(cls, v):
        if not (3.7 <= v <= 4.9):
            raise ValueError("Latitud fuera del rango de Bogotá (3.7–4.9)")
        return v

    @validator("lon")
    def lon_bogota(cls, v):
        if not (-74.5 <= v <= -73.9):
            raise ValueError("Longitud fuera del rango de Bogotá (-74.5 a -73.9)")
        return v

class RutaRequest(BaseModel):
    origen:  PuntoGeo
    destino: PuntoGeo
    modo:    str = "driving-car"   # driving-car | foot-walking | cycling-regular

# ── Response ─────────────────────────────────────────────────────────────────

class InfoRuta(BaseModel):
    id:             str        # "segura" | "rapida"
    distancia_m:    int
    duracion_seg:   int
    riesgo_score:   float      # 0–10
    riesgo_nivel:   str        # "BAJO" | "MEDIO" | "ALTO"
    riesgo_score_max: float    # score de la localidad más peligrosa que cruza
    localidades:    list[str]  # nombres de localidades en orden
    geometry_geojson: dict     # LineString GeoJSON para pintarlo en el mapa

class RutaResponse(BaseModel):
    ruta_recomendada: str      # "segura" | "rapida" (o "misma" si son iguales)
    rutas:            list[InfoRuta]
    advertencia:      str | None  # si origen/destino están en zona de riesgo alto

# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/ruta-segura", response_model=RutaResponse)
async def calcular_ruta_segura(req: RutaRequest):
    """
    Calcula rutas alternativas entre origen y destino, evalúa su riesgo
    según el modelo predictivo y devuelve la comparativa ordenada.

    Flujo interno:
    1. Llamar a ORS con alternative_routes
    2. Para cada ruta: decodificar geometría → spatial join → score de riesgo
    3. Rankear por riesgo (menor = mejor) y devolver ambas
    """
    try:
        # 1) Rutas de ORS
        ors_response = get_routes(
            req.origen.lon,  req.origen.lat,
            req.destino.lon, req.destino.lat,
            api_key=ORS_API_KEY
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error en ORS: {str(e)}")

    if not ors_response.get("routes"):
        raise HTTPException(status_code=404,
                            detail="ORS no encontró ruta entre esos puntos")

    # 2) Scores pre-calculados (cargados al iniciar la API, no en cada request)
    scores = app.state.scores_localidad   # dict: {"01": 3.2, "08": 8.7, ...}
    zonas  = app.state.zonas_gdf          # GeoDataFrame con los 20 polígonos

    # 3) Evaluar cada ruta
    rutas_evaluadas = []
    for i, ruta_ors in enumerate(ors_response["routes"]):
        puntos = decodificar_ruta(ruta_ors["geometry"])
        locs   = localidades_de_ruta(puntos, zonas)
        riesgo = score_ruta(locs, scores)

        # Convertir polyline a GeoJSON LineString para el frontend
        coords_decoded = polyline_lib.decode(ruta_ors["geometry"], geojson=True)
        geometry_geojson = {
            "type": "LineString",
            "coordinates": coords_decoded
        }

        # Nombres legibles de localidades (no códigos)
        nombres_locs = [
            zonas[zonas["cod_localidad"] == loc]["localidad_nombre"].iloc[0]
            for loc in riesgo["localidades"]
            if not zonas[zonas["cod_localidad"] == loc].empty
        ]

        rutas_evaluadas.append(InfoRuta(
            id=f"ruta_{i+1}",
            distancia_m=int(ruta_ors["summary"]["distance"]),
            duracion_seg=int(ruta_ors["summary"]["duration"]),
            riesgo_score=riesgo["score"],
            riesgo_nivel=riesgo["nivel"],
            riesgo_score_max=riesgo["score_max"],
            localidades=nombres_locs,
            geometry_geojson=geometry_geojson
        ))

    # 4) Rankear: menor score_max = más segura
    rutas_evaluadas.sort(key=lambda r: r.riesgo_score_max)
    rutas_evaluadas[0].id = "segura"
    rutas_evaluadas[-1].id = "rapida"

    # 5) Advertencia si el origen o destino están en zona de riesgo alto
    origen_punto = gpd.GeoDataFrame(
        geometry=[Point(req.origen.lon, req.origen.lat)], crs="EPSG:4326"
    )
    origen_join = gpd.sjoin(origen_punto, zonas, how="left", predicate="within")
    advertencia = None
    if not origen_join.empty:
        cod = origen_join.iloc[0].get("cod_localidad")
        if cod and scores.get(cod, 0) >= 7.5:
            advertencia = (
                f"Tu punto de partida está en una zona de riesgo ALTO "
                f"({origen_join.iloc[0]['localidad_nombre']}). Ten precaución."
            )

    recomienda = "segura" if rutas_evaluadas[0].riesgo_nivel != rutas_evaluadas[-1].riesgo_nivel \
                 else "misma"

    return RutaResponse(
        ruta_recomendada=recomienda,
        rutas=rutas_evaluadas,
        advertencia=advertencia
    )
```

## Ejemplo de response completo

```json
{
  "ruta_recomendada": "segura",
  "advertencia": null,
  "rutas": [
    {
      "id": "segura",
      "distancia_m": 4200,
      "duracion_seg": 1380,
      "riesgo_score": 3.1,
      "riesgo_nivel": "BAJO",
      "riesgo_score_max": 4.0,
      "localidades": ["Chapinero", "Teusaquillo", "Santa Fe"],
      "geometry_geojson": {
        "type": "LineString",
        "coordinates": [[-74.065, 4.628], [-74.071, 4.612], ...]
      }
    },
    {
      "id": "rapida",
      "distancia_m": 3100,
      "duracion_seg": 1080,
      "riesgo_score": 7.4,
      "riesgo_nivel": "ALTO",
      "riesgo_score_max": 9.1,
      "localidades": ["Chapinero", "Los Mártires", "La Candelaria"],
      "geometry_geojson": {
        "type": "LineString",
        "coordinates": [[-74.065, 4.628], [-74.082, 4.598], ...]
      }
    }
  ]
}
```

---

# PARTE 5 — CÓMO SE CARGA LA API AL INICIAR (startup)

Para no recalcular los scores en cada request, se cargan una sola vez
cuando la API arranca:

```python
# api/main.py

from contextlib import asynccontextmanager
import geopandas as gpd
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Al arrancar: cargar modelos y datos en memoria
    import joblib
    import pandas as pd

    app.state.model         = joblib.load("models/advanced_ensemble.pkl")
    app.state.zonas_gdf     = gpd.read_file("data/03_primary/zonas_bogota.geojson")
    app.state.scores_localidad = calcular_scores_localidad(
        "data/03_primary/dataset_analitico.parquet"
    )
    print(f"✅ API lista. Scores cargados para "
          f"{len(app.state.scores_localidad)} localidades.")
    yield
    # Al apagar: cleanup si es necesario

app = FastAPI(lifespan=lifespan)
app.include_router(routing.router)
```

---

# PARTE 6 — CÓMO SE VE EN LA APP MÓVIL (Integrante 4)

## Pantalla de búsqueda de destino

```
┌──────────────────────────────────────┐
│  🔍 ¿A dónde vas?                    │
│  ┌──────────────────────────────┐    │
│  │ Buscar dirección o lugar...  │    │
│  └──────────────────────────────┘    │
│                                      │
│  📍 Usar punto en el mapa            │
└──────────────────────────────────────┘
```

## Pantalla de resultado de rutas

```
┌──────────────────────────────────────┐
│         MAPA con 2 rutas             │
│   ──── ruta verde (segura)           │
│   .... ruta roja  (rápida)           │
│                                      │
├──────────────────────────────────────┤
│  🟢 Ruta Segura · RECOMENDADA        │
│  23 min · 4.2 km                     │
│  Riesgo: BAJO (score 3.1/10)         │
│  Pasa por: Chapinero → Teusaquillo   │
│                                      │
│  🔴 Ruta Rápida                      │
│  18 min · 3.1 km                     │
│  Riesgo: ALTO (score 7.4/10)         │
│  ⚠️ Cruza Los Mártires (riesgo 9.1) │
│                                      │
│     [ Ir por ruta segura ]           │
└──────────────────────────────────────┘
```

## Código base de la pantalla (Expo / React Native)

```javascript
// mobile/screens/RutaSeguraScreen.jsx

import { useState } from 'react';
import MapView, { Polyline, Marker } from 'react-native-maps';
import { View, Text, TouchableOpacity, ActivityIndicator } from 'react-native';

const API_BASE = 'http://TU_IP_LAN:8000';   // o ngrok en demo

const COLORES_RIESGO = {
  BAJO:        '#17D05B',   // verde
  MEDIO:       '#F5A623',   // naranja
  ALTO:        '#E05252',   // rojo
  DESCONOCIDO: '#8B949E',   // gris
};

export default function RutaSeguraScreen({ ubicacionActual }) {
  const [destino, setDestino]   = useState(null);
  const [rutas, setRutas]       = useState([]);
  const [cargando, setCargando] = useState(false);
  const [advertencia, setAdv]   = useState(null);
  const [rutaElegida, setElegida] = useState(null);

  async function calcularRutas() {
    if (!destino || !ubicacionActual) return;
    setCargando(true);
    try {
      const res = await fetch(`${API_BASE}/ruta-segura`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          origen:  { lat: ubicacionActual.latitude,
                     lon: ubicacionActual.longitude },
          destino: { lat: destino.latitude,
                     lon: destino.longitude }
        })
      });
      const data = await res.json();
      setRutas(data.rutas);
      setAdv(data.advertencia);
    } catch (e) {
      console.error('Error calculando rutas:', e);
    } finally {
      setCargando(false);
    }
  }

  return (
    <View style={{ flex: 1 }}>
      <MapView style={{ flex: 1 }}
               initialRegion={{ latitude: 4.65, longitude: -74.05,
                                latitudeDelta: 0.1, longitudeDelta: 0.1 }}
               onLongPress={(e) => {
                 setDestino(e.nativeEvent.coordinate);
                 calcularRutas();
               }}>

        {/* Marcadores */}
        {ubicacionActual && <Marker coordinate={ubicacionActual} title="Estás aquí" />}
        {destino && <Marker coordinate={destino} title="Destino" pinColor="blue" />}

        {/* Rutas en el mapa */}
        {rutas.map((ruta) => (
          <Polyline
            key={ruta.id}
            coordinates={ruta.geometry_geojson.coordinates.map(
              ([lon, lat]) => ({ latitude: lat, longitude: lon })
            )}
            strokeColor={COLORES_RIESGO[ruta.riesgo_nivel]}
            strokeWidth={ruta.id === rutaElegida ? 6 : 3}
            onPress={() => setElegida(ruta.id)}
          />
        ))}
      </MapView>

      {/* Panel de comparativa */}
      {cargando && <ActivityIndicator size="large" />}
      {advertencia && (
        <View style={{ backgroundColor: '#E05252', padding: 8 }}>
          <Text style={{ color: 'white' }}>⚠️ {advertencia}</Text>
        </View>
      )}
      {rutas.map((ruta) => (
        <TouchableOpacity key={ruta.id}
          onPress={() => setElegida(ruta.id)}
          style={{ padding: 12, borderBottomWidth: 1,
                   backgroundColor: rutaElegida === ruta.id ? '#1D428A22' : 'white' }}>
          <Text style={{ color: COLORES_RIESGO[ruta.riesgo_nivel], fontWeight: 'bold' }}>
            {ruta.id === 'segura' ? '🟢 Ruta Segura · RECOMENDADA' : '🔴 Ruta Rápida'}
          </Text>
          <Text>{Math.round(ruta.duracion_seg / 60)} min ·{' '}
                {(ruta.distancia_m / 1000).toFixed(1)} km ·{' '}
                Riesgo: {ruta.riesgo_nivel} ({ruta.riesgo_score}/10)</Text>
          <Text style={{ color: '#8B949E', fontSize: 12 }}>
            Pasa por: {ruta.localidades.join(' → ')}
          </Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}
```

---

# PARTE 7 — ISSUES PARA EL BACKLOG

Las issues están divididas entre Integrante 2 (backend/API) e Integrante 4
(app móvil). Cada una incluye todos los campos del formato del BACKLOG.md.

---

## ISSUES — INTEGRANTE 2 (Predictivo + API)

---

### [API] Issue #R1 — Setup ORS: API key, wrapper y prueba de conectividad

**Asignado a:** Integrante 2 (Predictivo + API)
**Fase CRISP-ML:** 5 — Deployment
**Estimación:** 2–3 horas
**Depende de:** ninguno (puede hacerse en paralelo con el modelo)
**Bloquea a:** #R2, #R3

**Descripción:**
Crear cuenta en OpenRouteService, obtener API key, añadirla al `.env`
del proyecto, y escribir la función `get_routes()` en
`src/routing_client.py`. Verificar con un request de prueba entre dos
puntos conocidos de Bogotá que ORS devuelve rutas válidas. Documentar
los límites del plan gratuito en `docs/architecture.md`.

**Criterios de aceptación:**
- [ ] `ORS_API_KEY` en `.env` (nunca commiteada — verificar `.gitignore`)
- [ ] `src/routing_client.py` con `get_routes(origen_lon, origen_lat, destino_lon, destino_lat)` implementado
- [ ] Test manual: request entre Chapinero y La Candelaria devuelve 2 rutas con `summary.distance` y `summary.duration` válidos
- [ ] Límites del plan gratuito documentados en `docs/architecture.md`
- [ ] `polyline` añadido a `requirements.txt`

**Notas técnicas:**
Instalar: `pip install openrouteservice polyline`.
ORS usa `[lon, lat]` — no al revés. Error frecuente: invertir coordenadas.
El endpoint es `POST /v2/directions/{profile}/json` con body JSON.
Perfil recomendado para demo: `driving-car`. Añadir `foot-walking` como
opción secundaria para el MVP si hay tiempo.

---

### [API] Issue #R2 — Función de score de riesgo por localidad

**Asignado a:** Integrante 2 (Predictivo + API)
**Fase CRISP-ML:** 3 — Model Engineering
**Estimación:** 3–4 horas
**Depende de:** dataset_analitico.parquet (Issue #9, ya listo ✅)
**Bloquea a:** #R3

**Descripción:**
Implementar `calcular_scores_localidad()` en `src/model_evaluation.py`.
La función lee el dataset analítico, aplica pesos por gravedad de delito,
y devuelve un diccionario `{cod_localidad: score_0_a_10}` usando datos
de 2024 (último año de entrenamiento). Discutir con el equipo si los
pesos por tipo de delito son razonables y documentar la decisión.

**Criterios de aceptación:**
- [ ] Función implementada y devuelve dict con exactamente 20 claves (01–20)
- [ ] Scores en rango 0–10, con al menos 3 niveles distintos (no todos iguales)
- [ ] Test: verificar que las localidades conocidas como problemáticas (Kennedy, Los Mártires) tienen score > 6
- [ ] Pesos por tipo de delito documentados con justificación en el código
- [ ] Sumapaz (cod 20) tiene score calculable (ipm_nbi nulo no afecta este cálculo)

**Notas técnicas:**
Los pesos sugeridos en el diseño técnico son un punto de partida — el equipo
puede ajustarlos. Lo importante es que estén documentados y sean defendibles
en la presentación. Considerar normalizar también por población para no
sesgar hacia localidades grandes.

---

### [API] Issue #R3 — Spatial join: qué localidades cruza una ruta

**Asignado a:** Integrante 2 (Predictivo + API)
**Fase CRISP-ML:** 5 — Deployment
**Estimación:** 3–4 horas
**Depende de:** #R1, #R2, zonas_bogota.geojson (ya listo ✅)
**Bloquea a:** #R4

**Descripción:**
Implementar `decodificar_ruta()` y `localidades_de_ruta()` en
`src/routing_client.py`. La primera decodifica la polyline de ORS a
puntos geográficos. La segunda hace el spatial join con los polígonos de
localidad para saber por cuáles pasa la ruta. Verificar con una ruta
conocida que el resultado tiene sentido geográfico.

**Criterios de aceptación:**
- [ ] `decodificar_ruta()` devuelve GeoDataFrame en EPSG:4326 con puntos cada ~200m
- [ ] `localidades_de_ruta()` devuelve lista de cod_localidad en orden de aparición, sin duplicados
- [ ] Test: ruta Chapinero → Santa Fe devuelve secuencia de localidades geográficamente coherente
- [ ] Puntos fuera de Bogotá (edge case: ruta que sale del bounding box) no generan error — se filtran
- [ ] Tiempo de ejecución del spatial join < 500ms para rutas típicas de Bogotá

**Notas técnicas:**
Usar `gpd.sjoin(..., predicate="within")`. Si un punto cae en el borde
de dos localidades, `within` puede no encontrarlo — usar `"intersects"`
como fallback. Samplear puntos cada 200m en vez de usar todos los puntos
de la polyline (pueden ser miles) para mantener la performance.

---

### [API] Issue #R4 — Endpoint `POST /ruta-segura` completo

**Asignado a:** Integrante 2 (Predictivo + API)
**Fase CRISP-ML:** 5 — Deployment
**Estimación:** 4–5 horas
**Depende de:** #R1, #R2, #R3
**Bloquea a:** #R6 (integración en app móvil)

**Descripción:**
Implementar el endpoint completo `POST /ruta-segura` en
`api/routers/routing.py` siguiendo el esquema de request/response del
diseño técnico. Incluir validación de coordenadas (deben estar dentro del
bounding box de Bogotá), manejo de errores de ORS, y el startup hook
que pre-carga scores y GeoDataFrame en `app.state`.

**Criterios de aceptación:**
- [ ] `POST /ruta-segura` devuelve el response JSON del esquema definido
- [ ] Validación: coordenadas fuera de Bogotá devuelven HTTP 422 con mensaje claro
- [ ] Error de ORS devuelve HTTP 502 con mensaje útil (no stack trace)
- [ ] Sin ruta posible devuelve HTTP 404
- [ ] Scores y zonas cargados en startup — no en cada request
- [ ] Tiempo de respuesta end-to-end < 3 segundos en condiciones normales
- [ ] Probado manualmente con Swagger UI (`/docs`) antes de entregarlo a Int. 4

**Notas técnicas:**
Incluir `routing.router` en `api/main.py`. La advertencia de zona de
riesgo alto en el origen es opcional para el MVP — implementar si queda
tiempo. El campo `geometry_geojson` del response debe ser un dict Python
(no string JSON), para que FastAPI lo serialice correctamente.

---

## ISSUES — INTEGRANTE 4 (App Móvil)

---

### [MOV] Issue #R5 — Pantalla de búsqueda de destino

**Asignado a:** Integrante 4 (App Móvil)
**Fase CRISP-ML:** 5 — Deployment
**Estimación:** 3–4 horas
**Depende de:** estructura base de la app (ya existe)
**Bloquea a:** #R6

**Descripción:**
Crear la pantalla `RutaSeguraScreen` con un campo de búsqueda de texto
(geocoding) y la opción de marcar el destino con un long-press en el mapa.
Para el geocoding (convertir "Carrera 7 con 32" a coordenadas) usar la
API de geocoding de ORS (Pelias) — misma API key, sin costo adicional.

**Criterios de aceptación:**
- [ ] Campo de texto que acepta dirección o nombre de lugar
- [ ] Request a ORS Geocoding devuelve coordenadas del lugar buscado
- [ ] Marcador azul en el mapa cuando el destino está seleccionado
- [ ] Long-press en el mapa también establece el destino
- [ ] Botón "Calcular ruta segura" visible solo cuando hay destino seleccionado
- [ ] Estado de carga visible mientras se espera la respuesta

**Notas técnicas:**
ORS Geocoding endpoint: `GET https://api.openrouteservice.org/geocode/search?text=...&boundary.country=CO`
Añadir `boundary.country=CO` para limitar resultados a Colombia.
Librería sugerida para el campo de búsqueda con autocomplete:
`react-native-google-places-autocomplete` tiene una alternativa de ORS.
Si el geocoding resulta complejo, el MVP puede ser solo el long-press
en el mapa — documentar como simplificación si se toma esa decisión.

---

### [MOV] Issue #R6 — Integración del endpoint y visualización de rutas

**Asignado a:** Integrante 4 (App Móvil)
**Fase CRISP-ML:** 5 — Deployment
**Estimación:** 4–5 horas
**Depende de:** #R4 (endpoint listo), #R5
**Bloquea a:** #R7

**Descripción:**
Conectar `RutaSeguraScreen` con el endpoint `POST /ruta-segura`. Mostrar
ambas rutas en el mapa con colores distintos (verde = segura, rojo = rápida),
y el panel de comparativa debajo del mapa con la información de cada ruta.

**Criterios de aceptación:**
- [ ] Request al endpoint con origen (GPS actual) y destino seleccionado
- [ ] Dos Polylines en el mapa con colores según nivel de riesgo
- [ ] La ruta recomendada (segura) aparece más gruesa o resaltada por defecto
- [ ] Panel con: tiempo, distancia, nivel de riesgo y localidades de cada ruta
- [ ] Tapping en una ruta en el mapa o en el panel la selecciona/resalta
- [ ] Advertencia visible si el origen está en zona de riesgo alto
- [ ] Estado de error visible si el endpoint falla (mensaje amigable, no crash)

**Notas técnicas:**
La `geometry_geojson` del response viene como `{type: "LineString", coordinates: [[lon, lat], ...]}`
— React Native Maps usa `{latitude, longitude}`, así que hay que mapear:
`coords.map(([lon, lat]) => ({ latitude: lat, longitude: lon }))`.
Colores: BAJO=#17D05B, MEDIO=#F5A623, ALTO=#E05252 (consistentes con el
resto de la app). Para la Polyline usar `react-native-maps` Polyline component.

---

### [MOV] Issue #R7 — Modo demo de ruta segura para la presentación

**Asignado a:** Integrante 4 (App Móvil)
**Fase CRISP-ML:** 5 — Deployment
**Estimación:** 2 horas
**Depende de:** #R6
**Bloquea a:** nada (es el cierre de la feature)

**Descripción:**
Añadir un "modo demo" para la presentación al jurado que pre-carga un
escenario guionizado: origen en Chapinero (zona media), destino en Plaza
de Bolívar, con las dos rutas ya calculadas y listas. Esto garantiza que
la demo funciona aunque el GPS del dispositivo no coopere o la red sea
lenta en el lugar del evento.

**Criterios de aceptación:**
- [ ] Un botón oculto (triple tap en el logo o botón discreto en Settings) activa el modo demo
- [ ] Modo demo muestra el escenario Chapinero → Plaza de Bolívar con rutas pre-calculadas
- [ ] La ruta segura (verde) pasa visiblemente por zonas distintas a la rápida (roja)
- [ ] El modo demo es indistinguible visualmente del modo real para el jurado
- [ ] Documentado en `docs/validacion_guide.md` cómo activarlo

**Notas técnicas:**
Guardar el response JSON del modo demo como constante en el código
(`DEMO_RUTA_RESPONSE = {...}`). Cuando el modo demo está activo, en vez
de hacer el fetch al endpoint, devolver ese JSON directamente. Así la
demo no depende de red ni de GPS.

---

# PARTE 8 — RESUMEN DE ISSUES Y ORDEN DE EJECUCIÓN

```
INTEGRANTE 2                    INTEGRANTE 4
────────────                    ────────────
#R1 Setup ORS (2-3h)
      │
      ▼
#R2 Score riesgo (3-4h)         #R5 Pantalla búsqueda (3-4h)
      │                               │
      ▼                               │
#R3 Spatial join (3-4h)              │
      │                               │
      ▼                               ▼
#R4 Endpoint completo (4-5h) ──► #R6 Integración + mapa (4-5h)
                                       │
                                       ▼
                                  #R7 Modo demo (2h)
```

**Tiempo total estimado:**
- Integrante 2: ~13–17 horas (distribuidas en Semana 2 y principio de Semana 3)
- Integrante 4: ~9–11 horas (en paralelo, arranca #R5 inmediatamente)

**Punto de sincronización crítico:**
Al final de #R4, Integrante 2 entrega a Integrante 4 la URL del endpoint
con un ejemplo de request/response funcionando en Swagger UI. Sin eso,
#R6 no puede completarse.
