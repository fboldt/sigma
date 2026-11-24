"""Download de uma cidade do ES a partir da sigla e das bandas desejadas."""

from utils.download import bands_download
from utils.download_arguments import city_download_params


def run(city_code=None, bands_code=None):
    try:
        return download_scene(city_code, bands_code)
    except ValueError as error:
        print(error)
        return None


def download_scene(city_code, bands_code):
    params = city_download_params(city_code, bands_code)
    print(
        f"Iniciando download para {params['location_name']} ({params['location_code']}). "
        f"Bandas: {', '.join(params['bands'])}. Limite de {params['max_products']} cena(s)."
    )
    result = bands_download(params)
    print(f"Download finalizado! Arquivos salvos em: {params['output_dir']}")
    return result


if __name__ == "__main__":
    run()
