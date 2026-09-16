from .pansharpening_core import pansharpen_hsv_tiled


def processar_pansharpening_tiles(
    caminho_pan,
    caminho_ms,
    caminho_saida,
    tamanho_tile=2048,
    diretorio_temp=None,
    sample_stride=4,
    crop_to_intersection=True,
    detail_strength=0.65,
):
    return pansharpen_hsv_tiled(
        multispectral_path=caminho_ms,
        panchromatic_path=caminho_pan,
        output_path=caminho_saida,
        tile_size=tamanho_tile,
        sample_stride=sample_stride,
        crop_to_intersection=crop_to_intersection,
        detail_strength=detail_strength,
    )
