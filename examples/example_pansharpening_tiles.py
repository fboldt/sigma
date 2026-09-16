import sys
from pathlib import Path

# Faz o Python enxergar a pasta raiz (sigma) como pacote local.
pasta_raiz = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pasta_raiz))

from utils.pansharpening_tiles import processar_pansharpening_tiles


if __name__ == "__main__":
    scene_id = "CBERS4A_WPM19513920210412"

    # BAND0 e a banda pancromatica do WPM; TRUE_COLOR e o RGB de 8 m.
    caminho_pan = (
        pasta_raiz
        / "mosaico_es_manual_rgb_pan"
        / "downloads"
        / scene_id
        / "CBERS_4A_WPM_20210412_195_139_L4_BAND0.tif"
    )
    caminho_ms = (
        pasta_raiz
        / "images"
        / "pansharp_lista_cenas"
        / "rgb"
        / f"TRUE_COLOR_{scene_id}.tif"
    )
    caminho_saida = (
        pasta_raiz
        / "images"
        / "pansharp_lista_cenas"
        / "pansharp_teste_unico"
        / f"PANSHARP_{scene_id}.tif"
    )

    tamanho_do_tile = 2048
    pasta_temporaria = pasta_raiz / "images" / "pansharp_lista_cenas" / "tiles_temp_unico"

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    pasta_temporaria.mkdir(parents=True, exist_ok=True)

    if not caminho_pan.exists() or not caminho_ms.exists():
        raise FileNotFoundError(
            "Arquivos de entrada nao encontrados:\n"
            f"PAN: {caminho_pan}\n"
            f"RGB: {caminho_ms}"
        )

    print(f"Cena: {scene_id}")
    print(f"PAN: {caminho_pan}")
    print(f"RGB/MS: {caminho_ms}")
    print(f"Saida: {caminho_saida}")

    processar_pansharpening_tiles(
        caminho_pan=str(caminho_pan),
        caminho_ms=str(caminho_ms),
        caminho_saida=str(caminho_saida),
        tamanho_tile=tamanho_do_tile,
        diretorio_temp=str(pasta_temporaria),
        sample_stride=4,
        crop_to_intersection=True,
        detail_strength=0.65,
    )

    print("Pansharpening concluido.")
