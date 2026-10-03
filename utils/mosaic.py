import math
import os
import shutil
import tempfile
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import rasterio as rio
from rasterio import windows as rio_windows
from rasterio.coords import BoundingBox
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.windows import Window, from_bounds
from utils.mosaic_clip import (
    extract_geojson_geometries,
    geometries_bounds,
    geometries_to_crs,
    inside_geometry_mask,
    resolve_clip_geometry,
)
from utils.mosaic_color_stats import DEFAULT_COLOR_TARGET
from utils.mosaic_geometry import (
    DEFAULT_WINDOW_SIZE,
    NODATA_VALUE,
    clamp_window,
    default_workers,
    ensure_same_crs,
    intersection_bounds,
    iter_windows,
    parallel_map,
    tiled_gtiff_profile,
)
from utils.mosaic_normalization import (
    DEFAULT_CLIP_MAX,
    apply_band_transforms,
    apply_transforms_clipped,
    clip_max_for_dtype,
    estimate_global_color_transforms,
    estimate_overlap_match,
)

# Tolerância (em pixels) ao alinhar janelas fracionadas com a grade de saída
GRID_EPSILON = 1e-3
# Quantas estimativas de sobreposição rodam ao mesmo tempo (cada uma usa algumas centenas de MB)
MAX_OVERLAP_WORKERS = 4


# Função para criar uma cópia rápida da cena, usada quando não há ajuste de cor pra fazer
def copy_scene(input_path, output_path):
    shutil.copy(input_path, output_path)
    return output_path


# Função para formatar as transformações de cor em texto legível para os logs
def format_transforms(transforms):
    if transforms is None:
        return "sem ajuste"
    parts = []
    for index, transform in enumerate(transforms, start=1):
        parts.append(
            f"B{index}: ganho={transform['gain']:.3f}, offset={transform['offset']:.1f}"
        )
    return "; ".join(parts)


# Função para decidir o ajuste de cor de cada cena a partir das áreas onde elas se sobrepõem.
def estimate_overlap_transforms(
    crs_files,
    reference_index=0,
    fallback_transforms=None,
    overlap_strength=0.75,
    workers=None,
):
    if reference_index < 0 or reference_index >= len(crs_files):
        raise ValueError("reference_index fora da lista de cenas.")
    if fallback_transforms is None:
        fallback_transforms = [None for _ in crs_files]

    overlap_workers = min(workers or default_workers(), MAX_OVERLAP_WORKERS)
    transforms = {reference_index: None}
    matched = [reference_index]
    pending = set(range(len(crs_files)))
    pending.remove(reference_index)
    estimates = {}

    # Função para estimar a cena pendente contra a cena que acabou de ser ajustada
    def evaluate(reference_scene_index):
        sources = sorted(pending)

        def run(source_index):
            return estimate_overlap_match(
                crs_files[reference_scene_index],
                crs_files[source_index],
                strength=overlap_strength,
                reference_transforms=transforms[reference_scene_index],
            )

        for source_index, estimate in zip(sources, parallel_map(run, sources, overlap_workers)):
            estimates[(source_index, reference_scene_index)] = estimate

    evaluate(reference_index)

    while pending:
        best = None
        for source_index in sorted(pending):
            for reference_scene_index in matched:
                estimate = estimates.get((source_index, reference_scene_index))
                if estimate is None:
                    continue
                if best is None or estimate["pixels"] > best[0]:
                    best = (estimate["pixels"], source_index, reference_scene_index, estimate)

        if best is None:
            source_index = min(pending)
            transforms[source_index] = fallback_transforms[source_index]
        else:
            _, source_index, reference_scene_index, estimate = best
            transforms[source_index] = estimate["transforms"]

        pending.remove(source_index)
        matched.append(source_index)
        if pending:
            evaluate(source_index)

    return [transforms[index] for index in range(len(crs_files))]


# Função que iguala as cores pela sobreposição e grava as cenas ajustadas em output_dir
def match_scenes_by_overlap(
    crs_files,
    output_dir,
    reference_index=0,
    fallback_transforms=None,
    overlap_strength=0.75,
):
    transforms = estimate_overlap_transforms(
        crs_files,
        reference_index,
        fallback_transforms,
        overlap_strength,
    )
    matched = []
    for index, (path, scene_transforms) in enumerate(zip(crs_files, transforms)):
        output_path = os.path.join(output_dir, f"matched_{index}.tif")
        if scene_transforms is None:
            matched.append(copy_scene(path, output_path))
        else:
            matched.append(apply_band_transforms(path, output_path, scene_transforms))
    return matched


