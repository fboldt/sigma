from utils.search import search_products
from utils.filter import products_filter
from utils.download import bands_download
from utils.rgb import rgb_batch_composite
from utils.mosaic import mosaic_scenes
from datetime import date
import requests
from shapely.geometry import shape, Polygon

def workflow_mosaic():

    # 1. Parâmetros de busca
    # Usuário cadastrado na plataforma do INPE
    user = 'izabelly.cristine.ic@gmail.com'
        
    # Polígono do local de busca
    # Localização: Espírito Santo (ES)
    url = "https://servicodados.ibge.gov.br/api/v4/malhas/estados/32?formato=application/vnd.geo+json&qualidade=minima" # URL do Query Builder na API do IBGE
    response = requests.get(url) 
    data = response.json() 
    polygon = shape(data['features'][0]['geometry'])
    
    # Especificações dos produtos a retornar
    max_cloud = 10            # Cobertura de nuvens (max)
    max_products =  2000      # Número de cenas por Dataset (max)

    # Intervalo para data da busca
    initial_date = date(2024, 1, 1)      # ano, mês, dia
    final_date = date(2025, 12, 31)      # ano, mês, dia

    # Informações referentes ao download das bandas
    bands = ['red', 'green', 'blue']    # Bandas para download
    output_dir = './images'             # Diretório onde os arquivos serão salvos

    # Dicionário com as informações de busca
    params = {
        'user': user,
        'bbox': Polygon(polygon),
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
    all_bands_path = bands_download(filter_products)
    print(f"Download finalizado! Arquivos salvos em: {output_dir}")

    # 5. Composição RGB
    # Nome completo do arquivo de saída
    output_file_path = './images/TRUE_COLOR' 
    print(f"Iniciando composição RGB.")
    files = rgb_batch_composite(all_bands_path, output_file_path)
    print(f"Composição finalizada! Arquivos salvos em: {output_file_path}")

    # 6. Formação do mosaico
    output_file_path='./images/MOSAIC'
    print(f'Iniciando formação do mosaico.')
    mosaic_scenes(files, output_file_path)
    print(f'Processo concluído! Mosaico salvo em: {output_file_path}')


if __name__ == "__main__":
    workflow_mosaic()