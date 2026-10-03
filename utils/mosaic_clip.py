import json
import os
import unicodedata
import numpy as np
import rasterio as rio
from rasterio.errors import WindowError
from rasterio.features import bounds as features_bounds
from rasterio.features import geometry_mask, geometry_window
from rasterio.warp import transform_geom
from rasterio.windows import Window
from utils.mosaic_geometry import (
    DEFAULT_WINDOW_SIZE,
    NODATA_VALUE,
    iter_windows,
    tiled_gtiff_profile,
)

IBGE_STATE_GEOJSON_URL = (
    "https://servicodados.ibge.gov.br/api/v4/malhas/estados/{state_id}"
    "?formato=application/vnd.geo+json&qualidade=minima"
)
IBGE_UF_CODES = {
    "RO": 11,
    "AC": 12,
    "AM": 13,
    "RR": 14,
    "PA": 15,
    "AP": 16,
    "TO": 17,
    "MA": 21,
    "PI": 22,
    "CE": 23,
    "RN": 24,
    "PB": 25,
    "PE": 26,
    "AL": 27,
    "SE": 28,
    "BA": 29,
    "MG": 31,
    "ES": 32,
    "RJ": 33,
    "SP": 35,
    "PR": 41,
    "SC": 42,
    "RS": 43,
    "MS": 50,
    "MT": 51,
    "GO": 52,
    "DF": 53,
}
IBGE_STATE_NAMES = {
    "rondonia": "RO",
    "acre": "AC",
    "amazonas": "AM",
    "roraima": "RR",
    "para": "PA",
    "amapa": "AP",
    "tocantins": "TO",
    "maranhao": "MA",
    "piaui": "PI",
    "ceara": "CE",
    "rio grande do norte": "RN",
    "paraiba": "PB",
    "pernambuco": "PE",
    "alagoas": "AL",
    "sergipe": "SE",
    "bahia": "BA",
    "minas gerais": "MG",
    "espirito santo": "ES",
    "rio de janeiro": "RJ",
    "sao paulo": "SP",
    "parana": "PR",
    "santa catarina": "SC",
    "rio grande do sul": "RS",
    "mato grosso do sul": "MS",
    "mato grosso": "MT",
    "goias": "GO",
    "distrito federal": "DF",
}


# Função para tirar acentos e padronizar texto
def normalize_text(value):
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(char for char in text if not unicodedata.combining(char))


# Função para converter UF, nome de estado ou código já em código numérico do IBGE
def normalize_ibge_state_id(state):
    if isinstance(state, int):
        return str(state)

    state_text = str(state).strip()
    if state_text.isdigit():
        return str(int(state_text))

    uf = state_text.upper()
    if uf in IBGE_UF_CODES:
        return str(IBGE_UF_CODES[uf])

    normalized_name = normalize_text(state_text)
    if normalized_name in IBGE_STATE_NAMES:
        return str(IBGE_UF_CODES[IBGE_STATE_NAMES[normalized_name]])

    valid_ufs = ", ".join(sorted(IBGE_UF_CODES))
    raise ValueError(
        "Estado nao reconhecido. Informe uma UF, nome de estado ou codigo IBGE. "
        f"UFs aceitas: {valid_ufs}."
    )


# Função para listar os caminhos locais onde o contorno de um estado pode já estar salvo em cache
def state_geojson_candidates(state):
    state_id = normalize_ibge_state_id(state)
    state_text = str(state).strip()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [os.path.join(project_root, f"contorno_{state_id}.geojson")]

    uf = state_text.upper()
    if uf in IBGE_UF_CODES:
        candidates.insert(0, os.path.join(project_root, f"contorno_{uf.lower()}.geojson"))
    else:
        normalized_name = normalize_text(state_text).replace(" ", "_")
        if normalized_name:
            candidates.insert(
                0,
                os.path.join(project_root, f"contorno_{normalized_name}.geojson"),
            )

    return candidates


# Função para normalizar a entrada de geometria
def extract_geojson_geometries(geometry):
    if hasattr(geometry, "__geo_interface__"):
        geometry = geometry.__geo_interface__

    if isinstance(geometry, str):
        with open(geometry, "r", encoding="utf-8") as file:
            geometry = json.load(file)

    if isinstance(geometry, (list, tuple)):
        geometries = []
        for item in geometry:
            geometries.extend(extract_geojson_geometries(item))
        return geometries

    if not isinstance(geometry, dict):
        raise TypeError(
            "A geometria de recorte deve ser GeoJSON, shapely, caminho .geojson ou lista desses formatos."
        )

    geometry_type = geometry.get("type")
    if geometry_type == "FeatureCollection":
        geometries = []
        for feature in geometry.get("features", []):
            geometries.extend(extract_geojson_geometries(feature))
        return geometries
    if geometry_type == "Feature":
        return extract_geojson_geometries(geometry.get("geometry"))
    if geometry_type in {
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
        "GeometryCollection",
    }:
        return [geometry]

    raise ValueError("GeoJSON de recorte invalido ou sem geometria.")


