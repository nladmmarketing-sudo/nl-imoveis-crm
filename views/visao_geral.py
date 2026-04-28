"""
Visao Geral v2.0 — KPIs com sparklines, trends e alertas inteligentes.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.supabase_client import fetch_leads_jetimob, fetch_vendas
from utils.auth import (
    escape, is_corretor, filtrar_por_perfil, get_usuario_atual, pode_ver_tudo
)
from utils.filtros import aplicar_filtro, aplicar_filtro_periodo_anterior, periodo_anterior
from utils.components import (
    kpi_card_v2, alert_box, calc_trend, sparkline_pts, render_kpi_grid
)


def render():
    user = get_usuario_atual()
    if not user:
        st.warning("Sessao expirada. Faca login novamente.")
        st.stop()
    if is_corretor() and not (user.get("corretor_nome_jetimob") or "").strip():
        st.error("Seu cadastro nao tem 'nome no Jetimob' configurado. Contate o admin.")
        st.stop()

    periodo = st.session_state.get("periodo_global", "Este mes")
    per_ant = periodo_anterior(periodo)

    st.markdown(f"""
    <div class="nl-header">
        <div class="badge">Painel Estrategico</div>
        <h1>NL Imoveis — <span>Visao Geral</span></h1>
        <div class="sub">CRECI 1440 J · Natal/RN · Periodo: <strong>{escape(periodo)}</strong></div>
    </div>
    """, unsafe_allow_html=True)

    # =========================================================
    # Carrega dados (RBAC + paginado)
    # =========================================================
    df_leads_all = filtrar_por_perfil(fetch_leads_jetimob(), "corretor")
    df_vendas_all = filtrar_por_perfil(fetch_vendas(), "corretor")

    # Periodo atual
    df_leads = aplicar_filtro(df_leads_all, periodo, "created_at")
    df_vendas = aplicar_filtro(df_vendas_all, periodo, "data_venda")

    # Periodo anterior (pra comparativo)
    df_leads_ant = aplicar_filtro_periodo_anterior(df_leads_all, periodo, "created_at")
    df_vendas_ant = aplicar_filtro_periodo_anterior(df_vendas_all, periodo, "data_venda")

    # Splits venda/locacao
    if not df_vendas.empty and "tipo_negocio" in df_vendas.columns:
        df_v = df_vendas[df_vendas["tipo_negocio"] == "venda"]
        df_l = df_vendas[df_vendas["tipo_negocio"] == "aluguel"]
    else:
        df_v = pd.DataFrame()
        df_l = pd.DataFrame()

    if not df_vendas_ant.empty and "tipo_negocio" in df_vendas_ant.columns:
        df_v_ant = df_vendas_ant[df_vendas_ant["tipo_negocio"] == "venda"]
        df_l_ant = df_vendas_ant[df_vendas_ant["tipo_negocio"] == "aluguel"]
    else:
        df_v_ant = pd.DataFrame()
        df_l_ant = pd.DataFrame()

    # Metricas
    total_leads = len(df_leads)
    total_vendas = len(df_v)
    total_loc = len(df_l)
    vgv = float(df_v["valor"].sum()) if not df_v.empty and "valor" in df_v.columns else 0.0
    receita_loc = float(df_l["valor"].sum()) if not df_l.empty and "valor" in df_l.columns else 0.0
    ticket = vgv / total_vendas if total_vendas else 0
    taxa_conv = ((total_vendas + total_loc) / total_leads * 100) if total_leads > 0 else 0

    # Anteriores
    leads_ant = len(df_leads_ant)
    vendas_ant = len(df_v_ant)
    loc_ant = len(df_l_ant)
    vgv_ant = float(df_v_ant["valor"].sum()) if not df_v_ant.empty and "valor" in df_v_ant.columns else 0.0
    conv_ant = ((vendas_ant + loc_ant) / leads_ant * 100) if leads_ant > 0 else 0

    # Trends
    t_leads, d_leads = calc_trend(total_leads, leads_ant)
    t_vendas, d_vendas = calc_trend(total_vendas, vendas_ant)
    t_loc, d_loc = calc_trend(total_loc, loc_ant)
    t_vgv, d_vgv = calc_trend(vgv, vgv_ant)
    t_conv, d_conv = calc_trend(taxa_conv, conv_ant)

    # Sparklines (ultimos 30 dias)
    spark_leads = sparkline_pts(df_leads_all, "created_at", dias=30)
    spark_vendas = sparkline_pts(df_vendas_all[df_vendas_all["tipo_negocio"] == "venda"]
                                  if "tipo_negocio" in df_vendas_all.columns else df_vendas_all,
                                  "data_venda", dias=30)
    spark_loc = sparkline_pts(df_vendas_all[df_vendas_all["tipo_negocio"] == "aluguel"]
                                if "tipo_negocio" in df_vendas_all.columns else df_vendas_all,
                                "data_venda", dias=30)

    # =========================================================
    # ALERTAS INTELIGENTES
    # =========================================================
    alertas = []
    if vgv > vgv_ant * 1.15 and vgv_ant > 0:
        alertas.append(alert_box(
            "Excelente desempenho de vendas!",
            f"VGV cresceu {((vgv/vgv_ant - 1)*100):.0f}% comparado ao periodo anterior ({per_ant}).",
            tipo="green", icon="🚀"
        ))
    if vgv_ant > 0 and vgv < vgv_ant * 0.85:
        alertas.append(alert_box(
            "Atencao: VGV em queda",
            f"VGV caiu {((1 - vgv/vgv_ant)*100):.0f}% vs {per_ant}. Verificar ritmo das vendas.",
            tipo="red", icon="⚠️"
        ))
    if taxa_conv < 1 and total_leads > 50:
        alertas.append(alert_box(
            "Conversao abaixo do ideal",
            f"Taxa de conversao em {taxa_conv:.2f}% (meta: 1.5%+). Investigar qualidade dos canais.",
            tipo="orange", icon="📉"
        ))
    if total_leads > leads_ant * 1.2 and leads_ant > 0:
        alertas.append(alert_box(
            "Volume de leads em alta",
            f"Recebimento de leads cresceu {((total_leads/leads_ant - 1)*100):.0f}% versus {per_ant}.",
            tipo="azul", icon="📥"
        ))

    for a in alertas:
        st.markdown(a, unsafe_allow_html=True)

    # =========================================================
    # KPIs V2.0 (com sparklines + trends)
    # =========================================================
    label_leads = "Meus Leads" if is_corretor() else "Total de Leads"
    label_vendas = "Minhas Vendas" if is_corretor() else "Vendas Fechadas"
    label_loc = "Minhas Locacoes" if is_corretor() else "Locacoes Fechadas"
    label_vgv = "Meu VGV" if is_corretor() else "VGV de Vendas"

    cor_conv = "green" if taxa_conv >= 1.5 else ("dourado" if taxa_conv >= 1 else "red")
    cards = [
        kpi_card_v2(label_vgv, f"R${vgv:,.0f}",
                    f"vs R${vgv_ant:,.0f} em {per_ant}",
                    icon="💰", color="green",
                    trend=t_vgv, trend_dir=d_vgv,
                    sparkline_pts_data=spark_vendas),
        kpi_card_v2(label_vendas, str(total_vendas),
                    f"vs {vendas_ant} em {per_ant} · ticket R${ticket:,.0f}",
                    icon="🏠", color="azul",
                    trend=t_vendas, trend_dir=d_vendas,
                    sparkline_pts_data=spark_vendas),
        kpi_card_v2(label_loc, str(total_loc),
                    f"R${receita_loc:,.0f} em receita",
                    icon="🔑", color="dourado",
                    trend=t_loc, trend_dir=d_loc,
                    sparkline_pts_data=spark_loc),
        kpi_card_v2(label_leads, f"{total_leads:,}",
                    f"vs {leads_ant:,} em {per_ant}",
                    icon="📥", color="purple",
                    trend=t_leads, trend_dir=d_leads,
                    sparkline_pts_data=spark_leads),
        kpi_card_v2("Taxa Conversao", f"{taxa_conv:.2f}%",
                    f"vs {conv_ant:.2f}% anterior · meta 1,5%",
                    icon="🎯", color=cor_conv,
                    trend=t_conv, trend_dir=d_conv),
    ]
    st.markdown(render_kpi_grid(cards), unsafe_allow_html=True)

    # =========================================================
    # Charts
    # =========================================================
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

    # =========================================================
    # Ranking de corretores (fechamentos do periodo)
    # =========================================================
    if pode_ver_tudo():
        st.markdown("""
        <div class="section-hdr">
            <div class="section-icon">🏆</div>
            <div>
                <h2>Ranking de Corretores</h2>
                <p>Performance de fechamentos no periodo</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        ranking_html = ""
        # Tenta primeiro por leads atribuidos (campo corretor)
        if not df_leads.empty and "corretor" in df_leads.columns:
            corretor_data = df_leads[df_leads["corretor"].notna() & (df_leads["corretor"] != "")]
            if not corretor_data.empty:
                ranking = corretor_data["corretor"].value_counts().head(10).reset_index()
                ranking.columns = ["Corretor", "Leads"]
                max_leads = ranking["Leads"].max()
                for i, row in ranking.iterrows():
                    pos = i + 1
                    rank_class = f"rank-{pos}" if pos <= 3 else "rank-other"
                    pct = row["Leads"] / max_leads * 100
                    ranking_html += f"""
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

        # Fallback: ranking por VENDAS/FECHAMENTOS
        if not ranking_html and not df_vendas.empty and "corretor" in df_vendas.columns:
            v_data = df_vendas[df_vendas["corretor"].notna() & (df_vendas["corretor"] != "")]
            if not v_data.empty:
                ranking = v_data.groupby("corretor").agg(
                    qtd=("nome_cliente", "count"),
                    total=("valor", "sum"),
                ).reset_index().sort_values("total", ascending=False).head(10)
                max_v = ranking["total"].max() if len(ranking) > 0 else 1
                for i, (_, row) in enumerate(ranking.iterrows(), start=1):
                    rank_class = f"rank-{i}" if i <= 3 else "rank-other"
                    pct = row["total"] / max_v * 100 if max_v > 0 else 0
                    ranking_html += f"""
                    <div class="ranking-item">
                        <div class="rank-num {rank_class}">{i}°</div>
                        <div style="flex:1">
                            <div class="rank-name">{escape(row['corretor'])}</div>
                            <div class="rank-sub">{int(row['qtd'])} fechamento(s)</div>
                            <div style="height:8px;background:#F3F6FA;border-radius:4px;overflow:hidden;margin-top:4px">
                                <div style="width:{pct:.0f}%;height:100%;background:{'#FFB700' if i == 1 else '#033677' if i <= 3 else '#9CA3AF'};border-radius:4px"></div>
                            </div>
                        </div>
                        <div class="rank-value">R${row['total']:,.0f}</div>
                    </div>
                    """

        if ranking_html:
            st.markdown(ranking_html, unsafe_allow_html=True)
        else:
            st.info("Sem fechamentos ou leads atribuidos a corretor no periodo selecionado.")

    # =========================================================
    # Recent leads (PII reduzida)
    # =========================================================
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">📋</div>
        <div>
            <h2>Ultimos Leads Recebidos</h2>
            <p>Nome, email e codigo do imovel · Para detalhes consulte o Jetimob</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not df_leads.empty:
        cols_show = ["created_at", "nome", "email", "codigo_imovel", "origem", "corretor", "status"]
        available = [c for c in cols_show if c in df_leads.columns]
        recent = df_leads.head(20)[available].copy()
        rename = {"created_at": "Data", "nome": "Nome", "email": "Email",
                  "codigo_imovel": "Codigo Imovel", "origem": "Origem",
                  "corretor": "Corretor", "status": "Status"}
        recent = recent.rename(columns={k: v for k, v in rename.items() if k in recent.columns})

        busca = st.text_input("🔍 Buscar (nome, email, codigo, corretor)",
                               placeholder="Digite pra filtrar...", key="busca_visao")
        if busca:
            mask = pd.Series([False] * len(recent))
            for col in recent.columns:
                mask |= recent[col].astype(str).str.contains(busca, case=False, na=False)
            recent = recent[mask]

        st.dataframe(recent, use_container_width=True, hide_index=True)

        csv = recent.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Exportar (CSV)",
            data=csv,
            file_name=f"leads_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            key="dl_visao",
        )

    # Footer
    st.markdown("""
    <div class="nl-footer">
        <strong>NL Imoveis</strong> · Painel Estrategico · CRECI 1440 J · Natal/RN<br>
        Dados em tempo real via Supabase + Jetimob CRM
    </div>
    """, unsafe_allow_html=True)
