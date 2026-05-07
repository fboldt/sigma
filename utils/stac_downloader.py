import os
import requests
from urllib.parse import urlparse
import pystac_client
import time

def buscar_itens_stac(url_api, colecao, bbox, periodo):
    catalog = pystac_client.Client.open(url_api)
    search = catalog.search(
        collections=[colecao], 
        bbox=bbox, 
        datetime=periodo
    )
    return list(search.items())

def baixar_asset(url_asset, pasta_destino='imagens_cbers4a', retries=5):
    os.makedirs(pasta_destino, exist_ok=True)
    
    nome_arquivo = os.path.basename(urlparse(url_asset).path)
    caminho_salvar = os.path.join(pasta_destino, nome_arquivo)
    
    for tentativa in range(retries):
        try:
            # Verifica se o arquivo já existe para retomar o download
            tamanho_local = os.path.getsize(caminho_salvar) if os.path.exists(caminho_salvar) else 0
            headers = {"Range": f"bytes={tamanho_local}-"} if tamanho_local > 0 else {}
            
            # stream=True é essencial para arquivos grandes
            with requests.get(url_asset, headers=headers, stream=True, timeout=30) as r:
                # 200 = OK (do zero), 206 = Partial Content (resumo), 416 = Já terminou
                if r.status_code == 416:
                    print(f"Arquivo {nome_arquivo} já está completo.")
                    return caminho_salvar
                
                r.raise_for_status()
                
                modo_abertura = "ab" if tamanho_local > 0 else "wb"
                
                with open(caminho_salvar, modo_abertura) as f_out:
                    # Usando blocos maiores (1MB) para performance em arquivos de GBs
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f_out.write(chunk)
                
                print(f"Download concluído: {nome_arquivo}")
                return caminho_salvar

        except (requests.exceptions.RequestException, requests.exceptions.ConnectionError) as e:
            print(f"Tentativa {tentativa + 1} falhou para {nome_arquivo}: {e}")
            if tentativa < retries - 1:
                time.sleep(5) # Espera 5 segundos antes de tentar de novo
            else:
                print(f"Erro persistente após {retries} tentativas.")
                raise