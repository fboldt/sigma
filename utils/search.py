from cbers4asat import Cbers4aAPI

# Função para buscar produtos
def search_products(params):
    # Instanciando o objeto com o usuário cadastrado na plataforma
    api = Cbers4aAPI(params['user'])

    # Busca por produtos
    products = api.query(location=params.get('location') or params.get('bbox'),
                         initial_date=params['initial_date'],
                         end_date=params['final_date'],
                         cloud=params['max_cloud'],
                         limit=params['max_products'],
                         collections=['CBERS4A_WPM_L4_DN']
                         )
    
    # Retorno dos produtos encontrados com base nos parâmetros
    return products