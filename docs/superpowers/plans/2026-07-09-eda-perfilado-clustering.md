# EDA de perfilado de zonas (Issue #25) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Producir `notebooks/06_eda_perfilado_clustering.ipynb`, el notebook exploratorio de la Issue #25 que caracteriza el perfil delictivo de cada localidad (composición por tipo, tendencia por año) y deja una hipótesis preliminar del número de perfiles, como insumo para el clustering formal de #27.

**Architecture:** Un único notebook nuevo con 3 secciones (perfiles por proporción, tendencia por año, hipótesis vía dendrograma jerárquico) construido y verificado de forma reproducible: cada tarea usa `nbformat` para escribir/anexar celdas al `.ipynb` y `nbclient` para ejecutarlo headless contra un kernel registrado de este `.venv`, comprobando que no queden celdas con error antes de commitear.

**Tech Stack:** Python 3.14 (`.venv` del repo), pandas, numpy, matplotlib, seaborn, scipy (`scipy.stats.linregress`/`zscore`, `scipy.cluster.hierarchy`). Herramientas de verificación (no productivas): `nbformat`, `nbclient`, `ipykernel`.

## Global Constraints

- **Sin fuga de información como principio del proyecto, pero no aplica igual en EDA:** este notebook describe el histórico completo (2018–2025) para caracterizar el dato — igual que `01_EDA_exploracion_datos.ipynb` — porque no aprende ningún parámetro de modelo. La restricción de usar solo `split == "train"` aplica al modelado formal (#27), no a este EDA.
- **Alcance = EDA, no modelado:** no estandarizar el vector de features completo (NUSE + IPM), no elegir un `k` final, no asignar cluster por localidad, no producir `models/clustering/clusters.joblib`. Todo eso es Issue #27 (features + K-Means) y #28 (validación interna).
- **Idioma:** markdown y mensajes impresos en español, siguiendo la convención del resto del repositorio.
- **Estilo visual:** reutilizar la paleta `COLORES` y la configuración de `matplotlib`/`seaborn` ya usadas en `01_EDA_exploracion_datos.ipynb` para consistencia entre notebooks del proyecto.
- **Fuente de datos:** `data/03_primary/dataset_analitico.parquet` (ya generado en este entorno — 1.760 filas = 20 localidades × 8 años × 11 tipos de delito).

---

### Task 0: Dependencia scipy + herramientas de ejecución de notebooks

**Files:**
- Modify: `requirements.txt`

**Interfaces:**
- Produces: `scipy` instalado y pineado en `requirements.txt` (dependencia real del código del notebook); un kernel de Jupyter llamado `alerta-ciudadana-venv` registrado para este `.venv`, usado por todas las tareas siguientes para ejecutar/verificar el notebook.

- [ ] **Step 1: Agregar `scipy` a `requirements.txt`**

Editar el bloque final del archivo (dependencias de EDA/notebooks):

Antes:
```
matplotlib==3.11.0
seaborn==0.13.2
```

Después:
```
matplotlib==3.11.0
seaborn==0.13.2
scipy==1.18.0          # EDA/#25 — regresión de tendencia (linregress) + dendrograma jerárquico
```

- [ ] **Step 2: Instalar dependencias actualizadas**

Run: `.venv/Scripts/pip.exe install -r requirements.txt`
Expected: termina sin errores; `scipy` aparece instalado (o ya satisfecho).

- [ ] **Step 3: Instalar herramientas de ejecución de notebooks (NO van en requirements.txt)**

Ningún código del repo importa `nbformat`/`nbclient`/`ipykernel` — solo se usan en este plan para construir y ejecutar el `.ipynb` de forma automática y reproducible, en vez de a mano en una UI de Jupyter.

Run: `.venv/Scripts/pip.exe install nbformat nbclient ipykernel`
Expected: instala `nbformat`, `nbclient`, `ipykernel` y sus dependencias sin errores.

- [ ] **Step 4: Registrar este `.venv` como kernel de Jupyter**

Run: `.venv/Scripts/python.exe -m ipykernel install --user --name alerta-ciudadana-venv --display-name ".venv (alerta-ciudadana test)"`
Expected: `Installed kernelspec alerta-ciudadana-venv in ...`

- [ ] **Step 5: Verificar que el dataset consolidado existe**

Run: `.venv/Scripts/python.exe -c "import pandas as pd; df = pd.read_parquet('data/03_primary/dataset_analitico.parquet'); print(df.shape)"`
Expected: `(1760, 11)`

Si falla porque el archivo no existe, correr primero `python pipelines/pipeline_ml.py` (requiere los intermedios de `data/02_intermediate/`; ver `src/README.md`) y repetir este paso antes de continuar.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt
git commit -m "chore(deps): agrega scipy para el EDA de perfilado de zonas (issue #25)"
```

---

### Task 1: Notebook — celda de título + carga de datos

**Files:**
- Create: `notebooks/06_eda_perfilado_clustering.ipynb`

**Interfaces:**
- Consumes: `data/03_primary/dataset_analitico.parquet` (columnas `cod_localidad, localidad_nombre, anio, tipo_delito, tipo_delito_nombre, conteo_siedco, conteo_nuse, poblacion, ipm_nbi, split, riesgo_alto`).
- Produces: variable de notebook `DF` (DataFrame, 1760×11, `localidad_nombre`/`tipo_delito_nombre` como `object` de Python) y diccionario `COLORES`, consumidos por las Tareas 2–4.

- [ ] **Step 1: Crear el notebook con la celda de título (markdown) y la celda de setup (código)**

Run:
```bash
.venv/Scripts/python.exe - <<'PY'
from pathlib import Path
import nbformat

NB_PATH = Path("notebooks/06_eda_perfilado_clustering.ipynb")

nb = nbformat.v4.new_notebook()
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "pygments_lexer": "ipython3"},
}

