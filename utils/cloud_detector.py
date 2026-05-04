import os
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds


def calcular_nuvens_tci(caminho_imagem, bbox_wgs84=None, salvar_mascara=True):
    with rasterio.open(caminho_imagem) as src:
        if src.count < 3:
            raise ValueError(f"A imagem {caminho_imagem} não possui 3 bandas RGB.")

        if bbox_wgs84:
            bbox_src = transform_bounds(
                "EPSG:4326",
                src.crs,
                *bbox_wgs84,
                densify_pts=21
            )

            window = from_bounds(*bbox_src, transform=src.transform)
            window = window.round_offsets().round_lengths()

            rgb = src.read([1, 2, 3], window=window).astype("float32")
            transform_saida = src.window_transform(window)
        else:
            rgb = src.read([1, 2, 3]).astype("float32")
            transform_saida = src.transform

        red = rgb[0]
        green = rgb[1]
        blue = rgb[2]

        valid = np.ones(red.shape, dtype=bool)

        if src.nodata is not None:
            valid &= red != src.nodata
            valid &= green != src.nodata
            valid &= blue != src.nodata

        valid &= np.isfinite(red)
        valid &= np.isfinite(green)
        valid &= np.isfinite(blue)

        if valid.sum() == 0:
            raise ValueError("Nenhum pixel válido encontrado na área analisada.")

        def normalizar(banda):
            p2 = np.nanpercentile(banda[valid], 2)
            p98 = np.nanpercentile(banda[valid], 98)
            return np.clip((banda - p2) / (p98 - p2 + 1e-6), 0, 1)

        r = normalizar(red)
        g = normalizar(green)
        b = normalizar(blue)

        brilho = (r + g + b) / 3

        max_rgb = np.maximum.reduce([r, g, b])
        min_rgb = np.minimum.reduce([r, g, b])
        saturacao = (max_rgb - min_rgb) / (max_rgb + 1e-6)

        # Critérios principais para nuvem em imagem RGB:
        # clara + pouco saturada + tons próximos de branco/cinza
        limiar_brilho = max(0.55, np.nanpercentile(brilho[valid], 75))

        mascara_nuvem = (
            valid
            & (brilho >= limiar_brilho)
            & (saturacao <= 0.28)
            & (r >= 0.45)
            & (g >= 0.45)
            & (b >= 0.45)
        )

        percentual_nuvem = mascara_nuvem.sum() / valid.sum() * 100

        area_total_km2 = None
        area_nuvem_km2 = None

        if src.crs and src.crs.is_projected:
            area_pixel_m2 = abs(transform_saida.a * transform_saida.e)
            area_total_km2 = valid.sum() * area_pixel_m2 / 1_000_000
            area_nuvem_km2 = mascara_nuvem.sum() * area_pixel_m2 / 1_000_000

        caminho_mascara = None

        if salvar_mascara:
            nome_base = os.path.splitext(os.path.basename(caminho_imagem))[0]
            pasta = os.path.dirname(caminho_imagem)
            caminho_mascara = os.path.join(pasta, f"{nome_base}_mascara_nuvens.tif")

            perfil = src.profile.copy()
            perfil.update(
                driver="GTiff",
                height=mascara_nuvem.shape[0],
                width=mascara_nuvem.shape[1],
                count=1,
                dtype="uint8",
                transform=transform_saida,
                nodata=255
            )

            saida = np.where(valid, mascara_nuvem.astype("uint8"), 255)

            with rasterio.open(caminho_mascara, "w", **perfil) as dst:
                dst.write(saida, 1)

        return {
            "imagem": caminho_imagem,
            "percentual_nuvem": percentual_nuvem,
            "area_total_km2": area_total_km2,
            "area_nuvem_km2": area_nuvem_km2,
            "mascara": caminho_mascara
        }
