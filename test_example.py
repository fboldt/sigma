import argparse
from examples.example_rgb import example_rgb


list_of_avaliable_examples = [
    "example_rgb"
]

def run_example(example_name):
    if example_name in list_of_avaliable_examples:
        eval(f"{example_name}()")
    else:
        print(f"Exemplo '{example_name}' não encontrado.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executar exemplos")
    parser.add_argument("example", choices=list_of_avaliable_examples, help="Nome do exemplo a ser executado")
    args = parser.parse_args()
    run_example(args.example)
    print("Teste da composição RGB concluído com sucesso!")
