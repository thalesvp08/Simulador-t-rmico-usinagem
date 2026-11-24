import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Simulador Térmico - Usinagem", layout="wide")

# classes dos materiais

class Tarugo:
    def __init__(self, comprimento, diametro, temp_ambiente=25.0):
        self.comprimento = comprimento
        self.diametro = diametro
        self.temp_ambiente = temp_ambiente

class Poliamida(Tarugo):
    def __init__(self, comprimento, diametro):
        super().__init__(comprimento, diametro)
        self.nome = "Poliamida"
        self.limite = 120.0   # temperatura em que amolece
        self.atrito = 0.065   # quanto calor o corte gera
        self.conducao = 0.10  # quanto calor vai pra dentro da peça


class Acrilico(Tarugo):
    def __init__(self, comprimento, diametro):
        super().__init__(comprimento, diametro)
        self.nome = "Acrílico"
        self.limite = 100.0
        self.atrito = 0.075
        self.conducao = 0.08


class Aluminio(Tarugo):
    def __init__(self, comprimento, diametro):
        super().__init__(comprimento, diametro)
        self.nome = "Alumínio"
        self.limite = 580.0
        self.atrito = 0.030
        self.conducao = 0.75
        

# simulação (monte carlo)

def simular(peca, rpm, prof, avanco, n=500):
    linhas = 10    # 0 = superfície, 9 = núcleo
    colunas = 50   # posições ao longo do comprimento
    falhas = np.zeros((linhas, colunas))

    for i in range(n):
        # a peça começa toda na temperatura ambiente
        temp = np.full((linhas, colunas), peca.temp_ambiente)

        for c in range(colunas):
            # variação aleatória em volta de 1 (vibração, desgaste...)
            ruido = np.random.normal(1.0, 0.1)
            calor = peca.atrito * rpm * prof * avanco * ruido

            # a peça toda esfria um pouco
            temp = temp - 0.02 * (temp - peca.temp_ambiente)

            # esquenta a coluna onde a ferramenta está
            temp[0, c] += calor
            temp[1:, c] += calor * peca.conducao

        # conta onde passou do limite (True vale 1)
        falhas += (temp > peca.limite)

    return falhas / n * 100


# interface

st.title("Simulador de Risco Térmico na Usinagem")
st.write("Simulação de Monte Carlo do superaquecimento no torneamento de um tarugo.")

st.sidebar.header("Parâmetros")

materiais = {
    "Poliamida": Poliamida,
    "Acrílico": Acrilico,
    "Alumínio": Aluminio
}

escolha = st.sidebar.selectbox("Material:", list(materiais.keys()))
rpm = st.sidebar.slider("Rotação (RPM):", 500, 3500, 1500, 100)
prof = st.sidebar.slider("Profundidade de corte (mm):", 0.5, 5.0, 2.0, 0.1)
avanco = st.sidebar.slider("Avanço (mm/rot):", 0.1, 1.5, 0.5, 0.1)

# tarugo de 200 mm de comprimento e 50 mm de diâmetro
peca = materiais[escolha](200, 50)

prob = simular(peca, rpm, prof, avanco)
risco_max = float(np.max(prob))
risco_med = float(np.mean(prob[0, :]))

col1, col2, col3 = st.columns(3)
col1.metric("Limite térmico", f"{peca.limite:.0f} °C")
col2.metric("Risco máximo", f"{risco_max:.1f}%")
col3.metric("Risco médio na superfície", f"{risco_med:.1f}%")

if risco_max >= 50:
    st.error(f"ALERTA: risco de {risco_max:.1f}% de falha térmica ({peca.nome}). Reduza o RPM ou a profundidade.")
elif risco_max >= 15:
    st.warning(f"Atenção: risco moderado ({risco_max:.1f}%) de superaquecimento no final do passe.")
else:
    st.success(f"Operação segura: risco de {risco_max:.1f}% para {peca.nome}.")

fig, ax = plt.subplots(figsize=(10, 4))
sns.heatmap(prob, cmap="YlOrRd", vmin=0, vmax=100, ax=ax, cbar_kws={"label": "Probabilidade (%)"})
ax.set_title(f"Mapa de risco térmico - {peca.nome} ({peca.comprimento}mm x Ø{peca.diametro}mm)")
ax.set_xlabel("Comprimento da peça")
ax.set_ylabel("Profundidade (0 = superfície, 9 = núcleo)")

st.pyplot(fig)
plt.close(fig)
