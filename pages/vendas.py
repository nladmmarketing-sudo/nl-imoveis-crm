"""
Pagina: Vendas - Acompanhamento de vendas e locacoes
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.supabase_client import fetch_vendas


def render():
    st.markdown("""
    <div class="main-header">
        <h1>Vendas</h1>
        <p>Acompanhamento de vendas e locacoes - NL Imoveis</p>
    </div>
    """, unsafe_allow_html=True)

    df = fetch_vendas()

    if df.empty:
        st.info("Nenhuma venda registrada ainda.")
        return

    # KPIs
    col1, col2, col3, col4 = st.columns(4)

    total = len(df)
    vendas = len(df[df["tipo_negocio"] == "venda"]) if "tipo_negocio" in df.columns else 0
    alugueis = len(df[df["tipo_negocio"] == "aluguel"]) if "tipo_negocio" in df.columns else 0
    valor_total = df["valor"].sum() if "valor" in df.columns else 0

    col1.metric("Total Negocios", total)
    col2.metric("Vendas", vendas)
    col3.metric("Locacoes", alugueis)
    col4.metric("Valor Total", f"R$ {valor_total:,.2f}")

    st.markdown("---")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        tipos = ["Todos"] + sorted(df["tipo_negocio"].dropna().unique().tolist()) if "tipo_negocio" in df.columns else ["Todos"]
        filtro_tipo = st.selectbox("Tipo", tipos)
    with col2:
        corretores = ["Todos"] + sorted(df["corretor"].dropna().unique().tolist()) if "corretor" in df.columns else ["Todos"]
        filtro_corretor = st.selectbox("Corretor", corretores, key="vendas_corretor")
    with col3:
        bairros = ["Todos"] + sorted(df["bairro"].dropna().unique().tolist()) if "bairro" in df.columns else ["Todos"]
        filtro_bairro = st.selectbox("Bairro", bairros, key="vendas_bairro")

    df_f = df.copy()
    if filtro_tipo != "Todos":
        df_f = df_f[df_f["tipo_negocio"] == filtro_tipo]
    if filtro_corretor != "Todos":
        df_f = df_f[df_f["corretor"] == filtro_corretor]
    if filtro_bairro != "Todos":
        df_f = df_f[df_f["bairro"] == filtro_bairro]

    # Table
    display_cols = ["data_venda", "nome_cliente", "tipo_negocio", "tipo_imovel", "codigo_imovel", "bairro", "valor", "corretor", "origem_lead"]
    available = [c for c in display_cols if c in df_f.columns]
    df_display = df_f[available].copy()
    col_names = {
        "data_venda": "Data", "nome_cliente": "Cliente", "tipo_negocio": "Tipo",
        "tipo_imovel": "Imovel", "codigo_imovel": "Codigo", "bairro": "Bairro",
        "valor": "Valor (R$)", "corretor": "Corretor", "origem_lead": "Origem"
    }
    df_display = df_display.rename(columns=col_names)
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # Charts
    st.markdown("---")
    c1, c2 = st.columns(2)

    with c1:
        if "corretor" in df_f.columns:
            st.subheader("Vendas por Corretor")
            vc = df_f["corretor"].value_counts().reset_index()
            vc.columns = ["Corretor", "Negocios"]
            fig = px.bar(vc, x="Corretor", y="Negocios", color_discrete_sequence=["#27AE60"])
            fig.update_layout(height=350, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        if "origem_lead" in df_f.columns:
            st.subheader("Vendas por Origem")
            oc = df_f["origem_lead"].value_counts().reset_index()
            oc.columns = ["Origem", "Negocios"]
            fig2 = px.pie(oc, values="Negocios", names="Origem", hole=0.4)
            fig2.update_layout(height=350)
            st.plotly_chart(fig2, use_container_width=True)
