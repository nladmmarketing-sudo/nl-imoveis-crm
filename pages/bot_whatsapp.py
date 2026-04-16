"""
Pagina: Bot WhatsApp - Leads do atendimento automatizado
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.supabase_client import fetch_leads_bot


def render():
    st.markdown("""
    <div class="main-header">
        <h1>Bot WhatsApp</h1>
        <p>Leads do atendimento automatizado via WhatsApp</p>
    </div>
    """, unsafe_allow_html=True)

    df = fetch_leads_bot()

    if df.empty:
        st.info("Nenhum lead do bot WhatsApp registrado.")
        return

    # KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Leads", len(df))

    ativos = len(df[df["bot_ativo"] == True]) if "bot_ativo" in df.columns else 0
    col2.metric("Bot Ativo", ativos)

    etapas = df["etapa"].nunique() if "etapa" in df.columns else 0
    col3.metric("Etapas", etapas)

    st.markdown("---")

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        if "etapa" in df.columns:
            etapas_list = ["Todas"] + sorted(df["etapa"].dropna().unique().tolist())
            filtro_etapa = st.selectbox("Etapa", etapas_list)
        else:
            filtro_etapa = "Todas"
    with col2:
        if "bot_ativo" in df.columns:
            filtro_bot = st.selectbox("Bot Ativo", ["Todos", "Sim", "Nao"])
        else:
            filtro_bot = "Todos"

    df_f = df.copy()
    if filtro_etapa != "Todas":
        df_f = df_f[df_f["etapa"] == filtro_etapa]
    if filtro_bot == "Sim":
        df_f = df_f[df_f["bot_ativo"] == True]
    elif filtro_bot == "Nao":
        df_f = df_f[df_f["bot_ativo"] == False]

    # Table
    display_cols = ["criado_em", "nome", "phone", "etapa", "bot_ativo", "interesse", "tipo_imovel", "localizacao", "quartos", "preco_max"]
    available = [c for c in display_cols if c in df_f.columns]
    df_display = df_f[available].copy()
    col_names = {
        "criado_em": "Data", "nome": "Nome", "phone": "Telefone",
        "etapa": "Etapa", "bot_ativo": "Bot Ativo", "interesse": "Interesse",
        "tipo_imovel": "Tipo Imovel", "localizacao": "Localizacao",
        "quartos": "Quartos", "preco_max": "Preco Max"
    }
    df_display = df_display.rename(columns={k: v for k, v in col_names.items() if k in df_display.columns})
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # Chart - Leads por etapa
    if "etapa" in df.columns:
        st.markdown("---")
        st.subheader("Leads por Etapa do Funil")
        etapa_counts = df["etapa"].value_counts().reset_index()
        etapa_counts.columns = ["Etapa", "Quantidade"]
        fig = px.funnel(etapa_counts, x="Quantidade", y="Etapa")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
