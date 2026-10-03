import sys
from pathlib import Path

# Sobe um nível para o diretório principal do projeto e adiciona ao path
project_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_dir)

from utils.search import search_products
from utils.filter import products_filter
from utils.download import bands_download
from utils.rgb import rgb_batch_composite
from utils.mosaic import mosaic_scenes
from utils.piramide import gerar_copia_com_piramides
from datetime import date
import requests
from shapely.geometry import shape, Polygon
import os

def workflow_mosaic():

    # 1. Parâmetros de busca
    # Download das bandas
    # Usuário cadastrado na plataforma do INPE
    user = 'email@email.com' # E-mail cadastrado na plataforma do INPE

    # Coordenadas do local de busca
    # Localização: Grande Vitória, Brasil
    x_min = -40.3470267     # Oeste
    y_min = -20.2931204     # Sul
    x_max = -40.3430267     # Leste
    y_max = -20.2891204     # Norte

    # Bounding Box a partir das coordenadas informadas
    bbox = [x_min, y_min, x_max, y_max]

    # Especificações dos produtos a retornar
    max_cloud = 10            # Cobertura de nuvens (max)
    max_products = 100        # Número de cenas por Dataset (max)

    # Intervalo para data da busca
    initial_date = date(2025, 1, 1)      # ano, mês, dia
    final_date = date(2026, 9, 15)       # ano, mês, dia

    # Informações referentes ao download das bandas
    bands = ['red', 'green', 'blue', 'nir']     # Bandas para download
    output_dir = './images'                            # Diretório onde os arquivos serão salvos

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

    # 2. Busca e Download de produtos
    print(f"Iniciando busca de produtos das bandas.")
    print(f"Iniciando download das bandas.")
    all_bands_path = bands_download(params)
    print(f"Download finalizado! Arquivos salvos em: {output_dir}")

    # 3. Composição RGB
    # Nome completo do arquivo de saída
    output_file_path = './images/TRUE_COLOR' 
    print(f"Iniciando composição RGB.")
    files = rgb_batch_composite(all_bands_path, output_file_path)
    print(f"Composição finalizada! Arquivos salvos em: {output_file_path}")

    # 4. Formação do mosaico
    output_file_path='./images/MOSAICO_WORKFLOW.tif'
    print(f'Iniciando formação do mosaico.')
    mosaic_scenes(files, output_file_path)
    print(f'Mosaico concluído! Mosaico salvo em: {output_file_path}')

    # 5. Adicionar pirâmides
    print(f'Iniciando adição de pirâmides.')
    gerar_copia_com_piramides(output_file_path)
    print(f'Pirâmides adicionadas! Arquivo final salvo em: {output_file_path.replace(".tif", "_com_piramides.tif")}')


if __name__ == "__main__":
    workflow_mosaic()