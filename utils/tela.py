from tkinter import *
from tkinter import messagebox

class Dados:
    oeste: float
    leste: float
    sul: float
    norte: float
    dataInicio : str
    dataFim : str
    nuvens : float
    limite : int

class Input:
    def __init__(self, text: str):
        self.__label = Label(tela, text=text)
        self.__input_field = Entry(tela, validate='key', validatecommand=valida, width=30, font=(12))

    def pack(self):
        self.__label.pack(pady=20)
        self.__input_field.pack()
        
def validar_decimal(texto):
    # Se estiver vazio, permite (para não travar quando apagar tudo)
    if texto in ("", "-"):
        return True

    # Aceita apenas números decimais (com ou sem ponto)
    try:
        float(texto)
        return True
    except ValueError:
        return False

def formata_data(data):

    # Converter vírgula para ponto se necessário
    data = str(data)
    dataFormatada = data.replace("/", ",")
    return dataFormatada

def enviar():
    messagebox.showinfo("Botão", "Dados registrados!")

tela = Tk()
tela.title("Tela Principal")
tela.geometry("400x300")
valida = (tela.register(validar_decimal), "%P")

Label(tela, text="Digite as coordenadas do local").pack(pady=10)

Dados.oeste = Input("Oeste").pack()
Dados.sul = Input("Sul").pack()
Dados.leste = Input("Leste").pack()
Dados.norte = Input("Norte").pack()
Label(tela, text="Data Inicial").pack(pady=20)
data = Entry(tela, width=30, font=(12)).pack()
Dados.dataInicio = formata_data(data)
Label(tela, text="Data Final").pack(pady=20)
data = Entry(tela, width=30, font=(12)).pack()
Dados.dataFim = formata_data(data)
Dados.nuvens = Input("Porcentagem de nuvens").pack()
Dados.limite = Input("Quantidade máxima").pack()


botao = Button(tela, text="Enviar", command=enviar).pack(pady=20)

tela.mainloop()