from cbers4asat import Cbers4aAPI
from datetime import date
import os
import glob

def bands_download(params):
    # Instanciando o objeto com o usuário cadastrado na plataforma
    api = Cbers4aAPI(params['user'])

    # Busca por produtos
    produtos = api.query(location=params['bbox'],
                         initial_date=params['initial_date'],
                         end_date=params['final_date'],
                         cloud=params['max_cloud'],
                         limit=params['max_products'],
                         collections=['CBERS4A_WPM_L4_DN']
                         )
    
    # Definido bandas para download
    bands = params.get('bands', ['red', 'green', 'blue', 'nir', 'pan'])

    api.download(products=produtos,
             bands=bands,
             threads=len(bands),
             outdir=params['output_dir'],
             with_folder=True
             )
    
    # Localização de produtos baixados
    all_bands_paths = bands_paths(params['output_dir'], produtos)
    return all_bands_paths

# Função para localizar os caminhos das bandas RGB dos produtos baixados
def bands_paths(output_dir, produtos):
    all_bands_paths = [] 
    
    for produto_info in produtos['features']:
        produto_id = produto_info['id'] # ID da cena atual
        
        # Localização da pasta da cena atual
        scene_folder_pattern = os.path.join(output_dir, f"*{produto_id}*")
        scene_dir_list = glob.glob(scene_folder_pattern)
        
        scene_dir = scene_dir_list[0] 
        
        # Prefixo para os nomes dos arquivos contendo as bandas
        scene_id_prefix = f"CBERS_4A_WPM_{produto_info['properties']['datetime'][:10].replace('-', '')}_{produto_info['properties']['path']}_{produto_info['properties']['row']}_L4"
        
        # Caminhos completos para as bandas
        red_band_path = os.path.join(scene_dir, f"{scene_id_prefix}_BAND3.tif")
        green_band_path = os.path.join(scene_dir, f"{scene_id_prefix}_BAND2.tif")
        blue_band_path = os.path.join(scene_dir, f"{scene_id_prefix}_BAND1.tif")

        # Adição à lista contendo o caminho das bandas de todas as cenas baixadas
        all_bands_paths.append({
             'id': produto_id,
             'red': red_band_path,
             'blue': blue_band_path,
             'green': green_band_path,
            })
        
    return all_bands_paths