from cbers4asat import Cbers4aAPI
from datetime import date

# Inicializando a biblioteca
api = Cbers4aAPI('juliaalmeidanasc8@gmail.com') # E-mail usado no login da plataforma https://www.dgi.inpe.br/catalogo/explore

# Área de interesse. Pode ser: bouding box, path row ou polygon.
bbox = [-40.2221, -20.2026, -40.2121, -20.1926]#Oeste, sul, leste e norte

# Buscando metadados. Este exemplo utiliza o path row (órbita/ponto). 
# Consulte a órbita/ponto: http://www.obt.inpe.br/OBT/assuntos/catalogo-cbers-amz-1
produtos = api.query(location=bbox,
                     initial_date=date(2024, 10, 28),
                     end_date=date(2025, 11, 28),
                     cloud=00,
                     limit=5,
                     collections=['CBERS4A_WPM_L4_DN'])

# Exibindo os resultados
print(produtos)

#exemplo de downloads RGB
api.download(products=produtos, bands=['red', 'green', 'blue'])
