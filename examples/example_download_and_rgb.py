from utils.download import bands_download
from utils.rgb import rgb_composite
from datetime import date
import os
import glob

def example_download_and_rgb():
    # Download das bandas
    # Usuário cadastrado na plataforma do INPE
    user = 'izabelly.cristine.ic@gmail.com'

    # Coordenadas do local de busca
    # Localização: Domingos Martins - ES, Brasil
    x_min = -40.8940507     # Oeste
    y_min = -20.5950702     # Sul
    x_max = -40.4260507     # Leste
    y_max = -20.1270702     # Norte

    # Bounding Box a partir das coordenadas informadas
    bbox = [x_min, y_min, x_max, y_max]

    # Especificações dos produtos a retornar
    max_cloud = 10          # Cobertuda de nuvens (max)
    max_products = 1        # Número de cenas por Dataset (max)

    # Intervalo para data da busca
    initial_date = date(2025, 1, 1)     # ano, mês, dia
    final_date = date(2025, 7, 12)      # ano, mês, dia

    # Diretório para download das bandas
    output_dir = './images'

    # Chamada da função bands_download
    r_band_path, g_band_path, b_band_path = bands_download(user, bbox, initial_date, final_date, max_cloud, max_products, output_dir)

    # Composição RGB
    # Diretório e nome do arquivo de saída para a imagem composta
    output_dir = './images' 
    output_filename = 'composicao_rgb.tif'

    output_file_path = os.path.join(output_dir, output_filename)

    # Caminhos completos para as bandas vermelha, verde e azul
    red_band_path = os.path.join(r_band_path)
    green_band_path = os.path.join(g_band_path)
    blue_band_path = os.path.join(b_band_path)

    # 3. Chamada da função para compor a imagem RGB
    rgb_composite(red_band_path, green_band_path, blue_band_path, output_file_path)

if __name__ == "__main__":
    example_download_and_rgb()