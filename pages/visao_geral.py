"""
Visao Geral - KPIs estrategicos e resumo executivo
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.supabase_client import fetch_leads_jetimob, fetch_vendas, fetch_corretores_plantao, count_table


def render():
    st.markdown("""
    <div class="nl-header">
        <div class="badge">Painel Estrategico</div>
        <h1>NL Imoveis — <span>Visao Geral</span></h1>
        <div class="sub">CRECI 1440 J · Natal/RN · Dados em tempo real via Supabase</div>
    </div>
    """, unsafe_allow_html=True)

    # Load data
    df_leads = fetch_leads_jetimob()
    df_vendas = fetch_vendas()

    total_leads = len(df_leads) if not df_leads.empty else 0
    total_vendas = len(df_vendas) if not df_vendas.empty else 0

    # VGV
    vgv = df_vendas["valor"].sum() if not df_vendas.empty and "valor" in df_vendas.columns else 0
    ticket_medio = vgv / total_vendas if total_vendas > 0 else 0
    taxa_conversao = (total_vendas / total_leads * 100) if total_leads > 0 else 0

    # KPIs
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="label">Total de Leads</div>
            <div class="num">{total_leads:,}</div>
            <div class="sub">Jetimob CRM</div>
        </div>
        <div class="kpi-card azul">
            <div class="label">Negocios Fechados</div>
            <div class="num">{total_vendas}</div>
            <div class="sub">Vendas + Locacoes registradas</div>
        </div>
        <div class="kpi-card green">
            <div class="label">VGV Total</div>
            <div class="num" style="color:#16A34A">R${vgv:,.0f}</div>
            <div class="sub">Ticket medio: R${ticket_medio:,.0f}</div>
        </div>
        <div class="kpi-card {'green' if taxa_conversao > 1 else 'red'}">
            <div class="label">Taxa de Conversao</div>
            <div class="num" style="color:{'#16A34A' if taxa_conversao > 1 else '#DC2626'}">{taxa_conversao:.2f}%</div>
            <div class="sub">Lead → Negocio fechado</div>
            <span class="kpi-badge {'badge-green' if taxa_conversao > 1 else 'badge-red'}">{'Saudavel' if taxa_conversao > 1 else 'Abaixo do ideal (meta: 1%+)'}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="chart-box"><h3>Leads ao Longo do Tempo</h3>', unsafe_allow_html=True)
        if not df_leads.empty and "created_at" in df_leads.columns:
            df_leads["data"] = pd.to_datetime(df_leads["created_at"], errors="coerce").dt.date
            timeline = df_leads.dropna(subset=["data"]).groupby("data").size().reset_index(name="Leads")
            fig = px.area(timeline, x="data", y="Leads", color_discrete_sequence=["#1C3882"])
            fig.update_layout(
                height=320, margin=dict(l=0, r=0, t=10, b=0),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                xaxis_title="", yaxis_title="Novos Leads"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados de leads.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="chart-box"><h3>Top 10 Origens de Leads</h3>', unsafe_allow_html=True)
        if not df_leads.empty and "origem" in df_leads.columns:
            origem_data = df_leads[df_leads["origem"].notna() & (df_leads["origem"] != "")]
            if not origem_data.empty:
                oc = origem_data["origem"].value_counts().head(10).reset_index()
                oc.columns = ["Origem", "Leads"]
                fig2 = px.bar(oc, x="Leads", y="Origem", orientation="h", color_discrete_sequence=["#F0A500"])
                fig2.update_layout(
                    height=320, margin=dict(l=0, r=0, t=10, b=0),
                    yaxis=dict(autorange="reversed"),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Leads sem origem registrada.")
        else:
            st.info("Sem dados de origem.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Ranking Corretores
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">🏆</div>
        <div>
            <h2>Ranking de Corretores — Volume de Leads</h2>
            <p>Distribuicao de leads por corretor no Jetimob CRM</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not df_leads.empty and "corretor" in df_leads.columns:
        corretor_data = df_leads[df_leads["corretor"].notna() & (df_leads["corretor"] != "")]
        if not corretor_data.empty:
            ranking = corretor_data["corretor"].value_counts().head(10).reset_index()
            ranking.columns = ["Corretor", "Leads"]
            max_leads = ranking["Leads"].max()

            html_ranking = ""
            for i, row in ranking.iterrows():
                pos = i + 1
                rank_class = f"rank-{pos}" if pos <= 3 else "rank-other"
                pct = row["Leads"] / max_leads * 100
                html_ranking += f"""
                <div class="ranking-item">
                    <div class="rank-num {rank_class}">{pos}°</div>
                    <div style="flex:1">
                        <div class="rank-name">{row['Corretor']}</div>
                        <div style="height:8px;background:#EAF3FB;border-radius:4px;overflow:hidden;margin-top:4px">
                            <div style="width:{pct:.0f}%;height:100%;background:{'#F0A500' if pos == 1 else '#1C3882' if pos <= 3 else '#9CA3AF'};border-radius:4px"></div>
                        </div>
                    </div>
                    <div class="rank-value">{row['Leads']:,} leads</div>
                </div>
                """
            st.markdown(html_ranking, unsafe_allow_html=True)
        else:
            st.info("Nenhum lead com corretor atribuido.")
    else:
        st.info("Sem dados de corretores.")

    # Recent leads
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">📋</div>
        <div>
            <h2>Ultimos Leads Recebidos</h2>
            <p>10 leads mais recentes no sistema</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not df_leads.empty:
        cols_show = ["created_at", "nome", "email", "telefone", "origem", "corretor", "status"]
        available = [c for c in cols_show if c in df_leads.columns]
        recent = df_leads.head(10)[available].copy()
        rename = {"created_at": "Data", "nome": "Nome", "email": "Email", "telefone": "Telefone",
                  "origem": "Origem", "corretor": "Corretor", "status": "Status"}
        recent = recent.rename(columns={k: v for k, v in rename.items() if k in recent.columns})
        st.dataframe(recent, use_container_width=True, hide_index=True)

    # Footer
    st.markdown("""
    <div class="nl-footer">
        <strong>NL Imoveis</strong> · Painel Estrategico · CRECI 1440 J · Natal/RN<br>
        Dados atualizados em tempo real via Supabase + Jetimob CRM
    </div>
    """, unsafe_allow_html=True)
