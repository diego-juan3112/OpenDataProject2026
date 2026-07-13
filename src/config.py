"""
config.py — Configuración central del pipeline de datos de Alerta Ciudadana.

Única fuente de verdad para rutas, URLs de descarga verificadas, CRS y las
llaves de cruce. Todo script de ingesta importa de aquí; nada de rutas ni URLs
hardcodeadas dispersas por el código (Regla 4: reproducibilidad).

URLs verificadas contra la API CKAN de datosabiertos.bogota.gov.co el 2026-06-30.
Si una descarga falla, revisar primero si el resource_id cambió en el portal.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# --------------------------------------------------------------------------- #
# Rutas del proyecto
# --------------------------------------------------------------------------- #
# config.py vive en src/ → la raíz del repo es el padre.
ROOT = Path(__file__).resolve().parent.parent

# Carga variables de entorno desde .env (no versionado). Debe ir tras definir
# ROOT para apuntar al .env de la raíz del repo sin depender del CWD.
load_dotenv(ROOT / ".env")

DATA = ROOT / "data"
RAW = DATA / "01_raw"
INTERIM = DATA / "02_intermediate"
PROCESSED = DATA / "03_primary"
MODEL_OUTPUT = DATA / "04_model_output"

RAW_SIEDCO = RAW / "siedco"
RAW_NUSE = RAW / "nuse"
RAW_LOCALIDAD = RAW / "localidad"
RAW_DANE = RAW / "dane"

# Salidas clave (los dos entregables de la Semana 1)
DATASET_ANALITICO = PROCESSED / "dataset_analitico.parquet"
ZONAS_GEOJSON = PROCESSED / "zonas_bogota.geojson"

# Diccionarios de datos
DOCS_DICT = ROOT / "docs" / "data-dictionaries"

# --------------------------------------------------------------------------- #
# OpenRouteService — routing externo (feature Ruta Más Segura, Issues #45–#48)
# --------------------------------------------------------------------------- #
# Motor de routing (OSM) que calcula las rutas navegables entre dos puntos de
# Bogotá. El perfil (driving-car, foot-walking…) va en la URL: {BASE}/{perfil}/json.
ORS_BASE_URL = "https://api.openrouteservice.org/v2/directions"
# Token del plan gratuito de ORS. Se lee del entorno (.env, NUNCA en el repo).
ORS_API_KEY = os.getenv("ORS_API_KEY", "")


def ensure_dirs() -> None:
    """Crea el árbol de carpetas de datos si no existe. Idempotente."""
    for d in (RAW_SIEDCO, RAW_NUSE, RAW_LOCALIDAD, RAW_DANE, INTERIM, PROCESSED, MODEL_OUTPUT):
        d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Sistemas de coordenadas (Regla 2)
# --------------------------------------------------------------------------- #
# Las fuentes oficiales de Bogotá publican en MAGNA-SIRGAS / Bogotá D.C.
CRS_ORIGEN = "EPSG:4686"   # MAGNA-SIRGAS geográficas — como vienen SIEDCO y Localidad
CRS_WEB = "EPSG:4326"      # WGS84 — para exportar GeoJSON a la API / dashboard / móvil

# --------------------------------------------------------------------------- #
# Llaves de cruce (Regla 1: siempre por código numérico, nunca por texto libre)
# --------------------------------------------------------------------------- #
# Bogotá usa un código de localidad propio de 2 dígitos (01..20). NO es el
# DIVIPOLA nacional (Bogotá municipio = 11001); es la llave uniforme entre las
# tres fuentes de la SDSCJ. Se normaliza como string de 2 dígitos con cero a la
# izquierda para evitar el clásico "1" vs "01".
KEY_LOCALIDAD = "cod_localidad"   # nombre canónico tras la normalización
DANE_BOGOTA = "11001"             # código DIVIPOLA de Bogotá D.C. (para escalar a más municipios)

# --------------------------------------------------------------------------- #
# Ventana temporal del dataset analítico (decisión de arranque)
# --------------------------------------------------------------------------- #
# Años completos 2018–2025 para entrenar sin sesgo de año parcial.
# 2026-YTD (ene–may) se reserva como conjunto de validación "futuro" para la
# validación espacio-temporal del Integrante 2.
ANIO_MIN = 2018
ANIO_MAX = 2025

# --------------------------------------------------------------------------- #
# Fuentes de datos — URLs de descarga verificadas (CKAN datosabiertos.bogota.gov.co)
# --------------------------------------------------------------------------- #
# SIEDCO — "Delito de Alto Impacto. Bogotá D.C." — polígono por localidad.
#   Se usa el GeoJSON de años completos 2018–2025 (viene comprimido .zip).
SIEDCO_GEOJSON_URL = (
    "https://datosabiertos.bogota.gov.co/dataset/"
    "7b270013-42ca-436b-9c1e-3bcb7d280c6b/resource/"
    "fc846aa6-68a9-456a-bdd3-f0284e162bd4/download/dai_geojson.zip"
)
# GPKG equivalente (respaldo si el GeoJSON diera problemas de lectura).
SIEDCO_GPKG_URL = (
    "https://datosabiertos.bogota.gov.co/dataset/"
    "7b270013-42ca-436b-9c1e-3bcb7d280c6b/resource/"
    "b24e6cfa-ae5d-465c-8fe7-e494cd377897/download/dai_gpkg.zip"
)

# NUSE — "Incidentes Tramitados en el C4 (NUSE Línea 123)" — CSV AGREGADO por
#   localidad/UPZ × mes × tipo (NO es nivel-incidente con lat/lon; ver diccionario).
NUSE_CSV_URL = (
    "https://datosabiertos.bogota.gov.co/dataset/"
    "9bdf518e-b756-4865-983f-0521111fbcd1/resource/"
    "30d65a8b-d0ed-4e95-977e-0d7cc2ea89ef/download/"
    "llamadastramitadas-c4-bogota_numerounicodeseguridadyemergencias-nuse_linea-123-a-31mayo2026.csv"
)
NUSE_DICC_CAMPOS_URL = (
    "https://datosabiertos.bogota.gov.co/dataset/"
    "9bdf518e-b756-4865-983f-0521111fbcd1/resource/"
    "93eb31c6-be3b-43ed-a633-a47ed3c7c5e7/download/definicioncampos.csv"
)

# Localidad — geometría oficial de las 20 localidades de Bogotá.
#   loca.json viene en formato Esri JSON; el SHP (loca.zip) es más portable para
#   GeoPandas/pyogrio y trae .prj con el CRS.
LOCALIDAD_SHP_URL = (
    "https://datosabiertos.bogota.gov.co/dataset/"
    "856cb657-8ca3-4ee8-857f-37211173b1f8/resource/"
    "30916322-7509-4cb4-8241-6be2b5109248/download/loca.zip"
)
LOCALIDAD_GPKG_URL = (
    "https://datosabiertos.bogota.gov.co/dataset/"
    "856cb657-8ca3-4ee8-857f-37211173b1f8/resource/"
    "b6c3fbda-1281-4735-8063-260e75ad95f8/download/loca.gpkg"
)

# Encoding de las fuentes de texto de la SDSCJ (los CSV vienen en latin-1, no UTF-8).
ENCODING_SDSCJ = "latin-1"
SEP_SDSCJ = ";"

# --------------------------------------------------------------------------- #
# Contexto socioeconómico DANE / SDP por localidad (Issue #6)
# --------------------------------------------------------------------------- #
# Ambas fuentes son AGREGADAS a nivel localidad (cero microdatos personales).
#
# 1) Población proyectada por localidad, 2005–2035 (Observatorio SDP, base Censo
#    DANE 2018). CSV desagregado por sexo/edad/año; se agrega a total por
#    (localidad × año). Viene con CODIGO_LOCALIDAD numérico (0 = Bogotá total).
DANE_POBLACION_CSV_URL = (
    "https://datosabiertos.bogota.gov.co/dataset/"
    "85bf790d-84d1-4eda-bd6f-40af62e71d95/resource/"
    "37e58cb3-c870-4608-8c37-ce45db0eb7c1/download/"
    "osb_demografia-poblacion-localidad.csv"
)
# 2) Pobreza multidimensional: "Personas pobres por el IPM — Censo 2018" dentro
#    del XLSX "Hábitat en cifras en las localidades" (SDP). Es un CONTEO de
#    personas pobres por localidad (19 localidades; Sumapaz no está en la EM). El
#    ingest lo convierte a incidencia (personas_pobres / población 2018).
DANE_HABITAT_XLSX_URL = (
    "https://datosabiertos.bogota.gov.co/dataset/"
    "66617126-7606-4851-835f-c1ecfab65b8c/resource/"
    "bb1e5ef3-c191-476d-943d-b33406e5e45c/download/"
    "indicadores-calidad-de-vida-habitat-en-cifras-en-las-localidades.xlsx"
)
# Año base del IPM (Censo DANE 2018). Se usa para calcular la incidencia y como
# año de la variable estructural (se difunde a todos los años del dataset).
IPM_ANIO_BASE = 2018

# --------------------------------------------------------------------------- #
# Fuentes consumidas DIRECTAMENTE del API nativo de datos.gov.co (Socrata SoQL).
# --------------------------------------------------------------------------- #
# A diferencia de SIEDCO/NUSE (federados: el archivo lo sirve el portal de
# Bogotá), estos microdatos de la Policía Nacional se consultan y filtran vía el
# API oficial de datos.gov.co. Son a nivel MUNICIPIO (Bogotá = 11001000), no por
# localidad; su rol es triangular/validar las cifras de SIEDCO y aportar una
# señal de estacionalidad (mes) a nivel ciudad.
DATOSGOV_BASE = "https://www.datos.gov.co/resource"

# Registro de datasets tabulares de datos.gov.co a consumir por API. OJO: la
# columna y el valor del código de Bogotá varían entre datasets (unos usan
# 'cod_muni'=11001, otros 'codigo_dane'=11001000). Verificado 2026-06-30.
DATOSGOV_DATASETS = {
    "hurto_personas": {
        "id": "4rxi-8m8d",            # HURTO PERSONAS - Policía Nacional
        "filtro_col": "cod_muni",
        "filtro_val": "11001",
        "tipo_col": None,
    },
    "violencia_intrafamiliar": {
        "id": "vuyt-mqpw",            # Reporte Delito Violencia Intrafamiliar - Policía Nacional
        "filtro_col": "codigo_dane",
        "filtro_val": "11001000",
        "tipo_col": None,             # este dataset no discrimina subtipo
    },
}

# --------------------------------------------------------------------------- #
# Tipología de delitos de SIEDCO (verificada contra los alias oficiales del
# servicio ArcGIS de la SDSCJ el 2026-06-30). El GeoJSON viene en formato ANCHO:
# una columna por (tipo, año) con patrón  CM<PREFIJO><AA>CONT  (HCE se trunca a
# ...CON por el límite de 10 caracteres del nombre de campo tipo shapefile).
# El ingest despivotea usando este mapa como única fuente de verdad de labels.
# --------------------------------------------------------------------------- #
SIEDCO_TIPOS = {
    "H": "Homicidios",
    "LP": "Lesiones Personales",
    "HP": "Hurto Personas",
    "HR": "Hurto Residencias",
    "HA": "Hurto Automotores",
    "HB": "Hurto Bicicletas",
    "HC": "Hurto Comercio",
    "HCE": "Hurto Celulares",
    "HM": "Hurto Motocicletas",
    "DS": "Delitos Sexuales",
    "VI": "Violencia Intrafamiliar",
}

# Nombres de campo de la geometría/identidad en el GeoJSON de SIEDCO.
SIEDCO_COL_CODLOCAL = "CMIULOCAL"    # código de localidad (2 dígitos, string)
SIEDCO_COL_NOMLOCAL = "CMNOMLOCAL"   # nombre de localidad (texto — NO usar para cruzar)
