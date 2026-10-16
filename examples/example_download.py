import sys
from pathlib import Path

# Sobe um nível para o diretório principal do projeto e adiciona ao path
project_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_dir)

from utils.download import bands_download
from datetime import date

def example_download():
        
    # Coordenadas do local de busca
    # Localização: Domingos Martins - ES, Brasil
    x_min = -40.8940507     # Oeste
    y_min = -20.5950702     # Sul
    x_max = -40.4260507     # Leste
    y_max = -20.1270702     # Norte

    # Usuário cadastrado na plataforma do INPE
    user = 'modestogabriele6@gmail.com'

    # Bounding Box a partir das coordenadas informadas
    bbox = [x_min, y_min, x_max, y_max]

    # Especificações dos produtos a retornar
    max_cloud = 10          # Cobertura de nuvens (max)
    # Um unico produto mantem este exemplo curto. O tempo exato ainda depende
    # da disponibilidade do servidor do INPE e da rede.
    max_products = 1        # Numero maximo de cenas

    # Intervalo para data da busca
    initial_date = date(2025, 1, 1)     # ano, mês, dia
    final_date = date(2025, 7, 12)      # ano, mês, dia

    # Bandas para download
    bands = ['blue', 'green', 'red', 'nir', 'pan']  # Bandas completas de uma cena

    # Diretório para download das bandas
    output_dir = './images'

    # Dicionário com as informações
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

    print(f"Iniciando download das bandas. Limite de {max_products} cena(s).")

    # Chamada da função bands_download
    bands_download(params)

    print(f"Download finalizado! Arquivos salvos em: {output_dir}")

if __name__ == "__main__":
    example_download()
