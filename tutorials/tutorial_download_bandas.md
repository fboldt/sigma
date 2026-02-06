# Tutorial: Download de Bandas

Este tutorial explica como utilizar a ferramenta para buscar e baixar automaticamente imagens do satélite **CBERS-4A**.

---

## 1. Pré-requisitos

Antes de iniciar, certifique-se de que seu ambiente de trabalho esteja organizado da seguinte forma:

```
seu_projeto/
├── utils/
│   └── download.py
├── script_download.py
```

---

## 2. Arquivos de Entrada Necessários

A função requer um dicionário contendo as configurações da busca, conforme descrito abaixo:

| Parâmetro       | Tipo   | Descrição |
|-----------------|--------|-----------|
| `user`          | string | E-mail cadastrado no INPE (dgi.inpe.br/catalogo) |
| `bbox`          | lista  | Coordenadas da área de interesse `[Oeste, Sul, Leste, Norte]` |
| `initial_date`  | date   | Data de início da busca (ano, mês, dia) |
| `final_date`    | date   | Data de fim da busca (ano, mês, dia) |
| `max_cloud`     | int    | Máximo de cobertura de nuvens permitida (0–100) |
| `bands`         | lista  | *(Opcional)* Bandas a serem baixadas. Padrão: todas |

---

## 3. Instalação das Dependências

No terminal, instale a dependência necessária (preferencialmente em um ambiente virtual):

```bash
pip install cbers4asat
```

---

## 4. Exemplo de Uso da Função

```python
# Importando as funções necessárias
from datetime import date
from utils.download import bands_download

# 1. Definição das variáveis individuais
user = 'seu.login@email.com'

norte = -20.3034695
sul = -20.3174695
leste = -40.4323689
oeste = -40.4463689

bbox = [oeste, sul, leste, norte]

# 2. Montagem do dicionário de parâmetros
params = {
    'user': user,
    'bbox': bbox,
    'max_cloud': 10,
    'max_products': 1,
    'initial_date': date(2025, 1, 1),
    'final_date': date(2025, 7, 12),
    'bands': ['red', 'green', 'blue', 'nir', 'pan'],
    'output_dir': './images'
}

# 3. Chamada da função
bands_download(params)
```

---

## 5. Resultados Esperados

Dentro do diretório especificado, serão criadas subpastas contendo os arquivos **.tif** originais correspondentes a cada banda baixada.

Esses arquivos podem ser utilizados posteriormente para análises ou composições RGB em softwares SIG.
