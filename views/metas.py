"""
Metas & Projecoes - Acompanhamento de metas gerenciais
3 secoes separadas: VENDAS, LOCACAO, LEADS
Somente admin pode editar. Gerentes/corretores apenas visualizam.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.supabase_client import fetch_vendas, fetch_leads_jetimob, limpar_cache
from utils.auth import is_admin, escape
from utils.config import get_config_int, set_config
from utils.auditoria import registrar
from utils.filtros import aplicar_filtro


# Valores padrao iniciais
META_VGV_PADRAO = 3000000           # R$ 3M
META_VENDAS_PADRAO = 10              # 10 vendas/mes
META_TICKET_PADRAO = 300000          # R$ 300k de ticket medio
META_RECEITA_LOC_PADRAO = 80000      # R$ 80k em receita locacao
META_LOCACOES_PADRAO = 30            # 30 locacoes/mes
META_ALUGUEL_MEDIO_PADRAO = 2500     # R$ 2.500
META_LEADS_PADRAO = 1500             # 1500 leads/mes


def _pct(real, meta):
    return min(real / meta * 100, 100) if meta > 0 else 0


def _status_color(pct_val):
    if pct_val >= 80:
        return "#16A34A", "badge-green", "No ritmo"
    if pct_val >= 50:
        return "#FFB700", "badge-gold", "Atencao"
    return "#DC2626", "badge-red", "Abaixo"


def _barra_progresso(label: str, real_str: str, meta_str: str, pct_val: float):
    """Renderiza uma barra de progresso bonita"""
    color, badge_cls, status_text = _status_color(pct_val)
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:1rem;margin:0.6rem 0;padding:0.8rem 1.2rem;background:white;border-radius:12px;box-shadow:0 2px 8px rgba(28,56,130,0.06);border:1px solid #D1E4F5">
        <div style="min-width:160px;font-size:0.88rem;font-weight:700;color:#033677">{escape(label)}</div>
        <div style="min-width:140px;font-size:0.85rem;color:#1F2937"><strong>{escape(real_str)}</strong> / {escape(meta_str)}</div>
        <div style="flex:1;height:14px;background:#F3F6FA;border-radius:7px;overflow:hidden">
            <div style="width:{pct_val:.0f}%;height:100%;background:{color};border-radius:7px;transition:width 0.5s"></div>
        </div>
        <div style="min-width:50px;text-align:right;font-size:0.85rem;font-weight:800;color:{color}">{pct_val:.0f}%</div>
        <span class="kpi-badge {badge_cls}">{status_text}</span>
    </div>
    """, unsafe_allow_html=True)


