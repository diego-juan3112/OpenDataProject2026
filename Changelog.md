# Changelog — Alerta Ciudadana

Registro cronológico de hitos, decisiones de alcance y cambios
que afectan a más de un integrante. Orden: más reciente primero.

---

## [Hito 1] — 2026-07-06 — Frente de Datos completo (Issues #1–#12)

### Entregables
- `data/03_primary/dataset_analitico.parquet` — 1.760 filas
  (20 localidades × 11 tipos de delito × 8 años), columna `split`
  marcada (train 2018–2024 / test 2025), variable objetivo `riesgo_alto`.
- `data/03_primary/zonas_bogota.geojson` — 20 polígonos de localidades
  de Bogotá en EPSG:4326, listos para consumo web y móvil.

### Fuentes integradas
5 fuentes oficiales: SIEDCO (delitos por localidad), NUSE/C4 Línea 123
(llamadas de emergencia), geometría de localidades (IDECA/Catastro),
microdatos Policía Nacional vía API Socrata de datos.gov.co, y contexto
socioeconómico DANE/SDP (población + IPM). Pipeline reproducible con
`python pipelines/pipeline_ml.py`.

### Decisiones de diseño (afectan a todo el equipo)
1. **Sin franja horaria.** Ninguna fuente abierta trae la hora del
   incidente. Grano temporal = año, no hora.
2. **NUSE como densidad por zona.** El dataset viene agregado por
   localidad/UPZ × mes, sin coordenadas individuales. Se usa como
   señal complementaria (`conteo_nuse`), no como capa de puntos.
3. **Split temporal sin fuga.** Train = 2018–2024, test = 2025.
   Las filas test NO se tocan hasta la evaluación final (#17).
4. **Variable objetivo por tipo de delito.** `riesgo_alto = 1` si
   `conteo_siedco` supera el P75 del mismo tipo en train. Umbral
   por tipo (no global) para evitar incompatibilidad de escala entre
   homicidios y hurtos.
5. **Sumapaz (cod 20) con `ipm_nbi` nulo.** No cubierta por la
   Encuesta Multipropósito. 88 filas nulas. Decisión de imputación
   pendiente (Int. 2 antes de #17; Int. 3 antes de #27).

### Sesgos identificados (EDA #11)
- **Sobre-vigilancia:** el delito registrado sigue la presencia
  institucional (corr SIEDCO/NUSE = 0.92). Zonas comerciales como
  Chapinero y La Candelaria tienen ratio registros/llamadas > 1;
  el sur residencial muestra subregistro (~0.52–0.57).
- **Pobreza ≠ delito en general.** La pobreza (IPM) predice
  violencia interpersonal (+0.60 homicidio, +0.36 VIF) pero no
  hurto de bienes (−0.19 automotores). Colapsar en un score único
  estigmatizaría zonas pobres. El modelo opera por tipo de delito.

### Desbloquea
- Int. 2: issues #14, #15, #16 (sin bloqueo) → #17 tras confirmar
  `variable_objetivo.md`.
- Int. 3: issues #26, #32 (insumo de sesgo disponible en notebook #11).
- Int. 4: `zonas_bogota.geojson` disponible para construir el mapa
  base con mock de riesgo mientras la API no esté lista.
- Ruta crítica de la semana: #26→#27 (Int. 3) ∥ #16→#17→#19 (Int. 2)
  → confluyen en #20 (API).

---

## [Sin versión] — en desarrollo
- Refactorización a la estructura estándar de la competencia (src/, pipelines/,
  data/01_raw…04_model_output, docs/, notebooks/, tests/).
- Pipeline de datos completado (Issues #1–#9).
