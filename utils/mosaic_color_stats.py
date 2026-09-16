import numpy as np
import rasterio as rio
from utils.mosaic_geometry import NODATA_VALUE, read_scene_sample

DEFAULT_COLOR_TARGET = "median"

# 1. Estatísticas básicas de brilho/cor
# Função para calcular o brilho de cada pixel a partir das bandas RGB
def brightness(data):
    if data.shape[0] >= 3:
        red, green, blue = data[0], data[1], data[2]
        return 0.299 * red + 0.587 * green + 0.114 * blue
    return np.mean(data, axis=0)


# Função para calcular percentis com segurança quando não há pixels válidos
def safe_percentile(values, percentiles):
    if values.size == 0:
        return None
    return np.percentile(values, percentiles)


# Função para remover pixels extremos (muito escuros ou muito claros) de uma máscara
def mask_without_extremes(data, valid_mask, lower_percentile=2, upper_percentile=98):
    if not np.any(valid_mask):
        return valid_mask

    scene_brightness = brightness(data)
    limits = safe_percentile(scene_brightness[valid_mask], (lower_percentile, upper_percentile))
    if limits is None:
        return valid_mask

    low, high = limits
    if high <= low:
        return valid_mask

    return valid_mask & (scene_brightness >= low) & (scene_brightness <= high)


# Função para obter uma máscara ampla da cena, usada na normalização global
def broad_scene_mask(data, valid_mask=None):
    if valid_mask is None:
        valid_mask = np.all(data > NODATA_VALUE, axis=0)

    mask = mask_without_extremes(data, valid_mask, 2, 98)
    if data.shape[0] < 3 or not np.any(mask):
        return mask

    red = data[0]
    green = data[1]
    blue = data[2]
    scene_brightness = brightness(data)
    rgb_max = np.maximum.reduce([red, green, blue])
    rgb_min = np.minimum.reduce([red, green, blue])
    saturation = (rgb_max - rgb_min) / np.maximum(scene_brightness, 1.0)

    valid_brightness = scene_brightness[valid_mask]
    if valid_brightness.size == 0:
        return mask

    p20, p92, p97 = np.percentile(valid_brightness, (20, 92, 97))
    neutral_cloud = (scene_brightness > p92) & (saturation < 0.22)
    very_bright = scene_brightness > p97
    saturated_color = (scene_brightness > p20) & (saturation > 0.90)

    return mask & ~neutral_cloud & ~very_bright & ~saturated_color


# Função para obter só os pixels de terra firme úteis para estatística de cor, ignorando extremos
def clear_land_mask(data, valid_mask=None):
    if valid_mask is None:
        valid_mask = np.all(data > NODATA_VALUE, axis=0)

    mask = mask_without_extremes(data, valid_mask, 1, 96)
    if data.shape[0] < 3 or not np.any(mask):
        return mask

    red = data[0]
    green = data[1]
    blue = data[2]
    scene_brightness = brightness(data)
    rgb_max = np.maximum.reduce([red, green, blue])
    rgb_min = np.minimum.reduce([red, green, blue])
    saturation = (rgb_max - rgb_min) / np.maximum(scene_brightness, 1.0)

    valid_brightness = scene_brightness[valid_mask]
    if valid_brightness.size == 0:
        return mask

    p10, p20, p55, p82, p90, p96 = np.percentile(
        valid_brightness, (10, 20, 55, 82, 90, 96)
    )

    blue_dominant = (blue > red * 1.10) & (blue > green * 0.94)
    cyan_dominant = (green > red * 1.08) & (blue > red * 1.04)
    dark_water = (scene_brightness < p55) & (blue > red * 1.04) & (green > red * 0.92)
    bright_coastal_water = cyan_dominant & (scene_brightness < p90) & (saturation > 0.10)
    medium_blue_water = (
        blue_dominant
        & (scene_brightness < p82)
        & (saturation > 0.16)
        & (red < green * 0.92)
    )
    open_water = dark_water | bright_coastal_water | medium_blue_water

    very_dark_shadow = scene_brightness < max(1.0, p20 * 0.60)
    bright_neutral_cloud = (scene_brightness > p90) & (saturation < 0.24)
    bright_colored_cloud = (scene_brightness > p96) & (saturation < 0.42)
    bright_blue_haze = (scene_brightness > p90) & blue_dominant & (saturation < 0.38)
    saturated_outlier = (scene_brightness > p10) & (saturation > 0.85)

    return (
        mask
        & ~open_water
        & ~very_dark_shadow
        & ~bright_neutral_cloud
        & ~bright_colored_cloud
        & ~bright_blue_haze
        & ~saturated_outlier
    )


# Função para obter a máscara de pixels válidos e comparáveis na sobreposição de duas cenas
def valid_overlap_mask(reference, source):
    mask = np.all(reference > NODATA_VALUE, axis=0) & np.all(source > NODATA_VALUE, axis=0)
    if not np.any(mask):
        return mask

    reference_land = clear_land_mask(reference, mask)
    source_land = clear_land_mask(source, mask)
    land_mask = mask & reference_land & source_land

    if np.count_nonzero(land_mask) >= 500:
        return land_mask

    # Fallback conservador: se a sobreposicao quase toda for mar/nuvem, nao usa agua,
    # mas ainda permite alguma terra escura ou urbana para evitar perder cenas isoladas.
    reference_brightness = brightness(reference)
    source_brightness = brightness(source)
    reference_limits = safe_percentile(reference_brightness[mask], (5, 95))
    source_limits = safe_percentile(source_brightness[mask], (5, 95))
    if reference_limits is None or source_limits is None:
        return land_mask

    reference_low, reference_high = reference_limits
    source_low, source_high = source_limits
    relaxed = (
        mask
        & (reference_brightness >= reference_low)
        & (reference_brightness <= reference_high)
        & (source_brightness >= source_low)
        & (source_brightness <= source_high)
    )
    return relaxed & (reference_land | source_land)


