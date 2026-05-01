import psutil

def calcular_tamanho_tile(ram_gb: float) -> int:
    multiplicador = max(1, min(16, (ram_gb / 2), (ram_gb / 4) + 4))
    return int(multiplicador) * 1024


def definir_tamanho_tile() -> int:
    ram_disponivel_gb = psutil.virtual_memory().available / (1024 ** 3)
    return calcular_tamanho_tile(ram_disponivel_gb)