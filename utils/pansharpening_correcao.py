import rasterio
from rasterio.windows import Window
from rasterio.enums import Resampling
import numpy as np
import warnings

def aplicar_pansharpening_raiz(caminho_pan, caminho_ms, caminho_saida):
    with rasterio.open(caminho_pan) as pan_ds:
        altura_pan = pan_ds.height
        largura_pan = pan_ds.width
        perfil_saida = pan_ds.profile.copy()
        
        with rasterio.open(caminho_ms) as ms_ds:
            num_bandas = ms_ds.count
            
            perfil_saida.update(
                count=num_bandas, 
                dtype='uint16',
                tiled=True,
                blockxsize=1024,
                blockysize=1024,
                compress=None
            )

            tamanho_bloco = 1024
            
            with rasterio.open(caminho_saida, 'w', **perfil_saida) as dest:
                for row_off in range(0, altura_pan, tamanho_bloco):
                    for col_off in range(0, largura_pan, tamanho_bloco):
                        altura_bloco = min(tamanho_bloco, altura_pan - row_off)
                        largura_bloco = min(tamanho_bloco, largura_pan - col_off)
                        
                        janela_pan = Window(col_off, row_off, largura_bloco, altura_bloco)
                        pan_block = pan_ds.read(1, window=janela_pan).astype('float32')
                        
                        limites_geo = pan_ds.window_bounds(janela_pan)
                        janela_ms = ms_ds.window(*limites_geo)
                        
                        ms_block = ms_ds.read(
                            window=janela_ms,
                            out_shape=(num_bandas, altura_bloco, largura_bloco),
                            resampling=Resampling.bilinear
                        ).astype('float32')
                        
                        soma_ms = np.sum(ms_block, axis=0) + 1e-8
                        bloco_fundido = np.empty_like(ms_block)
                        
                        for i in range(num_bandas):
                            bloco_fundido[i] = (ms_block[i] / soma_ms) * pan_block
                            
                        bloco_fundido = np.clip(bloco_fundido, 0, 65535).astype('uint16')
                        dest.write(bloco_fundido, window=janela_pan)


def aplicar_contraste_limpo_8bit(caminho_entrada, caminho_saida, percentil_min=1, percentil_max=99):
    with rasterio.open(caminho_entrada) as src:
        escala = 0.05
        out_shape = (src.count, int(src.height * escala), int(src.width * escala))
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            dados_reduzidos = src.read(out_shape=out_shape).astype('float32')

        p_min_bandas = []
        p_max_bandas = []
        
        for b in range(3):
            banda = dados_reduzidos[b]
            pixels_validos = banda[(banda > 0) & (banda < 60000)] if np.any((banda > 0) & (banda < 60000)) else banda
            
            pmin = np.percentile(pixels_validos, percentil_min)
            pmax = np.percentile(pixels_validos, percentil_max)
            p_min_bandas.append(pmin)
            p_max_bandas.append(pmax)

        perfil_saida = src.profile.copy()
        perfil_saida.update(
            count=3,
            dtype='uint8',
            compress='lzw',
            photometric='RGB',
            BIGTIFF='YES',
            tiled=True,
            blockxsize=512,
            blockysize=512
        )
    
    with rasterio.open(caminho_entrada) as src:
        with rasterio.open(caminho_saida, 'w', **perfil_saida) as dest:
            for ji, window in src.block_windows(1):
                bloco = src.read(window=window).astype('float32')
                bloco_rgb_8bit = np.empty((3, bloco.shape[1], bloco.shape[2]), dtype='uint8')
                mascara_artefatos = (bloco[0] == 0) | (bloco[0] > 60000) | (bloco[1] > 60000) | (bloco[2] > 60000)
                
                for b in range(3):
                    pmin = p_min_bandas[b]
                    pmax = p_max_bandas[b]
                    
                    if pmax - pmin == 0:
                        bloco_rgb_8bit[b] = 0
                        continue
                        
                    b_norm = (bloco[b] - pmin) / (pmax - pmin)
                    b_norm = np.clip(b_norm, 0, 1)
                    
                    bloco_final = (b_norm * 255).astype('uint8')
                    bloco_final[mascara_artefatos] = 0
                    bloco_rgb_8bit[b] = bloco_final
                    
                dest.write(bloco_rgb_8bit, window=window)