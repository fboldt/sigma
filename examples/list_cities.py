def run():
    list_cities()

def list_cities():
    import json
    with open('city_coordinates.json', encoding='utf-8') as f:
        cities = json.load(f)

    for city_code, city_info in cities.items():
        print(f"{city_code}: {city_info['city']}")
        print()