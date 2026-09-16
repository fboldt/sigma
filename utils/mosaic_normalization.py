import numpy as np
import rasterio as rio
from utils.mosaic_color_stats import (
    DEFAULT_COLOR_TARGET,
    brightness,
    color_profile,
    estimate_scene_color_stats,
    target_profile_from_scenes,
    valid_overlap_mask,
)
from utils.mosaic_geometry import (
    NODATA_VALUE,
    intersection_bounds,
    read_window_sample,
    window_for_bounds,
)

DEFAULT_CLIP_MAX = 1023

# Conversão de perfis de cor em transformações (ganho/offset por banda)

# Função para limitar o quanto as bandas RGB podem se afastar umas das outras
def regularize_rgb_transforms(transforms, max_gain_ratio=1.16, max_offset_delta=42.0,
):
    if len(transforms) < 3:
        return transforms

    gains = np.array([transform["gain"] for transform in transforms[:3]], dtype="float32")
    offsets = np.array([transform["offset"] for transform in transforms[:3]], dtype="float32")
    gain_center = float(np.median(gains))
    offset_center = float(np.median(offsets))

    min_gain = gain_center / max_gain_ratio
    max_gain = gain_center * max_gain_ratio
    for transform in transforms[:3]:
        transform["gain"] = float(np.clip(transform["gain"], min_gain, max_gain))
        transform["offset"] = float(
            np.clip(
                transform["offset"],
                offset_center - max_offset_delta,
                offset_center + max_offset_delta,
            )
        )
    return transforms


# Função para calcular o ganho/offset de cada banda a partir de dois perfis de cor
def profile_to_transforms(source_profile, target_profile, gain_limits=(0.55, 1.55), offset_limit=120.0, strength=0.90, color_gain_limits=(0.94, 1.06),
):
    source_brightness = source_profile["luma"]
    target_brightness = target_profile["luma"]
    source_range = source_brightness["high"] - source_brightness["low"]
    target_range = target_brightness["high"] - target_brightness["low"]

    if source_range <= 1 or target_range <= 1:
        raw_gain = 1.0
        raw_offset = target_brightness["mid"] - source_brightness["mid"]
    else:
        raw_gain = float(np.clip(target_range / source_range, *gain_limits))
        raw_offset = float(target_brightness["mid"] - raw_gain * source_brightness["mid"])

    brightness_gain = 1.0 + (raw_gain - 1.0) * strength
    brightness_offset = float(np.clip(raw_offset * strength, -offset_limit, offset_limit))

    transforms = []
    for band_index, source_ratio in enumerate(source_profile["ratios"]):
        if band_index < len(target_profile["ratios"]) and source_ratio > 0:
            raw_color_gain = target_profile["ratios"][band_index] / source_ratio
            color_gain = float(np.clip(raw_color_gain, *color_gain_limits))
            color_gain = 1.0 + (color_gain - 1.0) * min(1.0, strength)
        else:
            color_gain = 1.0

        transforms.append(
            {
                "gain": float(brightness_gain * color_gain),
                "offset": brightness_offset,
            }
        )

    return regularize_rgb_transforms(transforms, max_gain_ratio=1.08, max_offset_delta=12.0,
    )

# API de estimativa de transformações

# Função para estimar o ajuste de cor de cada cena em relação a um alvo global (todas as cenas)
def estimate_global_color_transforms(crs_files, reference_index=0, target_strategy=DEFAULT_COLOR_TARGET, strength=0.60,
):
    scene_profiles = []
    for index, path in enumerate(crs_files):
        profile = estimate_scene_color_stats(path)
        scene_profiles.append(profile)

    target_profile = target_profile_from_scenes(
        scene_profiles,
        reference_index,
        target_strategy=target_strategy,
    )
    if target_profile is None:
        return [None for _ in crs_files]

    transforms = []
    for profile in scene_profiles:
        if profile is None:
            transforms.append(None)
        else:
            transforms.append(
                profile_to_transforms(
                    profile,
                    target_profile,
                    gain_limits=(0.55, 1.55),
                    offset_limit=120.0,
                    strength=strength,
                )
            )
    return transforms


# Função para aplicar o ganho/offset de cada banda diretamente em um array de pixels
def apply_transforms_to_array(data, transforms):
    corrected = data.astype("float32", copy=True)
    for band_index, transform in enumerate(transforms):
        corrected[band_index] = (
            corrected[band_index] * transform["gain"] + transform["offset"]
        )
    return corrected


# Função para medir o quanto uma cena está puxando pro verde (sinal de erro de cor)
def green_tint_index(data):
    if data.shape[0] < 3:
        return np.zeros(data.shape[1:], dtype="float32")
    red, green, blue = data[0], data[1], data[2]
    return (green - 0.5 * (red + blue)) / np.maximum(brightness(data), 1.0)


