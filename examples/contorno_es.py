from shapely.geometry import shape
import requests
import json

def contorno_es(nome_saida="contorno_es.geojson"):
    # Polígono do local de busca
    # Localização: Espírito Santo (ES)
    url = "https://servicodados.ibge.gov.br/api/v4/malhas/estados/32?formato=application/vnd.geo+json&qualidade=minima" # URL do Query Builder na API do IBGE
    response = requests.get(url) 
    data = response.json() 
    
    with open(nome_saida, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

if __name__ == "__main__":
    contorno_es()