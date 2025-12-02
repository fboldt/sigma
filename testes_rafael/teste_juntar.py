
from cbers4asat.tools import rgbn_composite
import rasterio as rio
import numpy as np
import matplotlib.pyplot as plt
import os

# 1) Opcional: recriar a composição (se já existir, pode pular)
rgbn_composite(
    red='./band3.tif',
    green='./band2.tif',
    blue='./band1.tif',
    filename='CBERS4A_WPM22812420210704_TRUE_COLOR.tif',
    outdir='./STACK'
)

raster_path = "./STACK/CBERS4A_WPM22812420210704_TRUE_COLOR.tif"
out_png = "preview_true_color_fixed.png"

# 2) Ler como masked array (preserva nodata)
with rio.open(raster_path) as src:
    # read(masked=True) retorna numpy.ma.MaskedArray com shape (bands, H, W)
    img_ma = src.read(masked=True)

# 3) Função de stretch por banda usando apenas pixels válidos
def stretch_band_masked(band_ma, pmin=2, pmax=98):
    """
    band_ma: numpy.ma.MaskedArray (H, W)
    retorna: uint8 (H, W) com valores 0..255, e mantém nodata como 0
    """
    # converter pra float pra evitar overflow
    band = band_ma.astype(np.float32)
    # máscara de pixels válidos
    if isinstance(band, np.ma.MaskedArray):
        valid_mask = ~band.mask
        data = band.data
    else:
        valid_mask = np.ones(band.shape, dtype=bool)
        data = band

    # Se não houver pixels válidos, retorna zeros
    if not np.any(valid_mask):
        return np.zeros(band.shape, dtype=np.uint8)

    # Calcular percentis somente onde válido
    lo, hi = np.percentile(data[valid_mask], (pmin, pmax))
    if hi == lo:
        hi = lo + 1.0

    # Clip e normaliza
    clipped = np.clip(data, lo, hi)
    norm = (clipped - lo) / (hi - lo)
    norm[~valid_mask] = 0.0  # preencher nodata com 0 (preto)
    return (norm * 255).astype(np.uint8)

# 4) Aplicar stretch em cada banda (assume RGB em 1,2,3)
bands_count = img_ma.shape[0]
if bands_count < 3:
    raise SystemExit("O raster não tem 3 bandas RGB.")

r = stretch_band_masked(img_ma[0])
g = stretch_band_masked(img_ma[1])
b = stretch_band_masked(img_ma[2])

# Empilhar canais na ordem correta (H, W, 3)
rgb = np.dstack([r, g, b])

# 5) Salvar com matplotlib
plt.figure(figsize=(12, 12))
plt.imshow(rgb)
plt.axis("off")
plt.savefig(out_png, dpi=300, bbox_inches="tight")
plt.close()

print(f"Salvo: {out_png}")
