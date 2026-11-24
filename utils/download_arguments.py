"""Leitura dos argumentos de cidade e bandas para exemplos de download."""

import json
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CITY_COORDINATES_PATH = PROJECT_ROOT / "city_coordinates.json"
BAND_CODES = {
    "r": "red",
    "g": "green",
    "b": "blue",
    "n": "nir",
    "p": "pan",
}
BAND_ORDER = ("red", "green", "blue", "nir", "pan")
BANDS_HELP = "rgb, rgbn, rgbp ou rgbpn (r=red, g=green, b=blue, n=nir, p=pan)"


def _load_cities():
    with CITY_COORDINATES_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def resolve_city(city_code):
    if not isinstance(city_code, str) or not city_code.strip():
        raise ValueError(
            "Informe a sigla da cidade ou ES para todo o estado.\n"
            "Veja as siglas disponiveis com: python run.py list_cities\n"
            "Exemplo: python run.py download_scene VIX rgbpn"
        )

    code = city_code.strip().upper()
    cities = _load_cities()
    city = cities.get(code)
    if city is None:
        raise ValueError(
            f"Sigla de cidade invalida: {city_code}.\n"
            "Veja as siglas disponiveis com: python run.py list_cities\n"
            "Exemplo: python run.py download_scene VIX rgbpn"
        )

    return code, city


def parse_bands(bands_code):
    if not isinstance(bands_code, str) or not bands_code.strip():
        raise ValueError(
            "Informe as bandas apos a sigla da cidade.\n"
            f"Bandas aceitas: {BANDS_HELP}.\n"
            "Exemplo: python run.py download_scene VIX rgbpn"
        )

    normalized = bands_code.strip().lower()
    invalid = sorted(set(normalized) - set(BAND_CODES))
    if invalid:
        raise ValueError(
            f"Codigo de bandas invalido: {bands_code}.\n"
            f"Bandas aceitas: {BANDS_HELP}.\n"
            "Exemplo: python run.py download_scene VIX rgbpn"
        )

    selected = {BAND_CODES[letter] for letter in normalized}
    return [band for band in BAND_ORDER if band in selected]


def city_download_params(city_code, bands_code, max_products=None):
    """Monta parametros de download sem diferenciar letras maiusculas e minusculas."""
    code, city = resolve_city(city_code)
    bands = parse_bands(bands_code)
    load_dotenv(PROJECT_ROOT / ".env")

    if max_products is None:
        max_products = 100 if code == "ES" else 1

    return {
        "user": os.getenv("EMAIL_INPE"),
        "bbox": [city["west"], city["south"], city["east"], city["north"]],
        "max_cloud": 10,
        "max_products": max_products,
        "initial_date": date(2025, 1, 1),
        "final_date": date(2025, 7, 12),
        "bands": bands,
        "output_dir": str(PROJECT_ROOT / "images"),
        "location_name": city["city"],
        "location_code": code,
    }


def require_rgb_bands(bands):
    if {"red", "green", "blue"}.issubset(bands):
        return

    raise ValueError(
        "A composicao RGB exige as bandas red, green e blue.\n"
        "Use rgb, rgbn, rgbp ou rgbpn.\n"
        "Exemplo: python run.py example_download_and_rgb VIX rgbpn"
    )
