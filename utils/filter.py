import pandas as pd

def products_filter(products):
    
    # 
    features = products['features']

    # Lista contendo metadados para filtragem
    products_data = []
    for feature in features:
        products_data.append({
            'id': feature['id'],
            'cloud': feature['properties']['cloud_cover'],
            'path': feature['properties']['path'],
            'row': feature['properties']['row'],
            'feature': feature
        })

    # GeoDataFrame para armezenar colunas passíveis de filtragem
    data_frame = pd.DataFrame(products_data)

    # Ordena por nuvem e pega a primeira de cada Path/Row
    best_data_frame = data_frame.sort_values('cloud').drop_duplicates(subset=['path', 'row'], keep='first')

    # Reconstrói o formato original da api.download
    filter_products = {
        'type': 'FeatureCollection',
        'features': best_data_frame['feature'].tolist()
    }
    
    return filter_products