# Função para carregar o contorno de um estado
def load_state_boundary(state, geojson_path=None, prefer_local=True):
    data = None
    local_paths = [geojson_path] if geojson_path else state_geojson_candidates(state)

    if prefer_local:
        for path in local_paths:
            if path and os.path.exists(path):
                with open(path, "r", encoding="utf-8") as file:
                    data = json.load(file)
                break

    if data is None:
        import requests

        state_id = normalize_ibge_state_id(state)
        response = requests.get(
            IBGE_STATE_GEOJSON_URL.format(state_id=state_id),
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

    geometries = extract_geojson_geometries(data)
    if not geometries:
        raise ValueError(f"Nao foi possivel carregar o contorno do estado {state}.")
    return geometries[0] if len(geometries) == 1 else geometries


# Função para decidir qual geometria de recorte usar a partir dos parâmetros recebidos
def resolve_clip_geometry(clip_geometry, clip_state=None):
    if clip_geometry is not None and clip_state is not None:
        raise ValueError("Informe apenas clip_geometry ou clip_state, nao os dois.")

    if clip_state is not None:
        return load_state_boundary(clip_state)

    if clip_geometry is None:
        return None

    if isinstance(clip_geometry, int):
        return load_state_boundary(clip_geometry)

    if isinstance(clip_geometry, str) and not os.path.exists(clip_geometry):
        try:
            normalize_ibge_state_id(clip_geometry)
        except ValueError:
            return clip_geometry
        return load_state_boundary(clip_geometry)

    return clip_geometry


# Função para reprojetar as geometrias de recorte para o CRS do raster
def geometries_to_crs(geometries, geometry_crs, target_crs):
    if not geometry_crs or target_crs is None:
        return list(geometries)
    return [
        transform_geom(geometry_crs, target_crs, item, precision=6)
        for item in geometries
    ]


# Função para calcular o retângulo (esquerda, baixo, direita, cima) que envolve todas as geometrias
def geometries_bounds(geometries):
    boxes = [features_bounds(item) for item in geometries]
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


# Função para marcar (True) os pixels de uma janela que estão dentro das geometrias
def inside_geometry_mask(geometries, out_shape, transform):
    return geometry_mask(
        geometries,
        out_shape=out_shape,
        transform=transform,
        invert=True,
    )


# Função para recortar um raster por uma geometria, gravando nodata fora da área útil.
def clip_raster_to_geometry(
    input_path,
    output_path,
    geometry,
    geometry_crs="EPSG:4326",
    nodata=NODATA_VALUE,
    window_size=DEFAULT_WINDOW_SIZE,
):
    geometries = extract_geojson_geometries(geometry)
    if not geometries:
        raise ValueError("Informe pelo menos uma geometria para recortar a cena.")

    with rio.open(input_path) as src:
        if src.crs is None:
            raise ValueError(f"A cena {input_path} nao possui CRS definido.")

        geometries = geometries_to_crs(geometries, geometry_crs, src.crs)

        try:
            crop = geometry_window(src, geometries)
        except (ValueError, WindowError) as exc:
            raise ValueError(
                f"A cena {input_path} nao intersecta a geometria de recorte."
            ) from exc

        crop = Window(
            int(round(crop.col_off)),
            int(round(crop.row_off)),
            int(round(crop.width)),
            int(round(crop.height)),
        )
        if crop.width <= 0 or crop.height <= 0:
            raise ValueError(
                f"A cena {input_path} nao intersecta a geometria de recorte."
            )

        profile = tiled_gtiff_profile(src.profile.copy())
        profile.update(
            height=crop.height,
            width=crop.width,
            transform=src.window_transform(crop),
            nodata=nodata,
        )

        has_valid_pixels = False
        with rio.open(output_path, "w", **profile) as dst:
            for window in iter_windows(
                crop.width, crop.height, window_size, crop.col_off, crop.row_off
            ):
                data = src.read(window=window)
                inside = inside_geometry_mask(
                    geometries,
                    (int(window.height), int(window.width)),
                    src.window_transform(window),
                )
                data[:, ~inside] = nodata
                has_valid_pixels = has_valid_pixels or bool(np.any(data > nodata))
                dst.write(
                    data,
                    window=Window(
                        window.col_off - crop.col_off,
                        window.row_off - crop.row_off,
                        window.width,
                        window.height,
                    ),
                )

    if not has_valid_pixels:
        os.remove(output_path)
        raise ValueError(
            f"A cena {input_path} ficou sem pixels validos apos o recorte."
        )

    return output_path