"""
Equipe Vendas - Performance da equipe de vendas
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.supabase_client import fetch_leads_jetimob, fetch_vendas
from utils.auth import escape, filtrar_por_perfil, get_usuario_atual, is_corretor
from utils.filtros import aplicar_filtro


def render():
    # Guard de sessao + mapeamento (defesa em profundidade — app.py ja checa autenticacao)
    user = get_usuario_atual()
    if not user:
        st.warning("Sessao expirada. Faca login novamente.")
        st.stop()
    if is_corretor() and not (user.get("corretor_nome_jetimob") or "").strip():
        st.error("Seu cadastro nao tem 'nome no Jetimob' configurado. Contate o admin.")
        st.stop()

    periodo = st.session_state.get("periodo_global", "Ultimos 30 dias")

    st.markdown(f"""
    <div class="nl-header">
        <div class="badge">Equipe de Vendas</div>
        <h1>Performance <span>Vendas</span></h1>
        <div class="sub">Leads, funil e fechamentos · Periodo: <strong>{escape(periodo)}</strong></div>
    </div>
    """, unsafe_allow_html=True)

    # Filtra por perfil ANTES de qualquer agregacao (corretor so ve os proprios)
    df_vendas_all = filtrar_por_perfil(fetch_vendas(), "corretor")
    df_leads_all = filtrar_por_perfil(fetch_leads_jetimob(), "corretor")

    # Aplica filtro de periodo
    df_vendas = aplicar_filtro(df_vendas_all, periodo, "data_venda")
    df_leads = aplicar_filtro(df_leads_all, periodo, "created_at")

    # Filtrar vendas (tipo_negocio = venda)
    if not df_vendas.empty and "tipo_negocio" in df_vendas.columns:
        df_v = df_vendas[df_vendas["tipo_negocio"] == "venda"].copy()
    else:
        df_v = df_vendas.copy() if not df_vendas.empty else pd.DataFrame()

    total_vendas = len(df_v)
    vgv = df_v["valor"].sum() if not df_v.empty and "valor" in df_v.columns else 0
    ticket = vgv / total_vendas if total_vendas > 0 else 0

    # KPIs Vendas
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="label">Vendas Fechadas</div>
            <div class="num">{total_vendas}</div>
            <div class="sub">{escape(periodo)}</div>
        </div>
        <div class="kpi-card green">
            <div class="label">VGV Vendas</div>
            <div class="num" style="color:#16A34A">R${vgv:,.0f}</div>
            <div class="sub">Volume Geral de Vendas</div>
        </div>
        <div class="kpi-card azul">
            <div class="label">Ticket Medio</div>
            <div class="num">R${ticket:,.0f}</div>
            <div class="sub">por venda fechada</div>
        </div>
        <div class="kpi-card">
            <div class="label">Leads no periodo</div>
            <div class="num">{len(df_leads):,}</div>
            <div class="sub">Jetimob CRM</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Ranking Corretores por Vendas
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">🏆</div>
        <div>
            <h2>Ranking Corretores — Vendas</h2>
            <p>Performance individual por volume e VGV no periodo</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not df_v.empty and "corretor" in df_v.columns:
        perf = df_v.groupby("corretor").agg(
            vendas=("id", "count"),
            vgv=("valor", "sum")
        ).reset_index().sort_values("vgv", ascending=False)

        max_vgv = perf["vgv"].max() if not perf.empty else 1

        html = ""
        for i, (_, row) in enumerate(perf.iterrows(), start=1):
            rank_class = f"rank-{i}" if i <= 3 else "rank-other"
            pct = row["vgv"] / max_vgv * 100 if max_vgv > 0 else 0
            html += f"""
            <div class="ranking-item">
                <div class="rank-num {rank_class}">{i}°</div>
                <div style="flex:1">
                    <div class="rank-name">{escape(row['corretor'])}</div>
                    <div class="rank-sub">{row['vendas']} venda(s)</div>
                    <div style="height:8px;background:#EAF3FB;border-radius:4px;overflow:hidden;margin-top:4px">
                        <div style="width:{pct:.0f}%;height:100%;background:{'#F0A500' if i == 1 else '#1C3882'};border-radius:4px"></div>
                    </div>
                </div>
                <div class="rank-value">R${row['vgv']:,.0f}</div>
            </div>
            """
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("Nenhuma venda no periodo selecionado.")

    # Tabela de vendas com busca + export
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">📋</div>
        <div>
            <h2>Detalhamento de Vendas</h2>
            <p>Vendas registradas no periodo</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not df_v.empty:
        cols = ["data_venda", "nome_cliente", "tipo_imovel", "codigo_imovel", "bairro", "valor", "corretor", "origem_lead"]
        available = [c for c in cols if c in df_v.columns]
        display = df_v[available].copy()
        rename = {"data_venda": "Data", "nome_cliente": "Cliente", "tipo_imovel": "Imovel",
                  "codigo_imovel": "Codigo", "bairro": "Bairro", "valor": "Valor (R$)",
                  "corretor": "Corretor", "origem_lead": "Origem"}
        display = display.rename(columns={k: v for k, v in rename.items() if k in display.columns})

        busca = st.text_input("🔍 Buscar (cliente, codigo, bairro, corretor)", placeholder="Digite pra filtrar...", key="busca_vendas")
        if busca:
            mask = pd.Series([False] * len(display))
            for col in display.columns:
                mask |= display[col].astype(str).str.contains(busca, case=False, na=False)
            display = display[mask]

        st.dataframe(display, use_container_width=True, hide_index=True)

        csv = display.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Exportar (CSV)",
            data=csv,
            file_name=f"vendas_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            key="dl_vendas"
        )
    else:
        st.info("Nenhuma venda registrada no periodo.")

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="chart-box"><h3>Vendas por Bairro</h3>', unsafe_allow_html=True)
        if not df_v.empty and "bairro" in df_v.columns:
            bairro_data = df_v[df_v["bairro"].notna()]
            if not bairro_data.empty:
                bc = bairro_data["bairro"].value_counts().head(10).reset_index()
                bc.columns = ["Bairro", "Vendas"]
                fig = px.bar(bc, x="Vendas", y="Bairro", orientation="h", color_discrete_sequence=["#1C3882"])
                fig.update_layout(height=350, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(autorange="reversed"),
                                  plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="chart-box"><h3>Vendas por Origem</h3>', unsafe_allow_html=True)
        if not df_v.empty and "origem_lead" in df_v.columns:
            orig_data = df_v[df_v["origem_lead"].notna()]
            if not orig_data.empty:
                oc = orig_data["origem_lead"].value_counts().reset_index()
                oc.columns = ["Origem", "Vendas"]
                fig2 = px.pie(oc, values="Vendas", names="Origem", hole=0.4,
                              color_discrete_sequence=["#1C3882", "#F0A500", "#2a4fa8", "#FFD166", "#16A34A"])
                fig2.update_layout(height=350, margin=dict(l=0,r=0,t=10,b=0))
                st.plotly_chart(fig2, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
