"""
example_catalog.py
------------------
Central catalog of available example modules.
Each entry maps a string key to its corresponding example implementation.
"""
from examples import (
    echo,
    example_download,
    example_download_and_rgb,
    example_pansharpening_tiles,
    python_version,
    sum,
    contorno_es,
    example_download_and_rgb_es,
    example_download_es,
    example_mosaic,
    example_piramide,
    example_rgb,
    example_stac_downloader,
    example_workflow,
    workflow_mosaic
)
from examples import example_pansharpening_tiles


available_examples = {
    "python_version": python_version,  # exemplo sem parametros
    "echo": echo,  # exemplo com um parametro
    "sum": sum,  # exemplo com dois parametros
    "example_download": example_download,
    "contorno_es": contorno_es,
    "example_download_and_rgb": example_download_and_rgb,
    "example_download_and_rgb_es": example_download_and_rgb_es,
    "example_download_es": example_download_es,
    "example_mosaic": example_mosaic,
    "example_piramide": example_piramide,
    "example_rgb": example_rgb,
    "example_stac_downloader": example_stac_downloader,
    "example_pansharpening_tiles": example_pansharpening_tiles,
    "example_workflow": example_workflow,
    "workflow_mosaic": workflow_mosaic,
}
