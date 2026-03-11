import rasterio
from rasterio.merge import merge
from rasterio.io import MemoryFile
import numpy as np
from scipy.ndimage import binary_erosion

# Função para formar o mosaico
def mosaic_scenes(files, output_file_path): 
    memory_files = []     
    files_data = []  

    # 1. Aplicar padding nas cenas
    for file in files:
        padding_file = apply_padding(file)
        memory_files.append(padding_file)
        files_data.append(padding_file.open())

    # 2. Aplicar merge
    mosaic, out_trans = merge(files_data)

    # 3. Copiar os metadados e atualizar para o mosaico
    out_meta = files_data[0].meta.copy()
    out_meta.update({
        "driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_trans,
        "nodata": 0,
        "compress": "lzw",
        "BIGTIFF": "YES"
    })

    # 4. Salvar o arquivo final
    with rasterio.open(output_file_path, "w", **out_meta) as dest:
        dest.write(mosaic)

# Função para aplicar padding nas cenas
def apply_padding(file_path, cut_pixels=15):
    with rasterio.open(file_path) as src:
        data = src.read()

        # Cópia do profile
        profile = src.profile.copy()

        # Máscara de validade (onde todas as bandas > 0)
        mask = np.all(data > 0, axis=0)
        
        # Erosão para remover a rebarba
        mask_erosion = binary_erosion(mask, iterations=cut_pixels)
        
        for i in range(data.shape[0]):
            data[i][~mask_erosion] = 0

        # Cria arquivo em memória
        padding_file = MemoryFile()
        with padding_file.open(**profile) as mem_dst:
            mem_dst.write(data)
        
        return padding_file