#!/usr/bin/env python3
"""
teste3_fixed.py

Pipeline unificado:
1) consulta produtos CBERS4A via Cbers4aAPI
2) baixa bandas (red, green, blue, pan)
3) espera até os arquivos serem gravados no disco
4) recria composição RGB usando rgbn_composite (se bandas existirem)
5) gera preview PNG com stretch por banda preservando nodata

Ajuste as configurações abaixo conforme necessário.
"""
import os
import time
import glob
import shutil
from datetime import date

import rasterio as rio
import numpy as np
import matplotlib.pyplot as plt

from cbers4asat import Cbers4aAPI
from cbers4asat.tools import rgbn_composite

# -----------------------
# CONFIGURAÇÕES (edite)
# -----------------------
API_EMAIL = "rafaeldeps15@gmail.com"
BBOX = [-40.2221, -20.2026, -40.2121, -20.1926]  # [Oeste, Sul, Leste, Norte]
DATE_START = date(2024, 10, 22)
DATE_END = date(2025, 10, 22)
CLOUD = 0
LIMIT = 10
COLLECTIONS = ['CBERS4A_WPM_L4_DN']
BANDS_TO_DOWNLOAD = ['red', 'green', 'blue', 'pan']

DOWNLOAD_DIR = "./CBERS_DOWNLOADS"   # onde os produtos serão salvos
STACK_DIR = "./STACK"                # onde serão colocados os tifs compostos
PREVIEW_DIR = "./PREVIEWS"           # onde os PNGs serão salvos

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(STACK_DIR, exist_ok=True)
os.makedirs(PREVIEW_DIR, exist_ok=True)

# -----------------------
# Funções utilitárias
# -----------------------
def count_band_files(root_dir):
    """Conta arquivos tiff que parecem ser bandas (band1, band2, band3, pan)."""
    band_patterns = ('band1', 'band_1', 'b1', 'band01', 'band1.tif', 'band_01', 'banda1', 'band-1')
    pan_patterns = ('pan', 'panchro', 'p1', 'pan10', 'panchromatic')
    count = 0
    found = []
    for dirpath, _, files in os.walk(root_dir):
        for f in files:
            lf = f.lower()
            if (any(p in lf for p in band_patterns) or any(p in lf for p in pan_patterns)):
                if lf.endswith('.tif') or lf.endswith('.tiff'):
                    count += 1
                    found.append(os.path.join(dirpath, f))
    return count, found

def product_dirs_with_rgb(root_dir):
    """Retorna diretórios que contêm arquivos que parecem ser band1/2/3."""
    results = []
    for dirpath, _, files in os.walk(root_dir):
        lf_names = [f.lower() for f in files]
        has_b1 = any('band1' in n or 'b1' in n or 'band_01' in n or 'band01' in n or 'banda1' in n for n in lf_names)
        has_b2 = any('band2' in n or 'b2' in n or 'band_02' in n or 'band02' in n or 'banda2' in n for n in lf_names)
        has_b3 = any('band3' in n or 'b3' in n or 'band_03' in n or 'band03' in n or 'banda3' in n for n in lf_names)
        if has_b1 and has_b2 and has_b3:
            results.append(dirpath)
    return results

def stretch_band_masked(band_ma, pmin=2, pmax=98):
    """
    band_ma: numpy.ma.MaskedArray (H, W)
    retorna: uint8 (H, W) com valores 0..255, mantendo nodata como 0
    """
    band = band_ma.astype(np.float32)
    if isinstance(band, np.ma.MaskedArray):
        valid_mask = ~band.mask
        data = band.data
    else:
        valid_mask = np.ones(band.shape, dtype=bool)
        data = band

    if not np.any(valid_mask):
        return np.zeros(band.shape, dtype=np.uint8)

    lo, hi = np.percentile(data[valid_mask], (pmin, pmax))
    if hi == lo:
        hi = lo + 1.0

    clipped = np.clip(data, lo, hi)
    norm = (clipped - lo) / (hi - lo)
    norm[~valid_mask] = 0.0
    return (norm * 255).astype(np.uint8)