def _gauge(titulo: str, valor: float, meta: float, prefix: str = "", cor_principal: str = "#033677"):
    """Renderiza um gauge"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=valor,
        number={"prefix": prefix, "valueformat": ",.0f"},
        delta={"reference": meta, "valueformat": ",.0f", "prefix": prefix},
        gauge={
            "axis": {"range": [0, meta * 1.2 if meta > 0 else 1]},
            "bar": {"color": cor_principal},
            "steps": [
                {"range": [0, meta * 0.5], "color": "#FEE2E2"},
                {"range": [meta * 0.5, meta * 0.8], "color": "#FFDE76"},
                {"range": [meta * 0.8, meta], "color": "#DCFCE7"},
            ],
            "threshold": {"line": {"color": "#FFB700", "width": 4}, "thickness": 0.75, "value": meta}
        }
    ))
    fig.update_layout(height=260, margin=dict(l=20, r=20, t=10, b=10))
    return fig


def render():
    periodo = st.session_state.get("periodo_global", "Este mes")

    st.markdown(f"""
    <div class="nl-header">
        <div class="badge">Metas & Projecoes</div>
        <h1>Acompanhamento de <span>Metas</span></h1>
        <div class="sub">Vendas · Locacao · Leads · Periodo: <strong>{escape(periodo)}</strong></div>
    </div>
    """, unsafe_allow_html=True)

    # Carrega + filtra dados pelo periodo selecionado
    df_vendas_all = fetch_vendas()
    df_leads_all = fetch_leads_jetimob()

    df_vendas = aplicar_filtro(df_vendas_all, periodo, "data_venda")
    df_leads = aplicar_filtro(df_leads_all, periodo, "created_at")

    # Carrega metas salvas
    meta_vgv = get_config_int("meta_vgv", META_VGV_PADRAO)
    meta_vendas = get_config_int("meta_vendas", META_VENDAS_PADRAO)
    meta_ticket = get_config_int("meta_ticket", META_TICKET_PADRAO)
    meta_receita_loc = get_config_int("meta_receita_loc", META_RECEITA_LOC_PADRAO)
    meta_locacoes = get_config_int("meta_locacoes", META_LOCACOES_PADRAO)
    meta_aluguel_medio = get_config_int("meta_aluguel_medio", META_ALUGUEL_MEDIO_PADRAO)
    meta_leads = get_config_int("meta_leads", META_LEADS_PADRAO)

    # Calcula realizado por categoria
    if not df_vendas.empty and "tipo_negocio" in df_vendas.columns:
        df_v = df_vendas[df_vendas["tipo_negocio"] == "venda"]
        df_l = df_vendas[df_vendas["tipo_negocio"] == "aluguel"]
    else:
        df_v = pd.DataFrame()
        df_l = pd.DataFrame()

    # Vendas
    vendas_real = len(df_v)
    vgv_real = df_v["valor"].sum() if not df_v.empty and "valor" in df_v.columns else 0
    ticket_real = vgv_real / vendas_real if vendas_real > 0 else 0

    # Locacao
    locacoes_real = len(df_l)
    receita_loc_real = df_l["valor"].sum() if not df_l.empty and "valor" in df_l.columns else 0
    aluguel_medio_real = receita_loc_real / locacoes_real if locacoes_real > 0 else 0

    # Leads
    leads_real = len(df_leads)

    # =========================================================
    # SECAO 1: VENDAS
    # =========================================================
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon" style="background:#16A34A">💰</div>
        <div>
            <h2>Vendas</h2>
            <p>Metas e progresso da equipe de vendas no periodo selecionado</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if is_admin():
        with st.form("form_metas_vendas"):
            col1, col2, col3 = st.columns(3)
            with col1:
                novo_vgv = st.number_input("Meta VGV (R$)", value=meta_vgv, step=100000, format="%d")
            with col2:
                novo_vendas = st.number_input("Meta Vendas (qtd)", value=meta_vendas, step=1)
            with col3:
                novo_ticket = st.number_input("Meta Ticket Medio (R$)", value=meta_ticket, step=10000, format="%d")
            if st.form_submit_button("Salvar Metas de Vendas", use_container_width=True):
                ok = all([
                    set_config("meta_vgv", novo_vgv),
                    set_config("meta_vendas", novo_vendas),
                    set_config("meta_ticket", novo_ticket),
                ])
                if ok:
                    registrar("alterou_metas_vendas",
                              f"VGV={novo_vgv}, vendas={novo_vendas}, ticket={novo_ticket}")
                    limpar_cache()
                    st.success("Metas de Vendas atualizadas!")
                    st.rerun()
    else:
        st.markdown(f"""
        <div class="kpi-grid" style="grid-template-columns:repeat(3,1fr)">
            <div class="kpi-card green">
                <div class="label">Meta VGV</div>
                <div class="num">R${meta_vgv:,.0f}</div>
            </div>
            <div class="kpi-card azul">
                <div class="label">Meta Vendas</div>
                <div class="num">{meta_vendas}</div>
            </div>
            <div class="kpi-card">
                <div class="label">Meta Ticket Medio</div>
                <div class="num">R${meta_ticket:,.0f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    _barra_progresso("VGV", f"R${vgv_real:,.0f}", f"R${meta_vgv:,.0f}", _pct(vgv_real, meta_vgv))
    _barra_progresso("Vendas Fechadas", str(vendas_real), str(meta_vendas), _pct(vendas_real, meta_vendas))
    _barra_progresso("Ticket Medio", f"R${ticket_real:,.0f}", f"R${meta_ticket:,.0f}", _pct(ticket_real, meta_ticket))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="chart-box"><h3>VGV vs Meta</h3>', unsafe_allow_html=True)
        st.plotly_chart(_gauge("VGV", vgv_real, meta_vgv, "R$", "#16A34A"), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="chart-box"><h3>Vendas vs Meta</h3>', unsafe_allow_html=True)
        st.plotly_chart(_gauge("Vendas", vendas_real, meta_vendas, "", "#033677"), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # =========================================================
    # SECAO 2: LOCACAO
    # =========================================================
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon" style="background:#FFB700">🔑</div>
        <div>
            <h2>Locacao</h2>
            <p>Metas e progresso da equipe de locacao no periodo selecionado</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if is_admin():
        with st.form("form_metas_locacao"):
            col1, col2, col3 = st.columns(3)
            with col1:
                novo_receita_loc = st.number_input("Meta Receita (R$)", value=meta_receita_loc, step=5000, format="%d")
            with col2:
                novo_locacoes = st.number_input("Meta Locacoes (qtd)", value=meta_locacoes, step=1)
            with col3:
                novo_aluguel = st.number_input("Meta Aluguel Medio (R$)", value=meta_aluguel_medio, step=100, format="%d")
            if st.form_submit_button("Salvar Metas de Locacao", use_container_width=True):
                ok = all([
                    set_config("meta_receita_loc", novo_receita_loc),
                    set_config("meta_locacoes", novo_locacoes),
                    set_config("meta_aluguel_medio", novo_aluguel),
                ])
                if ok:
                    registrar("alterou_metas_locacao",
                              f"receita={novo_receita_loc}, locacoes={novo_locacoes}, aluguel={novo_aluguel}")
                    limpar_cache()
                    st.success("Metas de Locacao atualizadas!")
                    st.rerun()
    else:
        st.markdown(f"""
        <div class="kpi-grid" style="grid-template-columns:repeat(3,1fr)">
            <div class="kpi-card">
                <div class="label">Meta Receita</div>
                <div class="num">R${meta_receita_loc:,.0f}</div>
            </div>
            <div class="kpi-card azul">
                <div class="label">Meta Locacoes</div>
                <div class="num">{meta_locacoes}</div>
            </div>
            <div class="kpi-card">
                <div class="label">Meta Aluguel Medio</div>
                <div class="num">R${meta_aluguel_medio:,.0f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    _barra_progresso("Receita Locacao", f"R${receita_loc_real:,.0f}", f"R${meta_receita_loc:,.0f}", _pct(receita_loc_real, meta_receita_loc))
    _barra_progresso("Locacoes Fechadas", str(locacoes_real), str(meta_locacoes), _pct(locacoes_real, meta_locacoes))
    _barra_progresso("Aluguel Medio", f"R${aluguel_medio_real:,.0f}", f"R${meta_aluguel_medio:,.0f}", _pct(aluguel_medio_real, meta_aluguel_medio))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="chart-box"><h3>Receita vs Meta</h3>', unsafe_allow_html=True)
        st.plotly_chart(_gauge("Receita", receita_loc_real, meta_receita_loc, "R$", "#FFB700"), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="chart-box"><h3>Locacoes vs Meta</h3>', unsafe_allow_html=True)
        st.plotly_chart(_gauge("Locacoes", locacoes_real, meta_locacoes, "", "#FFB700"), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # =========================================================
    # SECAO 3: LEADS
    # =========================================================
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon" style="background:#2678BC">📥</div>
        <div>
            <h2>Leads</h2>
            <p>Captacao de novos leads no periodo</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if is_admin():
        with st.form("form_metas_leads"):
            novo_leads = st.number_input("Meta Leads (no periodo)", value=meta_leads, step=100, format="%d")
            if st.form_submit_button("Salvar Meta de Leads", use_container_width=True):
                if set_config("meta_leads", novo_leads):
                    registrar("alterou_metas_leads", f"leads={novo_leads}")
                    limpar_cache()
                    st.success("Meta de Leads atualizada!")
                    st.rerun()
    else:
        st.markdown(f"""
        <div class="kpi-grid" style="grid-template-columns:1fr">
            <div class="kpi-card azul">
                <div class="label">Meta de Leads</div>
                <div class="num">{meta_leads:,}</div>
                <div class="sub">no periodo selecionado</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    _barra_progresso("Leads Recebidos", f"{leads_real:,}", f"{meta_leads:,}", _pct(leads_real, meta_leads))

    st.markdown('<div class="chart-box"><h3>Leads vs Meta</h3>', unsafe_allow_html=True)
    st.plotly_chart(_gauge("Leads", leads_real, meta_leads, "", "#2678BC"), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Footer
    st.markdown("""
    <div class="nl-footer">
        <strong>NL Imoveis</strong> · Painel Estrategico · CRECI 1440 J · Natal/RN<br>
        Metas salvas no Supabase · Acompanhamento em tempo real
    </div>
    """, unsafe_allow_html=True)
