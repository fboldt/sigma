import json
import os
import unicodedata
import numpy as np
import rasterio as rio
from rasterio.mask import mask as raster_mask
from rasterio.warp import transform_geom
from utils.mosaic_geometry import NODATA_VALUE

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


# Função para recortar um raster por uma geometria, gravando nodata fora da área útil
def clip_raster_to_geometry(input_path, output_path, geometry, geometry_crs="EPSG:4326", nodata=NODATA_VALUE,
):
    geometries = extract_geojson_geometries(geometry)
    if not geometries:
        raise ValueError("Informe pelo menos uma geometria para recortar a cena.")

    with rio.open(input_path) as src:
        if src.crs is None:
            raise ValueError(f"A cena {input_path} nao possui CRS definido.")

        if geometry_crs:
            geometries = [
                transform_geom(geometry_crs, src.crs, item, precision=6)
                for item in geometries
            ]

        try:
            data, transform = raster_mask(
                src,
                geometries,
                crop=True,
                filled=True,
                nodata=nodata,
            )
        except ValueError as exc:
            raise ValueError(
                f"A cena {input_path} nao intersecta a geometria de recorte."
            ) from exc

        if not np.any(data > nodata):
            raise ValueError(
                f"A cena {input_path} ficou sem pixels validos apos o recorte."
            )

        profile = src.profile.copy()
        profile.update(
            height=data.shape[1],
            width=data.shape[2],
            transform=transform,
            nodata=nodata,
            compress="lzw",
            tiled=True,
            blockxsize=512,
            blockysize=512,
            BIGTIFF="YES",
        )

        with rio.open(output_path, "w", **profile) as dst:
            dst.write(data)

    return output_path