import os
import sys

# Garante que o script consiga enxergar a pasta 'utils' na raiz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.pansharpening_correcao import aplicar_pansharpening_raiz, aplicar_contraste_limpo_8bit

if __name__ == "__main__":
    caminho_pan = "band0.tif"
    caminho_ms = "cor_verdadeira.tif"
    caminho_intermediario = "resultado_pansharpening.tif" 
    caminho_saida_final = "exemplo_final.tif"

    # Levanta um erro real do Python se os arquivos não existirem
    if not os.path.exists(caminho_pan) or not os.path.exists(caminho_ms):
        raise FileNotFoundError(f"Os arquivos '{caminho_pan}' e '{caminho_ms}' não foram encontrados na raiz do projeto.")

    # Passo 1
    aplicar_pansharpening_raiz(caminho_pan, caminho_ms, caminho_intermediario)
    
    # Passo 2
    if os.path.exists(caminho_intermediario):
        aplicar_contraste_limpo_8bit(caminho_intermediario, caminho_saida_final)
        
        # Passo 3: Limpeza silenciosa
        try:
            os.remove(caminho_intermediario)
        except Exception:
            pass # Se não conseguir apagar por algum motivo, simplesmente ignora e segue em frente
    else:
        raise FileNotFoundError("O arquivo intermediário não foi gerado. O fluxo foi interrompido.")