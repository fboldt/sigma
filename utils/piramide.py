import rasterio
from rasterio.enums import Resampling
import os
import shutil # Biblioteca para copiar arquivos

def gerar_copia_com_piramides(caminho_original, fatores=[2, 4, 8, 16, 32]):
    # 1. Criar o nome do novo arquivo (ex: imagem_com_py.tif)
    nome_base, extensao = os.path.splitext(caminho_original)
    caminho_novo = f"{nome_base}_com_piramides{extensao}"

    # 2. Verificar se o arquivo original existe
    if not os.path.exists(caminho_original):
        return

    try:
        # 3. Copiar o arquivo original para o novo caminho
        # Isso garante que o original fique intacto
        shutil.copy2(caminho_original, caminho_novo)

        # 4. Abrir a CÓPIA para gerar as pirâmides
        with rasterio.open(caminho_novo, mode='r+') as dst:
            dst.build_overviews(fatores, Resampling.nearest)
            dst.update_tags(ns='rio_utils', overviews=str(fatores))
            
            return caminho_novo # Devolve o caminho do arquivo novo

    except Exception as e:
        return None