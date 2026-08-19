from __future__ import annotations

from pathlib import Path

import math
import numpy as np
import rasterio as rio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from rasterio.windows import transform as window_transform
from scipy.ndimage import gaussian_filter

from .raster_common import (
    EPSILON,
    LUMINANCE_WEIGHTS,
    _apply_colorinterp,
    _apply_tiff_layout,
    _dataset_scale,
    _iter_windows,
    intersection_window,
)

def _sample_scene_stats(
    pan_ds: rio.io.DatasetReader,
    ms_ds: rio.io.DatasetReader,
    analysis_window: Window,
    pan_base_window: Window,
    tile_size: int,
    sample_stride: int,
) -> tuple[float, float, float, float]:
    pan_scale = _dataset_scale(pan_ds, [1])
    ms_scale = _dataset_scale(ms_ds, [1, 2, 3])

    pan_sum = 0.0
    pan_sum_sq = 0.0
    val_sum = 0.0
    val_sum_sq = 0.0
    valid_count = 0

    for idx, window in enumerate(_iter_windows(analysis_window, tile_size)):
        if idx % max(sample_stride, 1) != 0:
            continue

        pan_window = Window(
            col_off=pan_base_window.col_off + window.col_off,
            row_off=pan_base_window.row_off + window.row_off,
            width=window.width,
            height=window.height,
        )

        pan_raw = pan_ds.read(1, window=pan_window)
        pan_mask = pan_ds.read_masks(1, window=pan_window) > 0
        pan = pan_raw.astype(np.float32) / pan_scale

        rgb_raw = ms_ds.read([1, 2, 3], window=window)
        rgb_mask = np.all(ms_ds.read_masks([1, 2, 3], window=window) > 0, axis=0)
        rgb = np.clip(np.moveaxis(rgb_raw.astype(np.float32) / ms_scale, 0, -1), 0.0, 1.0)
        intensity = np.tensordot(rgb, LUMINANCE_WEIGHTS, axes=([2], [0]))

        valid = np.isfinite(pan) & np.isfinite(intensity) & np.all(np.isfinite(rgb), axis=2)
        valid &= pan_mask
        valid &= rgb_mask

        if not np.any(valid):
            continue

        pan_valid = pan[valid]
        value_valid = intensity[valid]
        pan_sum += float(pan_valid.sum())
        pan_sum_sq += float((pan_valid * pan_valid).sum())
        val_sum += float(value_valid.sum())
        val_sum_sq += float((value_valid * value_valid).sum())
        valid_count += int(valid.sum())

    if valid_count == 0:
        raise ValueError("Nao foi possivel calcular estatisticas validas para o pansharpening.")

    pan_mean = pan_sum / valid_count
    pan_std = math.sqrt(max((pan_sum_sq / valid_count) - (pan_mean * pan_mean), EPSILON))
    value_mean = val_sum / valid_count
    value_std = math.sqrt(max((val_sum_sq / valid_count) - (value_mean * value_mean), EPSILON))

    return pan_mean, pan_std, value_mean, value_std

