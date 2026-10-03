import os
from pathlib import Path
import rasterio as rio
from rasterio.warp import reproject, Resampling
import numpy as np
from scipy.ndimage import median_filter
from cbers4asat.tools import rgbn_composite

# Função para composição manual
def rgb_composite(red_band, green_band, blue_band, output_file_path, nir_band=None):
    # Definir o diretório e o nome do arquivo de saída
    output_dir = os.path.dirname(output_file_path)
    output_filename = os.path.basename(output_file_path)
    
    # Criando os nomes das bandas temporárias
    t_r = os.path.join(output_dir, "temp_red.tif")
    t_g = os.path.join(output_dir, "temp_green.tif")
    t_b = os.path.join(output_dir, "temp_blue.tif")
    t_n = os.path.join(output_dir, "temp_nir.tif") if nir_band else None

    try:
        # 1. Processa e salva as bandas temporárias
        filling_band(red_band, t_r)
        filling_band(green_band, t_g)
        filling_band(blue_band, t_b)
        if nir_band:
            with rio.open(t_r) as ref:
                ref_profile = ref.profile.copy()
            filling_band(nir_band, t_n, ref_profile=ref_profile)

        # 2. Criação da composição RGB (ou RGBN, se a banda NIR tiver sido baixada) a partir da biblioteca cbers4asat
        rgbn_composite(red=t_r, 
                       green=t_g, 
                       blue=t_b,
                       nir=t_n,
                       filename=output_filename, 
                       outdir=output_dir)
        
    finally:
        # 3. Deleta os arquivos temporários
        temp_files = [t_r, t_g, t_b]
        if t_n:
            temp_files.append(t_n)

        for f in temp_files:
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

        # Criação da composição RGB (usa a banda NIR automaticamente, se ela tiver sido baixada)
        rgb_composite(red_band=scene['red'],
                      green_band=scene['green'],
                      blue_band=scene['blue'],
                      output_file_path=output_path,
                      nir_band=scene.get('nir'))
        
        all_rgb_paths.append(output_path)

    return all_rgb_paths

def filling_band(input_path, temp_path, ref_profile=None):
   with rio.open(input_path) as src:
        profile = src.profile.copy()

        if ref_profile is not None:
            # Reamostra a banda para a mesma grade da referência
            data = np.empty((ref_profile['height'], ref_profile['width']), dtype=src.dtypes[0])
            reproject(
                source=rio.band(src, 1),
                destination=data,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=ref_profile['transform'],
                dst_crs=ref_profile['crs'],
                resampling=Resampling.nearest
            )
            profile.update({
                'height': ref_profile['height'],
                'width': ref_profile['width'],
                'transform': ref_profile['transform'],
                'crs': ref_profile['crs'],
            })
        else:
            data = src.read(1)

        # Preenche dos pixels NoData
        mask = (data == 0)
        if np.any(mask):
            data[mask] = median_filter(data, size=3)[mask]
        
        # Salva o resultado no caminho temporário
        with rio.open(temp_path, 'w', **profile) as dst:
            dst.write(data, 1)