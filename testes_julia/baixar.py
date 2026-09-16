from cbers4asat import Cbers4aAPI
from datetime import date
import geopandas as gpd

api = Cbers4aAPI('juliaalmeidanasc8@gmail.com')

bbox = [-40.2221, -20.2026, -40.2121, -20.1926]  # [Oeste, Sul, Leste, Norte]

data_inicial = date(2024, 12, 1)
data_final = date(2025, 12, 1)

produtos = api.query(location=bbox,
                     initial_date=data_inicial,
                     end_date=data_final,
                     cloud=0,
                     limit=10,
                     collections=['CBERS4A_WPM_L4_DN'])

gdf = api.to_geodataframe(produtos)

# Utiliza a mesma lógica que o download de produtos no formato dicionário
api.download(products=gdf, bands=['red','green','blue', 'nir'],
             threads=4,  # Numero de downloads simultâneos
             outdir='./downloads1', 
             with_folder=True,
             with_metadata=True # Baixar com metadados
            )