from cbers4asat.tools import rgbn_composite
import rasterio as rio

def rgb_composite(red_band, green_band, blue_band, output_dir):

    output_filename = 'CBERS4A_TRUE_COLOR.tif' # Nome do arquivo de saída
    output_path = f'{output_dir}/{output_filename}' # Caminho completo do arquivo de saída

    # Criando a composição cor verdadeira
    rgbn_composite(red=red_band,
                green=green_band,
                blue=blue_band,
                filename=output_filename,
                outdir=output_dir)
    
    # Mensagem de confirmação
    print(f'Composição RGB salva em: {output_path}')