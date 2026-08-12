import os
import shutil
import tempfile
import numpy as np
import rasterio as rio
from rasterio.merge import merge
from utils.mosaic_clip import clip_raster_to_geometry, resolve_clip_geometry
from utils.mosaic_color_stats import DEFAULT_COLOR_TARGET
from utils.mosaic_geometry import NODATA_VALUE, ensure_same_crs
from utils.mosaic_normalization import (
    DEFAULT_CLIP_MAX,
    apply_band_transforms,
    clip_max_for_dtype,
    estimate_global_color_transforms,
    estimate_overlap_match,
    identity_transforms,
)


# Função para criar uma cópia rápida da cena, usada quando não há ajuste de cor pra fazer
def copy_scene(input_path, output_path):
    shutil.copy(input_path, output_path)
    return output_path


# Função para formatar as transformações de cor em texto legível para os logs
def format_transforms(transforms):
    parts = []
    for index, transform in enumerate(transforms, start=1):
        parts.append(
            f"B{index}: ganho={transform['gain']:.3f}, offset={transform['offset']:.1f}"
        )
    return "; ".join(parts)


# Função para igualar as cores das cenas usando as áreas onde elas se sobrepõem
def match_scenes_by_overlap(
    crs_files,
    output_dir,
    reference_index=0,
    fallback_transforms=None,
    overlap_strength=0.75,
):
    if reference_index < 0 or reference_index >= len(crs_files):
        raise ValueError("reference_index fora da lista de cenas.")
    if fallback_transforms is None:
        fallback_transforms = [None for _ in crs_files]

    matched = {}
    reference_output = os.path.join(output_dir, f"matched_{reference_index}.tif")
    matched[reference_index] = copy_scene(crs_files[reference_index], reference_output)

    pending = set(range(len(crs_files)))
    pending.remove(reference_index)

    while pending:
        best = None
        for source_index in pending:
            for reference_scene_index, reference_path in matched.items():
                estimate = estimate_overlap_match(
                    reference_path,
                    crs_files[source_index],
                    strength=overlap_strength,
                )
                if estimate is None:
                    continue
                candidate = (
                    estimate["pixels"],
                    source_index,
                    reference_scene_index,
                    estimate,
                )
                if best is None or candidate[0] > best[0]:
                    best = candidate

        if best is None:
            source_index = min(pending)
            transforms = fallback_transforms[source_index] or identity_transforms(
                crs_files[source_index]
            )
            output_path = os.path.join(output_dir, f"matched_{source_index}.tif")
            matched[source_index] = apply_band_transforms(
                crs_files[source_index], output_path, transforms
            )
            pending.remove(source_index)
            continue

        _, source_index, reference_scene_index, estimate = best
        output_path = os.path.join(output_dir, f"matched_{source_index}.tif")
        matched[source_index] = apply_band_transforms(
            crs_files[source_index], output_path, estimate["transforms"]
        )
        pending.remove(source_index)

    return [matched[index] for index in range(len(crs_files))]


# Função auxiliar do merge para somar os pixels válidos e contar quantas cenas cobrem cada um
def sum_valid_pixels(merged_data, new_data, merged_mask, new_mask, **kwargs):
    band_count = new_data.shape[0]
    values = np.asarray(new_data.filled(0), dtype="float32")
    mask = np.ma.getmaskarray(new_data)
    if mask.ndim == 0:
        valid = np.ones(values.shape[1:], dtype=bool)
    else:
        valid = ~np.any(mask, axis=0)

    valid &= np.all(values > NODATA_VALUE, axis=0)
    if not np.any(valid):
        return

    merged_data[:band_count] += values * valid
    merged_data[band_count] += valid.astype("float32")


