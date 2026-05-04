import os
import requests
from urllib.parse import urlparse
import pystac_client

def buscar_itens_stac(url_api, colecao, bbox, periodo):
    catalog = pystac_client.Client.open(url_api)
    
    search = catalog.search(
        collections=[colecao], 
        bbox=bbox, 
        datetime=periodo
    )
    
    return list(search.items())

def baixar_asset(url_asset, pasta_destino='imagens_cbers4a'):
    os.makedirs(pasta_destino, exist_ok=True)
    
    nome_arquivo = os.path.basename(urlparse(url_asset).path)
    caminho_salvar = os.path.join(pasta_destino, nome_arquivo)
    
    with requests.get(url_asset, stream=True) as r:
        r.raise_for_status() # Dispara um erro automaticamente se o download falhar (ex: erro 404 ou 500)
        
        # Download silencioso em blocos de 8KB para não sobrecarregar a memória RAM
        with open(caminho_salvar, "wb") as f_out:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk: 
                    f_out.write(chunk)
                    
    return caminho_salvar