# Função para medir o quão boa ficou uma transformação de cor, comparando com a referência
def estimate_transform_quality(reference, source, mask, transforms):
    corrected = apply_transforms_to_array(source, transforms)
    reference_brightness = brightness(reference)[mask]
    corrected_brightness = brightness(corrected)[mask]
    if reference_brightness.size == 0 or corrected_brightness.size == 0:
        return None

    reference_tint = green_tint_index(reference)[mask]
    corrected_tint = green_tint_index(corrected)[mask]
    high_clip = np.any(corrected[:3] >= DEFAULT_CLIP_MAX, axis=0)[mask]
    low_clip = np.any(corrected[:3] <= NODATA_VALUE, axis=0)[mask]

    return {
        "luma_delta": float(np.median(corrected_brightness) - np.median(reference_brightness)),
        "green_delta": float(np.median(corrected_tint) - np.median(reference_tint)),
        "high_clip_fraction": float(np.mean(high_clip)),
        "low_clip_fraction": float(np.mean(low_clip)),
    }


# Função para decidir se uma transformação de cor é segura o suficiente pra ser usada
def transforms_are_safe(metrics):
    if metrics is None:
        return False

    return (
        abs(metrics["luma_delta"]) <= 55.0
        and abs(metrics["green_delta"]) <= 0.10
        and metrics["high_clip_fraction"] <= 0.015
        and metrics["low_clip_fraction"] <= 0.020
    )


# Função para estimar o ganho/offset de cada banda a partir da área de sobreposição entre duas cenas
def estimate_overlap_match( reference_path, source_path, sample_max_size=1400, min_valid_pixels=1000, lower_percentile=20, upper_percentile=80, strength=0.75,
):
    with rio.open(reference_path) as reference_src, rio.open(source_path) as source_src:
        if reference_src.count != source_src.count:
            raise ValueError("As cenas precisam ter o mesmo numero de bandas.")

        bounds = intersection_bounds(reference_src.bounds, source_src.bounds)
        if bounds is None:
            return None

        reference_window = window_for_bounds(reference_src, bounds)
        source_window = window_for_bounds(source_src, bounds)
        if reference_window is None or source_window is None:
            return None

        max_window_size = max(
            reference_window.width,
            reference_window.height,
            source_window.width,
            source_window.height,
        )
        scale = max(1.0, max_window_size / sample_max_size)
        out_height = max(1, int(round(max(reference_window.height, source_window.height) / scale)))
        out_width = max(1, int(round(max(reference_window.width, source_window.width) / scale)))

        reference = read_window_sample(reference_src, reference_window, (out_height, out_width))
        source = read_window_sample(source_src, source_window, (out_height, out_width))

    mask = valid_overlap_mask(reference, source)
    valid_pixels = int(np.count_nonzero(mask))
    if valid_pixels < min_valid_pixels:
        return None

    reference_profile = color_profile(reference, mask, lower_percentile, upper_percentile)
    source_profile = color_profile(source, mask, lower_percentile, upper_percentile)
    if reference_profile is None or source_profile is None:
        return None

    transforms = profile_to_transforms(
        source_profile,
        reference_profile,
        gain_limits=(0.65, 1.45),
        offset_limit=90.0,
        strength=strength,
    )
    metrics = estimate_transform_quality(reference, source, mask, transforms)
    if not transforms_are_safe(metrics):
        return None

    return {"pixels": valid_pixels, "transforms": transforms, "metrics": metrics}


# Aplicação das transformações nos arquivos em disco

# Função para descobrir o valor máximo de corte permitido pelo tipo de dado da cena
def clip_max_for_dtype(dtype, requested_clip_max):
    dtype = np.dtype(dtype)
    if np.issubdtype(dtype, np.integer):
        dtype_max = np.iinfo(dtype).max
        return min(dtype_max, requested_clip_max)
    return requested_clip_max


# Função para aplicar o ganho/offset de cada banda em uma cena inteira e salvar o resultado
def apply_band_transforms(source_path, output_path, transforms, clip_min=0, clip_max=DEFAULT_CLIP_MAX):
    with rio.open(source_path) as src:
        profile = src.profile.copy()
        profile.update(nodata=NODATA_VALUE, compress="lzw", BIGTIFF="YES")
        output_clip_max = clip_max_for_dtype(src.dtypes[0], clip_max)

        with rio.open(output_path, "w", **profile) as dst:
            for _, window in src.block_windows(1):
                data = src.read(window=window).astype("float32")
                valid_mask = np.all(data > NODATA_VALUE, axis=0)

                data = apply_transforms_to_array(data, transforms)

                data = np.clip(data, clip_min, output_clip_max)
                data[:, ~valid_mask] = NODATA_VALUE
                dst.write(data.astype(src.dtypes[0]), window=window)

    return output_path


# Função para gerar transformações "neutras" (sem alterar nada), usadas como último recurso
def identity_transforms(path):
    with rio.open(path) as src:
        return [{"gain": 1.0, "offset": 0.0} for _ in range(src.count)]