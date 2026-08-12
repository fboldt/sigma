from utils.mosaic import mosaic_scenes


def example_mosaic():
    # A primeira cena define o CRS de referencia e a prioridade no merge.
    cenas = [
        "./images/TRUE_COLOR_CBERS4A_WPM19714020250630ETC2.tif",
        "./images/TRUE_COLOR_CBERS4A_WPM19713920250630ETC2.tif",
        "./images/TRUE_COLOR_CBERS4A_WPM19713820250630ETC2.tif",
        "./images/TRUE_COLOR_CBERS4A_WPM19713720250630ETC2.tif",
        "./images/TRUE_COLOR_CBERS4A_WPM19713620250630ETC2.tif",
        "./images/TRUE_COLOR_CBERS4A_WPM19614020251006ETC2.tif", 
        "./images/TRUE_COLOR_CBERS4A_WPM19613920250604ETC2.tif", 
        "./images/TRUE_COLOR_CBERS4A_WPM19613920201003.tif",
        "./images/TRUE_COLOR_CBERS4A_WPM19613820231024.tif", 
        "./images/TRUE_COLOR_CBERS4A_WPM19613820201003.tif",
        "./images/TRUE_COLOR_CBERS4A_WPM19613720231024.tif", 
        "./images/TRUE_COLOR_CBERS4A_WPM19613720201003.tif",
        "./images/TRUE_COLOR_CBERS4A_WPM19613620231124.tif",
        "./images/TRUE_COLOR_CBERS4A_WPM19513920260112ETC2.tif", 
        "./images/TRUE_COLOR_CBERS4A_WPM19513920210412.tif",
        "./images/TRUE_COLOR_CBERS4A_WPM19513820250609ETC2.tif",
        "./images/TRUE_COLOR_CBERS4A_WPM19513720250609ETC2.tif",
        "./images/TRUE_COLOR_CBERS4A_WPM19513620231230.tif"
    ]


    output_file_path = "./images/MOSAICO_ES_INTEIRO_NOVO.tif"
    mosaic_scenes(cenas, output_file_path, reference_index=0)

if __name__ == "__main__":
    example_mosaic()

