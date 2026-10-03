import sys
from pathlib import Path

# Sobe um nível para o diretório principal do projeto e adiciona ao path
project_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_dir)

import os
from utils.rgb import rgb_composite

def example_rgb():
    # Diretório contendo as bandas individuais
    input_path = './images/CBERS4A_WPM19513820250609ETC2' 

    # Diretório e nome do arquivo de saída para a imagem composta
    output_dir = './images' 
    output_filename = 'TRUE_COLOR.tif'

    output_file_path = os.path.join(output_dir, output_filename)

    # Caminhos completos para as bandas vermelha, verde e azul
    red_band_path = os.path.join(input_path, 'CBERS_4A_WPM_20250609_195_138_L4_BAND3.tif')      # Substitua pelo caminho correto da banda vermelha
    green_band_path = os.path.join(input_path, 'CBERS_4A_WPM_20250609_195_138_L4_BAND2.tif')    # Substitua pelo caminho correto da banda verde
    blue_band_path = os.path.join(input_path, 'CBERS_4A_WPM_20250609_195_138_L4_BAND1.tif')     # Substitua pelo caminho correto da banda azul
    nir_band_path = os.path.join(input_path, 'CBERS_4A_WPM_20250609_195_138_L4_BAND4.tif')      # Banda NIR (opcional). Substitua pelo caminho correto da banda NIR

    # 3. Chamada da função para compor a imagem RGB
    print(f"Iniciando composição RGB.")

    rgb_composite(red_band_path, green_band_path, blue_band_path, output_file_path, nir_band_path)

    print(f"Processo concluído! Composições salvas em: {output_file_path}")

if __name__ == "__main__":
    example_rgb()