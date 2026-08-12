import os
import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.enums import Resampling
from cbers4asat.tools import pansharpening

def get_scale_factor(pan_src, ms_src):
    return ms_src.res[0] / pan_src.res[0]


def tile_windows(width, height, tile_size):
    for row_off in range(0, height, tile_size):
        for col_off in range(0, width, tile_size):
            yield Window(
                col_off,
                row_off,
                min(tile_size, width  - col_off),
                min(tile_size, height - row_off),
            )


def save_tile_as_tif(data, transform, crs, dtype, path):
    n_bands, height, width = data.shape
    with rasterio.open(
        path, "w",
        driver="GTiff",
        height=height,
        width=width,
        count=n_bands,
        dtype=dtype,
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(data)


def processar_pansharpening_tiles(caminho_pan, caminho_ms, caminho_saida, tamanho_tile=4096, diretorio_temp="./tiles_temp"):
    os.makedirs(diretorio_temp, exist_ok=True)

    with rasterio.open(caminho_pan) as pan_src, rasterio.open(caminho_ms) as ms_src:
        pan_w, pan_h = pan_src.width, pan_src.height
        pan_transform = pan_src.transform
        pan_crs = pan_src.crs
        pan_dtype = pan_src.dtypes[0]
        scale_factor = get_scale_factor(pan_src, ms_src)
        n_ms_bands = ms_src.count

        out_meta = {
            "driver": "GTiff",
            "height": pan_h,
            "width": pan_w,
            "count": 3,
            "dtype": "float32",
            "crs": pan_crs,
            "transform": pan_transform,
            "compress": "lzw",
            "tiled": True,
            "blockxsize": 512,
            "blockysize": 512,
            "BIGTIFF": "YES",
        }

        windows = list(tile_windows(pan_w, pan_h, tamanho_tile))

        with rasterio.open(caminho_saida, "w", **out_meta) as dst:
            for idx, window in enumerate(windows):
                tile_transform = rasterio.windows.transform(window, pan_transform)

                # 1. Lê tile PAN
                pan_tile = pan_src.read(1, window=window)

                # 2. Lê tile MS e reamostra para resolução PAN
                ms_window = Window(
                    col_off=int(window.col_off / scale_factor),
                    row_off=int(window.row_off / scale_factor),
                    width=max(1, int(np.ceil(window.width  / scale_factor))),
                    height=max(1, int(np.ceil(window.height / scale_factor))),
                )
                ms_tile = ms_src.read(
                    window=ms_window,
                    out_shape=(n_ms_bands, window.height, window.width),
                    resampling=Resampling.bilinear,
                )

                # 3. Salva tiles temporários para a biblioteca processar
                pan_tmp = os.path.join(diretorio_temp, f"pan_tile_{idx}.tif")
                ms_tmp = os.path.join(diretorio_temp, f"ms_tile_{idx}.tif")
                out_filename = f"pansharp_tile_{idx}.tif"
                out_tmp = os.path.join(diretorio_temp, out_filename)

                save_tile_as_tif(pan_tile[np.newaxis, ...], tile_transform, pan_crs, pan_dtype, pan_tmp)
                save_tile_as_tif(ms_tile, tile_transform, pan_crs, pan_dtype, ms_tmp)

                # 4. Chama a função da biblioteca cbers4asat
                pansharpening(
                    panchromatic=pan_tmp,
                    multispectral=ms_tmp,
                    outdir=diretorio_temp,
                    filename=out_filename,
                )

                # 5. Lê resultado do tile fundido e grava na posição final do mosaico
                with rasterio.open(out_tmp) as tile_result:
                    result_data = tile_result.read()

                dst.write(result_data, window=window)

                # 6. Limpa arquivos temporários do disco
                for f in [pan_tmp, ms_tmp, out_tmp]:
                    if os.path.exists(f):
                        os.remove(f)

                del pan_tile, ms_tile, result_data
                
    # Tenta remover a pasta temporária se ela estiver vazia ao final
    try:
        os.rmdir(diretorio_temp)
    except OSError:
        pass