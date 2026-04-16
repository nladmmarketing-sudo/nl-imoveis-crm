"""
Pagina: Leads Jetimob - Listagem e filtros
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.supabase_client import fetch_leads_jetimob, get_supabase_client


def render():
    st.markdown("""
    <div class="main-header">
        <h1>Leads Jetimob</h1>
        <p>Gestao de leads recebidos via Jetimob CRM</p>
    </div>
    """, unsafe_allow_html=True)

    # Load data
    df = fetch_leads_jetimob()

    if df.empty:
        st.warning("Nenhum lead no Supabase ainda. Use o botao abaixo para importar da planilha ou aguarde os webhooks do Jetimob.")
        st.info("Os leads serao populados automaticamente quando o webhook do Jetimob enviar dados para o Supabase.")
        return

    # Filters
    st.markdown("### Filtros")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        origens = ["Todas"] + sorted(df["origem"].dropna().unique().tolist())
        filtro_origem = st.selectbox("Origem", origens)

    with col2:
        corretores = ["Todos"] + sorted(df[df["corretor"].notna() & (df["corretor"] != "")]["corretor"].unique().tolist())
        filtro_corretor = st.selectbox("Corretor", corretores)

    with col3:
        status_list = ["Todos"] + sorted(df[df["status"].notna() & (df["status"] != "")]["status"].unique().tolist())
        filtro_status = st.selectbox("Status", status_list)

    with col4:
        bairros = ["Todos"] + sorted(df[df["bairro"].notna() & (df["bairro"] != "")]["bairro"].unique().tolist())
        filtro_bairro = st.selectbox("Bairro", bairros)

    # Apply filters
    df_filtered = df.copy()
    if filtro_origem != "Todas":
        df_filtered = df_filtered[df_filtered["origem"] == filtro_origem]
    if filtro_corretor != "Todos":
        df_filtered = df_filtered[df_filtered["corretor"] == filtro_corretor]
    if filtro_status != "Todos":
        df_filtered = df_filtered[df_filtered["status"] == filtro_status]
    if filtro_bairro != "Todos":
        df_filtered = df_filtered[df_filtered["bairro"] == filtro_bairro]

    # KPIs after filter
    st.markdown("---")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Filtrado", f"{len(df_filtered):,}")
    k2.metric("Com Corretor", f"{df_filtered['corretor'].notna().sum():,}")
    k3.metric("Com Email", f"{df_filtered['email'].notna().sum():,}")
    k4.metric("Com Telefone", f"{df_filtered['telefone'].notna().sum():,}")

    # Charts
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["Tabela", "Por Origem", "Por Corretor"])

    with tab1:
        display_cols = ["created_at", "nome", "email", "telefone", "origem", "produto", "corretor", "status", "bairro"]
        available_cols = [c for c in display_cols if c in df_filtered.columns]
        df_display = df_filtered[available_cols].copy()

        col_names = {
            "created_at": "Data", "nome": "Nome", "email": "Email",
            "telefone": "Telefone", "origem": "Origem", "produto": "Produto",
            "corretor": "Corretor", "status": "Status", "bairro": "Bairro"
        }
        df_display = df_display.rename(columns=col_names)

        st.dataframe(df_display, use_container_width=True, hide_index=True, height=500)

        # Download CSV
        csv = df_filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Baixar CSV",
            csv,
            "leads_jetimob.csv",
            "text/csv",
            key="download_leads"
        )

    with tab2:
        origem_counts = df_filtered["origem"].value_counts().head(15).reset_index()
        origem_counts.columns = ["Origem", "Quantidade"]
        fig = px.pie(origem_counts, values="Quantidade", names="Origem", hole=0.4)
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        corretor_data = df_filtered[df_filtered["corretor"].notna() & (df_filtered["corretor"] != "")]
        if not corretor_data.empty:
            corretor_counts = corretor_data["corretor"].value_counts().reset_index()
            corretor_counts.columns = ["Corretor", "Leads"]
            fig2 = px.bar(corretor_counts, x="Corretor", y="Leads", color_discrete_sequence=["#2E86C1"])
            fig2.update_layout(height=450, xaxis_tickangle=-45)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Nenhum lead com corretor neste filtro.")
