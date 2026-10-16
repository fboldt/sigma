from cbers4asat import Cbers4aAPI
from cbers4asat.cbers4a import ItemCollection
from datetime import date
import os
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


# Tamanho de cada bloco gravado no disco durante a transferencia HTTP.
DOWNLOAD_CHUNK_SIZE = 8 * 1024 * 1024
# Arquivos maiores que este valor podem ser divididos em intervalos paralelos.
RANGE_DOWNLOAD_THRESHOLD = 256 * 1024 * 1024
# Numero de conexoes usadas para montar um arquivo grande por intervalos.
RANGE_DOWNLOAD_WORKERS = 4


class RangeDownloadError(RuntimeError):
    """O servidor recusou uma requisicao HTTP parcial."""

def _make_session():
    """Cria uma sessao HTTP com tentativas automaticas para erros temporarios."""
    retry_policy = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        backoff_factor=1,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods={"GET"},
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry_policy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _download_asset(url, email, output_path, retries=3):
    """Baixa uma banda para um arquivo temporario e a renomeia ao concluir.

    Para arquivos grandes, tenta usar quatro intervalos HTTP simultaneos. Caso
    o servidor recuse intervalos, baixa a mesma banda em uma unica conexao.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = output_path.with_suffix(f"{output_path.suffix}.part")
    size = _content_length(url, email)

    for attempt in range(1, retries + 1):
        try:
            if size is not None and size >= RANGE_DOWNLOAD_THRESHOLD:
                try:
                    _download_large_asset(url, email, partial_path, size)
                except (RangeDownloadError, requests.RequestException):
                    if partial_path.exists():
                        partial_path.unlink()
                    _download_stream(url, email, partial_path)
            else:
                _download_stream(url, email, partial_path)
            os.replace(partial_path, output_path)
            return
        except requests.RequestException:
            if partial_path.exists():
                partial_path.unlink()
            if attempt == retries:
                raise
            time.sleep(attempt * 2)


def _download_stream(url, email, partial_path):
    """Transfere uma banda inteira em uma conexao HTTP, em blocos de 8 MB."""
    with _make_session() as session:
        with session.get(
            url,
            params={"email": email},
            stream=True,
            allow_redirects=True,
            timeout=(30, 120),
        ) as response:
            response.raise_for_status()
            with open(partial_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    if chunk:
                        file.write(chunk)


def _content_length(url, email):
    """Consulta o tamanho remoto de uma banda para decidir se usa intervalos."""
    with _make_session() as session:
        response = session.head(
            url,
            params={"email": email},
            allow_redirects=True,
            timeout=(30, 120),
        )
        response.raise_for_status()
        length = response.headers.get("content-length")
        return int(length) if length is not None else None


def _download_range(url, email, partial_path, start, end):
    """Baixa um intervalo de bytes e o grava na posicao correta do .part."""
    with _make_session() as session:
        with session.get(
            url,
            params={"email": email},
            headers={"Range": f"bytes={start}-{end}"},
            stream=True,
            allow_redirects=True,
            timeout=(30, 120),
        ) as response:
            if response.status_code != 206:
                raise RangeDownloadError(
                    f"O servidor recusou o intervalo {start}-{end} (HTTP {response.status_code})."
                )
            with open(partial_path, "r+b") as file:
                file.seek(start)
                written = 0
                for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    if chunk:
                        file.write(chunk)
                        written += len(chunk)

    expected = end - start + 1
    if written != expected:
        raise RangeDownloadError(
            f"Intervalo incompleto: esperado {expected} bytes, recebido {written}."
        )


def _download_large_asset(url, email, partial_path, size):
    """Monta um arquivo grande a partir de quatro intervalos HTTP paralelos."""
    with open(partial_path, "wb") as file:
        file.truncate(size)

    part_size = (size + RANGE_DOWNLOAD_WORKERS - 1) // RANGE_DOWNLOAD_WORKERS
    ranges = [
        (start, min(start + part_size - 1, size - 1))
        for start in range(0, size, part_size)
    ]
    with ThreadPoolExecutor(max_workers=len(ranges)) as executor:
        futures = [
            executor.submit(_download_range, url, email, partial_path, start, end)
            for start, end in ranges
        ]
        for future in as_completed(futures):
            future.result()


def _download_bands_parallel(products, bands, output_dir, email, workers):
    """Resolve os URLs das bandas e inicia todos os downloads em paralelo.

    ItemCollection e get_features_assets pertencem ao cbers4asat e sao usados
    somente para consultar o catalogo INPE. A transferencia dos arquivos e'
    feita pelas funcoes _download_asset deste modulo, usando requests.
    """
    products_with_assets = ItemCollection(**products)
    # A busca por area traz somente a miniatura. Esta chamada busca os assets
    # (URLs das bandas) de cada produto, como a biblioteca faz internamente.
    products_with_assets.get_features_assets()

    tasks = []
    for item in products_with_assets:
        scene_dir = Path(output_dir) / item.id
        for band in bands:
            url = item.band_url(band)
            tasks.append((band, url, scene_dir / Path(url).name))

    if not tasks:
        raise ValueError("Nenhuma banda foi encontrada para baixar.")

    with ThreadPoolExecutor(max_workers=min(workers, len(tasks))) as executor:
        futures = [
            executor.submit(_download_asset, url, email, path)
            for _, url, path in tasks
        ]
        for future in as_completed(futures):
            future.result()

def bands_download(params, products=None):
    """Busca cenas quando necessario e baixa as bandas pedidas em paralelo.

    A API cbers4asat e' usada para a busca espacial e para obter os URLs dos
    assets. Esta funcao nao chama api.download(), pois o modulo implementa a
    transferencia HTTP concorrente em _download_bands_parallel.
    """
    # Instanciando o objeto com o usuario cadastrado na plataforma.
    api = Cbers4aAPI(params['user'])
    os.makedirs(params['output_dir'], exist_ok=True)

    if products == None:
        # Busca por produtos
        products = api.query(location=params.get('location') or params.get('bbox'),
                            initial_date=params['initial_date'],
                            end_date=params['final_date'],
                            cloud=params['max_cloud'],
                            limit=params['max_products'],
                            collections=['CBERS4A_WPM_L4_DN']
                            )
    
    # Definido bandas para download
    bands = params.get('bands', ['red', 'green', 'blue', 'nir', 'pan'])

    # A implementacao da biblioteca aguarda uma tarefa antes de submeter a
    # proxima. Aqui todas as bandas sao submetidas antes de qualquer espera.
    workers = params.get('download_workers', min(8, len(bands) * len(products['features'])))
    _download_bands_parallel(
        products,
        bands,
        params['output_dir'],
        params['user'],
        max(1, workers),
    )
    
    # Localização de produtos baixados
    all_bands_paths = bands_paths(params['output_dir'], products, bands)
    return all_bands_paths

def bands_paths(output_dir, produtos, bands=None):
    """Monta os caminhos esperados das bandas baixadas para cada produto."""
    all_bands_paths = [] 
    
    for produto_info in produtos['features']:
        produto_id = produto_info['id'] # ID da cena atual
        
        # Localização da pasta da cena atual
        scene_folder_pattern = os.path.join(output_dir, f"*{produto_id}*")
        scene_dir_list = glob.glob(scene_folder_pattern)
        
        scene_dir = scene_dir_list[0] 
        
        # Prefixo para os nomes dos arquivos contendo as bandas
        scene_id_prefix = f"CBERS_4A_WPM_{produto_info['properties']['datetime'][:10].replace('-', '')}_{produto_info['properties']['path']}_{produto_info['properties']['row']}_L4"
        
        band_numbers = {'blue': 1, 'green': 2, 'red': 3, 'nir': 4, 'pan': 0}
        requested_bands = bands or ['red', 'green', 'blue', 'nir', 'pan']
        scene_paths = {'id': produto_id}
        for band in requested_bands:
            if band not in band_numbers:
                raise ValueError(f"Banda desconhecida: {band}")
            scene_paths[band] = os.path.join(
                scene_dir, f"{scene_id_prefix}_BAND{band_numbers[band]}.tif"
            )

        # Retorna somente as bandas solicitadas pelo chamador.
        all_bands_paths.append(scene_paths)
        
    return all_bands_paths
