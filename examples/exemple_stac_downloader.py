import os
import sys

# Força o Python a enxergar a pasta raiz (sigma) como o diretório principal absoluto
pasta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, pasta_raiz)

from utils.stac_downloader import buscar_itens_stac, baixar_asset

if __name__ == "__main__":
    # Parâmetros da busca
    url_bdc = "https://data.inpe.br/bdc/stac/v1/"
    colecao = "CB4A-WPM-PCA-FUSED-1"
    bbox_interesse =[-41.1779558, -20.0230143, -40.9339558, -19.7790143]  # [Oeste, Sul, Leste, Norte]
    periodo = "2023-01-01/2026-04-04"
    pasta_saida = "imagens_cbers4a"

    # 1. Realiza a busca no catálogo
    itens = buscar_itens_stac(url_bdc, colecao, bbox_interesse, periodo)

    # Verifica se a busca encontrou algo
    if not itens:
        raise ValueError(f"Nenhuma imagem encontrada para os critérios selecionados.")

    # 2. Percorre TODOS os itens encontrados e realiza o download
    for item in itens:
        if 'tci' in item.assets:
            url_tci = item.assets['tci'].href 
            print(f"Iniciando download de: {item.id}")
            baixar_asset(url_tci, pasta_saida)