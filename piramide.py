import os
from osgeo import gdal

# Caminho para sua imagem CBERS-4A (ex: MUX, WPM ou PAN)
caminho_tif = "C:/caminho/para/sua/imagem_cbers.tif"

# Abre o dataset em modo de escrita (1)
ds = gdal.Open(caminho_tif, 1)

# Define os níveis de escala (geralmente potências de 2)
niveis = [2, 4, 8, 16, 32, 64]

# Constrói as pirâmides
# O algoritmo 'AVERAGE' é ótimo para dados ópticos/contínuos
ds.BuildOverviews("AVERAGE", niveis)

# Fecha o dataset para salvar as alterações
ds = None
print("Pirâmides geradas com sucesso!")