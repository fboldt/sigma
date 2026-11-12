import sys
from pathlib import Path

# Sobe um nível para o diretório principal do projeto e adiciona ao path
project_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_dir)

import os
from utils.rgb import rgb_composite
from utils.example_inputs import require_files

def run(images_dir=None):
    if images_dir is None:
        print("Informe a pasta com as imagens.")
        print(r"Exemplo: python run_example.py example_rgb ./images/NOME_DA_CENA")
        return

    try:
        return example_rgb(images_dir)
    except FileNotFoundError as erro:
        print(erro)
        print(r"Exemplo: python run_example.py example_rgb ./images/NOME_DA_CENA")

def example_rgb(images_dir):
    # Diretório contendo as bandas individuais
    input_path = Path(images_dir)

    # Diretório e nome do arquivo de saída para a imagem composta
    output_dir = input_path  # Diretório de saída (mesmo que o diretório de entrada)
    output_filename = 'TRUE_COLOR.tif'

    output_file_path = os.path.join(output_dir, output_filename)

    # Caminhos completos para as bandas vermelha, verde e azul
    red_band_path = next(input_path.glob("*BAND3.tif"))
    green_band_path = red_band_path.with_name(red_band_path.name.replace("BAND3.tif", "BAND2.tif"))
    blue_band_path = red_band_path.with_name(red_band_path.name.replace("BAND3.tif", "BAND1.tif"))
    nir_band_path = red_band_path.with_name(red_band_path.name.replace("BAND3.tif", "BAND4.tif"))   # Banda NIR (opcional). Substitua pelo caminho correto da banda NIR

    if not (red_band_path.exists() and green_band_path.exists() and blue_band_path.exists() or nir_band_path.exists()):
        raise FileNotFoundError("Uma ou mais bandas necessárias não foram encontradas no diretório especificado.")
    
    require_files("example_rgb", [red_band_path, green_band_path, blue_band_path])

    # 3. Chamada da função para compor a imagem RGB
    print(f"Iniciando composição RGB.")

    rgb_composite(
        red_band_path,
        green_band_path,
        blue_band_path,
        output_file_path,
        nir_band_path if os.path.isfile(nir_band_path) else None,
    )

    print(f"Processo concluído! Composições salvas em: {output_file_path}")

