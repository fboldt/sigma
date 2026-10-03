import sys
from pathlib import Path

# Sobe um nível para o diretório principal do projeto e adiciona ao path
project_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_dir)

from utils.rgb import rgb_batch_composite
from example_download_es import example_download_es

def example_download_and_rgb_es():

    # Download de bandas
    bands_path = example_download_es(bands=['red', 'green', 'blue', 'nir'])

    # Composição RGB
    # Nome completo do arquivo de saída
    output_file_path = './images/TRUE_COLOR' 

    # Chamada da função para compor a imagem RGB
    print(f"Iniciando composição RGB.")

    rgb_batch_composite(bands_path, output_file_path)

    print(f"Processo concluído! Composições salvas em: {output_file_path}")

if __name__ == "__main__":
    example_download_and_rgb_es()