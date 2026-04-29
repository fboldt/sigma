import psutil

def definir_tamanho_tile() -> int:
    ram_disponivel_gb = psutil.virtual_memory().available / (1024 ** 3)

    if ram_disponivel_gb >= 48:
        return 16384
    elif ram_disponivel_gb >= 32:
        return 12288
    elif ram_disponivel_gb >= 24:
        return 10240
    elif ram_disponivel_gb >= 16:
        return 8192
    elif ram_disponivel_gb >= 12:
        return 6144
    elif ram_disponivel_gb >= 8:
        return 4096
    elif ram_disponivel_gb >= 4:
        return 2048
    else:
        return 1024