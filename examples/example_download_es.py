from utils.download import bands_download
from datetime import date
import requests
from shapely.geometry import shape, Polygon

def example_download_es(bands=['red', 'green', 'blue', 'nir', 'pan']):

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
    max_products =  1         # Número de cenas por Dataset (max)

    # Intervalo para data da busca
    initial_date = date(2025, 1, 1)      # ano, mês, dia
    final_date = date(2025, 12, 31)      # ano, mês, dia

    # Diretório para download das bandas
    output_dir = './images'

    # Dicionário com as informações
    params = {
        'user': user,
        'bbox': Polygon(polygon),
        'max_cloud': max_cloud,
        'max_products': max_products,
        'initial_date': initial_date,
        'final_date': final_date,
        'bands': bands,                  # Por prdão, baixa todas as bandas (red, green, blue, NIR e PAN), mas pode ser definida pelo usuário
        'output_dir': output_dir
    }

    # Chamada da função bands_download
    return bands_download(params)

if __name__ == "__main__":
    example_download_es()