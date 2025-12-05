import numpy as np
import rasterio as rio

def stretch_band_masked(band_ma, pmin=0.5, pmax=99.5):
    """
    Aplica estiramento linear de percentis em uma banda, tratando máscaras,
    e retorna o array no formato 8-bit (uint8).
    
    Args:
        band_ma (numpy.ma.MaskedArray): Array da banda lido com masked=True.
        pmin (float): Percentil mínimo para o estiramento (ex: 0.5).
        pmax (float): Percentil máximo para o estiramento (ex: 99.5).
    """
    band = band_ma.astype(np.float32)
    
    if isinstance(band, np.ma.MaskedArray):
        valid_mask = ~band.mask
        data = band.data
    else:
        valid_mask = np.ones(band.shape, dtype=bool)
        data = band

    # Se não houver dados válidos, retorna array vazio
    if not np.any(valid_mask):
        return np.zeros(band.shape, dtype=np.uint8)

    # 1. Calcula os limites de corte de alto contraste
    lo, hi = np.percentile(data[valid_mask], (pmin, pmax))
    
    if hi == lo:
        hi = lo + 1.0

    # 2. Aplica o estiramento linear
    clipped = np.clip(data, lo, hi)
    norm = (clipped - lo) / (hi - lo)
    
    # 3. Aplica a máscara e converte para 8-bit
    norm[~valid_mask] = 0.0
    return (norm * 255).astype(np.uint8)