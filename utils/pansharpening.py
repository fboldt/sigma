from cbers4asat.tools import pansharpening
import rasterio as rio

def generate_pansharpened_image(multispectral,panchromatic,output_filename):
    pansharpening(
        # colocar arquivos de entrada e saída
        multispectral=multispectral, #arquivo multiespectral de entrada (RGB)
        panchromatic=panchromatic,  #arquivo pancromático de entrada (PAN)
        filename=output_filename    
    )
    raster = rio.open(output_filename)
    return raster