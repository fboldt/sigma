import os
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import rasterio as rio
from rasterio.enums import Resampling
from rasterio.errors import WindowError
from rasterio.warp import calculate_default_transform, reproject
from rasterio.windows import Window, from_bounds

NODATA_VALUE = 0

# Tamanho das janelas de processamento (em pixels).
DEFAULT_WINDOW_SIZE = 1024
DEFAULT_MAX_WORKERS = 6


# Função para decidir quantas threads usar (pode ser forçado com a variável MOSAIC_WORKERS)
def default_workers():
    env_value = os.environ.get("MOSAIC_WORKERS", "").strip()
    if env_value.isdigit() and int(env_value) > 0:
        return int(env_value)
    return max(1, min(os.cpu_count() or 1, DEFAULT_MAX_WORKERS))


# Função para rodar uma função em várias threads mantendo a ordem dos resultados
def parallel_map(func, items, workers=None):
    items = list(items)
    if not items:
        return []
    workers = max(1, min(workers or default_workers(), len(items)))
    if workers == 1:
        return [func(item) for item in items]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(func, items))


# Função para gerar as janelas (blocos) em que uma imagem é processada aos poucos
def iter_windows(width, height, size=DEFAULT_WINDOW_SIZE, col_off=0, row_off=0):
    for row in range(0, height, size):
        window_height = min(size, height - row)
        for col in range(0, width, size):
            window_width = min(size, width - col)
            yield Window(col_off + col, row_off + row, window_width, window_height)


# Função para montar o perfil de escrita de GeoTIFFs: em blocos (tiled), comprimido e com compressão em várias threads. 
def tiled_gtiff_profile(profile, compress="lzw"):
    profile = dict(profile)
    profile.update(
        driver="GTiff",
        tiled=True,
        blockxsize=512,
        blockysize=512,
        compress=compress,
        BIGTIFF="YES",
        NUM_THREADS="ALL_CPUS",
    )
    if compress:
        dtype = np.dtype(profile["dtype"])
        if np.issubdtype(dtype, np.integer):
            profile["predictor"] = 2
        elif np.issubdtype(dtype, np.floating):
            profile["predictor"] = 3
    return profile


# Função para reprojetar uma cena para o CRS alvo. 
def ensure_same_crs(input_path, output_path, target_crs, num_threads=1):
    with rio.open(input_path) as src:
        if src.crs == target_crs:
            return input_path

        transform, width, height = calculate_default_transform(
            src.crs, target_crs, src.width, src.height, *src.bounds
        )
        kwargs = tiled_gtiff_profile(src.meta.copy())
        kwargs.update(
            {
                "crs": target_crs,
                "transform": transform,
                "width": width,
                "height": height,
                "nodata": NODATA_VALUE,
            }
        )

        with rio.open(output_path, "w", **kwargs) as dst:
            bands = list(range(1, src.count + 1))
            reproject(
                source=rio.band(src, bands),
                destination=rio.band(dst, bands),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=target_crs,
                resampling=Resampling.bilinear,
                dst_nodata=NODATA_VALUE,
                num_threads=num_threads,
            )
    return output_path


# Função para calcular a área de interseção entre os limites de duas cenas
def intersection_bounds(a_bounds, b_bounds):
    left = max(a_bounds.left, b_bounds.left)
    bottom = max(a_bounds.bottom, b_bounds.bottom)
    right = min(a_bounds.right, b_bounds.right)
    top = min(a_bounds.top, b_bounds.top)
    if left >= right or bottom >= top:
        return None
    return (left, bottom, right, top)


# Função para converter os limites (bounds) de uma área em uma janela válida da imagem
def window_for_bounds(src, bounds):
    try:
        window = from_bounds(*bounds, transform=src.transform)
        window = window.round_offsets().round_lengths()
        return window.intersection(Window(0, 0, src.width, src.height))
    except WindowError:
        return None


# Função para garantir que uma janela (possivelmente fracionada) não saia dos limites da imagem
def clamp_window(window, width, height):
    col_start = min(max(window.col_off, 0.0), float(width))
    row_start = min(max(window.row_off, 0.0), float(height))
    col_end = min(max(window.col_off + window.width, 0.0), float(width))
    row_end = min(max(window.row_off + window.height, 0.0), float(height))
    if col_end <= col_start or row_end <= row_start:
        return None
    return Window(col_start, row_start, col_end - col_start, row_end - row_start)


# Função para ler uma amostra de dados de uma janela específica da imagem
def read_window_sample(src, window, out_shape):
    return src.read(
        window=window,
        out_shape=(src.count, out_shape[0], out_shape[1]),
        out_dtype="float32",
        resampling=Resampling.bilinear,
    )


# Função para ler uma amostra reduzida da cena inteira (usada nas estatísticas de cor)
def read_scene_sample(src, sample_max_size):
    max_size = max(src.width, src.height)
    scale = max(1.0, max_size / sample_max_size)
    out_height = max(1, int(round(src.height / scale)))
    out_width = max(1, int(round(src.width / scale)))
    return src.read(
        out_shape=(src.count, out_height, out_width),
        out_dtype="float32",
        resampling=Resampling.bilinear,
    )