"""
Equipe Locacao - Performance da equipe de locacao
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.supabase_client import fetch_leads_jetimob, fetch_vendas
from utils.auth import escape


def render():
    st.markdown("""
    <div class="nl-header">
        <div class="badge">Equipe de Locacao</div>
        <h1>Performance <span>Locacao</span></h1>
        <div class="sub">Acompanhamento de leads, funil e fechamentos da equipe de locacao</div>
    </div>
    """, unsafe_allow_html=True)

    df_vendas = fetch_vendas()
    df_leads = fetch_leads_jetimob()

    # Filtrar locacoes
    if not df_vendas.empty and "tipo_negocio" in df_vendas.columns:
        df_loc = df_vendas[df_vendas["tipo_negocio"] == "aluguel"].copy()
    else:
        df_loc = pd.DataFrame()

    total_loc = len(df_loc)
    receita = df_loc["valor"].sum() if not df_loc.empty and "valor" in df_loc.columns else 0
    ticket = receita / total_loc if total_loc > 0 else 0

    # KPIs
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="label">Locacoes Fechadas</div>
            <div class="num">{total_loc}</div>
            <div class="sub">Registradas no sistema</div>
        </div>
        <div class="kpi-card green">
            <div class="label">Receita Total</div>
            <div class="num" style="color:#16A34A">R${receita:,.0f}</div>
            <div class="sub">Soma dos alugueis fechados</div>
        </div>
        <div class="kpi-card azul">
            <div class="label">Aluguel Medio</div>
            <div class="num">R${ticket:,.0f}</div>
            <div class="sub">por locacao fechada</div>
        </div>
        <div class="kpi-card">
            <div class="label">Total Leads</div>
            <div class="num">{len(df_leads):,}</div>
            <div class="sub">Jetimob CRM</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Ranking Corretores
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">🏆</div>
        <div>
            <h2>Ranking Corretores — Locacao</h2>
            <p>Performance individual por volume e receita</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not df_loc.empty and "corretor" in df_loc.columns:
        perf = df_loc.groupby("corretor").agg(
            locacoes=("id", "count"),
            receita=("valor", "sum")
        ).reset_index().sort_values("receita", ascending=False)

        max_rec = perf["receita"].max() if not perf.empty else 1

        html = ""
        for i, row in perf.iterrows():
            pos = len(html.split("ranking-item"))
            rank_class = f"rank-{pos}" if pos <= 3 else "rank-other"
            pct = row["receita"] / max_rec * 100 if max_rec > 0 else 0
            html += f"""
            <div class="ranking-item">
                <div class="rank-num {rank_class}">{pos}°</div>
                <div style="flex:1">
                    <div class="rank-name">{escape(row['corretor'])}</div>
                    <div class="rank-sub">{row['locacoes']} locacao(es)</div>
                    <div style="height:8px;background:#EAF3FB;border-radius:4px;overflow:hidden;margin-top:4px">
                        <div style="width:{pct:.0f}%;height:100%;background:{'#F0A500' if pos <= 1 else '#1C3882'};border-radius:4px"></div>
                    </div>
                </div>
                <div class="rank-value">R${row['receita']:,.0f}</div>
            </div>
            """
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("Registre locacoes no sistema para ver o ranking.")

    # Tabela
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">📋</div>
        <div>
            <h2>Detalhamento de Locacoes</h2>
            <p>Todas as locacoes registradas</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not df_loc.empty:
        cols = ["data_venda", "nome_cliente", "tipo_imovel", "codigo_imovel", "bairro", "valor", "corretor", "origem_lead"]
        available = [c for c in cols if c in df_loc.columns]
        display = df_loc[available].copy()
        rename = {"data_venda": "Data", "nome_cliente": "Cliente", "tipo_imovel": "Imovel",
                  "codigo_imovel": "Codigo", "bairro": "Bairro", "valor": "Aluguel (R$)",
                  "corretor": "Corretor", "origem_lead": "Origem"}
        display = display.rename(columns={k: v for k, v in rename.items() if k in display.columns})
        st.dataframe(display, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma locacao registrada ainda.")

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="chart-box"><h3>Locacoes por Bairro</h3>', unsafe_allow_html=True)
        if not df_loc.empty and "bairro" in df_loc.columns:
            bairro_data = df_loc[df_loc["bairro"].notna()]
            if not bairro_data.empty:
                bc = bairro_data["bairro"].value_counts().head(10).reset_index()
                bc.columns = ["Bairro", "Locacoes"]
                fig = px.bar(bc, x="Locacoes", y="Bairro", orientation="h", color_discrete_sequence=["#1C3882"])
                fig.update_layout(height=350, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(autorange="reversed"),
                                  plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="chart-box"><h3>Locacoes por Origem</h3>', unsafe_allow_html=True)
        if not df_loc.empty and "origem_lead" in df_loc.columns:
            orig_data = df_loc[df_loc["origem_lead"].notna()]
            if not orig_data.empty:
                oc = orig_data["origem_lead"].value_counts().reset_index()
                oc.columns = ["Origem", "Locacoes"]
                fig2 = px.pie(oc, values="Locacoes", names="Origem", hole=0.4,
                              color_discrete_sequence=["#1C3882", "#F0A500", "#2a4fa8", "#FFD166", "#16A34A"])
                fig2.update_layout(height=350, margin=dict(l=0,r=0,t=10,b=0))
                st.plotly_chart(fig2, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
