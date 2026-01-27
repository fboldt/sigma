from utils.rgb import rgb_batch_composite
from example_download_es import example_download_es

def example_download_and_rgb_es():

    # Download de bandas
    bands_path = example_download_es(bands=['red', 'green', 'blue'])

    # Composição RGB
    # Nome completo do arquivo de saída
    output_file_path = './images/TRUE_COLOR' 

    # Chamada da função para compor a imagem RGB
    rgb_batch_composite(bands_path, output_file_path)

if __name__ == "__main__":
    example_download_and_rgb_es()