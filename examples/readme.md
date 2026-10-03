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
- **Python 3.11+** instalado.
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
python -m pip install --upgrade pip       # Opcional, evita erros com versões antigas do pip
pip install -r requirements.txt
```

### Como rodar os exemplos

Todos os scripts abaixo esperam ser executados **a partir da raiz do
repositório** (não de dentro da pasta `examples/`), porque usam caminhos
relativos como `./images`. Basta rodar com o Python normalmente:

```bash
python examples/nome_do_exemplo.py
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
python examples/example_download.py
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
python examples/example_download_and_rgb.py
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
python examples/example_rgb.py
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
python examples/exemple_pansharpening_tiles.py
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
python examples/example_mosaic.py
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
python examples/example_piramide.py
```

**Resultado esperado:** uma nova cópia do raster com as pirâmides embutidas,
com o caminho impresso no console ao final da execução (arquivo `.tif`,
melhor visualizado em uma ferramenta de SIG como o QGIS — veja a observação
no início do documento).

**Código:** https://github.com/fboldt/sigma/blob/main/examples/example_piramide.py

---

## 7. Workflow automatizado — `example_workflow.py`

Depois de entender cada etapa isoladamente, o `example_workflow.py` encadeia,
em um único script, a busca, o download, a composição RGB, o mosaico e as
pirâmides, sem intervenção manual entre uma etapa e outra:

1. **Busca e download** das bandas dos produtos disponíveis para a área e o
   período informados (`bands_download`, que faz a consulta ao catálogo e
   baixa as cenas encontradas).
2. **Composição RGB** em lote de todas as cenas baixadas
   (`rgb_batch_composite`).
3. **Formação do mosaico** a partir das composições geradas
   (`mosaic_scenes`).
4. **Pirâmides** no mosaico final (`gerar_copia_com_piramides`).

**Parâmetros principais configurados no exemplo:**
- `user`: e-mail cadastrado na plataforma do INPE (**troque pelo seu**).
- `bbox`: coordenadas da área de interesse (no exemplo, Grande Vitória - ES).
- `max_cloud` / `max_products`: filtros de cobertura de nuvens e número de
  cenas por dataset.
- `initial_date` / `final_date`: intervalo de busca.
- `bands`: bandas a baixar (no exemplo, `red`, `green`, `blue`, `nir`).
- `output_dir`: pasta de saída das bandas (`./images`).
- caminhos de saída: composições em `./images/TRUE_COLOR` e mosaico em
  `./images/MOSAICO_WORKFLOW.tif`.

**Como executar:**
```bash
python examples/example_workflow.py
```

**Resultado esperado:** as bandas baixadas em `./images/...`, uma composição
RGB por cena (`TRUE_COLOR_<cena>.tif`), o mosaico `MOSAICO_WORKFLOW.tif` e,
ao final, uma cópia com pirâmides (`MOSAICO_WORKFLOW_com_piramides.tif`).
Assim como todos os outros resultados deste pipeline, são arquivos `.tif`
georreferenciados, que só podem ser visualizados corretamente em uma
ferramenta de SIG como o QGIS (veja a observação no início do documento).

**Código:** https://github.com/fboldt/sigma/blob/main/examples/example_workflow.py

---

## 8. Detecção de nuvens — `example_cloud_detector.py`

Este exemplo lê todas as imagens `.tif`/`.tiff` de uma pasta (por padrão,
`imagens_cbers4a`) e, para cada uma, calcula o percentual de área coberta
por nuvens usando a função `calcular_nuvens_tci` (`utils/cloud_detector.py`).

**Como a detecção funciona:** a imagem é lida em blocos (padrão de
`tamanho_bloco` pixels, `2048` no exemplo) para não estourar memória.
Primeiro, a função tira uma amostra da imagem inteira para calcular, por
canal (R, G, B), os percentis 2 e 98 (usados para normalizar o contraste)
e um limiar global de brilho. Depois, bloco a bloco (processado na GPU via
`cupy`), ela classifica como nuvem os pixels que são simultaneamente
**claros** (brilho acima do limiar), **pouco saturados** e **bem
esbranquiçados** (baixa diferença entre os canais RGB), aplicando em
seguida operações morfológicas (`binary_opening`/`binary_closing`) para
limpar ruído da máscara. No fim, soma os pixels de nuvem e os pixels
válidos de todos os blocos para obter o percentual de nuvem da imagem
inteira (e a área em km², quando a imagem tem um CRS projetado).

Para cada imagem processada, o script:
1. Salva uma máscara de nuvens (`<nome_da_imagem>_mascara_nuvens.tif`), se
   `salvar_mascara=True`.
2. Salva os blocos RGB originais em uma subpasta (`<nome_da_imagem>_blocos_<tamanho>`),
   se `salvar_blocos=True`.
3. Se o percentual de nuvens for **menor ou igual a 3%**, copia a imagem
   original para uma pasta de "imagens boas" — no exemplo, há um caminho
   fixo do Windows que
   **precisa ser trocado** para um caminho válido na sua máquina antes de
   rodar.
4. Ao final, monta uma tabela com os resultados de todas as imagens
   (ordenada pelo percentual de nuvem) e salva em
   `resultado_nuvens_cbers4a.csv`.

**Como executar:**
```bash
python examples/example_cloud_detector.py
```

**Resultado esperado:** no console, o percentual de nuvem impresso para
cada imagem analisada; ao final, uma tabela resumo e o arquivo
`resultado_nuvens_cbers4a.csv` com as colunas `imagem`, `percentual_nuvem`,
`area_total_km2` e `area_nuvem_km2`. Além disso, para cada imagem: um
`.tif` de máscara de nuvens e (se `salvar_blocos=True`) uma subpasta com
os blocos RGB — todos arquivos `.tif`, que só podem ser visualizados
corretamente em uma ferramenta de SIG como o QGIS (veja a observação no
início do documento).

**Código:** https://github.com/fboldt/sigma/blob/main/examples/example_cloud_detector.py