titulo = """# 06 · EDA de perfilado de zonas para clustering (Issue #25)

**Responsable:** Integrante 3 (Clustering + Dashboard) · **Fase CRISP-ML:** 3 · **Alimenta a:** #26 (features + línea base z-score), #27 (K-Means formal).

Análisis exploratorio sobre el **dataset analítico unificado** (`data/03_primary/dataset_analitico.parquet`),
para caracterizar cómo se compone el delito en cada localidad (no solo cuánto, sino **de qué tipo**) y
adelantar una hipótesis visual de en cuántos perfiles distintos podrían agruparse las 20 localidades.

> **Alcance:** este notebook es EDA, no modelado. El K-Means formal (features estandarizadas con NUSE/IPM,
> elbow + silhouette cuantitativos, `k` final justificado) es la Issue #27; aquí solo se explora visualmente.

**Secciones**
1. Perfiles delictivos por localidad (proporción de cada tipo de delito)
2. Tendencia por año por localidad-tipo (¿sube o baja?)
3. Hipótesis preliminar de cuántos perfiles existen (dendrograma)
"""

setup = """import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import linregress, zscore
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster

# Paleta del proyecto (consistente con 01_EDA_exploracion_datos.ipynb, el dashboard y la app movil)
COLORES = {
    "bajo":   "#17D05B",
    "medio":  "#F5A623",
    "alto":   "#E05252",
    "neutro": "#C89B3C",
    "fondo":  "#0D1117",
}

plt.rcParams.update({"figure.dpi": 110, "axes.grid": True,
                     "grid.alpha": 0.25, "axes.axisbelow": True})
sns.set_style("whitegrid")

DF = pd.read_parquet("../data/03_primary/dataset_analitico.parquet")
DF["localidad_nombre"] = DF["localidad_nombre"].astype("string").astype(object)
DF["tipo_delito_nombre"] = DF["tipo_delito_nombre"].astype("string").astype(object)
print("Dataset:", DF.shape, "| columnas:", list(DF.columns))
print("Localidades:", DF["localidad_nombre"].nunique(), "| tipos de delito:", DF["tipo_delito_nombre"].nunique(),
      "| anios:", sorted(DF["anio"].unique()))
assert DF.shape == (1760, 11), "forma inesperada del dataset analitico"
assert DF["localidad_nombre"].nunique() == 20 and DF["tipo_delito_nombre"].nunique() == 11
DF.head()
"""

