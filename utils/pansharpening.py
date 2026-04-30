import os

import rasterio as rio

from .georaster import pansharpen_hsv_tiled


def generate_pansharpened_image(
    multispectral,
    panchromatic,
    output_filename,
    output_dir=None,
    tile_size=2048,
    sample_stride=4,
    crop_to_intersection=True,
):
    if output_dir is None:
        output_path = output_filename
    else:
        output_path = os.path.join(output_dir, output_filename)

    pansharpen_hsv_tiled(
        multispectral_path=multispectral,
        panchromatic_path=panchromatic,
        output_path=output_path,
        tile_size=tile_size,
        sample_stride=sample_stride,
        crop_to_intersection=crop_to_intersection,
    )

    return rio.open(output_path)
