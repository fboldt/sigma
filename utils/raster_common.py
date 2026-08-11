from __future__ import annotations

from typing import Iterator, Sequence

import numpy as np
import rasterio as rio
from rasterio.enums import ColorInterp
from rasterio.windows import Window, from_bounds

EPSILON = 1e-6
LUMINANCE_WEIGHTS = np.array([0.299, 0.587, 0.114], dtype=np.float32)

def _dtype_scale(dtype: str | np.dtype) -> float:
    dtype = np.dtype(dtype)
    if np.issubdtype(dtype, np.integer):
        return float(np.iinfo(dtype).max)
    return 1.0

def _dataset_scale(dataset: rio.io.DatasetReader, indexes: Sequence[int]) -> float:
    scale = _dtype_scale(dataset.dtypes[0])
    if scale != 1.0:
        return scale
    sample_height = min(128, dataset.height)
    sample_width = min(128, dataset.width)
    sample = dataset.read(
        indexes,
        out_shape=(len(indexes), sample_height, sample_width),
        masked=True,
    ).astype(np.float32)
    if sample.count() == 0:
        return 1.0
    return 65535.0 if float(sample.max()) > 1.5 else 1.0

def _recommended_block_size(size: int, default: int = 512) -> int | None:
    if size < 16:
        return None
    return max(16, min(default, (size // 16) * 16))

def _apply_tiff_layout(profile: dict, width: int, height: int) -> dict:
    profile.pop("blockxsize", None)
    profile.pop("blockysize", None)
    profile["compress"] = "deflate"
    profile["BIGTIFF"] = "IF_SAFER"
    blockx = _recommended_block_size(width)
    blocky = _recommended_block_size(height)
    if blockx is not None and blocky is not None:
        profile["tiled"] = True
        profile["blockxsize"] = blockx
        profile["blockysize"] = blocky
    else:
        profile["tiled"] = False
    return profile


def _rgb_colorinterp(count: int) -> tuple[ColorInterp, ...] | None:
    if count < 3:
        return None
    base = [ColorInterp.red, ColorInterp.green, ColorInterp.blue]
    if count > 3:
        base.extend([ColorInterp.undefined] * (count - 3))
    return tuple(base[:count])


def _normalized_colorinterp(
    source_colorinterp: Sequence[ColorInterp] | None,
    count: int,
) -> tuple[ColorInterp, ...] | None:
    if count < 3:
        return None
    rgb_default = _rgb_colorinterp(count)
    if not source_colorinterp:
        return rgb_default
    trimmed = tuple(source_colorinterp[:count])
    if len(trimmed) < 3:
        return rgb_default
    rgb_first_three = (ColorInterp.red, ColorInterp.green, ColorInterp.blue)
    if trimmed[:3] == rgb_first_three:
        return trimmed
    if trimmed[0] in (ColorInterp.gray, ColorInterp.undefined):
        return rgb_default
    return trimmed


def _apply_colorinterp(
    dataset: rio.io.DatasetWriter,
    source_colorinterp: Sequence[ColorInterp] | None = None,
) -> None:
    colorinterp = _normalized_colorinterp(source_colorinterp, dataset.count)
    if colorinterp is not None:
        dataset.colorinterp = colorinterp

def _round_window(window: Window) -> Window:
    return window.round_offsets().round_lengths()

def _iter_windows(base_window: Window, tile_size: int) -> Iterator[Window]:
    row_end = int(base_window.row_off + base_window.height)
    col_end = int(base_window.col_off + base_window.width)
    for row_off in range(int(base_window.row_off), row_end, tile_size):
        for col_off in range(int(base_window.col_off), col_end, tile_size):
            height = min(tile_size, row_end - row_off)
            width = min(tile_size, col_end - col_off)
            yield Window(col_off=col_off, row_off=row_off, width=width, height=height)

def _intersection_bounds(datasets: Sequence[rio.io.DatasetReader]) -> tuple[float, float, float, float]:
    left = max(ds.bounds.left for ds in datasets)
    bottom = max(ds.bounds.bottom for ds in datasets)
    right = min(ds.bounds.right for ds in datasets)
    top = min(ds.bounds.top for ds in datasets)
    if left >= right or bottom >= top:
        raise ValueError("As bandas nao possuem intersecao espacial suficiente.")
    return left, bottom, right, top

def intersection_window(
    reference: rio.io.DatasetReader,
    datasets: Sequence[rio.io.DatasetReader],
) -> Window:
    full_window = Window(0, 0, reference.width, reference.height)
    window = _round_window(from_bounds(*_intersection_bounds(datasets), transform=reference.transform))
    return full_window.intersection(window)
