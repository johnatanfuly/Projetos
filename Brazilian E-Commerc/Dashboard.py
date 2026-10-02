# O que eu quero extrair do dataset:olist_customers_dataset.csv = customer_city + customer_state
#                                   olist_order_items_dataset.csv = "price" +"freight_value"
#                                   olist_payments_dataset.csv = "payment_type" + "payment_value"
#                                   olist_products_dataset.csv = "product_category_name" + "product_photos_qty"


import os
import pandas as pd
import streamlit as st
import numpy as np
import plotly.express as px

# Configuração da página do Streamlit
st.set_page_config(page_title="Dashboard Olist", layout="wide")
st.title("📊 Análise de Dados - Brazilian E-Commerce 2016 a 2018")

# 1. Descobre automaticamente a pasta onde o dashboard.py está salvo
diretorio_atual = os.path.dirname(os.path.abspath(__file__))

# 2. Constrói o caminho completo e dinâmico para TODOS os arquivos CSV
caminho_customers = os.path.join(diretorio_atual, "olist_customers_dataset.csv")
caminho_items = os.path.join(diretorio_atual, "olist_order_items_dataset.csv")
caminho_payments = os.path.join(
    diretorio_atual, "olist_order_payments_dataset.csv"
)
caminho_products = os.path.join(diretorio_atual, "olist_products_dataset.csv")


# Carrega os dados com cache para o dashboard carregar muito mais rápido
@st.cache_data
def carregar_dados():
    customers = pd.read_csv(
        caminho_customers, usecols=["customer_city", "customer_state"]
    )
    items = pd.read_csv(caminho_items, usecols=["price", "freight_value"])
    payments = pd.read_csv(
        caminho_payments, usecols=[ "payment_value", "payment_type"]
    )
    products = pd.read_csv(
        caminho_products,
        usecols=["product_category_name", "product_photos_qty"],
    )
    return customers, items, payments, products


customer_city, valor, payment, category = carregar_dados()

# 3. Exibe os dados concatenados (A lista inteira combinada)
#st.subheader("Visualização de Todos os Registros Combinados")


# Concatenamos as colunas normalmente
df_combinado = pd.concat(
    [customer_city, valor, payment, category],
    axis=1,
)

# LIMITAÇÃO EXATA: Filtra o DataFrame do começo (0) até o índice de corte (99440)
df_combinado = df_combinado.iloc[:99440]

# O use_container_width garante que a tabela ocupe toda a largura da tela
#st.dataframe(df_combinado, use_container_width=True)


# --- ANÁLISE DOS INTERVALOS DE VALORES (SOMA DOS VALORES) ---
st.markdown("---")
st.header("💰 Faturamento Acumulado por Faixas de Valores")

# 1. Definição dos Intervalos Personalizados (Bins)
intervalos_20 = np.arange(0, 201, 20)      # [0, 20, 40, ..., 200]
intervalos_100 = np.arange(300, 601, 100)
intervalos_500 = np.arange(1000, 2001, 500) 
intervalos_2000 = np.arange(2000, 10001, 2000)  # [2000, 4000, 6000, 8000, 10000]

# Unifica e ordena os limites para criar os grupos corretamente
limites_faixas = sorted(list(set(intervalos_20) | set(intervalos_100) | set(intervalos_500) | set(intervalos_2000)))   

# MUDANÇA AQUI: Criamos duas colunas paralelas na tela em vez de abas
col1, col2 = st.columns(2)

# --- COLUNA 1: VALOR DO PAGAMENTO (payment_value) ---
with col1:
    # Cria a coluna com a faixa correspondente
    df_combinado["Faixa_Pagamento"] = pd.cut(
        df_combinado["payment_value"], 
        bins=limites_faixas, 
        include_lowest=True
    )
    
    # Agrupa por faixa e faz a SOMA do campo payment_value
    soma_pagamento = df_combinado.groupby("Faixa_Pagamento", as_index=False, observed=False)["payment_value"].sum()
    soma_pagamento.columns = ["Intervalo", "Total_Soma"]
    
    # Remove valores fora do intervalo (nulos)
    soma_pagamento = soma_pagamento.dropna(subset=["Intervalo"])
    
    # Ordena de forma crescent pelo início do intervalo numérico
    soma_pagamento["Inicio_Intervalo"] = soma_pagamento["Intervalo"].apply(lambda x: x.left)
    soma_pagamento = soma_pagamento.sort_values(by="Inicio_Intervalo", ascending=True)
    
    # Converte o intervalo para texto (necessário para o Plotly plotar o eixo X)
    soma_pagamento["Intervalo"] = soma_pagamento["Intervalo"].astype(str)

    # Criação do gráfico de soma usando Plotly
    fig_pagamento = px.bar(
        soma_pagamento,
        x="Intervalo",
        y="Total_Soma",
        title="Faturamento Total por Intervalo de Pagamento",
        labels={"Intervalo": "Faixas de Valores (R$)", "Total_Soma": "Soma Total (R$)"},
        text_auto=".2s",  
        color="Total_Soma",
        color_continuous_scale="Viridis"
    )
    fig_pagamento.update_layout(title_x=0.5, xaxis_tickangle=-45)
    st.plotly_chart(fig_pagamento, use_container_width=True)


