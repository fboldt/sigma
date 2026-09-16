from cbers4asat.tools import rgbn_composite
import rasterio as rio
from rasterio.plot import show
import numpy as np
import matplotlib.pyplot as plt

# Criando uma composição COR VERDADEIRA

# Cada parâmetro de cor representa o canal da imagem de saída

# Banda NIR é opcional
rgbn_composite(red='./downloads1/CBERS4A_WPM19513820250609ETC2/CBERS_4A_WPM_20250609_195_138_L4_BAND1.tif',
               green='./downloads1/CBERS4A_WPM19513820250609ETC2/CBERS_4A_WPM_20250609_195_138_L4_BAND2.tif',
               blue='./downloads1/CBERS4A_WPM19513820250609ETC2/CBERS_4A_WPM_20250609_195_138_L4_BAND1.tif',
               nir='./downloads1/CBERS4A_WPM19513820250609ETC2/CBERS_4A_WPM_20250609_195_138_L4_BAND4.tif',
               filename='CBERS4A_WPM22812420210704_TRUE_COLOR.tif',
               outdir='./STACK')

raster = rio.open("./STACK/CBERS4A_WPM22812420210704_TRUE_COLOR.tif")

'''data = raster.read()
# Normalizar para [0..1]
data_normalized = data / data.max()
plt.figure(figsize=(10, 10))'''
show(raster.read(), transform=raster.transform)
plt.savefig('./output_image4.png', dpi=150, bbox_inches='tight')
plt.close()