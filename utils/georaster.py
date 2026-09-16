from __future__ import annotations

from pathlib import Path
from typing import Sequence

import math
import numpy as np
import rasterio as rio
from rasterio.enums import Resampling
from rasterio.merge import copy_count, copy_sum, merge
from rasterio.transform import Affine
from rasterio.warp import calculate_default_transform, reproject, transform_bounds
from rasterio.windows import Window
from rasterio.windows import transform as window_transform

from .pansharpening_core import pansharpen_hsv_tiled
from .raster_common import (
    EPSILON,
    _apply_colorinterp,
    _apply_tiff_layout,
    _iter_windows,
    intersection_window,
)


def _read_reprojected_band(
    src: rio.io.DatasetReader,
    reference: rio.io.DatasetReader,
    window: Window,
    resampling: Resampling,
) -> np.ndarray:
    destination = np.full((int(window.height), int(window.width)), np.nan, dtype=np.float32)

    reproject(
        source=rio.band(src, 1),
        destination=destination,
        src_transform=src.transform,
        src_crs=src.crs,
        src_nodata=src.nodata,
        dst_transform=window_transform(window, reference.transform),
        dst_crs=reference.crs,
        dst_nodata=np.nan,
        resampling=resampling,
    )

    return destination


def stack_rgb_aligned(
    red_band: str,
    green_band: str,
    blue_band: str,
    output_file_path: str,
    crop_to_intersection: bool = True,
    resampling: Resampling = Resampling.bilinear,
) -> Path:
    output_path = Path(output_file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rio.open(red_band) as red_ds, rio.open(green_band) as green_ds, rio.open(blue_band) as blue_ds:
        if red_ds.crs is None:
            raise ValueError("A banda vermelha precisa ter CRS definido.")

        datasets = [red_ds, green_ds, blue_ds]
        window = (
            intersection_window(red_ds, datasets)
            if crop_to_intersection
            else Window(0, 0, red_ds.width, red_ds.height)
        )

        red = _read_reprojected_band(red_ds, red_ds, window, resampling)
        green = _read_reprojected_band(green_ds, red_ds, window, resampling)
        blue = _read_reprojected_band(blue_ds, red_ds, window, resampling)
        stacked = np.stack([red, green, blue], axis=0)

        output_dtype = np.dtype(red_ds.dtypes[0])
        nodata_value = 0
        stacked = np.nan_to_num(stacked, nan=nodata_value)

        if np.issubdtype(output_dtype, np.integer):
            info = np.iinfo(output_dtype)
            stacked = np.clip(stacked, info.min, info.max).astype(output_dtype)
            profile_dtype = output_dtype.name
        else:
            stacked = stacked.astype(np.float32)
            profile_dtype = "float32"

        profile = red_ds.profile.copy()
        profile.update(
            driver="GTiff",
            count=3,
            dtype=profile_dtype,
            width=int(window.width),
            height=int(window.height),
            transform=window_transform(window, red_ds.transform),
            nodata=nodata_value,
        )
        profile = _apply_tiff_layout(profile, int(window.width), int(window.height))

        with rio.open(output_path, "w", **profile) as dst:
            dst.write(stacked)
            _apply_colorinterp(dst)

    return output_path


def reproject_raster(
    input_path: str,
    output_path: str,
    dst_crs: str,
    resampling: Resampling = Resampling.cubic,
    dst_transform: Affine | None = None,
    dst_width: int | None = None,
    dst_height: int | None = None,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with rio.open(input_path) as src:
        source_colorinterp = tuple(src.colorinterp[: src.count])
        if dst_transform is None or dst_width is None or dst_height is None:
            # Sem grade de saida predefinida, o Rasterio escolhe sozinho uma
            # transformacao "boa o suficiente" para esta cena isolada.
            transform, width, height = calculate_default_transform(
                src.crs, dst_crs, src.width, src.height, *src.bounds
            )
        else:
            # Quando a grade comum ja foi calculada externamente, usamos essa
            # malha fixa para garantir que varias cenas sobrepostas caiam na
            # mesma matriz de pixels apos a reprojecao.
            transform = dst_transform
            width = int(dst_width)
            height = int(dst_height)

        profile = src.profile.copy()
        profile.update(crs=dst_crs, transform=transform, width=width, height=height)
        profile = _apply_tiff_layout(profile, width, height)

        with rio.open(output, "w", **profile) as dst:
            for band_index in range(1, src.count + 1):
                # A reprojecao acontece banda a banda, preservando nodata,
                # georreferenciamento e o metodo de interpolacao escolhido.
                reproject(
                    source=rio.band(src, band_index),
                    destination=rio.band(dst, band_index),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    src_nodata=src.nodata,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    dst_nodata=src.nodata,
                    resampling=resampling,
                )
            _apply_colorinterp(dst, source_colorinterp)

    return output


def compute_common_reprojection_grid(
    raster_paths: Sequence[str],
    dst_crs: str,
) -> tuple[float, float, float, float]:
    datasets = [rio.open(path) for path in raster_paths]
    try:
        if not datasets:
            raise ValueError("Nenhum raster foi informado para calcular a grade comum.")

        bounds_list: list[tuple[float, float, float, float]] = []
        resolutions: list[tuple[float, float]] = []

        for dataset in datasets:
            bounds_list.append(transform_bounds(dataset.crs, dst_crs, *dataset.bounds, densify_pts=21))

            if str(dataset.crs) == str(dst_crs):
                resolutions.append((abs(dataset.res[0]), abs(dataset.res[1])))
            else:
                transform, _, _ = calculate_default_transform(
                    dataset.crs, dst_crs, dataset.width, dataset.height, *dataset.bounds
                )
                resolutions.append((abs(transform.a), abs(transform.e)))

        # A grade comum usa:
        # - o envelope total do conjunto de rasters;
        # - a menor resolucao de pixel encontrada;
        # - limites arredondados para multiplos exatos dessa resolucao.
        # Assim todas as cenas passam a "encaixar" na mesma malha espacial.
        left = min(bounds[0] for bounds in bounds_list)
        bottom = min(bounds[1] for bounds in bounds_list)
        right = max(bounds[2] for bounds in bounds_list)
        top = max(bounds[3] for bounds in bounds_list)

        res_x = min(resolution[0] for resolution in resolutions)
        res_y = min(resolution[1] for resolution in resolutions)

        left = math.floor(left / res_x) * res_x
        bottom = math.floor(bottom / res_y) * res_y
        right = math.ceil(right / res_x) * res_x
        top = math.ceil(top / res_y) * res_y

        return left, top, res_x, res_y
    finally:
        for dataset in datasets:
            dataset.close()


def aligned_transform_for_bounds(
    bounds: tuple[float, float, float, float],
    origin_left: float,
    origin_top: float,
    res_x: float,
    res_y: float,
) -> tuple[Affine, int, int]:
    left, bottom, right, top = bounds

    # Este alinhamento nao expande o raster para o tamanho do mosaico inteiro.
    # Ele so desloca os limites da cena para coincidirem com a grade comum.
    aligned_left = origin_left + (math.floor((left - origin_left) / res_x) * res_x)
    aligned_right = origin_left + (math.ceil((right - origin_left) / res_x) * res_x)
    aligned_top = origin_top - (math.floor((origin_top - top) / res_y) * res_y)
    aligned_bottom = origin_top - (math.ceil((origin_top - bottom) / res_y) * res_y)

    width = max(1, int(round((aligned_right - aligned_left) / res_x)))
    height = max(1, int(round((aligned_top - aligned_bottom) / res_y)))
    transform = Affine(res_x, 0.0, aligned_left, 0.0, -res_y, aligned_top)

    return transform, width, height


def mosaic_rasters(
    raster_paths: Sequence[str],
    output_path: str,
    method: str = "first",
    mem_limit_mb: int = 256,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    datasets = [rio.open(path) for path in raster_paths]
    try:
        source_colorinterp = tuple(datasets[0].colorinterp[: datasets[0].count]) if datasets else ()
        output_dtype = np.dtype(datasets[0].dtypes[0]) if datasets else np.float32

        if method == "average":
            # Para RGB, "average" suaviza a transicao nas sobreposicoes:
            # somamos os valores das cenas e dividimos pela quantidade de
            # contribuicoes validas em cada pixel.
            summed, out_transform = merge(datasets, method=copy_sum, mem_limit=mem_limit_mb)
            counts, _ = merge(datasets, method=copy_count, mem_limit=mem_limit_mb)
            mosaic = np.divide(
                summed,
                np.maximum(counts, 1),
                out=np.zeros_like(summed, dtype=np.float32),
                where=counts > 0,
            )
            if np.issubdtype(output_dtype, np.integer):
                info = np.iinfo(output_dtype)
                mosaic = np.clip(np.rint(mosaic), max(info.min, 0), info.max).astype(output_dtype)

            profile = datasets[0].profile.copy()
            profile.update(
                driver="GTiff",
                height=mosaic.shape[1],
                width=mosaic.shape[2],
                transform=out_transform,
                count=mosaic.shape[0],
                dtype=np.dtype(mosaic.dtype).name,
            )
            profile = _apply_tiff_layout(profile, mosaic.shape[2], mosaic.shape[1])

            with rio.open(output, "w", **profile) as dst:
                dst.write(mosaic)
                _apply_colorinterp(dst, source_colorinterp)
        else:
            # "first" e o comportamento mais conservador e, para produtos
            # grandes como o pansharpening em 2 m, pode ser escrito direto
            # no disco para evitar manter o mosaico inteiro em memoria.
            dst_kwds = datasets[0].profile.copy()
            dst_kwds.update(
                driver="GTiff",
                count=datasets[0].count,
                dtype=output_dtype.name,
                compress="deflate",
                BIGTIFF="IF_SAFER",
                tiled=True,
                blockxsize=512,
                blockysize=512,
            )
            merge(
                datasets,
                method=method,
                mem_limit=mem_limit_mb,
                dst_path=str(output),
                dst_kwds=dst_kwds,
            )
            with rio.open(output, "r+") as dst:
                _apply_colorinterp(dst, source_colorinterp)
    finally:
        for dataset in datasets:
            dataset.close()

    return output


def render_rgb_visual(
    input_path: str,
    output_path: str,
    low_percentile: float = 2.0,
    high_percentile: float = 98.0,
    gamma: float = 1.15,
    tile_size: int = 2048,
    sample_size: int = 2048,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with rio.open(input_path) as src:
        if src.count < 3:
            raise ValueError("O raster precisa ter pelo menos 3 bandas para gerar visual RGB.")

        sample_height = min(sample_size, src.height)
        sample_width = min(sample_size, src.width)
        sample = src.read(
            [1, 2, 3],
            out_shape=(3, sample_height, sample_width),
            masked=True,
        ).astype(np.float32)

        valid_sample = np.all(~sample.mask, axis=0)
        if not np.any(valid_sample):
            raise ValueError("Nao foi possivel amostrar pixels validos para gerar o visual RGB.")

        channel_limits: list[tuple[float, float]] = []
        for band_index in range(3):
            values = sample[band_index].data[valid_sample]
            low = float(np.percentile(values, low_percentile))
            high = float(np.percentile(values, high_percentile))
            if not np.isfinite(low) or not np.isfinite(high) or high <= low:
                high = low + 1.0
            channel_limits.append((low, high))

        profile = src.profile.copy()
        profile.update(
            driver="GTiff",
            count=3,
            dtype="uint8",
            nodata=0,
        )
        profile = _apply_tiff_layout(profile, src.width, src.height)

        full_window = Window(0, 0, src.width, src.height)

        with rio.open(output, "w", **profile) as dst:
            for window in _iter_windows(full_window, tile_size):
                rgb = src.read([1, 2, 3], window=window, masked=True).astype(np.float32)
                valid = np.all(~rgb.mask, axis=0)
                rendered = np.zeros((3, int(window.height), int(window.width)), dtype=np.uint8)

                for band_index, (low, high) in enumerate(channel_limits):
                    stretched = np.clip((rgb[band_index].data - low) / (high - low), 0.0, 1.0)
                    stretched = np.power(stretched, 1.0 / max(gamma, EPSILON))
                    rendered[band_index] = np.round(stretched * 255.0).astype(np.uint8)

                if np.any(~valid):
                    rendered[:, ~valid] = 0

                dst.write(rendered, window=window)

            _apply_colorinterp(dst)

    return output


def _sample_rgb_percentile_limits(
    dataset: rio.io.DatasetReader,
    low_percentile: float,
    high_percentile: float,
    sample_size: int,
) -> np.ndarray:
    sample_height = min(sample_size, dataset.height)
    sample_width = min(sample_size, dataset.width)
    sample = dataset.read(
        [1, 2, 3],
        out_shape=(3, sample_height, sample_width),
        masked=True,
    ).astype(np.float32)

    valid = np.all(~sample.mask, axis=0)
    if not np.any(valid):
        raise ValueError("Nao foi possivel amostrar pixels validos para equalizar o RGB.")

    rgb_data = sample.data
    luma = (
        0.299 * rgb_data[0]
        + 0.587 * rgb_data[1]
        + 0.114 * rgb_data[2]
    )
    max_band = np.max(rgb_data[:3], axis=0)
    min_band = np.min(rgb_data[:3], axis=0)
    saturation = (max_band - min_band) / np.maximum(max_band, EPSILON)
    blue_ratio = rgb_data[2] / np.maximum(np.sum(rgb_data[:3], axis=0), EPSILON)

    luma_values = luma[valid]
    dark_limit = float(np.percentile(luma_values, 1))
    bright_limit = float(np.percentile(luma_values, 92))
    stable = (
        valid
        & (luma >= dark_limit)
        & (luma <= bright_limit)
        & (saturation <= 0.88)
        & (blue_ratio <= 0.55)
    )
    if int(np.count_nonzero(stable)) >= 1000:
        valid = stable

    limits: list[tuple[float, float]] = []
    for band_index in range(3):
        values = sample[band_index].data[valid]
        low = float(np.percentile(values, low_percentile))
        high = float(np.percentile(values, high_percentile))
        if not np.isfinite(low) or not np.isfinite(high) or high <= low:
            high = low + 1.0
        limits.append((low, high))

    return np.asarray(limits, dtype=np.float32)


def harmonize_rgb_rasters(
    raster_paths: Sequence[str],
    output_dir: str,
    low_percentile: float = 2.0,
    high_percentile: float = 98.0,
    sample_size: int = 2048,
    tile_size: int = 2048,
) -> list[Path]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    source_paths = [Path(path) for path in raster_paths]
    if not source_paths:
        return []

    source_limits: list[np.ndarray] = []
    for source_path in source_paths:
        with rio.open(source_path) as src:
            if src.count < 3:
                raise ValueError(f"O raster {source_path} precisa ter pelo menos 3 bandas RGB.")
            source_limits.append(
                _sample_rgb_percentile_limits(
                    src,
                    low_percentile=low_percentile,
                    high_percentile=high_percentile,
                    sample_size=sample_size,
                )
            )

    target_limits = np.median(np.stack(source_limits, axis=0), axis=0)
    outputs: list[Path] = []

    for source_path, limits in zip(source_paths, source_limits):
        output_path = output_root / source_path.name
        outputs.append(output_path)

        with rio.open(source_path) as src:
            profile = src.profile.copy()
            profile.update(driver="GTiff", nodata=src.nodata if src.nodata is not None else 0)
            profile = _apply_tiff_layout(profile, src.width, src.height)

            output_dtype = np.dtype(src.dtypes[0])
            full_window = Window(0, 0, src.width, src.height)

            with rio.open(output_path, "w", **profile) as dst:
                for window in _iter_windows(full_window, tile_size):
                    rgb = src.read([1, 2, 3], window=window, masked=True).astype(np.float32)
                    valid = np.all(~rgb.mask, axis=0)
                    balanced = np.zeros((3, int(window.height), int(window.width)), dtype=np.float32)

                    for band_index in range(3):
                        src_low, src_high = limits[band_index]
                        tgt_low, tgt_high = target_limits[band_index]
                        normalized = np.clip(
                            (rgb[band_index].data - src_low) / max(src_high - src_low, EPSILON),
                            0.0,
                            1.0,
                        )
                        balanced[band_index] = (normalized * (tgt_high - tgt_low)) + tgt_low

                    if np.any(~valid):
                        balanced[:, ~valid] = 0

                    if np.issubdtype(output_dtype, np.integer):
                        info = np.iinfo(output_dtype)
                        balanced = np.clip(balanced, max(info.min, 0), info.max)

                    dst.write(balanced.astype(output_dtype), window=window)

                _apply_colorinterp(dst, tuple(src.colorinterp[: src.count]))

    return outputs
