# Para ver todas as ferramentas disponíveis, verifique a documentação
from cbers4asat.tools import rgbn_composite
from rasterio.plot import show
import rasterio as rio

# Criando a composição cor verdadeira
rgbn_composite(red='./CBERS_4A_WPM_20250609_195_138_L4_BAND3.tif',
               green='./CBERS_4A_WPM_20250609_195_138_L4_BAND2.tif',
               blue='./CBERS_4A_WPM_20250609_195_138_L4_BAND1.tif',
               #nir='./CBERS_4A_WPM_20250609_195_138_L4_BAND0.tif',
               filename='CBERS4A_WPM22812420210704_TRUE_COLOR.tif',
               outdir='./STACK')

# Plotando a imagem
raster = rio.open("./STACK/CBERS4A_WPM22812420210704_TRUE_COLOR.tif")

show(raster)