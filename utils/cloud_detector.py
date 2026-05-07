import os
import numpy as np
import cupy as cp
import rasterio
from rasterio.windows import Window
from rasterio.enums import Resampling
from cupyx.scipy.ndimage import binary_opening, binary_closing


def calcular_nuvens_tci(
    caminho_imagem,
    bbox_wgs84=None,
    salvar_mascara=True,
    tamanho_bloco=1024
):
    if bbox_wgs84 is not None:
        raise NotImplementedError(
            "Esta versão em blocos está configurada para analisar a imagem inteira. "
            "Use bbox_wgs84=None."
        )

    caminho_mascara = None
    total_pixels_validos = 0
    total_pixels_nuvem = 0
    area_total_km2 = None
    area_nuvem_km2 = None

    with rasterio.open(caminho_imagem) as src:
        if src.count < 3:
            raise ValueError(f"A imagem {caminho_imagem} não possui 3 bandas RGB.")

        print("Calculando estatísticas globais da imagem...")

        altura_amostra = min(2000, src.height)
        largura_amostra = min(2000, src.width)

        amostra = src.read(
            [1, 2, 3],
            out_shape=(3, altura_amostra, largura_amostra),
            resampling=Resampling.average
        ).astype("float32")

        red_s = amostra[0]
        green_s = amostra[1]
        blue_s = amostra[2]

        valid_s = np.ones(red_s.shape, dtype=bool)

        if src.nodata is not None:
            valid_s &= red_s != src.nodata
            valid_s &= green_s != src.nodata
            valid_s &= blue_s != src.nodata

        valid_s &= np.isfinite(red_s)
        valid_s &= np.isfinite(green_s)
        valid_s &= np.isfinite(blue_s)

        if valid_s.sum() == 0:
            raise ValueError("Nenhum pixel válido encontrado na amostra da imagem.")

        p2_r, p98_r = np.nanpercentile(red_s[valid_s], [2, 98])
        p2_g, p98_g = np.nanpercentile(green_s[valid_s], [2, 98])
        p2_b, p98_b = np.nanpercentile(blue_s[valid_s], [2, 98])

        r_s = np.clip((red_s - p2_r) / (p98_r - p2_r + 1e-6), 0, 1)
        g_s = np.clip((green_s - p2_g) / (p98_g - p2_g + 1e-6), 0, 1)
        b_s = np.clip((blue_s - p2_b) / (p98_b - p2_b + 1e-6), 0, 1)

        brilho_s = (r_s + g_s + b_s) / 3

        limiar_brilho_global = np.clip(
            np.nanpercentile(brilho_s[valid_s], 94),
            0.60,
            0.80
        )

        print(f"Limiar global de brilho: {limiar_brilho_global:.4f}")

        perfil_mascara = src.profile.copy()
        perfil_mascara.update(
            driver="GTiff",
            count=1,
            dtype="uint8",
            nodata=255,
            compress="lzw"
        )

        if salvar_mascara:
            nome_base = os.path.splitext(os.path.basename(caminho_imagem))[0]
            pasta = os.path.dirname(caminho_imagem)
            caminho_mascara = os.path.join(
                pasta,
                f"{nome_base}_mascara_nuvens.tif"
            )

        dst = None

        try:
            if salvar_mascara:
                dst = rasterio.open(caminho_mascara, "w", **perfil_mascara)

            largura = src.width
            altura = src.height

            print(f"Processando imagem em blocos de {tamanho_bloco}x{tamanho_bloco}...")

            for row_off in range(0, altura, tamanho_bloco):
                for col_off in range(0, largura, tamanho_bloco):
                    win_width = min(tamanho_bloco, largura - col_off)
                    win_height = min(tamanho_bloco, altura - row_off)

                    window = Window(
                        col_off=col_off,
                        row_off=row_off,
                        width=win_width,
                        height=win_height
                    )

                    rgb_cpu = src.read([1, 2, 3], window=window).astype("float32")

                    red = cp.asarray(rgb_cpu[0])
                    green = cp.asarray(rgb_cpu[1])
                    blue = cp.asarray(rgb_cpu[2])

                    valid = cp.ones(red.shape, dtype=bool)

                    if src.nodata is not None:
                        valid &= red != src.nodata
                        valid &= green != src.nodata
                        valid &= blue != src.nodata

                    valid &= cp.isfinite(red)
                    valid &= cp.isfinite(green)
                    valid &= cp.isfinite(blue)

                    pixels_validos_bloco = int(valid.sum().get())

                    if pixels_validos_bloco == 0:
                        saida = np.full(
                            (win_height, win_width),
                            255,
                            dtype="uint8"
                        )

                        if salvar_mascara:
                            dst.write(saida, 1, window=window)

                        continue

                    r = cp.clip((red - p2_r) / (p98_r - p2_r + 1e-6), 0, 1)
                    g = cp.clip((green - p2_g) / (p98_g - p2_g + 1e-6), 0, 1)
                    b = cp.clip((blue - p2_b) / (p98_b - p2_b + 1e-6), 0, 1)

                    brilho = (r + g + b) / 3

                    max_rgb = cp.maximum(cp.maximum(r, g), b)
                    min_rgb = cp.minimum(cp.minimum(r, g), b)

                    saturacao = (max_rgb - min_rgb) / (max_rgb + 1e-6)
                    brancura = 1 - saturacao

                    limiar_brilho = cp.array(
                        limiar_brilho_global,
                        dtype=cp.float32
                    )

                    mascara_nuvem = (
                        valid
                        & (brilho >= limiar_brilho)
                        & (saturacao <= 0.16)
                        & (brancura >= 0.84)
                        & (r >= 0.68)
                        & (g >= 0.68)
                        & (b >= 0.68)
                    )

                    mascara_nuvem = binary_opening(mascara_nuvem, iterations=1)
                    mascara_nuvem = binary_closing(mascara_nuvem, iterations=1)
                    mascara_nuvem &= valid

                    pixels_nuvem_bloco = int(mascara_nuvem.sum().get())

                    total_pixels_validos += pixels_validos_bloco
                    total_pixels_nuvem += pixels_nuvem_bloco

                    if salvar_mascara:
                        mascara_cpu = cp.asnumpy(mascara_nuvem)
                        valid_cpu = cp.asnumpy(valid)

                        saida = np.where(
                            valid_cpu,
                            mascara_cpu.astype("uint8"),
                            255
                        )

                        dst.write(saida, 1, window=window)

                    del (
                        rgb_cpu,
                        red,
                        green,
                        blue,
                        valid,
                        r,
                        g,
                        b,
                        brilho,
                        max_rgb,
                        min_rgb,
                        saturacao,
                        brancura,
                        mascara_nuvem
                    )

                    cp.get_default_memory_pool().free_all_blocks()

        finally:
            if dst is not None:
                dst.close()

        if total_pixels_validos == 0:
            raise ValueError("Nenhum pixel válido encontrado na imagem.")

        percentual_nuvem = total_pixels_nuvem / total_pixels_validos * 100

        if src.crs and src.crs.is_projected:
            area_pixel_m2 = abs(src.transform.a * src.transform.e)
            area_total_km2 = total_pixels_validos * area_pixel_m2 / 1_000_000
            area_nuvem_km2 = total_pixels_nuvem * area_pixel_m2 / 1_000_000

    return {
        "imagem": caminho_imagem,
        "percentual_nuvem": percentual_nuvem,
        "area_total_km2": area_total_km2,
        "area_nuvem_km2": area_nuvem_km2,
        "mascara": caminho_mascara
    }
