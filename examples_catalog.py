"""
example_catalog.py
------------------
Central catalog of available example modules.
Each entry maps a string key to its corresponding example implementation.
"""
from examples import (
    download_scene,
    echo,
    example_download_and_rgb,
    example_pansharpening_tiles,
    python_version,
    state_outline,
    sum,
    example_download_and_rgb_es,
    example_download_es,
    example_mosaic,
    example_piramide,
    example_rgb,
    example_workflow,
    list_cities
)

available_examples = {
    "list_cities": list_cities,  
    "python_version": python_version,  # exemplo sem parametros
    "echo": echo,  # exemplo com um parametro
    "sum": sum,  # exemplo com dois parametros
    "download_scene": download_scene,
    "state_outline": state_outline,
    "example_download_and_rgb": example_download_and_rgb,
    "example_download_and_rgb_es": example_download_and_rgb_es,
    "example_download_es": example_download_es,
    "example_mosaic": example_mosaic,
    "example_piramide": example_piramide,
    "example_rgb": example_rgb,
    "example_pansharpening_tiles": example_pansharpening_tiles,
    "example_workflow": example_workflow,
}