def pansharpen_hsv_tiled(
    multispectral_path: str,
    panchromatic_path: str,
    output_path: str,
    tile_size: int = 2048,
    sample_stride: int = 4,
    crop_to_intersection: bool = True,
    detail_strength: float = 0.65,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with rio.open(panchromatic_path) as pan_ds, rio.open(multispectral_path) as ms_source:
        if pan_ds.crs is None or ms_source.crs is None:
            raise ValueError("PAN e RGB precisam estar georreferenciados.")
        if ms_source.count < 3:
            raise ValueError("O raster multiespectral precisa ter pelo menos 3 bandas.")

        analysis_window = (
            intersection_window(pan_ds, [pan_ds, ms_source])
            if crop_to_intersection
            else Window(0, 0, pan_ds.width, pan_ds.height)
        )
        out_transform = window_transform(analysis_window, pan_ds.transform)

        with WarpedVRT(
            ms_source,
            crs=pan_ds.crs,
            transform=out_transform,
            width=int(analysis_window.width),
            height=int(analysis_window.height),
            resampling=Resampling.bilinear,
        ) as ms_vrt:
            pan_mean, pan_std, value_mean, value_std = _sample_scene_stats(
                pan_ds=pan_ds,
                ms_ds=ms_vrt,
                analysis_window=Window(0, 0, ms_vrt.width, ms_vrt.height),
                pan_base_window=analysis_window,
                tile_size=tile_size,
                sample_stride=sample_stride,
            )

            pan_scale = _dataset_scale(pan_ds, [1])
            ms_scale = _dataset_scale(ms_source, [1, 2, 3])
            resolution_ratio = max(
                abs(ms_source.res[0] / pan_ds.res[0]),
                abs(ms_source.res[1] / pan_ds.res[1]),
            )
            blur_sigma = max(1.0, resolution_ratio / 2.0)
            blur_halo = int(math.ceil(blur_sigma * 4.0))

            output_dtype = np.dtype(ms_source.dtypes[0])
            output_scale = _dataset_scale(ms_source, [1, 2, 3])

            profile = pan_ds.profile.copy()
            profile.update(
                driver="GTiff",
                count=3,
                dtype=output_dtype.name,
                width=int(analysis_window.width),
                height=int(analysis_window.height),
                transform=out_transform,
                nodata=ms_source.nodata if ms_source.nodata is not None else 0,
            )
            profile = _apply_tiff_layout(
                profile, int(analysis_window.width), int(analysis_window.height)
            )

            with rio.open(output, "w", **profile) as dst:
                for target_window in _iter_windows(
                    Window(0, 0, analysis_window.width, analysis_window.height), tile_size
                ):
                    pan_window = Window(
                        col_off=analysis_window.col_off + target_window.col_off,
                        row_off=analysis_window.row_off + target_window.row_off,
                        width=target_window.width,
                        height=target_window.height,
                    )
                    padded_window = Window(
                        col_off=max(0, target_window.col_off - blur_halo),
                        row_off=max(0, target_window.row_off - blur_halo),
                        width=target_window.width + blur_halo * 2,
                        height=target_window.height + blur_halo * 2,
                    ).intersection(Window(0, 0, analysis_window.width, analysis_window.height))
                    padded_pan_window = Window(
                        col_off=analysis_window.col_off + padded_window.col_off,
                        row_off=analysis_window.row_off + padded_window.row_off,
                        width=padded_window.width,
                        height=padded_window.height,
                    )

                    pan_raw = pan_ds.read(1, window=pan_window)
                    pan_mask = pan_ds.read_masks(1, window=pan_window) > 0
                    pan_raw_padded = pan_ds.read(1, window=padded_pan_window)
                    pan_padded = pan_raw_padded.astype(np.float32) / pan_scale

                    rgb_raw = ms_vrt.read([1, 2, 3], window=target_window)
                    rgb_mask = np.all(ms_vrt.read_masks([1, 2, 3], window=target_window) > 0, axis=0)
                    rgb_tile = np.clip(
                        np.moveaxis(rgb_raw.astype(np.float32) / ms_scale, 0, -1),
                        0.0,
                        1.0,
                    )
                    intensity = np.tensordot(rgb_tile, LUMINANCE_WEIGHTS, axes=([2], [0]))

                    matched_pan = (
                        ((pan_padded - pan_mean) * (value_std / max(pan_std, EPSILON)))
                        + value_mean
                    )
                    low_pass_pan = gaussian_filter(matched_pan, sigma=blur_sigma, mode="reflect")
                    pan_detail = matched_pan - low_pass_pan
                    row_start = int(target_window.row_off - padded_window.row_off)
                    col_start = int(target_window.col_off - padded_window.col_off)
                    pan_detail = pan_detail[
                        row_start : row_start + int(target_window.height),
                        col_start : col_start + int(target_window.width),
                    ]
                    target_intensity = np.clip(intensity + (pan_detail * detail_strength), 0.0, 1.0)
                    gain = np.divide(
                        target_intensity,
                        np.maximum(intensity, EPSILON),
                        out=np.ones_like(target_intensity, dtype=np.float32),
                        where=intensity > EPSILON,
                    )
                    gain = np.clip(gain, 0.6, 1.6)

                    sharpened = np.clip(rgb_tile * gain[..., np.newaxis], 0.0, 1.0)
                    sharpened = np.moveaxis(sharpened, -1, 0) * output_scale

                    invalid = ~(pan_mask & rgb_mask)
                    if np.any(invalid):
                        sharpened[:, invalid] = 0

                    if np.issubdtype(output_dtype, np.integer):
                        info = np.iinfo(output_dtype)
                        sharpened = np.clip(sharpened, max(info.min, 0), info.max)

                    dst.write(sharpened.astype(output_dtype), window=target_window)

                _apply_colorinterp(dst)
    return output
