import argparse
from imports import available_examples

def run_example(example_name, *args, **kwargs):    
    if example_name in available_examples:
        available_examples[example_name].run(*args, **kwargs)
    else:
        print(f"Exemplo '{example_name}' não encontrado.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executar exemplos")
    parser.add_argument("example", choices=list(available_examples.keys()), help="Nome do exemplo a ser executado")
    parser.add_argument("args", nargs="*", help="Argumentos adicionais para o exemplo")
    args = parser.parse_args()
    run_example(args.example, *args.args)
    print("Exemplo executado com sucesso!")