# Função para ler da cena só o pedaço que cai dentro de uma janela do mosaico, já reamostrado para a grade de saída.
def read_scene_part(src, window_bounds, window_transform, window_height, window_width):
    overlap = intersection_bounds(src.bounds, window_bounds)
    if overlap is None:
        return None

    part = from_bounds(*overlap, transform=window_transform)
    col_start = max(0, math.ceil(part.col_off - GRID_EPSILON))
    row_start = max(0, math.ceil(part.row_off - GRID_EPSILON))
    col_end = min(window_width, math.floor(part.col_off + part.width + GRID_EPSILON))
    row_end = min(window_height, math.floor(part.row_off + part.height + GRID_EPSILON))
    if col_end <= col_start or row_end <= row_start:
        return None

    part_window = Window(col_start, row_start, col_end - col_start, row_end - row_start)
    part_bounds = rio_windows.bounds(part_window, window_transform)
    source_window = clamp_window(
        from_bounds(*part_bounds, transform=src.transform), src.width, src.height
    )
    if source_window is None:
        return None

    values = src.read(
        window=source_window,
        out_shape=(src.count, row_end - row_start, col_end - col_start),
        out_dtype="float32",
        resampling=Resampling.nearest,
    )
    return row_start, row_end, col_start, col_end, values


