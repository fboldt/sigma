# Tutoriais

Este documento reúne um tutorial para cada script da pasta `examples/`, na ordem lógica do
pipeline: baixar as cenas, montar a composição RGB, aplicar o pansharpening,
gerar o mosaico, criar as pirâmides e, por fim, rodar boa parte disso de
forma automatizada em um único script.

ℹ️ Todos os resultados gerados pelos exemplos abaixo são arquivos `.tif`
georreferenciados — eles não abrem como uma imagem comum. 
Para visualizá-los é preciso usar uma ferramenta de SIG
(Sistema de Informação Geográfica), como o
[QGIS](https://qgis.org/).

---

## Pré-requisitos

Antes de rodar qualquer um dos exemplos abaixo, você vai precisar de:

- **Git** instalado ([git-scm.com](https://git-scm.com/)).
- **Python 3.10+** instalado.
- Uma **conta cadastrada no catálogo do INPE**, já que o download das cenas
  do CBERS-4A exige um usuário válido (é o valor passado no campo `user` dos
  exemplos de download).

### Instalação

```bash
# 1. Clonar o repositório
git clone https://github.com/fboldt/sigma.git
cd sigma

# 2. Criar e ativar um ambiente virtual
python3 -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# 3. Instalar as dependências
pip install -r requirements.txt
```

### Como rodar os exemplos

Todos os scripts abaixo esperam ser executados **a partir da raiz do
repositório** (não de dentro da pasta `examples/`), porque usam caminhos
relativos como `./images` e fazem `import` de módulos da pasta `utils/`
(ex.: `from utils.download import bands_download`). Para que o Python
encontre esses módulos, é preciso incluir a raiz do projeto no
`PYTHONPATH` ao rodar cada exemplo:

**Linux / macOS:**
```bash
PYTHONPATH=. python examples/nome_do_exemplo.py
```

**Windows (PowerShell):**
```powershell
$env:PYTHONPATH = "."; python examples/nome_do_exemplo.py
```

**Windows (Prompt de Comando / cmd):**
```cmd
set PYTHONPATH=. && python examples/nome_do_exemplo.py
```

Antes de rodar, abra o script e ajuste os parâmetros conforme necessário
(bounding box, datas, caminhos de entrada/saída, seu usuário do INPE, etc.).

---

## 1. Download das bandas — `example_download.py`

Realiza a busca e o download de cenas CBERS-4A no catálogo do INPE, com base
em uma área (bounding box), um intervalo de datas, cobertura máxima de nuvens
e as bandas desejadas.

**Parâmetros principais configurados no exemplo:**
- `bbox`: coordenadas da área de interesse (no exemplo, Domingos Martins - ES).
- `max_cloud`: percentual máximo de nuvens aceito por cena.
- `max_products`: número máximo de cenas retornadas por dataset.
- `initial_date` / `final_date`: intervalo de busca.
- `bands`: lista de bandas a baixar (`red`, `green`, `blue`, `nir`, `pan`).
- `output_dir`: pasta onde as bandas baixadas serão salvas.

**Como executar:**
```bash
PYTHONPATH=. python examples/example_download.py          # Linux/macOS
$env:PYTHONPATH="."; python examples/example_download.py  # Windows (PowerShell)
```

**Resultado esperado:** uma subpasta dentro de `output_dir` (por padrão
`./images`) para cada cena encontrada, contendo os arquivos `.tif` de cada
banda solicitada.

**Código:** https://github.com/fboldt/sigma/blob/main/examples/example_download.py

---

## 2. Download + composição RGB automática — `example_download_and_rgb.py`

Faz o download das bandas (igual ao exemplo anterior, mas normalmente
limitado a `red`, `green` e `blue`) e, em seguida, gera automaticamente a
composição RGB de **todas** as cenas baixadas, sem passos manuais entre uma
etapa e outra.

**Parâmetros principais:** os mesmos do download (`bbox`, `max_cloud`,
`max_products`, datas, `bands`, `output_dir`), mais o prefixo de saída da
composição (`output_file_path`, ex.: `./images/TRUE_COLOR`).

**Como executar:**
```bash
PYTHONPATH=. python examples/example_download_and_rgb.py          # Linux/macOS
$env:PYTHONPATH="."; python examples/example_download_and_rgb.py  # Windows (PowerShell)
```

**Resultado esperado:** as pastas de bandas baixadas em `./images/...` e, em
seguida, um arquivo de composição RGB (`TRUE_COLOR_<cena>.tif`) para cada
cena baixada.

**Código:** https://github.com/fboldt/sigma/blob/main/examples/example_download_and_rgb.py

---

## 3. Composição RGB manual — `example_rgb.py`

Faz a composição RGB de bandas que **já foram baixadas** anteriormente,
apontando manualmente para os arquivos de cada banda (vermelho, verde e
azul) de uma cena específica.

**Parâmetros principais:**
- `input_path`: pasta da cena já baixada.
- `red_band_path`, `green_band_path`, `blue_band_path`: caminhos completos
  para cada banda.
- `output_file_path`: caminho e nome do arquivo composto de saída.

**Como executar:**
```bash
PYTHONPATH=. python examples/example_rgb.py          # Linux/macOS
$env:PYTHONPATH="."; python examples/example_rgb.py  # Windows (PowerShell)
```

Ajuste os caminhos das bandas para apontar para uma cena que você já tenha
baixado (por exemplo, com o `example_download.py`).

**Resultado esperado:** um único arquivo `.tif` de composição RGB (no
exemplo, `TRUE_COLOR.tif`) salvo em `output_dir`.

**Código:** https://github.com/fboldt/sigma/blob/main/examples/example_rgb.py

---

## 4. Pansharpening por tiles — `exemple_pansharpening_tiles.py`

Aplica pansharpening (fusão da banda pancromática de alta resolução com a
composição multiespectral) processando a imagem **em blocos (tiles)**, o que
evita estourar a memória em imagens grandes. Os tiles temporários são
gerados em uma pasta auxiliar e descartados depois de montado o resultado
final.

**Pré-requisito específico:** diferente dos outros exemplos, este script
espera encontrar dois arquivos **na raiz do projeto**:
- `pan.tif` — a banda pancromática.
- `cor_verdadeira.tif` — a composição multiespectral (por exemplo, o
  resultado de um dos exemplos de RGB acima).

Se algum dos dois não existir, o script lança um erro (`FileNotFoundError`)
antes mesmo de começar o processamento.

**Como executar:**
```bash
PYTHONPATH=. python examples/exemple_pansharpening_tiles.py          # Linux/macOS
$env:PYTHONPATH="."; python examples/exemple_pansharpening_tiles.py  # Windows (PowerShell)
```

**Resultado esperado:** um arquivo `pansharpened_output.tif` na raiz do
projeto, combinando a resolução espacial da banda pancromática com as cores
da composição multiespectral, além da pasta temporária `./tiles_temp`
(apagada/reaproveitada a cada execução).

**Código:** https://github.com/fboldt/sigma/blob/main/examples/exemple_pansharpening_tiles.py

---

## 5. Mosaico — `example_mosaic.py`

Une várias cenas (já processadas nas etapas anteriores) em um único mosaico
contínuo. A primeira cena da lista define o CRS de referência e tem
prioridade no merge das áreas sobrepostas.

**Parâmetros principais:**
- `cenas`: lista com os caminhos de todas as cenas a mosaicar.
- `output_file_path`: caminho do mosaico final.
- `reference_index`: índice da cena usada como referência (no exemplo, `0`).

**Como executar:**
```bash
PYTHONPATH=. python examples/example_mosaic.py          # Linux/macOS
$env:PYTHONPATH="."; python examples/example_mosaic.py  # Windows (PowerShell)
```

Substitua a lista `cenas` pelos arquivos de composição RGB que você já
gerou.

**Resultado esperado:** um único arquivo de mosaico (no exemplo,
`MOSAICO_ES.tif`) cobrindo toda a área combinada das cenas de entrada.

**Código:** https://github.com/fboldt/sigma/blob/main/examples/example_mosaic.py

---

## 6. Pirâmides — `example_piramide.py`

Gera pirâmides (overviews em múltiplas resoluções) para um raster já
existente, otimizando o carregamento em ferramentas de visualização como o
QGIS — evita que a ferramenta precise reprocessar a imagem inteira em
resolução máxima toda vez que você dá zoom out.

**Parâmetros principais:**
- `caminho_imagem_original`: caminho da imagem sem pirâmides (por exemplo, o
  mosaico gerado na etapa anterior).
- Opcionalmente, um segundo argumento com os fatores de pirâmide desejados
  (ex.: `[2, 4, 8]`).

**Como executar:**
```bash
PYTHONPATH=. python examples/example_piramide.py          # Linux/macOS
$env:PYTHONPATH="."; python examples/example_piramide.py  # Windows (PowerShell)
```

**Resultado esperado:** uma nova cópia do raster com as pirâmides embutidas,
com o caminho impresso no console ao final da execução (arquivo `.tif`,
melhor visualizado em uma ferramenta de SIG como o QGIS — veja a observação
no início do documento).

**Código:** https://github.com/fboldt/sigma/blob/main/examples/example_piramide.py

---

## 7. Workflow automatizado — `example_workflow.py`

Depois de entender cada etapa isoladamente, o `example_workflow.py` encadeia
automaticamente, em um único script, as etapas de busca, filtragem, download
e processamento das cenas, sem intervenção manual entre uma etapa e outra:

1. **Busca** dos produtos disponíveis para a área e o período informados
   (`search_products`).
2. **Filtragem** dos produtos retornados que caem em um mesmo local
   (`products_filter`).
3. **Download** das bandas dos produtos já filtrados (`bands_download`).
4. **Composição RGB** em lote de todas as cenas baixadas
   (`rgb_batch_composite`).
5. **Formação do mosaico** a partir das composições geradas
   (`mosaic_scenes`).

**Parâmetros principais configurados no exemplo:**
- `user`: e-mail cadastrado na plataforma do INPE.
- `bbox`: coordenadas da área de interesse (no exemplo, Rio de Janeiro - RJ).
- `max_cloud` / `max_products`: filtros de cobertura de nuvens e número de
  cenas por dataset.
- `initial_date` / `final_date`: intervalo de busca.
- `bands`: bandas a baixar (no exemplo, `red`, `green`, `blue`, `pan`).
- `output_dir`: pasta de saída das bandas (`./images`).
- caminho do mosaico final (`./images/MOSAICO_EXEMPLO_WORKFLOW`).

**Como executar:**
```bash
PYTHONPATH=. python examples/example_workflow.py          # Linux/macOS
$env:PYTHONPATH="."; python examples/example_workflow.py  # Windows (PowerShell)
```

**Resultado esperado:** ao final da execução, um mosaico único (por padrão
`MOSAICO_EXEMPLO_WORKFLOW.tif`) reunindo todas as cenas encontradas, filtradas,
baixadas e compostas em RGB automaticamente. Assim como todos os outros
resultados deste pipeline, é um arquivo `.tif` georreferenciado, que só pode
ser visualizado corretamente em uma ferramenta de SIG como o QGIS (veja a
observação no início do documento).

**Código:** https://github.com/fboldt/sigma/blob/main/examples/example_workflow.py