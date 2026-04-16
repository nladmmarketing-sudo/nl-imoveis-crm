"""
Pagina: Visao Geral - KPIs e resumo do CRM
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils.supabase_client import (
    fetch_leads_jetimob, fetch_vendas, fetch_corretores_plantao,
    fetch_leads_bot, count_table
)


def render():
    st.markdown("""
    <div class="main-header">
        <h1>Visao Geral</h1>
        <p>Resumo do CRM - NL Imoveis | Natal/RN</p>
    </div>
    """, unsafe_allow_html=True)

    # KPIs row
    col1, col2, col3, col4 = st.columns(4)

    # Count tables
    try:
        total_leads = count_table("leads_jetimob")
        total_vendas = count_table("vendas_nl")
        total_plantao = count_table("corretores_plantao")
        total_bot = count_table("leads")
    except Exception:
        total_leads = total_vendas = total_plantao = total_bot = 0

    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="number">{total_leads:,}</div>
            <div class="label">Leads Jetimob</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #27AE60;">
            <div class="number">{total_vendas:,}</div>
            <div class="label">Vendas</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #F39C12;">
            <div class="number">{total_plantao:,}</div>
            <div class="label">Escalas Plantao</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #8E44AD;">
            <div class="number">{total_bot:,}</div>
            <div class="label">Leads Bot WhatsApp</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Charts row
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Leads por Origem")
        df_leads = fetch_leads_jetimob()
        if not df_leads.empty and "origem" in df_leads.columns:
            origem_counts = df_leads["origem"].value_counts().head(10).reset_index()
            origem_counts.columns = ["Origem", "Quantidade"]
            fig = px.bar(
                origem_counts, x="Quantidade", y="Origem",
                orientation="h",
                color_discrete_sequence=["#2E86C1"]
            )
            fig.update_layout(
                height=350, margin=dict(l=0, r=0, t=10, b=0),
                yaxis=dict(autorange="reversed"),
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum lead cadastrado ainda. Importe os leads do Jetimob para ver os graficos.")

    with col_right:
        st.subheader("Leads por Corretor")
        if not df_leads.empty and "corretor" in df_leads.columns:
            corretor_counts = df_leads[df_leads["corretor"].notna() & (df_leads["corretor"] != "")]
            if not corretor_counts.empty:
                corretor_counts = corretor_counts["corretor"].value_counts().head(10).reset_index()
                corretor_counts.columns = ["Corretor", "Quantidade"]
                fig2 = px.bar(
                    corretor_counts, x="Quantidade", y="Corretor",
                    orientation="h",
                    color_discrete_sequence=["#27AE60"]
                )
                fig2.update_layout(
                    height=350, margin=dict(l=0, r=0, t=10, b=0),
                    yaxis=dict(autorange="reversed"),
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Nenhum lead com corretor atribuido.")
        else:
            st.info("Importe leads para ver distribuicao por corretor.")

    # Timeline chart
    st.subheader("Leads ao Longo do Tempo")
    if not df_leads.empty and "created_at" in df_leads.columns:
        df_leads["data"] = pd.to_datetime(df_leads["created_at"]).dt.date
        timeline = df_leads.groupby("data").size().reset_index(name="Leads")
        fig3 = px.area(
            timeline, x="data", y="Leads",
            color_discrete_sequence=["#2E86C1"]
        )
        fig3.update_layout(
            height=300, margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title="Data", yaxis_title="Novos Leads",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Importe leads para ver a timeline.")

    # Recent activity
    st.subheader("Ultimos Leads Recebidos")
    if not df_leads.empty:
        recent = df_leads.head(10)[["created_at", "nome", "email", "telefone", "origem", "corretor", "status"]]
        recent.columns = ["Data", "Nome", "Email", "Telefone", "Origem", "Corretor", "Status"]
        st.dataframe(recent, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum lead ainda.")
