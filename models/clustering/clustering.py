"""
clustering.py — Issue #27

Funciones puras para el clustering K-Means de perfiles de zona. Reciben la
matriz de features (ya estandarizada por #26) como parametro; no leen
archivos, para poder testear con datos sinteticos (data/ no existe en CI).
"""
from __future__ import annotations

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, silhouette_samples, adjusted_rand_score

# Las 11 tasas de tipo de delito (excluye tasa_nuse e ipm_nbi, que tambien
# viven en la matriz de features pero no son "tipo de delito").
COLS_TIPO_DELITO = ["tasa_DS", "tasa_H", "tasa_HA", "tasa_HB", "tasa_HC", "tasa_HCE",
                     "tasa_HM", "tasa_HP", "tasa_HR", "tasa_LP", "tasa_VI"]
COLS_VIOLENTO = ["tasa_H", "tasa_DS", "tasa_VI", "tasa_LP"]
COLS_PATRIMONIAL = ["tasa_HA", "tasa_HB", "tasa_HC", "tasa_HCE", "tasa_HM", "tasa_HR", "tasa_HP"]


def evaluar_k(
    features: pd.DataFrame,
    k_range: range,
    n_init: int = 10,
    random_state: int = 42,
) -> pd.DataFrame:
    """Inercia y silhouette de K-Means para cada k en k_range (Issue #27).

    No decide el k final por si sola: es el insumo para graficar la curva de
    codo + silhouette y justificar la eleccion de k (ver
    docs/data-dictionaries/clustering_perfiles.md). Maximizar silhouette a
    ciegas puede dar un k poco util (ver la nota en ese documento sobre por
    que k=3 se justifica por codo + interpretabilidad, no por silhouette
    maximo).
    """
    filas = []
    for k in k_range:
        modelo = KMeans(n_clusters=k, n_init=n_init, random_state=random_state)
        etiquetas = modelo.fit_predict(features.values)
        filas.append({
            "k": k,
            "inercia": modelo.inertia_,
            "silhouette": silhouette_score(features.values, etiquetas),
        })
    return pd.DataFrame(filas)


def entrenar_kmeans_final(
    features: pd.DataFrame,
    k: int,
    n_init: int = 10,
    random_state: int = 42,
) -> KMeans:
    """Entrena el K-Means final con los parametros ya decididos (Issue #27)."""
    modelo = KMeans(n_clusters=k, n_init=n_init, random_state=random_state)
    modelo.fit(features.values)
    return modelo


def nombrar_clusters(features: pd.DataFrame, modelo: KMeans) -> dict[int, str]:
    """Nombra cada cluster por regla sobre sus centroides reales (Issue #27).

    No asume que una etiqueta numerica de sklearn siempre corresponde al mismo
    grupo entre corridas o versiones: la regla mira los centroides del modelo
    ya entrenado, cluster por cluster.

    1. El cluster cuyo promedio de las 11 tasas de tipo de delito
       (COLS_TIPO_DELITO) sea el MAXIMO entre todos los clusters, y ademas
       supere 1.0 (claramente por encima del promedio) -> "Perfil de alto
       impacto generalizado".
    2. Si no aplica lo anterior y (promedio patrimonial - promedio violento)
       > 0.3 -> "Perfil hurto de bienes / ingreso alto".
    3. En cualquier otro caso -> "Perfil de bajo incidente relativo".
    """
    centroides = pd.DataFrame(modelo.cluster_centers_, columns=features.columns)
    intensidad_general = centroides[COLS_TIPO_DELITO].mean(axis=1)
    intensidad_violento = centroides[COLS_VIOLENTO].mean(axis=1)
    intensidad_patrimonial = centroides[COLS_PATRIMONIAL].mean(axis=1)

    idx_alto_impacto = intensidad_general.idxmax()

    nombres = {}
    for i in centroides.index:
        if i == idx_alto_impacto and intensidad_general[i] > 1.0:
            nombres[i] = "Perfil de alto impacto generalizado"
        elif (intensidad_patrimonial[i] - intensidad_violento[i]) > 0.3:
            nombres[i] = "Perfil hurto de bienes / ingreso alto"
        else:
            nombres[i] = "Perfil de bajo incidente relativo"
    return nombres


