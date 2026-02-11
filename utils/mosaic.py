import rasterio
from rasterio.merge import merge
import os

def mosaic_images(files, output_path):
    # 1. Abrir todos os arquivos
    files_data = []
    for file in files:
        src = rasterio.open(file)
        files_data.append(src)

    # 2. Fazer o merge
    mosaic, out_trans = merge(files_data)

    # 3. Copiar os metadados e atualizar para o mosaico
    out_meta = files_data[0].meta.copy()
    out_meta.update({
        "driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_trans,
        "crs": files_data[0].crs
    })

    # 4. Salvar o arquivo final
    with rasterio.open(output_path, "w", **out_meta) as dest:
        dest.write(mosaic)
        