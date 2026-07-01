# Estado del proyecto — Alerta Ciudadana

**Fecha de corte:** 2026-07-01 · **Frente:** Datos (Integrante 1) · **Semana:** 1

> **En una frase:** ya tenemos las **4 fuentes de datos abiertos descargadas,
> limpias y verificadas**, listas para armar el archivo único que alimenta al
> resto del equipo (modelos, API, dashboard y app móvil).

---

## 1. ¿Qué es este proyecto? (recordatorio de 20 segundos)

**Alerta Ciudadana** convierte los datos oficiales de criminalidad de **Bogotá**
en una **alerta útil**: estima qué tan riesgosa es cada zona de la ciudad y avisa
al ciudadano cuando entra a una zona de riesgo alto (vía una app móvil y un
dashboard). Todo se construye sobre **datos abiertos oficiales** (nada inventado).

---

## 2. ¿En qué punto vamos? (semáforo)

| Tarea | Qué es | Estado |
|---|---|---|
| #1 Validar fuentes | Confirmar que los datos existen y sirven | ✅ Hecho |
| #2 Preparar el repositorio | Carpetas, dependencias, reglas | ✅ Hecho |
| #3 Ingesta SIEDCO | Delitos por localidad | ✅ Hecho |
| #4 Ingesta NUSE | Llamadas a la Línea 123 | ✅ Hecho |
| #5 Geometría de localidades | Los "mapas" de las 20 zonas | ✅ Hecho |
| + API datos.gov.co | Consumo directo del portal nacional | ✅ Hecho |
| #6 Contexto DANE | Población, pobreza por zona | ⏳ Sigue |
| #7 Limpieza final | Unificar reglas de calidad | ⏳ Sigue |
| #8 Cruce de fuentes | Unir todo por código de zona | ⏳ Sigue |
| **#9 Dataset analítico** 🎯 | **El archivo final que todos usan** | ⏳ Sigue |

