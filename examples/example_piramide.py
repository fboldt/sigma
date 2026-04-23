import os
from utils import piramide

def example_piramide():
    # Caminho para a imagem original (sem pirâmides)
    caminho_imagem_original = './images/MOSAIC_NOVO.tif' 

    # Gerar a cópia com pirâmides
    caminho_imagem_com_piramides = gerar_copia_com_piramides(caminho_imagem_original) #pode adicionar os fatores de pirâmides como segundo argumento, ex: [2, 4, 8]

    if caminho_imagem_com_piramides:
        print(f"Pirâmides geradas com sucesso! Novo arquivo: {caminho_imagem_com_piramides}")
    else:
        print("Ocorreu um erro ao gerar as pirâmides.")

if __name__ == "__main__":
    example_piramide()