nb["cells"] = [
    nbformat.v4.new_markdown_cell(titulo),
    nbformat.v4.new_code_cell(setup),
]
nbformat.write(nb, NB_PATH)
print("Notebook creado con", len(nb["cells"]), "celdas")
PY
```
Expected: `Notebook creado con 2 celdas`

- [ ] **Step 2: Ejecutar el notebook y verificar que corre sin errores**

Run:
```bash
.venv/Scripts/python.exe - <<'PY'
import nbformat
from nbclient import NotebookClient

NB_PATH = "notebooks/06_eda_perfilado_clustering.ipynb"
nb = nbformat.read(NB_PATH, as_version=4)
client = NotebookClient(nb, kernel_name="alerta-ciudadana-venv", timeout=180,
                         resources={"metadata": {"path": "notebooks"}})
client.execute()
nbformat.write(nb, NB_PATH)

errores = [o for c in nb["cells"] if c["cell_type"] == "code"
           for o in c.get("outputs", []) if o.get("output_type") == "error"]
for c in nb["cells"]:
    if c["cell_type"] == "code":
        for o in c.get("outputs", []):
            if o.get("output_type") == "stream":
                print(o.get("text", ""), end="")
assert not errores, f"celdas con error: {errores}"
print("OK: notebook ejecutado sin errores")
PY
```
Expected (entre otras líneas): `Dataset: (1760, 11) | columnas: [...]`, `Localidades: 20 | tipos de delito: 11 | anios: [...]`, y al final `OK: notebook ejecutado sin errores`.

- [ ] **Step 3: Commit**

```bash
git add notebooks/06_eda_perfilado_clustering.ipynb
git commit -m "feat(clustering): crea notebook EDA de perfilado de zonas (setup + carga de datos)"
```

---

### Task 2: Sección 1 — Perfiles delictivos por localidad (criterio 1)

**Files:**
- Modify: `notebooks/06_eda_perfilado_clustering.ipynb`

**Interfaces:**
- Consumes: `DF` (Task 1).
- Produces: variables de notebook `PROP` (DataFrame 20×11, proporción de cada tipo por localidad, filas suman 1) y `orden_volumen` (Index de localidades ordenadas por volumen total descendente), consumidas por la Tarea 3.

- [ ] **Step 1: Anexar la celda markdown y la celda de código de la Sección 1**

Run:
```bash
.venv/Scripts/python.exe - <<'PY'
from pathlib import Path
import nbformat

NB_PATH = Path("notebooks/06_eda_perfilado_clustering.ipynb")
nb = nbformat.read(NB_PATH, as_version=4)

md = """## Sección 1 — Perfiles delictivos por localidad

¿De qué está hecho el delito en cada localidad? No el volumen (eso ya lo cubre
`01_EDA_exploracion_datos.ipynb`), sino la **composición**: qué proporción de los delitos
registrados en 2018–2025 corresponde a cada tipo. Dos localidades pueden tener volúmenes muy
distintos y aun así compartir perfil (o al revés) — esa composición es lo que el clustering de
#27 necesita capturar.
"""

code = """piv_siedco = DF.pivot_table(index="localidad_nombre", columns="tipo_delito_nombre",
                            values="conteo_siedco", aggfunc="sum")
PROP = piv_siedco.div(piv_siedco.sum(axis=1), axis=0)
assert np.allclose(PROP.sum(axis=1), 1.0), "las proporciones por localidad deben sumar 1"

orden_volumen = piv_siedco.sum(axis=1).sort_values(ascending=False).index
fig, ax = plt.subplots(figsize=(11, 8))
sns.heatmap(PROP.loc[orden_volumen], cmap="YlOrRd", linewidths=.4, linecolor="white",
            cbar_kws={"label": "Proporcion del total de delitos de la localidad"}, ax=ax)
ax.set_title("Perfil delictivo por localidad - proporcion de cada tipo (2018-2025)\\n"
             "(filas ordenadas por volumen total, no por proporcion)")
ax.set_xlabel(""); ax.set_ylabel("")
plt.tight_layout(); plt.show()

top_perfil = PROP.idxmax(axis=1)
print("Tipo de delito dominante (mayor proporcion) por localidad:")
print(top_perfil.value_counts().to_string())
print()
print("Composicion completa - Sumapaz vs. dos localidades del sur (referencia):")
print(PROP.loc[["SUMAPAZ", "RAFAEL URIBE URIBE", "SAN CRISTOBAL"]].round(3).T.to_string())
"""

