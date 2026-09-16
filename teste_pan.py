import rasterio
from rasterio.windows import Window
from rasterio.enums import Resampling
import numpy as np
import os
import time

def aplicar_pansharpening_raiz(caminho_pan, caminho_ms, caminho_saida):
    print(f"[{time.strftime('%X')}] Iniciando pansharpening RAIZ (Geometria + NumPy)...")
    
    with rasterio.open(caminho_pan) as pan_ds:
        altura_pan = pan_ds.height
        largura_pan = pan_ds.width
        perfil_saida = pan_ds.profile.copy()
        
        with rasterio.open(caminho_ms) as ms_ds:
            num_bandas = ms_ds.count
            
            # Limpamos o perfil de saída para ser o mais simples possível
            perfil_saida.update(
                count=num_bandas, 
                dtype='uint16',
                tiled=True,
                blockxsize=1024,
                blockysize=1024,
                compress=None # Sem compressão para não engasgar o gravador
            )

            tamanho_bloco = 1024
            
            print(f"[{time.strftime('%X')}] Processando a malha de {tamanho_bloco}x{tamanho_bloco}...")
            
            with rasterio.open(caminho_saida, 'w', **perfil_saida) as dest:
                
                # Criamos a nossa própria malha matemática
                for row_off in range(0, altura_pan, tamanho_bloco):
                    for col_off in range(0, largura_pan, tamanho_bloco):
                        
                        # Calcula o tamanho real (para não dar erro nas bordas finais da imagem)
                        altura_bloco = min(tamanho_bloco, altura_pan - row_off)
                        largura_bloco = min(tamanho_bloco, largura_pan - col_off)
                        
                        janela_pan = Window(col_off, row_off, largura_bloco, altura_bloco)
                        
                        # 1. Lê o bloco PAN
                        pan_block = pan_ds.read(1, window=janela_pan).astype('float32')
                        
                        # 2. O Pulo do Gato: Pega as coordenadas geográficas (Bounding Box) da janela atual
                        limites_geo = pan_ds.window_bounds(janela_pan)
                        
                        # 3. Calcula qual é a janela equivalente na imagem MS usando as coordenadas
                        janela_ms = ms_ds.window(*limites_geo)
                        
                        # 4. Lê o bloco MS e força a reamostragem "on the fly" para o tamanho do bloco PAN
                        ms_block = ms_ds.read(
                            window=janela_ms,
                            out_shape=(num_bandas, altura_bloco, largura_bloco),
                            resampling=Resampling.bilinear
                        ).astype('float32')
                        
                        # ==========================================
                        # Matemática do Brovey em NumPy
                        # ==========================================
                        soma_ms = np.sum(ms_block, axis=0) + 1e-8
                        bloco_fundido = np.empty_like(ms_block)
                        
                        for i in range(num_bandas):
                            bloco_fundido[i] = (ms_block[i] / soma_ms) * pan_block
                            
                        bloco_fundido = np.clip(bloco_fundido, 0, 65535).astype('uint16')
                        
                        # 5. Gravação direta
                        dest.write(bloco_fundido, window=janela_pan)

    print(f"[{time.strftime('%X')}] Pansharpening finalizado com sucesso!")

# ==========================================
if __name__ == "__main__":
    caminho_pan = "pan.tif"
    caminho_ms = "cor_verdadeira_nir.tif"
    caminho_saida = "resultado_pansharpening_raiz_nir.tif"

    if not os.path.exists(caminho_pan) or not os.path.exists(caminho_ms):
        print("\n[ERRO] Verifique os arquivos.")
    else:
        try:
            aplicar_pansharpening_raiz(caminho_pan, caminho_ms, caminho_saida)
        except Exception as e:
            import traceback
            print(f"\n[ERRO DETALHADO]\n{traceback.format_exc()}")