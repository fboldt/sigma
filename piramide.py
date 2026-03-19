import rasterio
from rasterio.enums import Resampling

caminho_tif = "ifes_resultado_pansharpening_raiz.tif"
fatores = [2, 4, 8, 16, 32]

# O segredo é o modo 'r+' (abre para leitura e permite escrita)
with rasterio.open(caminho_tif, mode='r+') as dst:
    print(f"Gerando pirâmides para: {caminho_tif}")
    # Agora o objeto 'dst' terá o atributo build_overviews
    dst.build_overviews(fatores, Resampling.average)
    
print("Sucesso! O arquivo .ovr foi criado ou o .tif foi atualizado.")