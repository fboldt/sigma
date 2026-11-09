from __future__ import annotations

import csv
import re
import time
from dataclasses import dataclass
from pathlib import Path

import rasterio as rio
import requests
from cbers4asat.cbers4a import Item
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from .georaster import stack_rgb_aligned
from .pansharpening_tiles import processar_pansharpening_tiles


BANDS = {
    "blue": 1,
    "green": 2,
    "red": 3,
    "pan": 0,
}


@dataclass(frozen=True)
class PansharpBatchConfig:
    project_root: Path
    download_dir: Path
    output_root: Path
    user: str | None = None
    collection: str = "CBERS4A_WPM_L4_DN"
    tile_size: int = 1024
    sample_stride: int = 8
    detail_strength: float = 0.65
    retries: int = 4
    chunk_size_mb: int = 8
    overwrite_rgb: bool = False
    overwrite_pansharp: bool = False
    dry_run: bool = False

    @property
    def rgb_dir(self) -> Path:
        return self.output_root / "rgb"

    @property
    def pansharp_dir(self) -> Path:
        return self.output_root / "pansharp"

    @property
    def report_path(self) -> Path:
        return self.output_root / "relatorio_lista_pansharp.csv"

    @property
    def chunk_size(self) -> int:
        return max(1, self.chunk_size_mb) * 1024 * 1024


def scene_parts(scene_id: str) -> tuple[str, str, str]:
    match = re.fullmatch(r"CBERS4A_WPM(\d{3})(\d{3})(\d{8})(?:ETC2)?", scene_id)
    if not match:
        raise ValueError(f"ID de cena inesperado: {scene_id}")
    path, row, date_token = match.groups()
    return path, row, date_token


def band_prefix(scene_id: str) -> str:
    path, row, date_token = scene_parts(scene_id)
    return f"CBERS_4A_WPM_{date_token}_{int(path)}_{int(row)}"


def is_valid_geotiff(path: Path | None) -> bool:
    if path is None or not path.exists() or path.stat().st_size == 0:
        return False
    try:
        with rio.open(path) as src:
            if src.width <= 0 or src.height <= 0 or src.count <= 0:
                return False
            src.read(1, window=((src.height - 1, src.height), (src.width - 1, src.width)))
        return True
    except Exception:
        return False