interpretacion = """**Interpretación.** El **tipo dominante por sí solo casi no diferencia localidades**: Hurto a
Personas es el tipo con mayor proporción en **19 de las 20 localidades** (entre 33% y 57% del total
según la zona), reflejo de que ya en `01_EDA_exploracion_datos.ipynb` se identificó como el delito
más frecuente en toda la ciudad. La única excepción es **Sumapaz**, donde el tipo dominante es
**Violencia Intrafamiliar (39%)** — un perfil cualitativamente distinto al resto, consistente con ser
la única localidad rural y de muy baja población. Esto confirma que **el perfil de zona no se puede
leer del top-1**: hace falta la composición completa. Al comparar Sumapaz con dos localidades del sur
(Rafael Uribe Uribe, San Cristóbal) se ve el patrón que ya señalaba `docs/HANDOFF_INT1.md` — la
proporción de Violencia Intrafamiliar y Lesiones Personales sube notablemente frente a localidades
comerciales como Chapinero o Teusaquillo (~10–12% cada una), mientras el Hurto a Personas baja. Esa
asimetría composicional es la señal que un clustering sobre proporciones (no sobre volúmenes crudos)
debería capturar.
"""

nb["cells"].append(nbformat.v4.new_markdown_cell(md))
nb["cells"].append(nbformat.v4.new_code_cell(code))
nb["cells"].append(nbformat.v4.new_markdown_cell(interpretacion))
nbformat.write(nb, NB_PATH)
print("Total de celdas ahora:", len(nb["cells"]))
PY
```
Expected: `Total de celdas ahora: 5`

- [ ] **Step 2: Ejecutar el notebook completo y verificar**

Run: (mismo comando exacto del Task 1, Step 2)
```bash
.venv/Scripts/python.exe - <<'PY'
import nbformat
from nbclient import NotebookClient

NB_PATH = "notebooks/06_eda_perfilado_clustering.ipynb"
nb = nbformat.read(NB_PATH, as_version=4)
client = NotebookClient(nb, kernel_name="alerta-ciudadana-venv", timeout=180,
                         resources={"metadata": {"path": "notebooks"}})
client.execute()
nbformat.write(nb, NB_PATH)

errores = [o for c in nb["cells"] if c["cell_type"] == "code"
           for o in c.get("outputs", []) if o.get("output_type") == "error"]
for c in nb["cells"]:
    if c["cell_type"] == "code":
        for o in c.get("outputs", []):
            if o.get("output_type") == "stream":
                print(o.get("text", ""), end="")
assert not errores, f"celdas con error: {errores}"
print("OK: notebook ejecutado sin errores")
PY
```
Expected (además de lo del Task 1): `Tipo de delito dominante (mayor proporcion) por localidad:` seguido de `Hurto Personas    19` y `Violencia Intrafamiliar    1`, y al final `OK: notebook ejecutado sin errores`.

- [ ] **Step 3: Commit**

```bash
git add notebooks/06_eda_perfilado_clustering.ipynb
git commit -m "feat(clustering): agrega Seccion 1 (perfiles por proporcion de delito) al EDA de zonas"
```

---

### Task 3: Sección 2 — Tendencia por año por localidad-tipo (criterio 2)

**Files:**
- Modify: `notebooks/06_eda_perfilado_clustering.ipynb`

**Interfaces:**
- Consumes: `DF`, `orden_volumen` (Tasks 1–2).
- Produces: variable de notebook `TENDENCIA` (DataFrame 220×3: `localidad_nombre`, `tipo_delito_nombre`, `pendiente_rel`, `tendencia`), no consumida por tareas posteriores (Sección 3 usa `PROP`, no `TENDENCIA`).

- [ ] **Step 1: Anexar la celda markdown y la celda de código de la Sección 2**

Run:
```bash
.venv/Scripts/python.exe - <<'PY'
from pathlib import Path
import nbformat

