import os
import pandas as pd
from datetime import datetime
import sys
import shutil
pasta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, pasta_raiz)

from utils.cloud_detector import calcular_nuvens_tci


'''bbox_interesse = [
    -41.1779558, -20.0230143,
    -40.9339558, -19.7790143
]'''

pasta_imagens = "imagens_cbers4a"

resultados = []

for nome_arquivo in os.listdir(pasta_imagens):
    if not nome_arquivo.lower().endswith((".tif", ".tiff")):
        continue

    if "mascara_nuvens" in nome_arquivo:
        continue

    caminho = os.path.join(pasta_imagens, nome_arquivo)

    print(f"{datetime.now()} - Analisando: {nome_arquivo}")

    try:
        resultado = calcular_nuvens_tci(
            caminho_imagem=caminho,
            bbox_wgs84=None,
            salvar_mascara=True,
            tamanho_bloco=2048,
            salvar_blocos=True
        )

        resultados.append(resultado)

        print(f"Nuvens: {resultado['percentual_nuvem']:.2f}%")
        if resultado["percentual_nuvem"] <= 3:
            destino = os.path.join(
                "C:/Users/Julia Almeida/sigma/teste_imagens",
                os.path.basename(caminho)
            )
            shutil.copy(caminho, destino)
    except Exception as erro:
        print(f"Erro ao analisar {nome_arquivo}: {erro}")

df = pd.DataFrame(resultados)

df = df.sort_values("percentual_nuvem")

df.to_csv("resultado_nuvens_cbers4a.csv", index=False)

print("\nResultado final:")
print(df[["imagem", "percentual_nuvem", "area_total_km2", "area_nuvem_km2"]])
