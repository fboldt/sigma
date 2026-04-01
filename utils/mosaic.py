import rasterio
from rasterio.merge import merge
from rasterio.io import MemoryFile
import numpy as np
from scipy.ndimage import binary_erosion
from scipy.ndimage import binary_fill_holes

# Função para unir cenas, formando o mosaico
def mosaic_scenes(files, output_file_path): 
    memory_files = []     
    opened_files = []  

    try:
        for file_path in files:
            with rasterio.open(file_path) as src:
                data = src.read()
                profile = src.profile.copy()
                
                # Aplicando padding
                mask = apply_padding(data)
                
                # Aplicando normalização
                out_data = apply_stretch(data, mask)

                # Criando arquivo temporário
                profile.update(dtype='uint8', nodata=0)
                mem_file = MemoryFile()
                with mem_file.open(**profile) as mem_dst:
                    mem_dst.write(out_data)
                
                memory_files.append(mem_file)
                opened_files.append(mem_file.open())

        # Unindo imagens para formar o mosaico
        res = opened_files[0].res # Resolução original
        mosaic, out_trans = merge(opened_files, nodata=0, res=res)

        # Alterando metadados no aquivo final
        out_meta = opened_files[0].meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_trans,
            "compress": "lzw",
            "BIGTIFF": "YES"
        })

        with rasterio.open(output_file_path, "w", **out_meta) as dest:
            dest.write(mosaic)

    finally:
        # Limpeza de memória
        for f in opened_files: f.close()
        for m in memory_files: m.close()

# Função para aplicar padding
def apply_padding(data, cut_pixels=15):
    # Máscara de validade (onde todas as bandas > 0)
    mask = np.all(data > 0, axis=0)

    # Preenchimento dos vãos internos
    mask_filled = binary_fill_holes(mask)

    # Erosão da borda externa
    mask_erosion = binary_erosion(mask_filled, iterations=cut_pixels)

    return mask_erosion

# Função para normalizar o mosaisaico
def apply_stretch(data, mask, percent=2):
    out_data = np.zeros(data.shape, dtype=np.uint8)
    
    for i in range(data.shape[0]):
        band = data[i]

        # Seleciona pixels válidos
        valid_pixels = band[mask]

        if valid_pixels.size > 0:
            # Cálculo da média das cores
            low, high = np.percentile(valid_pixels, (percent, 100 - percent))
            div = (high - low) if (high - low) > 0 else 1
            
            stretched = np.clip((band.astype(np.float32) - low) * 254.0 / div + 1, 1, 255)
            out_data[i][mask] = stretched[mask].astype(np.uint8)
            
    return out_data
