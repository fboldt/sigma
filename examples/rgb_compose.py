import rasterio as rio
import numpy as np
import matplotlib.pyplot as plt
from rasterio.enums import ColorInterp
from os.path import join
from cbers4asat.tools import rgbn_composite

from utils.stretch_band_masked import stretch_band_masked

# Cofigurações do arquivo
OUTDIR = './images/STACK'
FILENAME_TIFF_ORIGINAL = 'CBERS4A_WPM22812420210704_TRUE_COLOR.tif'
OUTPUT_PATH_TIFF = join(OUTDIR, FILENAME_TIFF_ORIGINAL)
OUTPUT_PATH_PNG = join(OUTDIR, 'preview_true_color_fixed.png')
OUTPUT_PATH_TIFF_VIEWER = join(OUTDIR, 'CBERS4A_8BIT_VIEWER.tif')


def process_and_export_visuals():
    """
    Fluxo principal: Gera TIFF bruto, aplica stretch e exporta PNG + TIFF 8-bit.
    """
    
    # 1. Gerar TIFF a partir da função da biblioteca cbers4asat
    rgbn_composite(
        red='./images/bandas/BAND3.tif',
        green='./images/bandas/BAND2.tif',
        blue='./images/bandas/BAND1.tif',
        filename=FILENAME_TIFF_ORIGINAL,
        outdir=OUTDIR
    )
    print(f"TIFF de alta resolução gerado: {OUTPUT_PATH_TIFF}")

    # 2. Aplica stretch e gerar TIFF 8-bit e png
    with rio.open(OUTPUT_PATH_TIFF) as src:
        img_ma = src.read(masked=True)
        base_meta = src.meta.copy()

    bands_count = img_ma.shape[0]
    if bands_count < 3:
        raise SystemExit("O raster não tem 3 bandas RGB.")

    # Aplica o estiramento de alto contraste em cada banda
    r = stretch_band_masked(img_ma[0])
    g = stretch_band_masked(img_ma[1])
    b = stretch_band_masked(img_ma[2])

    rgb_8bit = np.dstack([r, g, b])

    # Gera o png
    plt.figure(figsize=(12, 12))
    plt.imshow(rgb_8bit)
    plt.axis("off")
    plt.savefig(OUTPUT_PATH_PNG, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"PNG gerado em: {OUTPUT_PATH_PNG}")

    # Gera TIFF 8-bit
    rgb_out_rasterio = np.transpose(rgb_8bit, [2, 0, 1]) 

    out_meta = base_meta.copy()
    out_meta.update({
        'dtype': rio.uint8,
        'count': 3,
        'photometric': 'RGB',
        'interleave': 'pixel',
        'compress': 'LZW'
    })

    color_interp_list = [ColorInterp.red, ColorInterp.green, ColorInterp.blue]
    out_meta["colorinterp"] = color_interp_list

    with rio.open(OUTPUT_PATH_TIFF_VIEWER, 'w', **out_meta) as dst:
        dst.write(rgb_out_rasterio)
        
    print(f"TIFF de 8-bit gerado em: {OUTPUT_PATH_TIFF_VIEWER}")

if __name__ == '__main__':
    process_and_export_visuals()