# Função para juntar as cenas tirando a média dos pixels onde elas se sobrepõem
def merge_mean(src_files_to_mosaic, output_file_path, out_meta, mem_limit=512):
    band_count = src_files_to_mosaic[0].count
    output_dtype = np.dtype(src_files_to_mosaic[0].dtypes[0])
    output_clip_max = clip_max_for_dtype(output_dtype, DEFAULT_CLIP_MAX)
    output_dir = os.path.dirname(os.path.abspath(output_file_path))
    temp_handle, temp_path = tempfile.mkstemp(
        prefix=".merge_sum_",
        suffix=".tif",
        dir=output_dir,
    )
    os.close(temp_handle)
    os.remove(temp_path)

    sum_meta = out_meta.copy()
    sum_meta.update(dtype="float32", nodata=0.0)

    try:
        merge(
            src_files_to_mosaic,
            nodata=NODATA_VALUE,
            dtype="float32",
            output_count=band_count + 1,
            method=sum_valid_pixels,
            mem_limit=mem_limit,
            dst_path=temp_path,
            dst_kwds=sum_meta,
        )

        with rio.open(temp_path) as summed:
            final_meta = summed.profile.copy()
            final_meta.update(
                count=band_count,
                dtype=output_dtype.name,
                nodata=NODATA_VALUE,
                compress=out_meta.get("compress", "lzw"),
                tiled=out_meta.get("tiled", True),
                blockxsize=out_meta.get("blockxsize", 512),
                blockysize=out_meta.get("blockysize", 512),
                BIGTIFF=out_meta.get("BIGTIFF", "YES"),
            )

            with rio.open(output_file_path, "w", **final_meta) as dst:
                for _, window in summed.block_windows(1):
                    data = summed.read(window=window).astype("float32")
                    counts = data[band_count]
                    valid = counts > 0
                    out = np.zeros((band_count, data.shape[1], data.shape[2]), dtype="float32")
                    out[:, valid] = data[:band_count, valid] / counts[valid]
                    out = np.clip(out, NODATA_VALUE, output_clip_max)
                    out[:, ~valid] = NODATA_VALUE
                    dst.write(out.astype(output_dtype), window=window)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


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
):
    """Gera o mosaico e, se um recorte for informado, recorta o resultado final.

    O recorte é opcional e acontece só depois do mosaico pronto. Pode ser
    passado de duas formas (uma ou outra, não as duas):
    - clip_geometry: um GeoJSON (dict, caminho de arquivo .geojson, objeto
      shapely ou lista desses formatos), ou até uma UF/nome/código do IBGE
      direto nesse parâmetro.
    - clip_state: uma UF ("ES"), nome ("Espirito Santo") ou código IBGE (32)
      do estado cujo contorno oficial deve ser usado como recorte.
    """
    if not input_files:
        raise ValueError("Informe pelo menos uma cena para formar o mosaico.")
    if reference_index < 0 or reference_index >= len(input_files):
        raise ValueError("reference_index fora da lista de cenas.")
    if color_target not in {"median", "reference"}:
        raise ValueError("color_target deve ser 'median' ou 'reference'.")
    if merge_method not in {"mean", "first", "last", "min", "max"}:
        raise ValueError("merge_method deve ser 'mean', 'first', 'last', 'min' ou 'max'.")
    normalization_strength = float(np.clip(normalization_strength, 0.0, 1.0))
    resolved_clip_geometry = resolve_clip_geometry(clip_geometry, clip_state=clip_state)

    os.makedirs(os.path.dirname(os.path.abspath(output_file_path)), exist_ok=True)
    work_parent = os.path.dirname(os.path.abspath(output_file_path))
    work_dir = tempfile.mkdtemp(prefix=".mosaic_work_", dir=work_parent)

    dir_crs = os.path.join(work_dir, "1_crs")
    dir_matched = os.path.join(work_dir, "2_matched")
    os.makedirs(dir_crs, exist_ok=True)
    os.makedirs(dir_matched, exist_ok=True)

    src_files_to_mosaic = []
    try:
        with rio.open(input_files[reference_index]) as src:
            target_crs = src.crs

        crs_files = [
            ensure_same_crs(path, os.path.join(dir_crs, f"crs_{index}.tif"), target_crs)
            for index, path in enumerate(input_files)
        ]

        if match_colors and len(crs_files) > 1:
            fallback_transforms = estimate_global_color_transforms(
                crs_files,
                reference_index,
                target_strategy=color_target,
                strength=normalization_strength,
            )
            if use_overlap:
                matched_files = match_scenes_by_overlap(
                    crs_files,
                    dir_matched,
                    reference_index,
                    fallback_transforms,
                    overlap_strength=normalization_strength,
                )
            else:
                matched_files = []
                for index, path in enumerate(crs_files):
                    transforms = fallback_transforms[index]
                    output_path = os.path.join(dir_matched, f"matched_{index}.tif")
                    if transforms is None:
                        matched_files.append(copy_scene(path, output_path))
                    else:
                        matched_files.append(apply_band_transforms(path, output_path, transforms))
        else:
            matched_files = crs_files

        merge_order = [matched_files[reference_index]] + [
            path for index, path in enumerate(matched_files) if index != reference_index
        ]
        src_files_to_mosaic = [rio.open(path) for path in merge_order]
        out_meta = src_files_to_mosaic[0].meta.copy()
        out_meta.update(
            driver="GTiff",
            nodata=NODATA_VALUE,
            compress="lzw",
            tiled=True,
            blockxsize=512,
            blockysize=512,
            BIGTIFF="YES",
        )

        # Se vai recortar depois, o mosaico mesclado fica só num arquivo temporário;
        # senão, já sai direto no caminho final.
        mosaic_target_path = (
            os.path.join(work_dir, "mosaic_uncropped.tif")
            if resolved_clip_geometry is not None
            else output_file_path
        )

        if merge_method == "mean":
            merge_mean(src_files_to_mosaic, mosaic_target_path, out_meta, mem_limit=512)
        else:
            merge(
                src_files_to_mosaic,
                nodata=NODATA_VALUE,
                method=merge_method,
                mem_limit=512,
                dst_path=mosaic_target_path,
                dst_kwds=out_meta,
            )

        if resolved_clip_geometry is not None:
            clip_raster_to_geometry(
                input_path=mosaic_target_path,
                output_path=output_file_path,
                geometry=resolved_clip_geometry,
                geometry_crs=clip_geometry_crs,
                nodata=NODATA_VALUE,
            )

    finally:
        for src in src_files_to_mosaic:
            src.close()
        shutil.rmtree(work_dir, ignore_errors=True)

    return output_file_path