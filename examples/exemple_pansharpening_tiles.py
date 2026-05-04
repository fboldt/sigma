import os
import sys
pasta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, pasta_raiz)

from utils.pansharpening_tiles import processar_pansharpening_tiles
from utils.definir_tile import definir_tamanho_tile

if __name__ == "__main__":
    caminho_pan = "pan.tif"
    caminho_ms = "cor_verdadeira.tif"
    caminho_saida = "pansharpened_output.tif"

    tamanho_do_tile = definir_tamanho_tile()

    pasta_temporaria = "./tiles_temp"

    if not os.path.exists(caminho_pan) or not os.path.exists(caminho_ms):
        raise FileNotFoundError(f"Os arquivos '{caminho_pan}' ou '{caminho_ms}' não foram encontrados na raiz.")



    processar_pansharpening_tiles(
        caminho_pan=caminho_pan,
        caminho_ms=caminho_ms,
        caminho_saida=caminho_saida,
        tamanho_tile=tamanho_do_tile,
        diretorio_temp=pasta_temporaria
    )