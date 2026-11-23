from shapely.geometry import shape
import requests
import json
import os

def run():
    return contorno_es("contorno_es.geojson")

def contorno_es(nome_saida="contorno_es.geojson"):
    # Polígono do local de busca
    # Localização: Espírito Santo (ES)
    url = "https://servicodados.ibge.gov.br/api/v4/malhas/estados/32?formato=application/vnd.geo+json&qualidade=minima" # URL do Query Builder na API do IBGE

    print("Iniciando download do contorno do Espírito Santo (IBGE)...")
    response = requests.get(url)
    response.raise_for_status()  # interrompe com erro claro se a requisição falhar
    print(f"Download concluído.")

    data = response.json()
    n_feicoes = len(data.get("features", []))
    print(f"GeoJSON lido com sucesso: {n_feicoes} feição(ões) encontrada(s).")

    print(f"Salvando arquivo em '{nome_saida}'...")
    with open(nome_saida, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    caminho = os.path.abspath(nome_saida)
    tamanho_kb = os.path.getsize(nome_saida) / 1024
    print(f"Arquivo GeoJSON salvo em: {caminho} ({tamanho_kb:.1f} KB)")

if __name__ == "__main__":
    contorno_es()