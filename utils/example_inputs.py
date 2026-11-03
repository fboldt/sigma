"""Mensagens de validacao de entradas usadas pelos exemplos locais."""
from pathlib import Path

DOWNLOAD_COMMAND = "python run_example.py example_download"

def require_files(example_name, required_paths, download_command=DOWNLOAD_COMMAND):
    """Interrompe um exemplo com os arquivos ausentes e um comando de teste."""
    missing = [Path(path) for path in required_paths if not Path(path).is_file()]
    if not missing:
        return

    missing_text = "\n".join(f"- {path}" for path in missing)
    raise FileNotFoundError(
        f"O exemplo '{example_name}' foi interrompido porque faltam arquivos de entrada:\n"
        f"{missing_text}\n\n"
        "Para baixar uma cena de teste, execute na raiz do projeto:\n"
        f"{download_command}"
    )


def require_directory(example_name, directory, download_command=DOWNLOAD_COMMAND):
    """Interrompe um exemplo quando o diretorio de entrada nao existe."""
    directory = Path(directory)
    if directory.is_dir():
        return

    raise FileNotFoundError(
        f"O exemplo '{example_name}' foi interrompido porque o diretorio nao existe:\n"
        f"- {directory}\n\n"
        "Para baixar uma cena de teste, execute na raiz do projeto:\n"
        f"{download_command}"
    )
