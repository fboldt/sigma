import os
from cbers4asat.tools import rgbn_composite
import rasterio as rio

def rgb_composite(red_band, green_band, blue_band, output_file_path):

    #1. Definir o diretório e o nome do arquivo de saída
    output_dir = os.path.dirname(output_file_path)
    output_filename = os.path.basename(output_file_path)
    
    # Criando a composição cor verdadeira
    rgbn_composite(red=red_band,
                green=green_band,
                blue=blue_band,
                filename=output_filename,
                outdir=output_dir)