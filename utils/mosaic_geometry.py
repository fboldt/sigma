import shutil
import rasterio as rio
from rasterio.enums import Resampling
from rasterio.errors import WindowError
from rasterio.warp import calculate_default_transform, reproject
from rasterio.windows import Window, from_bounds

NODATA_VALUE = 0


# Função para reprojetar uma cena para o CRS alvo (ou só copiar, se já estiver no CRS certo)
def ensure_same_crs(input_path, output_path, target_crs):
    with rio.open(input_path) as src:
        if src.crs == target_crs:
            shutil.copy(input_path, output_path)
            return output_path

        transform, width, height = calculate_default_transform(
            src.crs, target_crs, src.width, src.height, *src.bounds
        )
        kwargs = src.meta.copy()
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
            for i in range(1, src.count + 1):
                reproject(
                    source=rio.band(src, i),
                    destination=rio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=target_crs,
                    resampling=Resampling.bilinear,
                    dst_nodata=NODATA_VALUE,
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