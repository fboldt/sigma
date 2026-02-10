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
        output_path = os.path.join(output_dir, output_filename)

        # Criação da composição RGB
        rgb_composite(red_band=scene['red'],
                       green_band=scene['green'],
                       blue_band=scene['blue'],
                       output_file_path=output_path)
