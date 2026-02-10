# Tutorial: Download e Composição RGB de Bandas

## 1. Pré-requisitos

Antes de iniciar, certifique-se de que seu ambiente de trabalho está organizado da seguinte forma:

```
seu_projeto/
├── utils/
│   ├── download.py
│   └── rgb.py
├── script.py
```

## 2. Fluxo de Processamento

- **Etapa de download**: uso da função `bands_download` para download de bandas de acordo com os parâmetros do usuário.
- **Etapa de composição**: uso da função `rgb_batch_composite` para composição das cenas baixadas.

## 3. Instalação das Dependências

No terminal, instale as dependências necessárias (preferencialmente em um ambiente virtual):

```bash
pip install cbers4asat rasterio numpy matplotlib scikit-image geomet geojson
```

## 4. Exemplo de Uso

```python
from utils.download import bands_download
from utils.rgb import rgb_batch_composite
from datetime import date

# Usuário cadastrado na plataforma do INPE
user = 'seu.login@email.com'

# Coordenadas do local de busca
x_min = -40.8940507  # Oeste
y_min = -20.5950702  # Sul
x_max = -40.4260507  # Leste
y_max = -20.1270702  # Norte

# Bounding Box
bbox = [x_min, y_min, x_max, y_max]

# Especificações
max_cloud = 10
max_products = 5

# Intervalo de datas
initial_date = date(2025, 1, 1)
final_date = date(2025, 7, 12)

# Diretório de saída
output_dir = './images'

params = {
    'user': user,
    'bbox': bbox,
    'max_cloud': max_cloud,
    'max_products': max_products,
    'initial_date': initial_date,
    'final_date': final_date,
    'bands': bands,
    'output_dir': output_dir
}

# Etapa 1: Download
bands_path = bands_download(params)

# Etapa 2: Composição RGB
output_file_path = './images/TRUE_COLOR'
rgb_batch_composite(bands_path, output_file_path)
```

## 5. Resultados Esperados

- **Bandas**: arquivos `.tif` organizados em subpastas.
- **Composição RGB**: arquivos GeoTIFF com prefixo e ID da cena.
- **Visualização**: os arquivos podem ser visualizados no QGIS ou ArcGIS.
