from cbers4asat import Cbers4aAPI
from datetime import date
import os
import glob

def bands_download(user, bbox, initial_date, final_date, max_cloud, max_products, output_dir):
    # Instanciando o objeto com o usuário cadastrado na plataforma
    api = Cbers4aAPI(user)

    # Busca no catálogo de imagens
    produtos = api.query(location=bbox,
                        initial_date=initial_date,
                        end_date=final_date,
                        cloud=max_cloud,
                        limit=max_products,
                        collections=['CBERS4A_WPM_L4_DN']
                        )
    
    produto_info = produtos['features'][0]
    produto_id = produto_info['id']
    
    # Download dos produtos encontrados
    api.download(products=produtos,
             bands=['red', 'green', 'blue'],
             threads=3,  # Número de downloads simultâneos
             outdir=output_dir,
             with_folder=True # Agrupar bandas de uma cena em uma subpasta
             )
    
    # Encontrando os produtos baixados
    scene_folder_pattern = os.path.join(output_dir, f"*{produto_id}*")
    scene_dir_list = glob.glob(scene_folder_pattern)


    scene_dir = scene_dir_list[0]
    
    # Prefixo para os nomes dos arquivos contendo as bandas
    scene_id_prefix = f"CBERS_4A_WPM_{produto_info['properties']['datetime'][:10].replace('-', '')}_{produto_info['properties']['path']}_{produto_info['properties']['row']}_L4"
    
    # Caminhos completos para as bandas vermelha, verde e azul
    red_band_path = os.path.join(scene_dir, f"{scene_id_prefix}_BAND3.tif")
    green_band_path = os.path.join(scene_dir, f"{scene_id_prefix}_BAND2.tif")
    blue_band_path = os.path.join(scene_dir, f"{scene_id_prefix}_BAND1.tif")

    return red_band_path, green_band_path, blue_band_path