import os
import sys

# Força o Python a enxergar a pasta raiz (sigma) como o diretório principal absoluto
pasta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, pasta_raiz)

from utils.pansharpening_tiles import processar_pansharpening_tiles

if __name__ == "__main__":
    # Configuração de caminhos e parâmetros
    caminho_pan = "pan.tif"
    caminho_ms = "cor_verdadeira.tif"
    caminho_saida = "pansharpened_output.tif"
    
    tamanho_do_tile = 4096 # Reduza para 2048 se faltar memória RAM
    pasta_temporaria = "./tiles_temp"

    # Validação de segurança
    if not os.path.exists(caminho_pan) or not os.path.exists(caminho_ms):
        raise FileNotFoundError(f"Os arquivos '{caminho_pan}' ou '{caminho_ms}' não foram encontrados na raiz.")

    # Execução silenciosa
    processar_pansharpening_tiles(
        caminho_pan=caminho_pan,
        caminho_ms=caminho_ms,
        caminho_saida=caminho_saida,
        tamanho_tile=tamanho_do_tile,
        diretorio_temp=pasta_temporaria
    )