def run():
    list_cities()

def list_cities():
    import json
    with open('city_coordinates.json') as f:
        cities = json.load(f)
    
    for city_code, city_info in cities.items():
        print(f"{city_code}: {city_info['city']}")
        # print(f"Coordinates: West: {city_info['west']}, South: {city_info['south']}, East: {city_info['east']}, North: {city_info['north']}")
        print()
