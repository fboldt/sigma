from cbers4asat import Cbers4aAPI
from datetime import date

api = Cbers4aAPI('rafaeldeps15@gmail.com')

#No exemplo abaixo, a área de interesse é a foto que pega o ifes serra
bbox = [-40.2221, -20.2026, -40.2121, -20.1926]  # [Oeste, Sul, Leste, Norte]

produtos = api.query(
    location=bbox,
    initial_date=date(2024, 10, 22),
    end_date=date(2025, 10, 22),
    cloud=00,           # ajuste se quiser menos nuvem
    limit=10,           #quantidade máxima de produtos a retornar
    collections=['CBERS4A_WPM_L4_DN']
)

print(produtos)

# Exemplo de download RGB (opcional)
api.download(products=produtos, bands=['red','green','blue','pan'])
# pan é 2 metros de resolução espacial e red, green e blue são 8 metros de resolução espacial