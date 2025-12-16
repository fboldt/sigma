import os
from utils.rgb import rgb_composite

def example_rgb():
    # Diretório contendo as bandas individuais
    input_path = './images/CBERS4A_WPM19713820250630ETC2' 

    # Diretório e nome do arquivo de saída para a imagem composta
    output_dir = './images' 
    output_filename = 'TRUE_COLOR.tif'

    output_file_path = os.path.join(output_dir, output_filename)

    # Caminhos completos para as bandas vermelha, verde e azul
    red_band_path = os.path.join(input_path, 'CBERS_4A_WPM_20250630_197_138_L4_BAND3.tif')
    green_band_path = os.path.join(input_path, 'CBERS_4A_WPM_20250630_197_138_L4_BAND2.tif')
    blue_band_path = os.path.join(input_path, 'CBERS_4A_WPM_20250630_197_138_L4_BAND1.tif')

    # 3. Chamada da função para compor a imagem RGB
    rgb_composite(red_band_path, green_band_path, blue_band_path, output_file_path)

if __name__ == "__main__":
    example_rgb()