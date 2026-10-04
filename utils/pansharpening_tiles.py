import os

from .pansharpening_core import pansharpen_hsv_tiled


# Função para pansharpening de uma cena
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


# Função para pansharpening automatizado
def pansharpening_batch_composite(bands_path, rgb_paths, output_file_path):
    all_pansharp_paths = []

    # Extrai o diretório e o nome base
    output_dir = os.path.dirname(output_file_path)
    base_filename = os.path.basename(output_file_path)
    os.makedirs(output_dir, exist_ok=True)

    # O rgb_batch_composite devolve as composições na mesma ordem das cenas
    for scene, rgb_path in zip(bands_path, rgb_paths):
        scene_id = scene.get('id')
        pan_path = scene.get('pan')

        # Cena sem banda PAN (ex.: limite de cota da API) não passa pelo pansharpening
        if pan_path is None:
            continue

        # Nome do arquivo com a especificação referente à cena
        output_filename = f"{base_filename}_{scene_id}.tif"
        output_path = os.path.join(output_dir, output_filename)

        processar_pansharpening_tiles(caminho_pan=pan_path,
                                      caminho_ms=rgb_path,
                                      caminho_saida=output_path)

        all_pansharp_paths.append(output_path)

    return all_pansharp_paths