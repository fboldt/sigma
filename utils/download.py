from cbers4asat import Cbers4aAPI
from datetime import date

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
    
    # Download dos produtos encontrados
    api.download(products=produtos,
             bands=['red', 'green', 'blue'],
             threads=3,  # Número de downloads simultâneos
             outdir=output_dir,
             with_folder=True # Agrupar bandas de uma cena em uma subpasta
             )