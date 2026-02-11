from utils.mosaic import mosaic_images

def example_moisaic():
    # Lista com os caminhos das imagens que você quer unir
    cenas = [
        './images/TRUE_COLOR_CBERS4A_WPM19713820250630ETC2.tif',
        './images/TRUE_COLOR_CBERS4A_WPM19613920250604ETC2.tif'
    ]

    # Nome do arquivo final
    output_file_path = './images/mosaic.tif'

    # Chamada da função
    mosaic_images(cenas, output_file_path)

if __name__ == "__main__":
    example_moisaic()