**Traducción:** de 12 tareas del frente de datos, **llevamos 5 completas + 1 extra**.
Falta el tramo de unir todo en un solo archivo (#6 → #9), que es la meta de la
Semana 1.

---

## 3. ¿Qué logramos, exactamente? (con números reales)

Descargamos y procesamos **4 fuentes oficiales**. Esto es lo que hay en cada una:

### 📊 SIEDCO — Delitos de alto impacto (la fuente principal)
- **Qué trae:** cuántos delitos hubo en cada una de las **20 localidades** de
  Bogotá, por **11 tipos de delito** (homicidio, hurto a personas, hurto de celular,
  violencia intrafamiliar, etc.), **cada año de 2018 a 2025**.
- **Resultado:** una tabla limpia de **1.760 filas** (20 localidades × 11 tipos ×
  8 años) que suma **2.135.884 casos** en total.
- **Ejemplo real:** el delito más frecuente es el hurto a personas en las
  localidades grandes (Suba tuvo 17.656 hurtos a personas en 2023).

### 📞 NUSE — Llamadas a la Línea 123 (señal complementaria)
- **Qué trae:** cuántas **llamadas de emergencia** entraron por localidad y UPZ
  (una subdivisión más pequeña que la localidad), por mes y tipo.
- **Resultado:** **763.074 filas** (2018–2025) que suman **20.996.584 llamadas**.
- **Ejemplo real:** las llamadas más comunes son por RIÑA (3,5 millones), RUIDO
  (2,2 millones) y ACCIDENTE DE TRÁNSITO (1,4 millones).

### 🗺️ Geometría de localidades (los polígonos del mapa)
- **Qué trae:** la forma geográfica de las **20 localidades** para poder pintarlas
  en el mapa.
- **Resultado:** un archivo de mapa (`localidades.geojson`) con las 20 zonas, en
  el sistema de coordenadas que usa la web.

### 🏛️ Microdatos de la Policía Nacional (desde el API de datos.gov.co)
- **Qué trae:** hurto a personas y violencia intrafamiliar de Bogotá, traídos
  **directamente del API oficial de datos.gov.co**.
- **Resultado:** **8.188 registros de hurto** + **39.861 de violencia
  intrafamiliar** consultados por el API.
- **Para qué sirve:** para **validar** que las cifras de SIEDCO son correctas
  (ver punto 6).

---

## 4. ¿Cómo lo conseguimos? (el método, sin tecnicismos)

1. **No creímos en las descripciones: fuimos a ver el dato real.** En vez de asumir
   lo que el portal decía, descargamos una muestra de cada fuente y miramos columna
   por columna qué había de verdad. Ahí descubrimos cosas que cambiaron el plan
   (ver punto 5).
2. **Todo es reproducible y automático.** Cada fuente se baja y se procesa con un
   script que se puede volver a correr desde cero, sin abrir Excel ni tocar nada a
   mano. Si mañana el dato se actualiza, corremos el script y listo.
3. **Verificamos cada paso antes de pasar al siguiente.** Después de cada ingesta
   revisamos que los números tuvieran sentido (¿20 localidades?, ¿los totales son
   creíbles?) antes de continuar.
4. **Documentamos los problemas, no los escondimos.** Cada rareza del dato quedó
   escrita en un "diccionario de datos" como parte del rigor técnico.

---

## 5. ¿Por qué se hizo así? (3 decisiones importantes)

Al mirar los datos reales encontramos que **la realidad no cuadraba con el plan
original**. Tomamos 3 decisiones (cada una consultada y aprobada):

### Decisión 1 — NUSE no son "puntos en el mapa", es densidad por zona
- **El plan decía:** usar NUSE como puntos exactos en tiempo real.
- **La realidad:** NUSE viene **agrupado por zona y mes**, no trae la ubicación
  exacta de cada incidente.
- **Qué hicimos:** lo usamos como una **capa de densidad por UPZ** (que igual es
  más detallada que la localidad). Sigue aportando valor, solo que de otra forma.

### Decisión 2 — No existe la "franja horaria" en los datos abiertos
- **El plan decía:** predecir riesgo por zona, **hora del día** y tipo de delito.
- **La realidad:** **ninguna** fuente pública trae la hora del hecho (SIEDCO es
  anual, NUSE es mensual, la Policía trae la fecha pero no la hora).
- **Qué hicimos:** cambiamos el objetivo a predecir riesgo por **zona + año + tipo
  de delito**. La hora del día queda como mejora futura (requiere datos que hoy no
  son públicos).

### Decisión 3 — Entrenar con 2018–2024 y evaluar con 2025
- **Por qué:** para que el modelo demuestre que predice el futuro, se entrena con
  el pasado (hasta 2024) y se prueba con el año siguiente (2025). Nunca se mezclan
  al azar. Esto se llama "validación sin fuga de información".

> **En resumen:** el producto sigue siendo el mismo (mapa de riesgo por zona +
> alerta en el móvil), solo ajustamos el "grano" del análisis a lo que los datos
> abiertos realmente permiten. Ser honestos con esto **suma puntos** en el criterio
> de rigor técnico.

---

## 6. El hallazgo estrella: los datos están validados

Comparamos el hurto a personas de **dos fuentes oficiales independientes** (SIEDCO
por localidad, del portal de Bogotá; y la Policía Nacional por API de datos.gov.co).
Coinciden **casi al 100%**:

| Año | SIEDCO | Policía Nacional | Diferencia |
|---|---|---|---|
| 2018 | 105.943 | 105.964 | 0,0 % |
| 2020 | 83.124 | 83.136 | 0,0 % |
| 2023 | 157.604 | 158.745 | 0,7 % |
| 2024 | 129.779 | 130.504 | 0,6 % |
| 2025 | 101.894 | 123.017 | **17,2 %** |

**Qué significa:** de 2018 a 2024, dos entidades distintas reportan prácticamente
el mismo número → nuestros datos son confiables. El desfase de **2025** confirma que
el año en curso **todavía no está completo** en los archivos oficiales → por eso lo
usamos solo para evaluar, no para entrenar.

---

## 7. ¿Qué se implementó, en concreto? (archivos)

**Código del pipeline** (en `data-engineering/`):
- `config.py` — el "panel de control": rutas, direcciones de descarga verificadas,
  y la lista oficial de los 11 tipos de delito.
- `utils.py` — herramientas de descarga (no baja dos veces lo mismo).
- `ingest_siedco.py`, `ingest_nuse.py`, `ingest_divipola.py`, `ingest_datosgov.py` —
  un script por fuente.

**Salidas ya generadas** (en `data/interim/`, no se suben a git por peso):
- `siedco_delitos.parquet`, `nuse_incidentes.parquet`, `localidades.geojson`,
  `datosgov_policia.parquet`.

**Documentación** (en `docs/data-dictionaries/`):
- Un "diccionario de datos" por fuente (columnas, tipos, problemas de calidad) +
  un inventario general. Total: 5 documentos.

**Orden del repositorio:**
- Reorganizamos las carpetas para que coincidan con el plan maestro (`api/`, `app/`,
  `mobile/`, `models/predictivo`, `models/clustering`), cada una con su README
  explicando quién la trabaja y para qué. Eliminamos carpetas basura y duplicadas.

---

## 8. ¿Qué sigue? (próximos pasos claros)

**Frente de datos (Integrante 1), para cerrar la Semana 1:**
1. **#6 Contexto DANE** — añadir población y pobreza (NBI) por localidad, para que
   el modelo entienda el contexto de cada zona.
2. **#7 Limpieza final** — consolidar todas las reglas de calidad en un solo paso.
3. **#8 Cruce** — unir las 4 fuentes por el **código de la localidad** (nunca por
   nombre, porque los nombres varían entre fuentes).
4. **#9 Dataset analítico** 🎯 — el archivo final `dataset_analitico.parquet` +
   `zonas_bogota.geojson`. **Cuando esto exista, arranca todo el resto del equipo.**

**Los demás integrantes (Semana 2, cuando #9 esté listo):**
- **Integrante 2:** modelo predictivo de riesgo + la API que sirve los datos.
- **Integrante 3:** agrupación de zonas por perfil (clustering) + el dashboard.
- **Integrante 4:** la app móvil que dispara la alerta al entrar a una zona de
  riesgo.

> **La pieza crítica es el archivo #9.** Todo lo hecho hasta ahora existe para que
> ese archivo salga bien construido y a tiempo.

---

## 9. Puntaje: ¿dónde estamos sumando?

| Criterio del reto | Cómo lo estamos atacando |
|---|---|
| **Uso de datos abiertos (20 pts)** | 4 fuentes oficiales, una consumida por API directo de datos.gov.co, y cifras validadas por triangulación |
| **Análisis y rigor técnico (15 pts)** | Descubrimos y documentamos los límites reales del dato; validación sin fuga de información |
| **Impacto y escalabilidad (20 pts)** | Cruce por código DANE → listo para sumar más ciudades |

---

*Documento vivo. Se actualiza al cerrar cada bloque de tareas.*