def construir_zona_cluster(
    features: pd.DataFrame,
    modelo: KMeans,
    nombres: dict[int, str],
) -> pd.DataFrame:
    """Tabla zona-cluster-nombre_perfil (Issue #27), lista para servir/dashboard."""
    etiquetas = modelo.predict(features.values)
    return pd.DataFrame({
        "cod_localidad": features.index,
        "cluster": etiquetas,
        "nombre_perfil": [nombres[c] for c in etiquetas],
    })


def silhouette_por_cluster(features: pd.DataFrame, modelo: KMeans) -> pd.DataFrame:
    """Silhouette medio y minimo por cluster (Issue #28).

    A diferencia de evaluar_k (que reporta un unico silhouette global por k),
    esta funcion desagrega por cluster: un cluster grande y cohesivo puede
    esconder un cluster pequeno y debil en el promedio global.

    Devuelve un DataFrame con columnas cluster, n, silhouette_medio,
    silhouette_min, ordenado por cluster.
    """
    etiquetas = modelo.predict(features.values)
    valores = silhouette_samples(features.values, etiquetas)
    detalle = pd.DataFrame({"cluster": etiquetas, "silhouette": valores})
    return (detalle.groupby("cluster")["silhouette"]
                    .agg(n="count", silhouette_medio="mean", silhouette_min="min")
                    .reset_index())


def comparar_particiones(etiquetas_a, etiquetas_b) -> float:
    """Adjusted Rand Index entre dos particiones (Issue #28).

    Invariante a como se numeren los clusters (una permutacion de etiquetas
    da el mismo ARI): compara si las MISMAS zonas quedan agrupadas juntas,
    no si los numeros de cluster coinciden. Se reutiliza tanto para la
    prueba de estabilidad de semillas como para comparar contra el baseline
    trivial de terciles por conteo.
    """
    return adjusted_rand_score(etiquetas_a, etiquetas_b)


def evaluar_estabilidad_semillas(
    features: pd.DataFrame,
    etiquetas_referencia,
    k: int,
    semillas,
    n_init: int = 10,
) -> pd.DataFrame:
    """ARI de K-Means reentrenado con cada semilla vs. las etiquetas de
    referencia (Issue #28).

    etiquetas_referencia son las del modelo final ya entrenado (p. ej.
    random_state=42). Para cada semilla en `semillas` se reentrena un
    K-Means nuevo con ese random_state y se compara contra la referencia
    con comparar_particiones. ARI cercano a 1.0 en todas las semillas
    indica que la particion no depende de la inicializacion aleatoria.

    Devuelve un DataFrame con columnas semilla, ari.
    """
    filas = []
    for semilla in semillas:
        modelo = KMeans(n_clusters=k, n_init=n_init, random_state=semilla)
        etiquetas = modelo.fit_predict(features.values)
        filas.append({
            "semilla": semilla,
            "ari": comparar_particiones(etiquetas_referencia, etiquetas),
        })
    return pd.DataFrame(filas)


def terciles_por_conteo(conteo_total: pd.Series, k: int) -> pd.Series:
    """Agrupa zonas en k grupos por conteo total, via cuantiles (Issue #28).

    Baseline trivial para contrastar contra la tipologia real de K-Means: un
    ordenamiento de una sola dimension (volumen bruto), sin las 13 features
    del perfil de zona. Usa el mismo k que el clustering real para que la
    comparacion (via comparar_particiones) sea directa.

    Devuelve una serie de enteros 0..k-1 (0 = grupo de menor conteo), mismo
    indice que conteo_total. Si hay empates que impiden cortar en
    exactamente k grupos, pd.qcut reduce el numero de grupos
    (duplicates="drop") en vez de fallar.
    """
    return pd.qcut(conteo_total, q=k, labels=False, duplicates="drop")
