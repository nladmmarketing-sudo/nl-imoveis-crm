"""
Visao Geral - KPIs estrategicos e resumo executivo
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.supabase_client import fetch_leads_jetimob, fetch_vendas
from utils.auth import escape, is_admin, is_corretor, filtrar_por_perfil, get_usuario_atual, pode_ver_tudo
from utils.filtros import aplicar_filtro


def render():
    # Guard de sessao + mapeamento (defesa em profundidade)
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
        <div class="badge">Painel Estrategico</div>
        <h1>NL Imoveis — <span>Visao Geral</span></h1>
        <div class="sub">CRECI 1440 J · Natal/RN · Periodo: <strong>{escape(periodo)}</strong></div>
    </div>
    """, unsafe_allow_html=True)

    # Filtra por perfil ANTES de qualquer agregacao
    df_leads_all = filtrar_por_perfil(fetch_leads_jetimob(), "corretor")
    df_vendas_all = filtrar_por_perfil(fetch_vendas(), "corretor")

    df_leads = aplicar_filtro(df_leads_all, periodo, "created_at")
    df_vendas = aplicar_filtro(df_vendas_all, periodo, "data_venda")

    total_leads = len(df_leads)
    total_vendas = len(df_vendas)

    vgv = df_vendas["valor"].sum() if not df_vendas.empty and "valor" in df_vendas.columns else 0
    ticket_medio = vgv / total_vendas if total_vendas > 0 else 0
    taxa_conversao = (total_vendas / total_leads * 100) if total_leads > 0 else 0

    # Labels dinamicos: corretor ve "Meu/Minhas", outros perfis ve agregado
    label_leads = "Meus Leads" if is_corretor() else "Total de Leads"
    label_negocios = "Minhas Vendas" if is_corretor() else "Negocios Fechados"
    label_vgv = "Meu VGV" if is_corretor() else "VGV Total"

    # KPIs
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="label">{label_leads}</div>
            <div class="num">{total_leads:,}</div>
            <div class="sub">Jetimob CRM · {escape(periodo)}</div>
        </div>
        <div class="kpi-card azul">
            <div class="label">{label_negocios}</div>
            <div class="num">{total_vendas}</div>
            <div class="sub">Vendas + Locacoes</div>
        </div>
        <div class="kpi-card green">
            <div class="label">{label_vgv}</div>
            <div class="num" style="color:#16A34A">R${vgv:,.0f}</div>
            <div class="sub">Ticket medio: R${ticket_medio:,.0f}</div>
        </div>
        <div class="kpi-card {'green' if taxa_conversao > 1 else 'red'}">
            <div class="label">Taxa de Conversao</div>
            <div class="num" style="color:{'#16A34A' if taxa_conversao > 1 else '#DC2626'}">{taxa_conversao:.2f}%</div>
            <div class="sub">Lead → Negocio fechado</div>
            <span class="kpi-badge {'badge-green' if taxa_conversao > 1 else 'badge-red'}">{'Saudavel' if taxa_conversao > 1 else 'Abaixo do ideal'}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="chart-box"><h3>Leads ao Longo do Tempo</h3>', unsafe_allow_html=True)
        if not df_leads.empty and "created_at" in df_leads.columns:
            df_leads_copy = df_leads.copy()
            df_leads_copy["data"] = pd.to_datetime(df_leads_copy["created_at"], errors="coerce").dt.date
            timeline = df_leads_copy.dropna(subset=["data"]).groupby("data").size().reset_index(name="Leads")
            if not timeline.empty:
                fig = px.area(timeline, x="data", y="Leads", color_discrete_sequence=["#033677"])
                fig.update_layout(
                    height=320, margin=dict(l=0, r=0, t=10, b=0),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    xaxis_title="", yaxis_title="Novos Leads"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem dados no periodo.")
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
                fig2 = px.bar(oc, x="Leads", y="Origem", orientation="h", color_discrete_sequence=["#FFB700"])
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

    # Ranking Corretores — apenas para perfis que veem todos os corretores
    if pode_ver_tudo():
        st.markdown("""
        <div class="section-hdr">
            <div class="section-icon">🏆</div>
            <div>
                <h2>Ranking de Corretores — Volume de Leads</h2>
                <p>Distribuicao de leads por corretor no periodo</p>
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
                            <div class="rank-name">{escape(row['Corretor'])}</div>
                            <div style="height:8px;background:#F3F6FA;border-radius:4px;overflow:hidden;margin-top:4px">
                                <div style="width:{pct:.0f}%;height:100%;background:{'#FFB700' if pos == 1 else '#033677' if pos <= 3 else '#9CA3AF'};border-radius:4px"></div>
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

    # Recent leads (PII reduzida)
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">📋</div>
        <div>
            <h2>Ultimos Leads Recebidos</h2>
            <p>Nome, email e codigo do imovel · Para telefone/detalhes, consulte o Jetimob CRM</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not df_leads.empty:
        # PII: mostrar apenas nome, email, codigo_imovel, origem, corretor, status
        cols_show = ["created_at", "nome", "email", "codigo_imovel", "origem", "corretor", "status"]
        available = [c for c in cols_show if c in df_leads.columns]
        recent = df_leads.head(20)[available].copy()
        rename = {
            "created_at": "Data",
            "nome": "Nome",
            "email": "Email",
            "codigo_imovel": "Codigo Imovel",
            "origem": "Origem",
            "corretor": "Corretor",
            "status": "Status",
        }
        recent = recent.rename(columns={k: v for k, v in rename.items() if k in recent.columns})

        # Busca
        busca = st.text_input("🔍 Buscar (nome, email, codigo, corretor)", placeholder="Digite pra filtrar...", key="busca_visao")
        if busca:
            mask = pd.Series([False] * len(recent))
            for col in recent.columns:
                mask |= recent[col].astype(str).str.contains(busca, case=False, na=False)
            recent = recent[mask]

        st.dataframe(recent, use_container_width=True, hide_index=True)

        # Export CSV
        csv = recent.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Exportar leads (CSV)",
            data=csv,
            file_name=f"leads_recentes_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )

        st.caption(f"ℹ️ Para ver telefones e historico completo de cada lead, acesse o Jetimob CRM.")

    # Footer
    st.markdown("""
    <div class="nl-footer">
        <strong>NL Imoveis</strong> · Painel Estrategico · CRECI 1440 J · Natal/RN<br>
        Dados em tempo real via Supabase + Jetimob CRM
    </div>
    """, unsafe_allow_html=True)
