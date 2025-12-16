import os
from cbers4asat.tools import rgbn_composite
import rasterio as rio

# Função para composição manual
def rgb_composite(red_band, green_band, blue_band, output_file_path):

    # Definir o diretório e o nome do arquivo de saída
    output_dir = os.path.dirname(output_file_path)
    output_filename = os.path.basename(output_file_path)
    
    # Criação da composição cor verdadeira
    rgbn_composite(red=red_band,
                green=green_band,
                blue=blue_band,
                filename=output_filename,
                outdir=output_dir)

# Função para composição automatizada
def rgb_batch_composite(bands_path, output_file_path):

    # Extrai o diretório e o nome base
    output_dir = os.path.dirname(output_file_path)
    base_filename = os.path.basename(output_file_path)

    for scene in bands_path:
        scene_id = scene.get('id')
        
        # Nome do arquivo com a especificação referente à cena  
        output_filename = f"{base_filename}_{scene_id}.tif" 
        
        # Criação da composição RGB
        rgbn_composite(red=scene['red'],
                       green=scene['green'],
                       blue=scene['blue'],
                       filename=output_filename,
                       outdir=output_dir)