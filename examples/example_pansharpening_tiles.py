"""Pansharpening por tiles a partir da pasta de uma cena CBERS."""
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.definir_tile import definir_tamanho_tile
from utils.example_inputs import require_directory, require_files
from utils.pansharpening_tiles import processar_pansharpening_tiles


def _pan_path(scene_directory):
    matches = sorted(scene_directory.glob("*_BAND0.tif"))
    return matches[0] if matches else scene_directory / "BAND0.tif"


def run(scene_directory=None):
    """Gera PANSHARP usando a PAN da cena e o TRUE_COLOR ja' composto.

    Exemplo:
        python run_example.py exemple_pansharpening_tiles ./images/CENA
    """
    if scene_directory is None:
        raise ValueError(
            "Informe a pasta da cena. Exemplo:\n"
            "python run_example.py exemple_pansharpening_tiles "
            "./images/CBERS4A_WPM19513820250609ETC2"
        )

    scene_dir = Path(scene_directory).expanduser()
    require_directory("exemple_pansharpening_tiles", scene_dir)

    scene_id = scene_dir.name
    pan_path = _pan_path(scene_dir)
    rgb_path = PROJECT_ROOT / "images" / f"TRUE_COLOR_{scene_id}.tif"
    require_files(
        "exemple_pansharpening_tiles",
        [rgb_path, pan_path],
    )

    output_path = PROJECT_ROOT / "images" / f"PANSHARP_{scene_id}.tif"
    temp_dir = PROJECT_ROOT / "images" / "pansharpening_tiles_temp"
    tile_size = definir_tamanho_tile()

    print(f"[*] TRUE_COLOR: {rgb_path}")
    print(f"[*] PAN: {pan_path}")
    print(f"[*] Tile calculado pela RAM disponivel: {tile_size} px")
    result = processar_pansharpening_tiles(
        caminho_pan=str(pan_path),
        caminho_ms=str(rgb_path),
        caminho_saida=str(output_path),
        tamanho_tile=tile_size,
        diretorio_temp=str(temp_dir),
    )
    print(f"[SUCESSO] Pansharpening: {output_path}")
    return result


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else None)
