"""
Pagina: Corretores - Escala de plantao e performance
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.supabase_client import fetch_corretores_plantao, fetch_leads_jetimob


def render():
    st.markdown("""
    <div class="main-header">
        <h1>Corretores</h1>
        <p>Escala de plantao e distribuicao de leads</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Escala de Plantao", "Performance"])

    with tab1:
        render_plantao()

    with tab2:
        render_performance()


def render_plantao():
    df = fetch_corretores_plantao()

    if df.empty:
        st.info("Nenhuma escala de plantao cadastrada.")
        return

    st.subheader("Escala de Plantao")

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        corretores = ["Todos"] + sorted(df["nome"].unique().tolist())
        filtro = st.selectbox("Corretor", corretores, key="plantao_corretor")
    with col2:
        turnos = ["Todos"] + sorted(df["turno"].dropna().unique().tolist())
        filtro_turno = st.selectbox("Turno", turnos, key="plantao_turno")

    df_filtered = df.copy()
    if filtro != "Todos":
        df_filtered = df_filtered[df_filtered["nome"] == filtro]
    if filtro_turno != "Todos":
        df_filtered = df_filtered[df_filtered["turno"] == filtro_turno]

    # Table
    display = df_filtered[["data", "nome", "telefone", "turno", "hora_inicio", "hora_fim"]].copy()
    display.columns = ["Data", "Corretor", "Telefone", "Turno", "Inicio", "Fim"]
    st.dataframe(display, use_container_width=True, hide_index=True, height=400)

    # Stats
    st.markdown("---")
    st.subheader("Plantoes por Corretor")
    counts = df["nome"].value_counts().reset_index()
    counts.columns = ["Corretor", "Plantoes"]
    fig = px.bar(counts, x="Corretor", y="Plantoes", color_discrete_sequence=["#F39C12"])
    fig.update_layout(height=350, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)


def render_performance():
    df_leads = fetch_leads_jetimob()

    if df_leads.empty:
        st.info("Importe os leads do Jetimob para ver a performance dos corretores.")
        return

    st.subheader("Performance por Corretor")

    corretor_data = df_leads[df_leads["corretor"].notna() & (df_leads["corretor"] != "")]
    if corretor_data.empty:
        st.info("Nenhum lead com corretor atribuido.")
        return

    # Leads per broker
    perf = corretor_data.groupby("corretor").agg(
        total_leads=("id", "count"),
        com_email=("email", lambda x: x.notna().sum()),
        com_telefone=("telefone", lambda x: x.notna().sum()),
    ).reset_index()
    perf.columns = ["Corretor", "Total Leads", "Com Email", "Com Telefone"]
    perf = perf.sort_values("Total Leads", ascending=False)

    st.dataframe(perf, use_container_width=True, hide_index=True)

    # Chart
    fig = px.bar(perf.head(15), x="Corretor", y="Total Leads", color_discrete_sequence=["#27AE60"])
    fig.update_layout(height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