NB_PATH = Path("notebooks/06_eda_perfilado_clustering.ipynb")
nb = nbformat.read(NB_PATH, as_version=4)

md = """## Sección 2 — Tendencia por año por localidad-tipo

¿Cada combinación localidad–tipo de delito sube, baja o se mantiene estable entre 2018 y 2025? Se
ajusta una regresión lineal simple (`conteo_siedco` contra `anio`) por cada una de las 20 × 11 = 220
combinaciones y se clasifica la pendiente relativa al nivel medio de esa serie. **Nota:** 2020 tiene una
caída marcada por el confinamiento (ver `01_EDA_exploracion_datos.ipynb`, Sección 2); una tendencia de
varios años no debe leerse como si ese año fuera el patrón normal.
"""

code = """filas = []
for (loc, tipo), g in DF.groupby(["localidad_nombre", "tipo_delito_nombre"]):
    g = g.sort_values("anio")
    pendiente, _, _, _, _ = linregress(g["anio"], g["conteo_siedco"])
    media = g["conteo_siedco"].mean()
    pendiente_rel = (pendiente / media) if media > 0 else 0.0
    filas.append({"localidad_nombre": loc, "tipo_delito_nombre": tipo, "pendiente_rel": pendiente_rel})
TENDENCIA = pd.DataFrame(filas)

UMBRAL_TENDENCIA = 0.03  # pendiente relativa: > +3%/anio promedio = sube, < -3%/anio = baja
TENDENCIA["tendencia"] = np.select(
    [TENDENCIA["pendiente_rel"] > UMBRAL_TENDENCIA, TENDENCIA["pendiente_rel"] < -UMBRAL_TENDENCIA],
    ["sube", "baja"], default="estable",
)
assert len(TENDENCIA) == 220, "se esperan 20 localidades x 11 tipos = 220 combinaciones"

piv_tendencia = TENDENCIA.pivot(index="localidad_nombre", columns="tipo_delito_nombre", values="pendiente_rel")
fig, ax = plt.subplots(figsize=(11, 8))
sns.heatmap(piv_tendencia.loc[orden_volumen], cmap="RdBu_r", center=0, vmin=-0.2, vmax=0.2,
            linewidths=.4, linecolor="white",
            cbar_kws={"label": "Pendiente relativa anual (rojo = sube, azul = baja)"}, ax=ax)
ax.set_title("Tendencia 2018-2025 por localidad-tipo (pendiente relativa de regresion lineal)")
ax.set_xlabel(""); ax.set_ylabel("")
plt.tight_layout(); plt.show()

print("Conteo de combinaciones localidad-tipo por tendencia:")
print(TENDENCIA["tendencia"].value_counts().to_string())
print()
print("Tendencia agregada por tipo de delito (cuantas localidades suben/bajan/estable):")
print(TENDENCIA.groupby(["tipo_delito_nombre", "tendencia"]).size().unstack(fill_value=0).to_string())
"""

interpretacion = """**Interpretación.** La tendencia **no es uniforme por tipo de delito** — hay patrones consistentes
en casi todas las localidades:

- **Sube en casi toda la ciudad:** Hurto de Motocicletas (15 de 20 localidades en tendencia "sube"),
  Delitos Sexuales y Homicidios (10 de 20 cada uno, con solo 1–2 localidades en baja).
- **Baja en casi toda la ciudad:** Lesiones Personales, Hurto de Celulares y Hurto de Comercio (19 de 20
  localidades cada uno), y Hurto de Residencias y Hurto de Bicicletas (17 y 15 de 20).
- **Sumapaz es la serie más ruidosa** (pendientes relativas de hasta −53%): con conteos anuales muy
  bajos (decenas de casos), una variación pequeña en términos absolutos se traduce en una pendiente
  relativa enorme — hay que leer sus tendencias con cautela, no como una señal fuerte.

Que el Hurto de Motocicletas suba de forma generalizada mientras el Hurto de Celulares y de Comercio bajan
de forma igual de generalizada sugiere que estos patrones responden a una dinámica **de tipo de delito a
nivel ciudad** más que a algo específico de cada localidad — una hipótesis a tener en cuenta si #26/#27
deciden incluir la tendencia como feature adicional al perfil estático de proporciones.
"""

