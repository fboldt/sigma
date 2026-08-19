from utils.search import search_products
from utils.filter import products_filter
from utils.download import bands_download
from utils.rgb import rgb_batch_composite
from utils.mosaic import mosaic_scenes
from datetime import date
import requests
from shapely.geometry import shape, Polygon
import os

def workflow_mosaic():

    # 1. Parâmetros de busca
    # Download das bandas
    # Usuário cadastrado na plataforma do INPE
    user = 'izabellyglassiner@gmail.com'

    # Coordenadas do local de busca
    # Localização: Domingos Martins - ES, Brasil
    x_min = -42.080195454621    # Oeste
    y_min = -20.98380835559   # Sul
    x_max = -39.262195454621     # Leste
    y_max = -18.16580835559    # Norte

    # Bounding Box a partir das coordenadas informadas
    bbox = [x_min, y_min, x_max, y_max]

    # Especificações dos produtos a retornar
    max_cloud = 0         # Cobertuda de nuvens (max)
    max_products = 5        # Número de cenas por Dataset (max)

    # Intervalo para data da busca
    initial_date = date(2023, 1, 1)     # ano, mês, dia
    final_date = date(2026, 4, 26)      # ano, mês, dia

    # Informações referentes ao download das bandas
    bands = ['red', 'green', 'blue', 'pan']    # Bandas para download
    output_dir = './images'             # Diretório onde os arquivos serão salvos

    # Dicionário com as informações de busca
    params = {
        'user': user,
        'bbox': bbox,
        'max_cloud': max_cloud,
        'max_products': max_products,
        'initial_date': initial_date,
        'final_date': final_date,
        'bands': bands,
        'output_dir': output_dir
    }

    # 2. Busca de produtos
    print(f"Iniciando busca de produtos das bandas.")
    products = search_products(params)

    # 3. Filtragem de produtos encontrados
    print(f"Iniciando filtragem de produtos retornados em um mesmo local.")
    filter_products = products_filter(products)

    # 4. Download dos produtos filrados
    print(f"Iniciando download das bandas.")
    all_bands_path = bands_download(params, filter_products)
    print(f"Download finalizado! Arquivos salvos em: {output_dir}")

    # 5. Composição RGB
    # Nome completo do arquivo de saída
    output_file_path = './images/TRUE_COLOR' 
    print(f"Iniciando composição RGB.")
    files = rgb_batch_composite(all_bands_path, output_file_path)
    print(f"Composição finalizada! Arquivos salvos em: {output_file_path}")

    # 6. Formação do mosaico
    output_file_path='./images/MOSAICO_EXEMPLO_WORKFLOW'
    print(f'Iniciando formação do mosaico.')
    mosaic_scenes(files, output_file_path)
    print(f'Processo concluído! Mosaico salvo em: {output_file_path}')


if __name__ == "__main__":
    workflow_mosaic()