# Tutorial: Composição RGB de Bandas

Este tutorial descreve como utilizar a ferramenta responsável por gerar
composições RGB automaticamente a partir das imagens do satélite
**CBERS-4A**.

------------------------------------------------------------------------

## 1. Pré-requisitos

Antes de começar, organize seu ambiente de trabalho da seguinte forma:

    seu_projeto/
    ├── utils/                  <-- Pasta contendo os scripts do projeto Sigma
    │   └── rgb.py
    ├── script_composicao.py    <-- Arquivo que você criará seguindo este tutorial

------------------------------------------------------------------------

## 2. Arquivos de entrada necessários

A função utilizada requer três arquivos de bandas e o caminho de saída
para o resultado.

  -------------------------------------------------------------------------
  Parâmetro            Tipo     Descrição
  -------------------- -------- -------------------------------------------
  `red_band_path`      string   Caminho da banda vermelha

  `green_band_path`    string   Caminho da banda verde

  `blue_band_path`     string   Caminho da banda azul

  `output_file_path`   string   Caminho base e nome do arquivo final
  -------------------------------------------------------------------------

------------------------------------------------------------------------

## 3. Instalação das dependências

No terminal, instale as dependências necessárias --- preferencialmente
em um ambiente virtual:

``` bash
pip install rasterio numpy matplotlib cbers4asat scikit-image geomet geojson
```

------------------------------------------------------------------------

## 4. Exemplo de uso da função

``` python
# Importando as funções necessárias
import os
from utils.rgb import rgb_composite

# 1. Defina os caminhos para seus arquivos de dados
caminho_banda_r = './images/CBERS_4A_WPM_..._BAND3.tif'
caminho_banda_g = './images/CBERS_4A_WPM_..._BAND2.tif'
caminho_banda_b = './images/CBERS_4A_WPM_..._BAND1.tif'

# 2. Defina o caminho e o nome do arquivo de saída
caminho_saida = './images/RESULTADO_RGB'

# 3. Chame a função
rgb_composite(
    red_band=caminho_banda_r,
    green_band=caminho_banda_g,
    blue_band=caminho_banda_b,
    output_file_path=caminho_saida
)
```

------------------------------------------------------------------------

## 5. Arquivo gerado

-   **Arquivo produzido:** Um novo arquivo **GeoTIFF** será criado no
    caminho definido por `output_file_path`.
-   **Visualização:** O arquivo pode ser aberto em softwares SIG, como
    **QGIS** e **ArcGIS**.