def make_download_session() -> requests.Session:
    retries = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        other=3,
        backoff_factor=1.5,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods={"GET"},
    )
    adapter = HTTPAdapter(max_retries=retries)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def safe_download_band(
    session: requests.Session,
    url: str,
    email: str,
    output_path: Path,
    retries: int,
    chunk_size: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if is_valid_geotiff(output_path):
        print(f"    banda valida ja existe: {output_path.name}")
        return

    if output_path.exists():
        print(f"    removendo banda incompleta/corrompida: {output_path.name}")
        output_path.unlink()

    partial_path = output_path.with_suffix(output_path.suffix + ".part")
    if partial_path.exists():
        partial_path.unlink()

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            print(f"    baixando {output_path.name} ({attempt}/{retries})...")
            with session.get(
                url,
                params={"email": email},
                stream=True,
                allow_redirects=True,
                timeout=(20, 180),
            ) as response:
                response.raise_for_status()
                with partial_path.open("wb") as file:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            file.write(chunk)

            if not is_valid_geotiff(partial_path):
                raise RuntimeError(f"download terminou, mas o GeoTIFF nao abriu: {output_path.name}")

            partial_path.replace(output_path)
            print(f"    download validado: {output_path.name}")
            return
        except Exception as exc:
            last_error = exc
            if partial_path.exists():
                partial_path.unlink()
            wait_seconds = min(60, attempt * 5)
            print(f"    [!] falha: {exc}")
            if attempt < retries:
                print(f"        tentando novamente em {wait_seconds}s...")
                time.sleep(wait_seconds)

    raise RuntimeError(f"nao foi possivel baixar {output_path.name}") from last_error


def find_first_valid(paths: list[Path]) -> Path | None:
    for path in paths:
        if is_valid_geotiff(path):
            return path
    return None


def find_existing_band(project_root: Path, download_dir: Path, scene_id: str, band_number: int) -> Path | None:
    prefix = band_prefix(scene_id)
    scene_dir = download_dir / scene_id
    preferred = sorted(scene_dir.glob(f"{prefix}_*_BAND{band_number}.tif"))
    preferred += sorted(scene_dir.glob(f"*_BAND{band_number}.tif"))
    found = find_first_valid(preferred)
    if found:
        return found

    patterns = [
        f"{prefix}_*_BAND{band_number}.tif",
        f"*{scene_id}*BAND{band_number}.tif",
    ]
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(project_root.rglob(pattern))

    candidates = sorted(set(path for path in candidates if path.is_file()))
    return find_first_valid(candidates)


def find_existing_product(output_dir: Path, filename: str) -> Path | None:
    preferred = output_dir / filename
    if is_valid_geotiff(preferred):
        return preferred
    return None


def download_missing_bands(
    session: requests.Session,
    scene_id: str,
    missing_bands: list[str],
    config: PansharpBatchConfig,
) -> None:
    if not config.user:
        raise ValueError("Informe --user ou defina CBERS4A_USER para baixar bandas faltantes.")

    item = Item.from_search(scene_id, config.collection)
    scene_dir = config.download_dir / scene_id
    for band in missing_bands:
        url = item.band_url(band)
        output_path = scene_dir / Path(url).name
        safe_download_band(
            session=session,
            url=url,
            email=config.user,
            output_path=output_path,
            retries=config.retries,
            chunk_size=config.chunk_size,
        )


def build_record(
    config: PansharpBatchConfig,
    scene_id: str,
) -> dict[str, str | Path | None]:
    record: dict[str, str | Path | None] = {"scene_id": scene_id}
    for band, band_number in BANDS.items():
        record[band] = find_existing_band(
            config.project_root,
            config.download_dir,
            scene_id,
            band_number,
        )
    record["rgb"] = find_existing_product(config.rgb_dir, f"TRUE_COLOR_{scene_id}.tif")
    record["pansharp"] = find_existing_product(config.pansharp_dir, f"PANSHARP_{scene_id}.tif")
    return record


def missing_raw_bands(record: dict[str, str | Path | None]) -> list[str]:
    return [band for band in ("red", "green", "blue", "pan") if record.get(band) is None]


def write_report(report_path: Path, records: list[dict[str, str | Path | None]]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "scene_id",
        "red",
        "green",
        "blue",
        "pan",
        "rgb",
        "pansharp",
        "status",
    ]
    with report_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        for record in records:
            writer.writerow({column: str(record.get(column) or "") for column in columns})


def run_pansharp_batch(
    scene_ids: list[str],
    config: PansharpBatchConfig,
) -> list[dict[str, str | Path | None]]:
    print(f"Projeto: {config.project_root}")
    print(f"Downloads/bandas: {config.download_dir}")
    print(f"Saidas novas: {config.output_root}")
    print()

    records = [build_record(config, scene_id) for scene_id in scene_ids]

    any_missing_download = any(missing_raw_bands(record) for record in records)
    if any_missing_download and not config.user and not config.dry_run:
        raise ValueError("Informe --user ou defina CBERS4A_USER para baixar bandas faltantes.")

    session = make_download_session()
    try:
        for record in records:
            process_scene_record(session, record, config)
    finally:
        session.close()

    write_report(config.report_path, records)
    print(f"Relatorio salvo em: {config.report_path}")
    print("Concluido.")
    return records


def process_scene_record(
    session: requests.Session,
    record: dict[str, str | Path | None],
    config: PansharpBatchConfig,
) -> None:
    scene_id = str(record["scene_id"])
    print(f"Cena {scene_id}")

    missing_before = missing_raw_bands(record)
    if missing_before:
        print(f"  bandas faltantes: {', '.join(missing_before)}")
        if config.dry_run:
            print("  dry-run: baixaria apenas essas bandas faltantes.")
        else:
            download_missing_bands(
                session=session,
                scene_id=scene_id,
                missing_bands=missing_before,
                config=config,
            )
            record.update(build_record(config, scene_id))
    else:
        print("  bandas brutas RGB+PAN ja existem.")

    ensure_rgb(record, config)
    ensure_pansharp(record, config)
    print()


def ensure_rgb(record: dict[str, str | Path | None], config: PansharpBatchConfig) -> None:
    scene_id = str(record["scene_id"])
    rgb_output = config.rgb_dir / f"TRUE_COLOR_{scene_id}.tif"
    if record.get("rgb") is not None and not config.overwrite_rgb:
        print(f"  RGB ja existe, pulando: {record['rgb']}")
        return

    if any(record.get(band) is None for band in ("red", "green", "blue")):
        print("  [AVISO] RGB pulado porque ainda faltam bandas red/green/blue.")
        record["status"] = "sem_rgb_por_falta_de_bandas"
        return

    if config.dry_run:
        print(f"  dry-run: criaria RGB em {rgb_output}")
        record["rgb"] = rgb_output
        return

    print(f"  criando RGB: {rgb_output.name}")
    stack_rgb_aligned(
        red_band=str(record["red"]),
        green_band=str(record["green"]),
        blue_band=str(record["blue"]),
        output_file_path=str(rgb_output),
    )
    record["rgb"] = rgb_output


def ensure_pansharp(record: dict[str, str | Path | None], config: PansharpBatchConfig) -> None:
    scene_id = str(record["scene_id"])
    pansharp_output = config.pansharp_dir / f"PANSHARP_{scene_id}.tif"
    if record.get("pansharp") is not None and not config.overwrite_pansharp:
        print(f"  pansharp ja existe, pulando: {record['pansharp']}")
        record["status"] = "pansharp_existente"
        return

    if record.get("rgb") is None or record.get("pan") is None:
        print("  [AVISO] pansharp pulado porque falta RGB ou PAN.")
        record["status"] = "sem_pansharp_por_falta_de_rgb_ou_pan"
        return

    if config.dry_run:
        print(f"  dry-run: criaria pansharp em {pansharp_output}")
        record["pansharp"] = pansharp_output
        record["status"] = "dry_run_criaria_pansharp"
        return

    print(f"  criando pansharp: {pansharp_output.name}")
    processar_pansharpening_tiles(
        caminho_pan=str(record["pan"]),
        caminho_ms=str(record["rgb"]),
        caminho_saida=str(pansharp_output),
        tamanho_tile=config.tile_size,
        sample_stride=config.sample_stride,
        detail_strength=config.detail_strength,
    )
    record["pansharp"] = pansharp_output
    record["status"] = "pansharp_criado"