# 2. Perfis de cor (estatísticas por banda + brilho + proporções RGB)

# Função para calcular estatísticas (baixo/médio/alto) de cada banda dentro de uma máscara
def band_stats(data, mask, lower_percentile, upper_percentile):
    if np.count_nonzero(mask) == 0:
        return None

    stats = []
    for band_index in range(data.shape[0]):
        values = data[band_index][mask]
        low, mid, high = np.percentile(
            values, (lower_percentile, 50, upper_percentile)
        )
        stats.append({"low": float(low), "mid": float(mid), "high": float(high)})
    return stats


# Função para calcular estatísticas de brilho (baixo/médio/alto) dentro de uma máscara
def brightness_stats(data, mask, lower_percentile, upper_percentile):
    if np.count_nonzero(mask) == 0:
        return None

    values = brightness(data)[mask]
    low, mid, high = np.percentile(values, (lower_percentile, 50, upper_percentile))
    return {"low": float(low), "mid": float(mid), "high": float(high)}


# Função para calcular a proporção de cada banda de cor em relação ao brilho
def color_ratio_stats(data, mask):
    if data.shape[0] < 3 or np.count_nonzero(mask) == 0:
        return [1.0 for _ in range(data.shape[0])]

    scene_brightness = np.maximum(brightness(data), 1.0)
    ratios = []
    for band_index in range(data.shape[0]):
        if band_index < 3:
            values = data[band_index][mask] / scene_brightness[mask]
            values = np.clip(values, 0.2, 3.0)
            ratios.append(float(np.median(values)))
        else:
            ratios.append(1.0)
    return ratios


# Função para montar o perfil de cor completo de uma amostra (estatísticas + brilho + proporções)
def color_profile(data, mask, lower_percentile, upper_percentile):
    stats = band_stats(data, mask, lower_percentile, upper_percentile)
    stats_brightness = brightness_stats(data, mask, lower_percentile, upper_percentile)
    if stats is None or stats_brightness is None:
        return None

    return {
        "stats": stats,
        "luma": stats_brightness,
        "ratios": color_ratio_stats(data, mask),
    }


# 3. Amostragem de estatísticas por cena

# Função para estimar o perfil de cor de uma cena inteira (usado na normalização global)
def estimate_scene_color_stats(scene_path, sample_max_size=1600, min_valid_pixels=3000, lower_percentile=10, upper_percentile=90,
):
    with rio.open(scene_path) as src:
        data = read_scene_sample(src, sample_max_size)

    valid_mask = np.all(data > NODATA_VALUE, axis=0)
    mask = broad_scene_mask(data, valid_mask)
    pixels = int(np.count_nonzero(mask))

    if pixels < min_valid_pixels:
        mask = mask_without_extremes(data, valid_mask, 2, 98)
        pixels = int(np.count_nonzero(mask))

    if pixels < min_valid_pixels:
        return None

    profile = color_profile(data, mask, lower_percentile, upper_percentile)
    if profile is None:
        return None

    profile["pixels"] = pixels
    return profile


# 3. Combinação de estatísticas de várias cenas em um alvo (mediana ou referência)

# Função para calcular a mediana das estatísticas de banda entre várias cenas
def median_stats_from_scenes(available):
    band_count = len(available[0]["stats"])
    target = []
    for band_index in range(band_count):
        target.append(
            {
                "low": float(np.median([item["stats"][band_index]["low"] for item in available])),
                "mid": float(np.median([item["stats"][band_index]["mid"] for item in available])),
                "high": float(np.median([item["stats"][band_index]["high"] for item in available])),
            }
        )
    return target


# Função para calcular o perfil "mediano" (brilho + proporções) entre várias cenas
def median_profile_from_scenes(available):
    target = {
        "stats": median_stats_from_scenes(available),
        "luma": {
            "low": float(np.median([item["luma"]["low"] for item in available])),
            "mid": float(np.median([item["luma"]["mid"] for item in available])),
            "high": float(np.median([item["luma"]["high"] for item in available])),
        },
        "ratios": [],
    }

    band_count = len(available[0]["ratios"])
    for band_index in range(band_count):
        target["ratios"].append(
            float(np.median([item["ratios"][band_index] for item in available]))
        )
    return target


# Função para escolher o perfil de cor alvo entre as cenas (mediana geral ou a cena de referência)
def target_profile_from_scenes(scene_profiles, reference_index=0, target_strategy=DEFAULT_COLOR_TARGET,
):
    available = [item for item in scene_profiles if item is not None]
    if not available:
        return None

    if target_strategy == "reference":
        if (
            0 <= reference_index < len(scene_profiles)
            and scene_profiles[reference_index] is not None
        ):
            return scene_profiles[reference_index]
        return median_profile_from_scenes(available)

    return median_profile_from_scenes(available)