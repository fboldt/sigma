# Sigma - Sistema Integrado de Geração de Mosaicos Aeroespaciais

Uma abordagem baseada em fusão de imagens e correspondência com imagens de satélite

🌐 **[Acesse a documentação completa do projeto](https://fboldt.github.io/sigma/)**

## Descrição

O SIGMA é um pipeline em Python que automatiza a geração de um ortomosaico contínuo e georreferenciado do estado do Espírito Santo a partir de imagens do satélite CBERS-4A. O projeto reúne todas as etapas do processo — busca e download das cenas no catálogo do INPE, pansharpening, correção radiométrica e mosaicagem — sem intervenção manual, entregando um mosaico final recortado pelos limites do estado.

O trabalho está vinculado ao **IntegraCAR**, o maior projeto de extensão do Ifes, desenvolvido em parceria com a Fapes (Fundação de Amparo à Pesquisa do Espírito Santo) e o IDAF (Instituto de Defesa Agropecuária e Florestal), com o objetivo de integrar e automatizar o Cadastro Ambiental Rural (CAR) no estado.

## Pré-requisitos

Antes de começar, você vai precisar ter instalado:

- [Git](https://git-scm.com/)
- [Python 3.10+](https://www.python.org/downloads/)

## Instalação e execução local

**1. Clone o repositório**
```bash
git clone https://github.com/fboldt/sigma.git
cd sigma
```

**2. Crie e ative um ambiente virtual**

Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

**3. Instale as dependências**
```bash
pip install -r requirements.txt
```

**4. Execute o projeto**
```bash
python run_example.py
```

Você também pode rodar qualquer um dos scripts prontos dentro da pasta `examples/` da mesma forma, bastando ajustar os parâmetros desejados antes de executar:
```bash
python examples/nome_do_exemplo.py
```

## Estrutura do repositório

| Pasta / arquivo | Descrição |
|---|---|
| `utils/` | Funções e módulos reutilizáveis do projeto. |
| `examples/` | Exemplos prontos para uso: scripts já configurados, onde basta alterar os parâmetros e executar. |
| `tutorials/` | Tutoriais em passo a passo explicando como executar os códigos do projeto do início ao fim. |
| `workflow-sigma.ipynb` | Notebook demonstrando o fluxo de trabalho completo do projeto. |
| `requirements.txt` | Lista de dependências Python do projeto. |
