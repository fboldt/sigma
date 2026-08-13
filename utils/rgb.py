import os
from pathlib import Path
import rasterio as rio
import numpy as np
from scipy.ndimage import median_filter
from cbers4asat.tools import rgbn_composite

# Função para composição manual
def rgb_composite(red_band, green_band, blue_band, output_file_path):
    # Definir o diretório e o nome do arquivo de saída
    output_dir = os.path.dirname(output_file_path)
    output_filename = os.path.basename(output_file_path)
    
    # Criando os nomes das bandas temporárias
    t_r = os.path.join(output_dir, "temp_red.tif")
    t_g = os.path.join(output_dir, "temp_green.tif")
    t_b = os.path.join(output_dir, "temp_blue.tif")

    try:
        # 1. Processa e salva as bandas temporárias
        filling_band(red_band, t_r)
        filling_band(green_band, t_g)
        filling_band(blue_band, t_b)

        # 2. Criação da composição RGB a partir da biblioteca cbers4asat
        rgbn_composite(red=t_r, 
                       green=t_g, 
                       blue=t_b,
                       filename=output_filename, 
                       outdir=output_dir)
        
    finally:
        # 3. Deleta os arquivos temporários
        for f in [t_r, t_g, t_b]:
            if os.path.exists(f):
                os.remove(f)

# Função para composição automatizada
def rgb_batch_composite(bands_path, output_file_path):
    all_rgb_paths = []

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
        
        all_rgb_paths.append(output_path)

    return all_rgb_paths

def filling_band(input_path, temp_path):
   with rio.open(input_path) as src:
        data = src.read(1)
        profile = src.profile.copy()

        # Preenche dos pixels NoData
        mask = (data == 0)
        if np.any(mask):
            data[mask] = median_filter(data, size=3)[mask]
        
        # Salva o resultado no caminho temporário
        with rio.open(temp_path, 'w', **profile) as dst:
            dst.write(data, 1)