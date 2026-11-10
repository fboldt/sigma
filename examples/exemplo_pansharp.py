import sys
from pathlib import Path

# Sobe um nível para o diretório principal do projeto e adiciona ao path
project_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_dir)

from utils.pansharpening import generate_pansharpened_image
from rasterio.plot import show

#arquivos de entrada
multispectral='./ms_4km_tile_py.tif'
panchromatic='./pan_4km_tile_py.tif'
#arquivo de saída
output_filename='pansharpened_tile10km_py.tif'

# chamda a função de pansharpening
raster = generate_pansharpened_image(multispectral,panchromatic,output_filename)

show(raster)