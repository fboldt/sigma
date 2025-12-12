import os
from utils.rgb import rgb_composite

def example_rgb():
    # 1. Diretório contendo as bandas individuais
    input_path = './images/bandas' 

    # 2. Diretório de saída para a imagem composta
    output_path = './images' 

    # Caminhos completos para as bandas vermelha, verde e azul
    red_band_path = os.path.join(input_path, 'BAND3.tif')
    green_band_path = os.path.join(input_path, 'BAND2.tif')
    blue_band_path = os.path.join(input_path, 'BAND1.tif')

    # 3. Chamada da função para compor a imagem RGB
    rgb_composite(red_band_path, green_band_path, blue_band_path, output_path)

if __name__ == "__main__":
    example_rgb()