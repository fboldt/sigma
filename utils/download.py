from cbers4asat import Cbers4aAPI
from datetime import date
import os
import glob
import time
import logging
logger = logging.getLogger(__name__)


# Função para baixar produtos
def bands_download(params, products=None):
    # Instanciando o objeto com o usuário cadastrado na plataforma
    api = Cbers4aAPI(params['user'])

    if products == None:
        # Busca por produtos
        products = api.query(location=params.get('location') or params.get('bbox'),
                            initial_date=params['initial_date'],
                            end_date=params['final_date'],
                            cloud=params['max_cloud'],
                            limit=params['max_products'],
                            collections=['CBERS4A_WPM_L4_DN']
                            )

    # Definido bandas para download
    bands = params.get('bands', ['red', 'green', 'blue', 'nir', 'pan'])

    # A banda PAN tem limite de cota da API (10 downloads/hora), então é baixada separadamente, com espaçamento de tempo. 
    bands_sem_pan = [b for b in bands if b != 'pan']
    baixar_pan = 'pan' in bands

    downloaded_rgb_nir = {'type': products.get('type', 'FeatureCollection'), 'features': []}
    if bands_sem_pan:
        downloaded_rgb_nir = download_with_retries(api=api,
                 products=products,
                 bands=bands_sem_pan,
                 outdir=params['output_dir']
                 )

    if baixar_pan:
        download_pan_with_retries(api=api,
                 products=products,
                 outdir=params['output_dir'],
                 requests_per_hour=params.get('pan_requests_per_hour', 10)
                 )

    # Localização de produtos baixados. Usa a lista completa de produtos consultados
    all_bands_paths = bands_paths(params['output_dir'], products)
    return all_bands_paths


# Função para baixar os produtos em rodadas
def download_with_retries(api, products, bands, outdir, max_trials=5, wait_time=60):
    downloaded_products = []
    pending_products = list(products['features'])
    errors = {}

    trial = 1
    while pending_products and trial <= max_trials:
        failed_this_round = []

        for product in pending_products:
            id_product = {'type': products.get('type', 'FeatureCollection'), 'features': [product]}
            try:
                api.download(products=id_product, bands=bands,
                             threads=len(bands), outdir=outdir, with_folder=True)
                downloaded_products.append(product)
                errors.pop(product['id'], None)
            except Exception as e:
                errors[product['id']] = repr(e)
                logger.warning("Falha ao baixar %s (tentativa %d): %r", product['id'], trial, e)
                failed_this_round.append(product)

        pending_products = failed_this_round
        if pending_products and trial < max_trials:
            time.sleep(wait_time)
        trial += 1

    result = {'type': products.get('type', 'FeatureCollection'), 'features': downloaded_products}
    return result, errors


# Função para baixar a banda PAN respeitando o limite de cota da API (10 downloads/hora por e-mail). 
def download_pan_with_retries(api, products, outdir, max_trials=3, requests_per_hour=10, wait_time=30):
    downloaded_products = []
    pending_products = list(products['features'])

    # Intervalo mínimo entre downloads de PAN, com margem de segurança de 5%
    min_interval = (3600 / requests_per_hour) * 1.05

    trial = 1
    while pending_products and trial <= max_trials:
        failed_this_round = []
        quota_hit = False

        for i, product in enumerate(pending_products):
            if quota_hit:
                failed_this_round.append(product)
                continue

            id_product = {'type': products.get('type', 'FeatureCollection'), 'features': [product]}

            try:
                api.download(products=id_product,
                             bands=['pan'],
                             threads=1,
                             outdir=outdir,
                             with_folder=True
                             )
                downloaded_products.append(product)

                if i < len(pending_products) - 1:
                    time.sleep(min_interval)

            except Exception as e:
                message = str(e)

                if "limite" in message.lower() or "limit" in message.lower():
                    failed_this_round.append(product)
                    quota_hit = True
                else:
                    failed_this_round.append(product)
                    time.sleep(wait_time)

        pending_products = failed_this_round

        if pending_products:
            if trial < max_trials:
                if quota_hit:
                    time.sleep(3600)
                else:
                    time.sleep(wait_time)

        trial += 1

    if pending_products:
        failed_ids = [produto['id'] for produto in pending_products]

    return {'type': products.get('type', 'FeatureCollection'), 'features': downloaded_products}


# Função para localizar os caminhos das bandas RGB dos produtos baixados
def bands_paths(output_dir, produtos):
    all_bands_paths = [] 
    
    for produto_info in produtos['features']:
        produto_id = produto_info['id'] # ID da cena atual
        
        # Localização da pasta da cena atual
        scene_folder_pattern = os.path.join(output_dir, f"*{produto_id}*")
        scene_dir_list = glob.glob(scene_folder_pattern)

        if not scene_dir_list:
            # Nenhuma banda dessa cena foi baixada
            continue

        scene_dir = scene_dir_list[0]
        
        # Prefixo para os nomes dos arquivos contendo as bandas
        scene_id_prefix = f"CBERS_4A_WPM_{produto_info['properties']['datetime'][:10].replace('-', '')}_{produto_info['properties']['path']}_{produto_info['properties']['row']}_L4"
        
        # Caminhos completos para as bandas
        nir_band_path = os.path.join(scene_dir, f"{scene_id_prefix}_BAND4.tif")
        red_band_path = os.path.join(scene_dir, f"{scene_id_prefix}_BAND3.tif")
        green_band_path = os.path.join(scene_dir, f"{scene_id_prefix}_BAND2.tif")
        blue_band_path = os.path.join(scene_dir, f"{scene_id_prefix}_BAND1.tif")
        pan_band_path = os.path.join(scene_dir, f"{scene_id_prefix}_BAND0.tif")

        # Adição à lista contendo o caminho das bandas de todas as cenas baixadas
        scene_bands = {'id': produto_id}

        # Cada banda só entra no dicionário se ela tiver sido baixada
        if os.path.exists(red_band_path):
            scene_bands['red'] = red_band_path
        if os.path.exists(green_band_path):
            scene_bands['green'] = green_band_path
        if os.path.exists(blue_band_path):
            scene_bands['blue'] = blue_band_path
        if os.path.exists(nir_band_path):
            scene_bands['nir'] = nir_band_path
        if os.path.exists(pan_band_path):
            scene_bands['pan'] = pan_band_path

        all_bands_paths.append(scene_bands)
        
    return all_bands_paths