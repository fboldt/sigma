import sys
from pathlib import Path

# Sobe um nível para o diretório principal do projeto e adiciona ao path
project_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_dir)

import os
from utils.rgb import rgb_composite
from utils.example_inputs import require_directory, require_files

DOWNLOAD_COMMAND = "python run.py download_scene"
USAGE_COMMAND = "python run.py example_rgb ./images/NOME_DA_CENA"

def run(images_dir=None):
    if images_dir is None:
        print("Informe a pasta com as imagens.")
        print(f"Para baixar uma cena de teste, execute na raiz do projeto: {DOWNLOAD_COMMAND}")
        print(f"Depois, execute o exemplo informando a pasta da cena: {USAGE_COMMAND}")
        return

    try:
        return example_rgb(images_dir)
    except FileNotFoundError as erro:
        print(erro)
        print(f"Exemplo de execução: {USAGE_COMMAND}")

def example_rgb(images_dir):
    # Diretório contendo as bandas individuais
    input_path = Path(images_dir).expanduser()
    require_directory(
        "example_rgb",
        input_path,
        download_command=DOWNLOAD_COMMAND,
    )

    # Diretório e nome do arquivo de saída para a imagem composta
    output_dir = input_path  # Diretório de saída (mesmo que o diretório de entrada)
    output_filename = f'TRUE_COLOR_{Path(input_path).name}.tif'

    output_file_path = os.path.join(output_dir, output_filename)

    # Descobre o prefixo da cena a partir de qualquer banda existente.
    sample_band = next(input_path.glob("*_BAND*.tif"), None)
    if sample_band is None:
        raise FileNotFoundError(
            f"Nenhum arquivo de banda (*_BAND*.tif) foi encontrado em {input_path}.\n"
            f"Para baixar uma cena de teste, execute na raiz do projeto: {DOWNLOAD_COMMAND}"
        )

    band_prefix = sample_band.name.rsplit("BAND", 1)[0]
    red_band_path = input_path / f"{band_prefix}BAND3.tif"
    green_band_path = input_path / f"{band_prefix}BAND2.tif"
    blue_band_path = input_path / f"{band_prefix}BAND1.tif"
    nir_band_path = input_path / f"{band_prefix}BAND4.tif"  # Banda NIR opcional.

    require_files(
        "example_rgb",
        [red_band_path, green_band_path, blue_band_path],
        download_command=DOWNLOAD_COMMAND,
    )

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

