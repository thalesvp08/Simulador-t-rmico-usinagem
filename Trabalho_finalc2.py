import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Configuração inicial da página (precisa ser o primeiro comando do Streamlit)
st.set_page_config(page_title="Simulador Térmico - Usinagem", layout="wide")


# --- Definição das Classes (Herança) ---

class Tarugo:
    """Classe base com as dimensões geométricas comuns a qualquer peça cilíndrica."""
    def __init__(self, comprimento, diametro, temperatura_ambiente=25.0):
        self.comprimento = comprimento
        self.diametro = diametro
        self.temperatura_ambiente = temperatura_ambiente


class Poliamida(Tarugo):
    def __init__(self, comprimento, diametro, temperatura_ambiente=25.0):
        super().__init__(comprimento, diametro, temperatura_ambiente)
        self.nome = "Poliamida"
        self.limite_termico = 120.0   # Temperatura crítica de amolecimento (°C)
        self.fator_atrito = 0.065     # Polímero retém bastante calor no contato com a ferramenta
        self.fator_conducao = 0.10    # Baixa difusão térmica para o interior da peça


class Acrilico(Tarugo):
    def __init__(self, comprimento, diametro, temperatura_ambiente=25.0):
        super().__init__(comprimento, diametro, temperatura_ambiente)
        self.nome = "Acrílico"
        self.limite_termico = 100.0
        self.fator_atrito = 0.075
        self.fator_conducao = 0.08


class Aluminio(Tarugo):
    def __init__(self, comprimento, diametro, temperatura_ambiente=25.0):
        super().__init__(comprimento, diametro, temperatura_ambiente)
        self.nome = "Alumínio"
        self.limite_termico = 580.0
        self.fator_atrito = 0.030     # Menor geração localizada de calor
        self.fator_conducao = 0.75    # Alta condutividade: espalha o calor rápido para o núcleo


# --- Simulação Numérica (Monte Carlo + NumPy) ---

def simular_probabilidade_superaquecimento(peca, rpm, profundidade, avanco, n_simulacoes=500):
    """
    Discretiza a seção longitudinal do tarugo em uma matriz 2D (raio x comprimento)
    e estima a probabilidade de cada célula ultrapassar o limite térmico do material.
    """
    linhas = 10   # Camadas radiais (0 = superfície usinada, 9 = núcleo)
    colunas = 50  # Discretização do avanço ao longo do comprimento
    taxa_resfriamento_ar = 0.02

    # Acumulador de quantas vezes cada ponto da malha falhou nas N simulações
    contagem_falhas = np.zeros((linhas, colunas))

    for _ in range(n_simulacoes):
        # Inicializa a peça inteira na temperatura ambiente
        malha_termica = np.full((linhas, colunas), peca.temperatura_ambiente)

        for passe_atual in range(colunas):
            # Ruído gaussiano (±10%) para representar vibração, desgaste e variação de corte
            variacao_processo = np.random.normal(loc=1.0, scale=0.10)
            calor_gerado = (peca.fator_atrito * rpm * profundidade * avanco) * variacao_processo

            # Resfriamento convectivo aplicado de forma vetorizada na matriz inteira
            calor_perdido = taxa_resfriamento_ar * (malha_termica - peca.temperatura_ambiente)
            malha_termica -= calor_perdido

            # Aporte de calor na superfície (linha 0) e condução parcial para as camadas internas
            malha_termica[0, passe_atual] += calor_gerado
            malha_termica[1:, passe_atual] += calor_gerado * peca.fator_conducao

        # Comparação booleana: soma 1 nas posições que ultrapassaram o limite térmico
        contagem_falhas += (malha_termica > peca.limite_termico)

    # Retorna a matriz em porcentagem (0% a 100%)
    return (contagem_falhas / n_simulacoes) * 100


# --- Interface Web (Streamlit) ---

st.title("Simulador de Risco Térmico na Usinagem")
st.write("Análise probabilística (Monte Carlo) de superaquecimento durante o torneamento cilíndrico.")

st.sidebar.header("Parâmetros do Processo")

# Dicionário para instanciar a classe escolhida sem precisar de vários if/elif
materiais_disponiveis = {
    "Poliamida": Poliamida,
    "Acrílico": Acrilico,
    "Alumínio": Aluminio
}

material_escolhido = st.sidebar.selectbox("Material do Tarugo:", list(materiais_disponiveis.keys()))
rpm = st.sidebar.slider("Rotação do Torno (RPM):", min_value=500, max_value=3500, value=1500, step=100)
profundidade = st.sidebar.slider("Profundidade de Corte (mm):", min_value=0.5, max_value=5.0, value=2.0, step=0.1)
avanco = st.sidebar.slider("Avanço da Ferramenta (mm/rot):", min_value=0.1, max_value=1.5, value=0.5, step=0.1)

# Cria o objeto da subclasse correspondente (tarugo padrão de 200mm x Ø50mm)
classe_material = materiais_disponiveis[material_escolhido]
peca_atual = classe_material(comprimento=200, diametro=50)

# Executa a simulação e extrai os indicadores principais da matriz resultante
probabilidades = simular_probabilidade_superaquecimento(peca_atual, rpm, profundidade, avanco)
risco_maximo = float(np.max(probabilidades))
risco_medio_superficie = float(np.mean(probabilidades[0, :]))

# Exibição das métricas resumidas
col1, col2, col3 = st.columns(3)
col1.metric("Limite Térmico", f"{peca_atual.limite_termico:.0f} °C")
col2.metric("Risco Máximo na Peça", f"{risco_maximo:.1f}%")
col3.metric("Risco Médio na Superfície", f"{risco_medio_superficie:.1f}%")

# Diagnóstico automático baseado no pico de probabilidade
if risco_maximo >= 50.0:
    st.error(f"ALERTA CRÍTICO: Risco de {risco_maximo:.1f}% de falha térmica na superfície ({peca_atual.nome}). Reduza o RPM ou a profundidade.")
elif risco_maximo >= 15.0:
    st.warning(f"ATENÇÃO: Risco moderado ({risco_maximo:.1f}%) de superaquecimento localizado no final do passe.")
else:
    st.success(f"OPERAÇÃO SEGURA: Risco térmico controlado ({risco_maximo:.1f}%) para {peca_atual.nome}.")

# Plotagem do mapa de calor
fig, ax = plt.subplots(figsize=(10, 4))
sns.heatmap(probabilidades, cmap="YlOrRd", vmin=0, vmax=100, ax=ax, cbar_kws={"label": "Probabilidade (%)"})
ax.set_title(f"Mapa de Risco Térmico - {peca_atual.nome} ({peca_atual.comprimento}mm x Ø{peca_atual.diametro}mm)")
ax.set_xlabel("Comprimento da Peça (Avanço da Ferramenta)")
ax.set_ylabel("Profundidade (0 = Superfície, 9 = Núcleo)")

st.pyplot(fig)
plt.close(fig)  # Libera a figura da memória após renderizar