nb["cells"].append(nbformat.v4.new_markdown_cell(md))
nb["cells"].append(nbformat.v4.new_code_cell(code))
nb["cells"].append(nbformat.v4.new_markdown_cell(interpretacion))
nbformat.write(nb, NB_PATH)
print("Total de celdas ahora:", len(nb["cells"]))
PY
```
Expected: `Total de celdas ahora: 8`

- [ ] **Step 2: Ejecutar el notebook completo y verificar**

Run: (mismo comando exacto del Task 1, Step 2)
```bash
.venv/Scripts/python.exe - <<'PY'
import nbformat
from nbclient import NotebookClient

NB_PATH = "notebooks/06_eda_perfilado_clustering.ipynb"
nb = nbformat.read(NB_PATH, as_version=4)
client = NotebookClient(nb, kernel_name="alerta-ciudadana-venv", timeout=180,
                         resources={"metadata": {"path": "notebooks"}})
client.execute()
nbformat.write(nb, NB_PATH)

errores = [o for c in nb["cells"] if c["cell_type"] == "code"
           for o in c.get("outputs", []) if o.get("output_type") == "error"]
for c in nb["cells"]:
    if c["cell_type"] == "code":
        for o in c.get("outputs", []):
            if o.get("output_type") == "stream":
                print(o.get("text", ""), end="")
assert not errores, f"celdas con error: {errores}"
print("OK: notebook ejecutado sin errores")
PY
```
Expected (además de lo previo): `Conteo de combinaciones localidad-tipo por tendencia:` con `baja  106`, `estable  61`, `sube  53`, y al final `OK: notebook ejecutado sin errores`.

- [ ] **Step 3: Commit**

```bash
git add notebooks/06_eda_perfilado_clustering.ipynb
git commit -m "feat(clustering): agrega Seccion 2 (tendencia por anio) al EDA de zonas"
```

---

### Task 4: Sección 3 — Hipótesis preliminar de perfiles (criterio 3)

**Files:**
- Modify: `notebooks/06_eda_perfilado_clustering.ipynb`

**Interfaces:**
- Consumes: `PROP` (Task 2).
- Produces: nada consumido por tareas posteriores (última sección de contenido).

- [ ] **Step 1: Anexar la celda markdown y la celda de código de la Sección 3**

Run:
```bash
.venv/Scripts/python.exe - <<'PY'
from pathlib import Path
import nbformat

NB_PATH = Path("notebooks/06_eda_perfilado_clustering.ipynb")
nb = nbformat.read(NB_PATH, as_version=4)

md = """## Sección 3 — Hipótesis preliminar de cuántos perfiles existen

Sobre la matriz de proporciones de la Sección 1 (estandarizada por tipo de delito, para que ningún tipo
de alto volumen domine la distancia), se corre un clustering jerárquico (`ward`) solo para **leer
visualmente** en cuántos grupos parecen separarse las 20 localidades. **Esto no es el clustering final**:
no hay estandarización con las features completas (NUSE, IPM), ni elección formal de `k` por
elbow/silhouette, ni asignación de cluster por localidad — todo eso es la Issue #27.
"""

