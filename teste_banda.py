import os
import requests
from urllib.parse import urlparse
from tqdm import tqdm
import pystac_client

# 1. Busca no STAC
url_bdc = "https://data.inpe.br/bdc/stac/v1/"
catalog = pystac_client.Client.open(url_bdc)

colecao = "CB4A-WPM-PCA-FUSED-1"
bbox_interesse = [-41.1779558, -20.0230143, -40.9339558, -19.7790143]  # [Oeste, Sul, Leste, Norte]
periodo = "2023-01-01/2023-12-31"

# --- CONFIGURAÇÃO DE NUVENS ---
# Escolha a porcentagem máxima de nuvens permitida (0 a 100)
limite_nuvens = 0 

print(f"Buscando imagens do ES com no máximo {limite_nuvens}% de nuvens...")

# Parâmetro 'query' filtra as propriedades do item no STAC
search = catalog.search(
    collections=[colecao], 
    bbox=bbox_interesse, 
    datetime=periodo,
    query={"eo:cloud_cover": {"lte": limite_nuvens}} # lte = Less Than or Equal a 10
)
items = list(search.items())

print(f"Foram encontrados {len(items)} itens superando o filtro de nuvens.")

# 2. Função de Download Direto
def baixar_imagem_bdc(url_asset, pasta_destino='imagens_cbers4a'):
    os.makedirs(pasta_destino, exist_ok=True)
    
    nome_arquivo = os.path.basename(urlparse(url_asset).path)
    caminho_salvar = os.path.join(pasta_destino, nome_arquivo)
    
    print(f"\nIniciando o download: {nome_arquivo}")
    
    with requests.get(url_asset, stream=True) as r:
        r.raise_for_status() 
        tamanho_total = int(r.headers.get('content-length', 0))
        
        with tqdm.wrapattr(open(caminho_salvar, "wb"), "write", miniters=1, total=tamanho_total) as f_out:
            for chunk in r.iter_content(chunk_size=8192):
                f_out.write(chunk)
                
    print(f"\nSucesso! Arquivo salvo em: {caminho_salvar}")

# 3. Executando o download do primeiro item limpo retornado
if items:
    url_tci = items[0].assets['tci'].href 
    
    # Se quiser ver a porcentagem exata de nuvens da imagem escolhida antes de baixar:
    nuvens_reais = items[0].properties.get('eo:cloud_cover')
    print(f"A imagem selecionada possui {nuvens_reais}% de cobertura de nuvens.")
    
    baixar_imagem_bdc(url_tci)
else:
    print("Nenhuma imagem com esse critério de nuvens foi encontrada no período.")