# Função para juntar as cenas
def merge_scenes(
    paths,
    transforms=None,
    output_path=None,
    merge_method="mean",
    clip_geometry=None,
    clip_geometry_crs="EPSG:4326",
    window_size=DEFAULT_WINDOW_SIZE,
    workers=None,
):
    if not paths:
        raise ValueError("Informe pelo menos uma cena para formar o mosaico.")
    if output_path is None:
        raise ValueError("Informe output_path.")
    if merge_method not in {"mean", "first", "last", "min", "max"}:
        raise ValueError("merge_method deve ser 'mean', 'first', 'last', 'min' ou 'max'.")
    if transforms is None:
        transforms = [None for _ in paths]
    if len(transforms) != len(paths):
        raise ValueError("transforms precisa ter uma entrada por cena.")

    workers = workers or default_workers()
    window_size = max(512, (int(window_size) // 512) * 512)

    scene_info = []
    for path in paths:
        with rio.open(path) as src:
            scene_info.append(
                {
                    "bounds": src.bounds,
                    "count": src.count,
                    "dtype": np.dtype(src.dtypes[0]),
                    "crs": src.crs,
                    "transform": src.transform,
                }
            )

    reference = scene_info[0]
    band_count = reference["count"]
    output_dtype = reference["dtype"]
    output_crs = reference["crs"]
    ref_transform = reference["transform"]
    if any(info["count"] != band_count for info in scene_info):
        raise ValueError("As cenas precisam ter o mesmo numero de bandas.")
    if ref_transform.b != 0 or ref_transform.d != 0 or ref_transform.e >= 0:
        raise ValueError("Rasters rotacionados ou com eixo Y invertido nao sao suportados.")

    output_clip_max = clip_max_for_dtype(output_dtype, DEFAULT_CLIP_MAX)
    scene_clip_max = [clip_max_for_dtype(info["dtype"], DEFAULT_CLIP_MAX) for info in scene_info]
    scene_is_integer = [np.issubdtype(info["dtype"], np.integer) for info in scene_info]

    # Geometria de recorte (já no CRS do mosaico) e limites que o mosaico vai cobrir
    geometries = None
    geometry_box = None
    left = min(info["bounds"].left for info in scene_info)
    bottom = min(info["bounds"].bottom for info in scene_info)
    right = max(info["bounds"].right for info in scene_info)
    top = max(info["bounds"].top for info in scene_info)
    if clip_geometry is not None:
        geometries = extract_geojson_geometries(clip_geometry)
        if not geometries:
            raise ValueError("Informe pelo menos uma geometria para recortar a cena.")
        geometries = geometries_to_crs(geometries, clip_geometry_crs, output_crs)
        geometry_box = BoundingBox(*geometries_bounds(geometries))
        left = max(left, geometry_box.left)
        bottom = max(bottom, geometry_box.bottom)
        right = min(right, geometry_box.right)
        top = min(top, geometry_box.top)
        if left >= right or bottom >= top:
            raise ValueError("As cenas nao intersectam a geometria de recorte.")

    # Grade de saída alinhada à grade da cena de referência (mesma resolução e origem)
    res_x = ref_transform.a
    res_y = -ref_transform.e
    first_col = math.floor((left - ref_transform.c) / res_x + GRID_EPSILON)
    last_col = math.ceil((right - ref_transform.c) / res_x - GRID_EPSILON)
    first_row = math.floor((ref_transform.f - top) / res_y + GRID_EPSILON)
    last_row = math.ceil((ref_transform.f - bottom) / res_y - GRID_EPSILON)
    out_width = int(last_col - first_col)
    out_height = int(last_row - first_row)
    out_transform = Affine(
        res_x,
        0.0,
        ref_transform.c + first_col * res_x,
        0.0,
        -res_y,
        ref_transform.f - first_row * res_y,
    )

    profile = tiled_gtiff_profile(
        {
            "driver": "GTiff",
            "dtype": output_dtype.name,
            "count": band_count,
            "crs": output_crs,
            "transform": out_transform,
            "width": out_width,
            "height": out_height,
            "nodata": NODATA_VALUE,
        }
    )

    window_list = list(iter_windows(out_width, out_height, window_size))

    # Cada thread abre as suas próprias referências aos arquivos
    local = threading.local()
    opened = []
    opened_lock = threading.Lock()

    def thread_handles():
        handles = getattr(local, "handles", None)
        if handles is None:
            handles = [rio.open(path) for path in paths]
            local.handles = handles
            with opened_lock:
                opened.extend(handles)
        return handles

    # Função que processa uma janela do mosaico
    def process_window(window):
        height = int(window.height)
        width = int(window.width)
        window_transform = rio_windows.transform(window, out_transform)
        window_bounds = BoundingBox(*rio_windows.bounds(window, out_transform))

        inside = None
        if geometries is not None:
            if intersection_bounds(window_bounds, geometry_box) is None:
                return window, None, False
            inside = inside_geometry_mask(geometries, (height, width), window_transform)
            if not inside.any():
                return window, None, False

        accumulated = np.zeros((band_count, height, width), dtype="float32")
        if merge_method == "mean":
            counts = np.zeros((height, width), dtype="float32")
        else:
            filled = np.zeros((height, width), dtype=bool)

        for index, src in enumerate(thread_handles()):
            part = read_scene_part(src, window_bounds, window_transform, height, width)
            if part is None:
                continue
            row_start, row_end, col_start, col_end, values = part

            if transforms[index] is not None:
                values = apply_transforms_clipped(
                    values,
                    transforms[index],
                    scene_clip_max[index],
                    integer_output=scene_is_integer[index],
                )
            valid = np.all(values > NODATA_VALUE, axis=0)
            if not valid.any():
                continue

            target = accumulated[:, row_start:row_end, col_start:col_end]
            if merge_method == "mean":
                values *= valid
                target += values
                counts[row_start:row_end, col_start:col_end] += valid
                continue

            have = filled[row_start:row_end, col_start:col_end]
            if merge_method == "first":
                take = valid & ~have
                target[:, take] = values[:, take]
            elif merge_method == "last":
                take = valid
                target[:, take] = values[:, take]
            else:
                both = valid & have
                take = valid & ~have
                combine = np.minimum if merge_method == "min" else np.maximum
                target[:, both] = combine(target[:, both], values[:, both])
                target[:, take] = values[:, take]
                take = valid
            have |= take

        if merge_method == "mean":
            has_data = counts > 0
            np.divide(accumulated, np.maximum(counts, 1.0), out=accumulated)
            accumulated[:, ~has_data] = NODATA_VALUE
            np.clip(accumulated, NODATA_VALUE, output_clip_max, out=accumulated)

        if inside is not None:
            accumulated[:, ~inside] = NODATA_VALUE

        result = accumulated.astype(output_dtype)
        return window, result, bool(np.any(result > NODATA_VALUE))

    any_valid = False
    pending = deque()

    try:
        with rio.open(output_path, "w", **profile) as dst, ThreadPoolExecutor(
            max_workers=workers
        ) as pool:

            # Função que espera a janela mais antiga ficar pronta e grava no arquivo final
            def write_oldest():
                nonlocal any_valid
                future = pending.popleft()
                window, result, has_valid = future.result()
                if result is not None:
                    dst.write(result, window=window)
                    any_valid = any_valid or has_valid

            max_in_flight = workers * 2
            for window in window_list:
                pending.append(pool.submit(process_window, window))
                while len(pending) >= max_in_flight:
                    write_oldest()
            while pending:
                write_oldest()

        if geometries is not None and not any_valid:
            raise ValueError("O mosaico ficou sem pixels validos apos o recorte.")
    except BaseException:
        if os.path.exists(output_path):
            os.remove(output_path)
        raise
    finally:
        for handle in opened:
            handle.close()

    return output_path


# Função com a assinatura antiga do merge por média. 
def merge_mean(src_files_to_mosaic, output_file_path, out_meta=None, mem_limit=512):
    return merge_scenes(
        [src.name for src in src_files_to_mosaic],
        None,
        output_file_path,
        merge_method="mean",
    )


# Função principal: recebe as cenas de entrada e gera o mosaico final
def mosaic_scenes(
    input_files,
    output_file_path,
    reference_index=0,
    match_colors=True,
    use_overlap=False,
    color_target=DEFAULT_COLOR_TARGET,
    normalization_strength=0.90,
    merge_method="mean",
    clip_geometry=None,
    clip_geometry_crs="EPSG:4326",
    clip_state=None,
    workers=None,
    temp_dir=None,
):
    if not input_files:
        raise ValueError("Informe pelo menos uma cena para formar o mosaico.")
    if reference_index < 0 or reference_index >= len(input_files):
        raise ValueError("reference_index fora da lista de cenas.")
    if color_target not in {"median", "reference"}:
        raise ValueError("color_target deve ser 'median' ou 'reference'.")
    if merge_method not in {"mean", "first", "last", "min", "max"}:
        raise ValueError("merge_method deve ser 'mean', 'first', 'last', 'min' ou 'max'.")
    normalization_strength = float(np.clip(normalization_strength, 0.0, 1.0))
    workers = workers or default_workers()
    resolved_clip_geometry = resolve_clip_geometry(clip_geometry, clip_state=clip_state)

    output_dir = os.path.dirname(os.path.abspath(output_file_path))
    os.makedirs(output_dir, exist_ok=True)
    work_parent = temp_dir or output_dir
    os.makedirs(work_parent, exist_ok=True)
    work_dir = tempfile.mkdtemp(prefix=".mosaic_work_", dir=work_parent)

    try:
        with rio.open(input_files[reference_index]) as src:
            target_crs = src.crs

        # 1) Reprojeção
        needs_reproject = []
        for path in input_files:
            with rio.open(path) as src:
                needs_reproject.append(src.crs != target_crs)
        reproject_count = sum(needs_reproject)
        reproject_workers = min(workers, reproject_count) if reproject_count else 1
        warp_threads = max(1, workers // reproject_workers)

        def prepare(item):
            index, path = item
            return ensure_same_crs(
                path,
                os.path.join(work_dir, f"crs_{index}.tif"),
                target_crs,
                num_threads=warp_threads,
            )

        crs_files = parallel_map(prepare, enumerate(input_files), reproject_workers)

        # 2) Decide o ajuste de cor de cada cena
        transforms = [None for _ in crs_files]
        if match_colors and len(crs_files) > 1:
            transforms = estimate_global_color_transforms(
                crs_files,
                reference_index,
                target_strategy=color_target,
                strength=normalization_strength,
                workers=workers,
            )
            if use_overlap:
                transforms = estimate_overlap_transforms(
                    crs_files,
                    reference_index,
                    fallback_transforms=transforms,
                    overlap_strength=normalization_strength,
                    workers=workers,
                )

        # 3) Merge, ajuste de cor e recorte
        merge_order = [reference_index] + [
            index for index in range(len(crs_files)) if index != reference_index
        ]
        merge_scenes(
            [crs_files[index] for index in merge_order],
            [transforms[index] for index in merge_order],
            output_file_path,
            merge_method=merge_method,
            clip_geometry=resolved_clip_geometry,
            clip_geometry_crs=clip_geometry_crs,
            workers=workers,
        )
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return output_file_path