code = """PROP_Z = PROP.apply(zscore)
Z = linkage(PROP_Z.values, method="ward")

fig, ax = plt.subplots(figsize=(12, 6))
dendrogram(Z, labels=PROP_Z.index.tolist(), leaf_rotation=90,
           color_threshold=0.7 * max(Z[:, 2]), ax=ax)
ax.set_title("Dendrograma - perfiles de proporcion de delito por localidad (linkage ward)")
ax.set_ylabel("Distancia (ward)")
plt.tight_layout(); plt.show()

print("Tamano de los grupos para distintos cortes de k:")
for k in (2, 3, 4, 5, 6):
    grupos = fcluster(Z, t=k, criterion="maxclust")
    tamanos = sorted((int(x) for x in np.bincount(grupos)[1:]), reverse=True)
    print(f"  k={k}: tamanos = {tamanos}")
"""

interpretacion = """**Interpretación.** Sumapaz aparece como grupo propio de tamaño 1 en **todos** los cortes de `k`
probados (2 a 6): su perfil es tan distinto que el algoritmo lo aísla de inmediato, confirmando la
lectura de la Sección 1. Descontando Sumapaz, el resto de la ciudad se reparte así: con `k=2` casi toda
la ciudad queda en un único grupo de 19 localidades (no aporta información útil); con `k=3` se abren
dos grupos de 12 y 7; con `k=4`, de 8, 7 y 4; a partir de `k=5` empiezan a aparecer grupos de tamaño 2,
señal de que se está fragmentando de más.

**Hipótesis preliminar:** probablemente existan **entre 3 y 4 perfiles principales** entre las 19
localidades restantes, más Sumapaz como caso atípico a tratar aparte (incluir, excluir o cluster propio
— decisión pendiente, ver `docs/HANDOFF_INT1.md`). En la línea de lo ya documentado ahí: un perfil de
zonas comerciales/alta afluencia dominadas por hurto (Chapinero, Teusaquillo, Candelaria) y un perfil de
zonas del sur con mayor peso relativo de violencia interpersonal (Rafael Uribe, San Cristóbal, Usme)
deberían quedar en grupos distintos si `k=3` o `k=4` se confirma en #27 con el método formal (elbow +
silhouette sobre las features completas).
"""

nb["cells"].append(nbformat.v4.new_markdown_cell(md))
nb["cells"].append(nbformat.v4.new_code_cell(code))
nb["cells"].append(nbformat.v4.new_markdown_cell(interpretacion))
nbformat.write(nb, NB_PATH)
print("Total de celdas ahora:", len(nb["cells"]))
PY
```
Expected: `Total de celdas ahora: 11`

- [ ] **Step 2: Ejecutar el notebook completo y verificar**

Run: (mismo comando exacto del Task 1, Step 2)
```bash
.venv/Scripts/python.exe - <<'PY'
import nbformat
from nbclient import NotebookClient

NB_PATH = "notebooks/06_eda_perfilado_clustering.ipynb"
nb = nbformat.read(NB_PATH, as_version=4)
client = NotebookClient(nb, kernel_name="alerta-ciudadana-venv", timeout=180,
                         resources={"metadata": {"path": "notebooks"}})
client.execute()
nbformat.write(nb, NB_PATH)

errores = [o for c in nb["cells"] if c["cell_type"] == "code"
           for o in c.get("outputs", []) if o.get("output_type") == "error"]
for c in nb["cells"]:
    if c["cell_type"] == "code":
        for o in c.get("outputs", []):
            if o.get("output_type") == "stream":
                print(o.get("text", ""), end="")
assert not errores, f"celdas con error: {errores}"
print("OK: notebook ejecutado sin errores")
PY
```
Expected (además de lo previo): `Tamano de los grupos para distintos cortes de k:` con `k=2: tamanos = [19, 1]` ... `k=6: tamanos = [6, 4, 4, 3, 2, 1]`, y al final `OK: notebook ejecutado sin errores`.

- [ ] **Step 3: Commit**

```bash
git add notebooks/06_eda_perfilado_clustering.ipynb
git commit -m "feat(clustering): agrega Seccion 3 (dendrograma e hipotesis de perfiles) al EDA de zonas"
```

---

### Task 5: Verificación final de los 3 criterios de aceptación

**Files:**
- Read only: `notebooks/06_eda_perfilado_clustering.ipynb`

**Interfaces:**
- Consumes: el notebook completo producido por las Tareas 1–4.
- Produces: confirmación objetiva (no una nueva celda) de que los 3 criterios de aceptación de la Issue #25 están cubiertos.

- [ ] **Step 1: Releer el notebook ejecutado y comprobar los 3 criterios de aceptación con asserts explícitos**

Run:
```bash
.venv/Scripts/python.exe - <<'PY'
import nbformat