def make_preview_from_raster(raster_path, out_png_path):
    """Lê o raster (assume RGB em bandas 1,2,3), aplica stretch preservando nodata e salva PNG."""
    with rio.open(raster_path) as src:
        img_ma = src.read(masked=True)  # (bands, H, W)
    if img_ma.shape[0] < 3:
        raise RuntimeError(f"O raster {raster_path} não tem 3 bandas RGB.")
    r = stretch_band_masked(img_ma[0])
    g = stretch_band_masked(img_ma[1])
    b = stretch_band_masked(img_ma[2])
    rgb = np.dstack([r, g, b])
    plt.figure(figsize=(12, 12))
    plt.imshow(rgb)
    plt.axis("off")
    plt.savefig(out_png_path, dpi=300, bbox_inches="tight")
    plt.close()

def find_band_files_by_product(root_dir):
    """
    Busca recursivamente por diretórios que contenham band1/2/3 (ou variações).
    Retorna lista de dicionários: {'product_dir': path, 'band1': p1, 'band2': p2, 'band3': p3}
    """
    candidates = []
    for dirpath, _, files in os.walk(root_dir):
        lf_names = [f.lower() for f in files]
        # localizar arquivos concretos para cada banda
        band1_fp = None
        band2_fp = None
        band3_fp = None
        for fname in files:
            lf = fname.lower()
            full = os.path.join(dirpath, fname)
            if any(x in lf for x in ('band1', 'band_1', 'b1', 'band01', 'banda1', 'b1.tif')) and lf.endswith(('.tif', '.tiff')):
                band1_fp = full
            if any(x in lf for x in ('band2', 'band_2', 'b2', 'band02', 'banda2', 'b2.tif')) and lf.endswith(('.tif', '.tiff')):
                band2_fp = full
            if any(x in lf for x in ('band3', 'band_3', 'b3', 'band03', 'banda3', 'b3.tif')) and lf.endswith(('.tif', '.tiff')):
                band3_fp = full
        if band1_fp and band2_fp and band3_fp:
            candidates.append({'product_dir': dirpath, 'band1': band1_fp, 'band2': band2_fp, 'band3': band3_fp})
    return candidates

# -----------------------
# Download + espera
# -----------------------
def download_and_wait(api, produtos, download_dir, expected_min_files=None, timeout=900, stable_secs=8):
    """
    Chama api.download(...) e aguarda até que os arquivos de banda tenham sido escritos.
    - expected_min_files: sugestão de quantos arquivos esperar (ex: len(produtos)*4)
    - timeout: tempo máximo (segundos) para aguardar
    - stable_secs: tempo que o contador de arquivos precisa ficar estável para considerar completado
    """
    print("Iniciando download das bandas (chamada a api.download)...")
    cwd = os.getcwd()
    try:
        os.makedirs(download_dir, exist_ok=True)
        os.chdir(download_dir)
        # chamada ao método de download — se a biblioteca aceitar outdir, seria melhor usá-la.
        try:
            api.download(products=produtos, bands=BANDS_TO_DOWNLOAD)
        except TypeError:
            # fallback se api.download não aceitar named args de bands
            api.download(produtos)
    finally:
        os.chdir(cwd)

    print("download() retornou — aguardando arquivos serem gravados no disco...")
    start = time.time()
    last_count = -1
    stable_since = None

    if expected_min_files is None:
        expected_min_files = len(produtos) * len(BANDS_TO_DOWNLOAD)

    while True:
        elapsed = time.time() - start
        if elapsed > timeout:
            print(f"\n[timeout] Tempo máximo de espera ({timeout}s) atingido.")
            break

        count, found = count_band_files(download_dir)
        print(f"[{int(elapsed)}s] arquivos de banda detectados: {count} (esperados ~{expected_min_files})", end='\r')

        if count == last_count:
            if stable_since is None:
                stable_since = time.time()
            elif time.time() - stable_since >= stable_secs:
                print(f"\nNúmero de arquivos estável por {stable_secs}s — assumindo fim do download.")
                break
        else:
            stable_since = None
            last_count = count

        if expected_min_files and count >= expected_min_files:
            print(f"\nEncontrados >= {expected_min_files} arquivos — provavelmente finalizado.")
            break

        prod_dirs = product_dirs_with_rgb(download_dir)
        if prod_dirs:
            print(f"\nAchei {len(prod_dirs)} diretório(s) com bandas RGB completas. Seguindo pipeline.")
            break

        time.sleep(2)

    _, found = count_band_files(download_dir)
    if found:
        print("\nExemplos de arquivos encontrados:")
        for s in found[:10]:
            print(" -", s)
    else:
        print("\nNenhum arquivo de banda detectado.")

