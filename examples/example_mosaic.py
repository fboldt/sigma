import sys
from pathlib import Path

# Sobe um nível para o diretório principal do projeto e adiciona ao path
project_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_dir)

from utils.mosaic import mosaic_scenes


def example_mosaic():
    # A primeira cena define o CRS de referencia e a prioridade no merge.
    cenas = [
        "./images/TRUE_COLOR_CBERS4A_WPM19714020250630ETC2.tif", # Substitua pelos caminhos corretos das suas imagens
        "./images/TRUE_COLOR_CBERS4A_WPM19713920250630ETC2.tif",
        "./images/TRUE_COLOR_CBERS4A_WPM19713820250630ETC2.tif",
        "./images/TRUE_COLOR_CBERS4A_WPM19713720250630ETC2.tif",
        "./images/TRUE_COLOR_CBERS4A_WPM19713620250630ETC2.tif",
        "./images/TRUE_COLOR_CBERS4A_WPM19614020251006ETC2.tif", 
        "./images/TRUE_COLOR_CBERS4A_WPM19613920250604ETC2.tif"
    ]


    output_file_path = "./images/MOSAICO_ES.tif"
    mosaic_scenes(cenas, output_file_path, reference_index=0)

if __name__ == "__main__":
    example_mosaic()

