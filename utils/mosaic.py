from glob import glob
from pathlib import Path

from rasterio.enums import Resampling

from .georaster import mosaic_rasters, reproject_raster


def reproject_files(file_paths, output_dir, dst_crs="EPSG:4674", resampling=Resampling.cubic):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []

    for file_path in file_paths:
        source = Path(file_path)
        output_path = output_dir / source.name
        outputs.append(
            reproject_raster(
                input_path=str(source),
                output_path=str(output_path),
                dst_crs=dst_crs,
                resampling=resampling,
            )
        )

    return outputs


def reproject_folder(input_glob, output_dir, dst_crs="EPSG:4674", resampling=Resampling.cubic):
    return reproject_files(sorted(glob(input_glob)), output_dir, dst_crs=dst_crs, resampling=resampling)


def mosaic_files(file_paths, output_path, method="first"):
    return mosaic_rasters(file_paths, output_path, method=method)
