"""Download do ES inteiro seguido da composicao RGB."""

from utils.download_arguments import city_download_params, require_rgb_bands
from utils.download import bands_download
from utils.rgb import rgb_batch_composite


def run(bands_code=None):
    try:
        return example_download_and_rgb_es(bands_code)
    except ValueError as error:
        print(error)
        return None


def example_download_and_rgb_es(bands_code):
    params = city_download_params("ES", bands_code)
    require_rgb_bands(params["bands"])
    print(
        f"Iniciando download para {params['location_name']} ({params['location_code']}). "
        f"Bandas: {', '.join(params['bands'])}. Limite de {params['max_products']} cena(s)."
    )
    bands_path = bands_download(params)
    print(f"Download finalizado! Arquivos salvos em: {params['output_dir']}")

    print("Iniciando composicao RGB.")
    rgb_paths = rgb_batch_composite(bands_path, params["output_dir"])
    print(f"Composicoes salvas nas pastas das cenas: {params['output_dir']}")
    return rgb_paths


if __name__ == "__main__":
    run()