# --- COLUNA 2: VALOR DO FRETE (freight_value) ---
with col2:
    # Cria a coluna com a faixa correspondente
    df_combinado["Faixa_Frete"] = pd.cut(
        df_combinado["freight_value"], 
        bins=limites_faixas, 
        include_lowest=True
    )
    
    # Agrupa por faixa e faz a SOMA do campo freight_value
    soma_frete = df_combinado.groupby("Faixa_Frete", as_index=False, observed=False)["freight_value"].sum()
    soma_frete.columns = ["Intervalo", "Total_Soma"]
    
    # Remove valores nulos
    soma_frete = soma_frete.dropna(subset=["Intervalo"])
    
    # Ordena de forma crescente pelo início do intervalo numérico
    soma_frete["Inicio_Intervalo"] = soma_frete["Intervalo"].apply(lambda x: x.left)
    soma_frete = soma_frete.sort_values(by="Inicio_Intervalo", ascending=True)
    
    # Converte para texto
    soma_frete["Intervalo"] = soma_frete["Intervalo"].astype(str)

    # Criação do gráfico de soma usando Plotly
    fig_frete = px.bar(
        soma_frete,
        x="Intervalo",
        y="Total_Soma",
        title="Gasto Total de Frete por Intervalo",
        labels={"Intervalo": "Faixas de Valores (R$)", "Total_Soma": "Soma Total do Frete (R$)"},
        text_auto=".2s",  
        color="Total_Soma",
        color_continuous_scale="Cividis"
    )
    fig_frete.update_layout(title_x=0.5, xaxis_tickangle=-45)
    st.plotly_chart(fig_frete, use_container_width=True)


# --- GRÁFICO DE ROSCA: DISTRIBUIÇÃO POR ESTADO (customer_state) ---
st.markdown("---")
st.header("📍 Distribuição Regional de Clientes")

# 1. Agrupa os dados contando a quantidade de clientes por estado
df_estado = df_combinado["customer_state"].value_counts().reset_index()
df_estado.columns = ["Estado", "Quantidade_Clientes"]

# 2. Cria o gráfico de pizza com furo de 30% (hole=0.3)
fig_donut = px.pie(
    df_estado,
    names="Estado",
    values="Quantidade_Clientes",
    title="<b>Proporção de Clientes por Estado</b>",
    hole=0.3,  
    color_discrete_sequence=px.colors.sequential.Viridis  
)

# 3. Ajustes finos no layout e exibição das porcentagens
fig_donut.update_traces(
    textposition="inside", 
    textinfo="percent+label"  
)

fig_donut.update_layout(
    title_x=0.5,
    legend_title_text="Estados"
)

# 4. Exibe o gráfico no Streamlit
st.plotly_chart(fig_donut, use_container_width=True)


# --- GRÁFICO DE COMPARAÇÃO POR FORMA DE PAGAMENTO ---
st.markdown("---")
st.header("💳 Faturamento por Forma de Pagamento (Comparativo)")

# Correção de segurança: Remove espaços ocultos dos nomes das colunas (caso existam)
df_combinado.columns = df_combinado.columns.str.strip()

# Verifica se as colunas realmente existem antes de tentar criar o gráfico
if "payment_type" in df_combinado.columns and "payment_value" in df_combinado.columns:

    # 1. Cria uma cópia limpa contendo apenas o que precisamos, descartando linhas vazias
    df_pagamentos = df_combinado[["payment_type", "payment_value"]].dropna().copy()

    # Garante que a coluna de valores seja tratada estritamente como número decimal
    df_pagamentos["payment_value"] = pd.to_numeric(df_pagamentos["payment_value"], errors="coerce")
    df_pagamentos = df_pagamentos.dropna(subset=["payment_value"])

    # Dicionário para traduzir as formas de pagamento do Olist para o português
    traducoes = {
        "credit_card": "Cartão de Crédito",
        "boleto": "Boleto Bancário",
        "voucher": "Vale/Voucher",
        "debit_card": "Cartão de Débito",
        "not_defined": "Não Definido"
    }

    # Aplica a tradução com segurança
    df_pagamentos["payment_type"] = df_pagamentos["payment_type"].astype(str).map(traducoes).fillna(df_pagamentos["payment_type"])

    # 2. Agrupa por tipo de pagamento e faz a SOMA dos valores vendidos
    faturamento_por_pagamento = (
        df_pagamentos.groupby("payment_type", as_index=False)["payment_value"]
        .sum()
    )

    # 3. Ordena do maior faturamento para o menor (Ordem Decrescente)
    faturamento_por_pagamento = faturamento_por_pagamento.sort_values(by="payment_value", ascending=False)

    # 4. Cria o gráfico de barras comparativo usando Plotly
    fig_comparativo = px.bar(
        faturamento_por_pagamento,
        x="payment_type",
        y="payment_value",
        title="<b>Volume Total de Vendas por Tipo de Pagamento</b>",
        labels={
            "payment_type": "Forma de Pagamento",
            "payment_value": "Total Vendido (R$)",
        },
        text_auto=".2s",  
        color="payment_value",  
        color_continuous_scale="Cividis",
    )

    # 5. Ajustes de layout
    fig_comparativo.update_layout(
        title_x=0.5,
        xaxis_title=None,
        showlegend=False
    )

    # 6. Exibe o gráfico na tela do Streamlit
    st.plotly_chart(fig_comparativo, use_container_width=True)

else:
    st.error(f"Erro: As colunas 'payment_type' ou 'payment_value' não foram encontradas. Colunas disponíveis na tabela: {list(df_combinado.columns)}")


