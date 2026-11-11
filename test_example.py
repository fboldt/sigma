# test_example.py
import os
import sys
import importlib
from pathlib import Path

PASTA_EXAMPLES = Path(__file__).parent / "examples"

EXEMPLOS = sorted(
    arquivo.stem
    for arquivo in PASTA_EXAMPLES.glob("*.py")
    if not arquivo.name.startswith("_")
)


def carregar_exemplo(nome):
    """Importa examples/<nome>.py e devolve a função que o executa."""
    modulo = importlib.import_module(f"examples.{nome}")

    # Procura uma função com o mesmo nome do arquivo (ex.: example_rgb)
    # ou, se não existir, uma função chamada "run"
    funcao = getattr(modulo, nome, None) or getattr(modulo, "run", None)
    if funcao is None:
        print(f"Erro: examples/{nome}.py não tem uma função '{nome}' nem 'run'.",
              file=sys.stderr)
        sys.exit(1)
    return funcao


def main():
    uso = "Uso: python test_example.py <exemplo> <diretorio_imagens>"

    if len(sys.argv) != 3:
        print("Erro: parâmetros faltando.", file=sys.stderr)
        print(uso, file=sys.stderr)
        print(f"Exemplos disponíveis: {', '.join(EXEMPLOS)}", file=sys.stderr)
        sys.exit(1)

    nome, image_dir = sys.argv[1], sys.argv[2]

    if nome not in EXEMPLOS:
        print(f"Erro: exemplo '{nome}' não encontrado em examples/.", file=sys.stderr)
        print(f"Exemplos disponíveis: {', '.join(EXEMPLOS)}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(image_dir):
        print(f"Erro: o diretório '{image_dir}' não existe.", file=sys.stderr)
        sys.exit(1)

    funcao = carregar_exemplo(nome)
    funcao(image_dir)


if __name__ == "__main__":
    main()