# -----------------------
# Pipeline principal
# -----------------------
def main():
    api = Cbers4aAPI(API_EMAIL)

    print("Consultando produtos...")
    produtos = api.query(
        location=BBOX,
        initial_date=DATE_START,
        end_date=DATE_END,
        cloud=CLOUD,
        limit=LIMIT,
        collections=COLLECTIONS
    )

    if not produtos:
        print("Nenhum produto encontrado com esses parâmetros.")
        return

    print(f"Produtos encontrados: {len(produtos)}")

    # inicia download e aguarda gravação
    try:
        download_and_wait(api, produtos, DOWNLOAD_DIR, expected_min_files=len(produtos)*len(BANDS_TO_DOWNLOAD), timeout=900, stable_secs=8)
    except Exception as e:
        print("Erro durante o download/wait:", e)
        return

    # localizar conjuntos de bandas (band1,band2,band3)
    print("Procurando bandas baixadas...")
    candidates = find_band_files_by_product(DOWNLOAD_DIR)
    if not candidates:
        print("Não foi possível encontrar automaticamente diretórios com band1/2/3.")
        print("Vou tentar detectar pastas que contenham bandas RGB completas mesmo com nomes diferentes...")
        candidates = find_band_files_by_product(DOWNLOAD_DIR)  # tentativa redundante (pode ajustar)
        if not candidates:
            # fallback: usar product_dirs_with_rgb para pelo menos localizar pastas com 3 bandas
            prod_dirs = product_dirs_with_rgb(DOWNLOAD_DIR)
            if prod_dirs:
                candidates = []
                for pd in prod_dirs:
                    # achar caminhos concretos
                    files = os.listdir(pd)
                    band1 = band2 = band3 = None
                    for f in files:
                        lf = f.lower()
                        full = os.path.join(pd, f)
                        if any(x in lf for x in ('band1', 'band_1', 'b1', 'band01', 'banda1')):
                            band1 = full
                        if any(x in lf for x in ('band2', 'band_2', 'b2', 'band02', 'banda2')):
                            band2 = full
                        if any(x in lf for x in ('band3', 'band_3', 'b3', 'band03', 'banda3')):
                            band3 = full
                    if band1 and band2 and band3:
                        candidates.append({'product_dir': pd, 'band1': band1, 'band2': band2, 'band3': band3})

    if not candidates:
        print("Ainda não foram encontrados conjuntos válidos de bandas. Liste os arquivos com `ls -R CBERS_DOWNLOADS` e cole aqui para eu ajustar os padrões.")
        return

    print(f"Conjuntos válidos encontrados: {len(candidates)}")
    for idx, c in enumerate(candidates, start=1):
        prod_dir = c['product_dir']
        base_name = os.path.basename(prod_dir.rstrip("/\\"))
        if not base_name:
            base_name = f"product_{idx}"
        out_stack_name = f"{base_name}_TRUE_COLOR.tif"
        out_stack_path = os.path.join(STACK_DIR, out_stack_name)
        print(f"[{idx}/{len(candidates)}] Criando composição para {prod_dir} -> {out_stack_path}")
        try:
            # note o mapeamento: band3 -> red, band2 -> green, band1 -> blue (seguindo seu script original)
            rgbn_composite(
                red=c['band3'],
                green=c['band2'],
                blue=c['band1'],
                filename=out_stack_name,
                outdir=STACK_DIR
            )
        except Exception as e:
            print(f"Erro ao criar composição para {prod_dir}: {e}")
            continue

        # gerar preview PNG
        out_png = os.path.join(PREVIEW_DIR, f"{base_name}_preview.png")
        try:
            make_preview_from_raster(out_stack_path, out_png)
            print(f"Preview salvo: {out_png}")
        except Exception as e:
            print(f"Erro ao gerar preview para {out_stack_path}: {e}")
            continue

    print("Pipeline finalizado.")

if __name__ == "__main__":
    main()
