import os
import sys
from pathlib import Path

# Sobe um nível para o diretório principal do projeto e adiciona ao path
project_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_dir)

from utils.stac_downloader import buscar_itens_stac, baixar_asset


if __name__ == "__main__":
    url_bdc = "https://data.inpe.br/bdc/stac/v1/"
    colecao = "CB4A-WPM-PCA-FUSED-1"

    bbox_interesse = [
        -40.3108, -20.2836,
        -40.2986, -20.2725
    ]  # [Oeste, Sul, Leste, Norte]

    periodo = "2023-01-01/2026-04-04"
    pasta_saida = "imagens_cbers4a"

    itens = buscar_itens_stac(
        url_bdc,
        colecao,
        bbox_interesse,
        periodo
    )

    if not itens:
        raise ValueError("Nenhuma imagem encontrada para os critérios selecionados.")

    print(f"Foram encontrados {len(itens)} itens.")

    print("\nAssets disponíveis no primeiro item:")
    for nome_asset in itens[0].assets:
        print("-", nome_asset)

    for item in itens:
        if "tci" in item.assets:
            url_tci = item.assets["tci"].href

            print(f"\nIniciando download de: {item.id}")
            baixar_asset(url_tci, pasta_saida)
        else:
            print(f"\nItem {item.id} não possui asset 'tci'.")
            print("Assets disponíveis:", list(item.assets.keys()))
