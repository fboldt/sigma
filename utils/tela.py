from tkinter import *
from tkinter import messagebox
from datetime import datetime

class Dados:
    def __init__(self, oeste, sul, leste, norte, dataInicio, dataFim, nuvens, limite):
        self.oeste = oeste
        self.sul = sul
        self.leste = leste
        self.norte = norte
        self.dataInicio = dataInicio
        self.dataFim = dataFim
        self.nuvens = nuvens
        self.limite = limite

class Input:
    def __init__(self, text: str, valida=None):
        self.label = Label(tela, text=text)
        self.entry = Entry(
            tela,
            validate='key' if valida else 'none',
            validatecommand=valida,
            width=30,
            font=(12)
        )

    def pack(self):
        self.label.pack(pady=5)
        self.entry.pack()

    def get(self):
        return self.entry.get()

    def clear(self):
        self.entry.delete(0, END)

def validar_decimal(texto):
    if texto in ("", "-"):
        return True
    try:
        float(texto)
        return True
    except ValueError:
        return False

def formata_data(data):
    return data.replace("/", ",")

def validar_data(data):
    try:
        datetime.strptime(data, "%d/%m/%Y")
        return True
    except ValueError:
        return False

def enviar():
    data_ini = data_inicio.get()
    data_f = data_fim.get()

    if not validar_data(data_ini) or not validar_data(data_f):
        messagebox.showerror("Erro", "Data inválida! Use DD/MM/AAAA")
        return

    dados = Dados(
        oeste.get(),
        sul.get(),
        leste.get(),
        norte.get(),
        formata_data(data_ini),
        formata_data(data_f),
        nuvens.get(),
        limite.get()
    )

    messagebox.showinfo("Sucesso", "Dados registrados!")

    for campo in [oeste, leste, sul, norte, data_inicio, data_fim, nuvens, limite]:
        campo.clear()


tela = Tk()
tela.title("Tela Principal")
tela.geometry("400x500")

valida_decimal = (tela.register(validar_decimal), "%P")

Label(tela, text="Digite as coordenadas do local").pack(pady=10)

oeste = Input("Oeste", valida_decimal)
oeste.pack()

sul = Input("Sul", valida_decimal)
sul.pack()

leste = Input("Leste", valida_decimal)
leste.pack()

norte = Input("Norte", valida_decimal)
norte.pack()

Label(tela, text="Data Inicial (DD/MM/AAAA)").pack(pady=10)
data_inicio = Input(" ", None)
data_inicio.pack()

Label(tela, text="Data Final (DD/MM/AAAA)").pack(pady=10)
data_fim = Input(" ", None)
data_fim.pack()

nuvens = Input("Porcentagem de nuvens", valida_decimal)
nuvens.pack()

limite = Input("Quantidade máxima")
limite.pack()

Button(tela, text="Enviar", command=enviar).pack(pady=20)

tela.mainloop()