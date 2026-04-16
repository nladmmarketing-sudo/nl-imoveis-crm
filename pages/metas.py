"""
Metas & Projecoes - Acompanhamento de metas gerenciais
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.supabase_client import fetch_vendas, fetch_leads_jetimob


def render():
    st.markdown("""
    <div class="nl-header">
        <div class="badge">Metas & Projecoes</div>
        <h1>Acompanhamento de <span>Metas</span></h1>
        <div class="sub">Definicao e acompanhamento de metas da equipe comercial</div>
    </div>
    """, unsafe_allow_html=True)

    df_vendas = fetch_vendas()
    df_leads = fetch_leads_jetimob()

    # Configuracao de metas (editavel)
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">🎯</div>
        <div>
            <h2>Configurar Metas</h2>
            <p>Defina as metas do periodo para acompanhamento</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        meta_vgv = st.number_input("Meta VGV Vendas (R$)", value=3000000, step=100000, format="%d")
    with col2:
        meta_vendas = st.number_input("Meta Vendas (qtd)", value=10, step=1)
    with col3:
        meta_locacoes = st.number_input("Meta Locacoes (qtd)", value=30, step=1)
    with col4:
        meta_leads = st.number_input("Meta Leads/mes", value=1500, step=100)

    # Calcular realizado
    if not df_vendas.empty and "tipo_negocio" in df_vendas.columns:
        vendas_real = len(df_vendas[df_vendas["tipo_negocio"] == "venda"])
        locacoes_real = len(df_vendas[df_vendas["tipo_negocio"] == "aluguel"])
        vgv_real = df_vendas[df_vendas["tipo_negocio"] == "venda"]["valor"].sum() if "valor" in df_vendas.columns else 0
    else:
        vendas_real = len(df_vendas) if not df_vendas.empty else 0
        locacoes_real = 0
        vgv_real = df_vendas["valor"].sum() if not df_vendas.empty and "valor" in df_vendas.columns else 0

    leads_real = len(df_leads) if not df_leads.empty else 0

    # Progress
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">📈</div>
        <div>
            <h2>Progresso vs Meta</h2>
            <p>Acompanhamento em tempo real</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    def pct(real, meta):
        return min(real / meta * 100, 100) if meta > 0 else 0

    def status_color(pct_val):
        if pct_val >= 80: return "#16A34A", "badge-green", "No ritmo"
        if pct_val >= 50: return "#F0A500", "badge-gold", "Atencao"
        return "#DC2626", "badge-red", "Abaixo"

    metrics = [
        ("VGV Vendas", f"R${vgv_real:,.0f}", f"R${meta_vgv:,.0f}", pct(vgv_real, meta_vgv)),
        ("Vendas Fechadas", str(vendas_real), str(meta_vendas), pct(vendas_real, meta_vendas)),
        ("Locacoes Fechadas", str(locacoes_real), str(meta_locacoes), pct(locacoes_real, meta_locacoes)),
        ("Leads Gerados", f"{leads_real:,}", f"{meta_leads:,}", pct(leads_real, meta_leads)),
    ]

    for label, real, meta, pct_val in metrics:
        color, badge_cls, status_text = status_color(pct_val)
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:1rem;margin:0.6rem 0;padding:0.8rem 1.2rem;background:white;border-radius:12px;box-shadow:0 2px 8px rgba(28,56,130,0.06);border:1px solid #D1E4F5">
            <div style="min-width:160px;font-size:0.88rem;font-weight:700;color:#1C3882">{label}</div>
            <div style="min-width:120px;font-size:0.85rem;color:#1F2937"><strong>{real}</strong> / {meta}</div>
            <div style="flex:1;height:14px;background:#EAF3FB;border-radius:7px;overflow:hidden">
                <div style="width:{pct_val:.0f}%;height:100%;background:{color};border-radius:7px;transition:width 0.5s"></div>
            </div>
            <div style="min-width:50px;text-align:right;font-size:0.85rem;font-weight:800;color:{color}">{pct_val:.0f}%</div>
            <span class="kpi-badge {badge_cls}">{status_text}</span>
        </div>
        """, unsafe_allow_html=True)

    # Gauge charts
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="chart-box"><h3>VGV vs Meta</h3>', unsafe_allow_html=True)
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=vgv_real,
            number={"prefix": "R$", "valueformat": ",.0f"},
            delta={"reference": meta_vgv, "valueformat": ",.0f", "prefix": "R$"},
            gauge={
                "axis": {"range": [0, meta_vgv * 1.2]},
                "bar": {"color": "#1C3882"},
                "steps": [
                    {"range": [0, meta_vgv * 0.5], "color": "#FEE2E2"},
                    {"range": [meta_vgv * 0.5, meta_vgv * 0.8], "color": "#FEF3C7"},
                    {"range": [meta_vgv * 0.8, meta_vgv], "color": "#DCFCE7"},
                ],
                "threshold": {"line": {"color": "#F0A500", "width": 4}, "thickness": 0.75, "value": meta_vgv}
            }
        ))
        fig.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="chart-box"><h3>Vendas vs Meta</h3>', unsafe_allow_html=True)
        fig2 = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=vendas_real,
            delta={"reference": meta_vendas},
            gauge={
                "axis": {"range": [0, meta_vendas * 1.5]},
                "bar": {"color": "#16A34A"},
                "steps": [
                    {"range": [0, meta_vendas * 0.5], "color": "#FEE2E2"},
                    {"range": [meta_vendas * 0.5, meta_vendas * 0.8], "color": "#FEF3C7"},
                    {"range": [meta_vendas * 0.8, meta_vendas], "color": "#DCFCE7"},
                ],
                "threshold": {"line": {"color": "#F0A500", "width": 4}, "thickness": 0.75, "value": meta_vendas}
            }
        ))
        fig2.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Footer
    st.markdown("""
    <div class="nl-footer">
        <strong>NL Imoveis</strong> · Painel Estrategico · CRECI 1440 J · Natal/RN<br>
        Metas configuraveis pelo gerente · Dados em tempo real
    </div>
    """, unsafe_allow_html=True)