NB_PATH = "notebooks/06_eda_perfilado_clustering.ipynb"
nb = nbformat.read(NB_PATH, as_version=4)

texto = ""
for c in nb["cells"]:
    if c["cell_type"] == "code":
        for o in c.get("outputs", []):
            if o.get("output_type") == "stream":
                texto += o.get("text", "")
    elif c["cell_type"] == "markdown":
        texto += c.get("source", "")

# Criterio 1: perfiles delictivos por localidad (proporcion de cada tipo)
assert "Tipo de delito dominante (mayor proporcion) por localidad:" in texto
assert "Violencia Intrafamiliar" in texto and "Hurto Personas" in texto

# Criterio 2: tendencia por anio identificada (sube/baja por localidad-tipo)
assert "Conteo de combinaciones localidad-tipo por tendencia:" in texto
for etiqueta in ("sube", "baja", "estable"):
    assert etiqueta in texto

# Criterio 3: hipotesis preliminar de cuantos perfiles distintos podrian existir
assert "Tamano de los grupos para distintos cortes de k:" in texto
assert "Hipotesis preliminar" in texto.replace("ó", "o").replace("é", "e")

n_code = sum(1 for c in nb["cells"] if c["cell_type"] == "code")
n_md = sum(1 for c in nb["cells"] if c["cell_type"] == "markdown")
print(f"Celdas de codigo: {n_code} | celdas markdown: {n_md} | total: {len(nb['cells'])}")
print("OK: los 3 criterios de aceptacion de la Issue #25 estan cubiertos en el notebook ejecutado")
PY
```
Expected: `Celdas de codigo: 4 | celdas markdown: 7 | total: 11` seguido de `OK: los 3 criterios de aceptacion de la Issue #25 estan cubiertos en el notebook ejecutado`.

- [ ] **Step 2: Marcar la Issue #25 como completa en `BACKLOG.md`**

En `BACKLOG.md`, dentro del bloque `### [CLUST] #25 — EDA para perfilado de zonas (en paralelo) 🟢`, marcar los 3 checkboxes de "Criterios de aceptación":

Antes:
```
- [ ] Notebook con perfiles delictivos por localidad (proporción de cada tipo de delito).
- [ ] Tendencia por año identificada (¿sube o baja cada tipo de delito por localidad?).
- [ ] Hipótesis preliminar de cuántos perfiles distintos podrían existir.
```

Después:
```
- [x] Notebook con perfiles delictivos por localidad (proporción de cada tipo de delito).
- [x] Tendencia por año identificada (¿sube o baja cada tipo de delito por localidad?).
- [x] Hipótesis preliminar de cuántos perfiles distintos podrían existir.
```

- [ ] **Step 3: Commit final**

```bash
git add BACKLOG.md
git commit -m "docs(backlog): marca issue #25 (EDA de perfilado de zonas) como completa"
```

---

## Notas para quien retome este trabajo (Issue #26/#27)

- `PROP` (proporciones por localidad) y la hipótesis de 3–4 perfiles + Sumapaz aparte son el punto de partida directo para el vector de features de #26.
- El umbral `UMBRAL_TENDENCIA = 0.03` de la Sección 2 es una elección de EDA para visualizar dirección, no un valor validado — si #26/#27 deciden usar la tendencia como feature, hay que revisar ese umbral con más cuidado (o usar la pendiente cruda en vez de clasificarla).
- El tratamiento de Sumapaz sigue **sin resolver** (ver `docs/HANDOFF_INT1.md`): este notebook aporta evidencia (aislado en todos los cortes de k) pero no toma la decisión.
