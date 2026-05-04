from cbers4asat.tools import pansharpening
import rasterio as rio
#pansharpening da bliblioteca cbers4asat, utilizar apenas em imagens pequenas pois nescessita de um alto numero de RAM
def generate_pansharpened_image(multispectral,panchromatic,output_filename):
    pansharpening(
        # colocar arquivos de entrada e saída
        multispectral=multispectral, #arquivo multiespectral de entrada (RGB)
        panchromatic=panchromatic,  #arquivo pancromático de entrada (PAN)
        filename=output_filename    
    )
    raster = rio.open(output_filename)
    return raster