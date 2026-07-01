"""
utils.py — Utilidades compartidas por los scripts de ingesta.

Descarga idempotente (no vuelve a bajar si el archivo ya existe y no está vacío)
y extracción de ZIP. Mantiene los scripts de ingesta enfocados en la lógica de
cada fuente en vez de repetir el manejo de red.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import requests
from tqdm import tqdm

_HEADERS = {"User-Agent": "Mozilla/5.0 (AlertaCiudadana-pipeline)"}


def download(url: str, dest: Path, *, force: bool = False, timeout: int = 120) -> Path:
    """
    Descarga `url` a `dest` mostrando barra de progreso. Idempotente: si `dest`
    ya existe con tamaño > 0 y no se fuerza, no vuelve a descargar.

    Devuelve la ruta del archivo descargado.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and dest.stat().st_size > 0 and not force:
        print(f"  [skip] ya existe: {dest.name} ({dest.stat().st_size/1e6:.1f} MB)")
        return dest

    print(f"  [get ] {url}")
    with requests.get(url, headers=_HEADERS, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=f"  {dest.name}", leave=False
        ) as bar:
            for chunk in r.iter_content(chunk_size=1 << 16):
                f.write(chunk)
                bar.update(len(chunk))
        tmp.replace(dest)  # descarga atómica: solo renombra si terminó completa
    print(f"  [ok  ] {dest.name} ({dest.stat().st_size/1e6:.1f} MB)")
    return dest


def unzip(zip_path: Path, dest_dir: Path, *, force: bool = False) -> list[Path]:
    """
    Extrae `zip_path` en `dest_dir`. Idempotente por contenido: si los archivos
    ya existen y no se fuerza, no re-extrae. Devuelve la lista de rutas extraídas.
    """
    zip_path, dest_dir = Path(zip_path), Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        extracted = [dest_dir / n for n in names]
        if not force and all(p.exists() for p in extracted):
            print(f"  [skip] ya extraído: {zip_path.name}")
            return extracted
        zf.extractall(dest_dir)
    print(f"  [ok  ] extraído {zip_path.name} -> {len(extracted)} archivo(s)")
    return extracted
