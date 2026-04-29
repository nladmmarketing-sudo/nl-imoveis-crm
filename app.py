"""
Painel Estrategico - NL Imoveis
Dashboard gerencial para acompanhamento de vendas, locacao e performance
"""
import base64
from pathlib import Path

import streamlit as st
from PIL import Image
from utils.auth import (
    usuario_logado, render_login, get_usuario_atual,
    is_admin, is_gerente, logout, escape
)
from utils.supabase_client import limpar_cache
from utils.filtros import seletor_periodo

_LOGO_PATH = Path(__file__).parent / "assets" / "brand" / "logo" / "nl-logo-principal.png"

st.set_page_config(
    page_title="NL Imoveis - Painel Estrategico",
    page_icon=Image.open(_LOGO_PATH),
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_data(show_spinner=False)
def _font_data_url(filename: str, mime: str) -> str:
    path = Path(__file__).parent / "assets" / "brand" / "fonts" / filename
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


_FONT_GEORAMA_REGULAR = _font_data_url("Georama-Regular.ttf", "font/ttf")
_FONT_GEORAMA_MEDIUM = _font_data_url("Georama-Medium.woff2", "font/woff2")
_FONT_MULTA_PECUNIA = _font_data_url("MultaPecunia.woff2", "font/woff2")


@st.cache_data(show_spinner=False)
def _logo_data_url(filename: str) -> str:
    path = Path(__file__).parent / "assets" / "brand" / "logo" / filename
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


_LOGO_PRINCIPAL_URL = _logo_data_url("nl-logo-principal.png")

# ---- Verificar autenticacao ANTES de tudo ----
if not usuario_logado():
    render_login()
    st.stop()

# CSS NL Imoveis - paleta oficial (Manual da Marca 28/01/2025)
st.markdown(f"""
<style>
    @font-face {{
        font-family: 'Georama';
        src: url('{_FONT_GEORAMA_REGULAR}') format('truetype');
        font-weight: 400;
        font-style: normal;
        font-display: swap;
    }}
    @font-face {{
        font-family: 'Georama';
        src: url('{_FONT_GEORAMA_MEDIUM}') format('woff2');
        font-weight: 500 800;
        font-style: normal;
        font-display: swap;
    }}
    @font-face {{
        font-family: 'MultaPecunia';
        src: url('{_FONT_MULTA_PECUNIA}') format('woff2');
        font-weight: 400;
        font-style: normal;
        font-display: swap;
    }}

    :root {{
        /* Paleta oficial NL Imoveis */
        --nl-azul-noturno: #033677;
        --nl-ouro-vivo: #FFB700;
        --nl-ceu-claro: #F3F6FA;
        --nl-sol-dourado: #FFDE76;
        --nl-azul-horizonte: #2678BC;
        --nl-azul-profundo: #001833;
        --nl-terra-fertil: #9B5400;

        /* Aliases compativeis com o CSS existente */
        --azul: var(--nl-azul-noturno);
        --azul-light: var(--nl-azul-horizonte);
        --dourado: var(--nl-ouro-vivo);
        --dourado-light: var(--nl-sol-dourado);
        --bg: var(--nl-ceu-claro);
        --green: #16A34A;
        --red: #DC2626;
        --orange: #EA580C;
        --gray: #6B7280;
        --border: #D1E4F5;
    }}

    .main .block-container {{ padding-top: 1rem; max-width: 1200px; }}
    html, body, [class*="css"], [class*="st-"],
    .stMarkdown, .stText, button, input, textarea, select {{
        font-family: 'Georama', -apple-system, 'Segoe UI', sans-serif;
    }}
    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Georama', -apple-system, 'Segoe UI', sans-serif;
        font-weight: 700;
    }}
</style>
""", unsafe_allow_html=True)

# CSS v2.0 — NL Imoveis Design System
st.markdown("""
<style>
    /* ═══════════════════════════════════════════════════
       LAYOUT BASE
    ═══════════════════════════════════════════════════ */
    .main .block-container { padding-top: 1.2rem; max-width: 1240px; }

    /* ═══════════════════════════════════════════════════
       HEADER v2.0 — gradiente profundo com reflexo ouro
    ═══════════════════════════════════════════════════ */
    .nl-header {
        background: linear-gradient(140deg, #033677 0%, #012B61 55%, #001833 100%);
        padding: 2rem 2.5rem 2rem 2.5rem;
        border-radius: 20px;
        margin-bottom: 1.75rem;
        color: white;
        position: relative;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(3,54,119,0.28), 0 2px 8px rgba(3,54,119,0.15);
    }
    /* Circulo decorativo superior-direito */
    .nl-header::before {
        content: '';
        position: absolute;
        top: -80px; right: -80px;
        width: 280px; height: 280px;
        background: radial-gradient(circle, rgba(255,183,0,0.12) 0%, transparent 70%);
        border-radius: 50%;
        pointer-events: none;
    }
    /* Linha dourada na base */
    .nl-header::after {
        content: '';
        position: absolute;
        bottom: 0; left: 2.5rem; right: 2.5rem;
        height: 2px;
        background: linear-gradient(90deg, var(--dourado) 0%, transparent 100%);
        opacity: 0.4;
        pointer-events: none;
    }
    .nl-header .badge {
        display: inline-block;
        background: linear-gradient(90deg, var(--dourado) 0%, #FFD040 100%);
        color: var(--azul);
        padding: 0.22rem 0.85rem;
        border-radius: 50px;
        font-size: 0.68rem;
        font-weight: 800;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        margin-bottom: 0.85rem;
        box-shadow: 0 2px 8px rgba(255,183,0,0.35);
    }
    .nl-header h1 {
        color: white;
        margin: 0;
        font-size: 2.1rem;
        font-weight: 800;
        line-height: 1.1;
        letter-spacing: -0.5px;
    }
    .nl-header h1 span { color: var(--dourado); }
    .nl-header .sub {
        color: rgba(255,255,255,0.6);
        font-size: 0.88rem;
        margin-top: 0.45rem;
    }
    .nl-header .sub strong { color: rgba(255,255,255,0.9); }

    /* ═══════════════════════════════════════════════════
       KPI CARDS v2.0 — glassmorphism suave + acento gradiente
    ═══════════════════════════════════════════════════ */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-bottom: 1.75rem;
    }
    .kpi-card {
        background: linear-gradient(145deg, #ffffff 0%, #f7faff 100%);
        border-radius: 18px;
        padding: 1.4rem 1.5rem 1.3rem 1.5rem;
        box-shadow: 0 4px 20px rgba(3,54,119,0.09), 0 1px 4px rgba(3,54,119,0.06);
        border: 1px solid rgba(209,228,245,0.7);
        position: relative;
        overflow: hidden;
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 28px rgba(3,54,119,0.15), 0 2px 8px rgba(3,54,119,0.08);
    }
    /* Acento top — cor por tipo */
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 4px;
        background: linear-gradient(90deg, var(--dourado) 0%, #FFD040 100%);
        border-radius: 18px 18px 0 0;
    }
    .kpi-card.azul::before {
        background: linear-gradient(90deg, #033677 0%, #2678BC 100%);
    }
    .kpi-card.green::before {
        background: linear-gradient(90deg, #16A34A 0%, #22C55E 100%);
    }
    .kpi-card.red::before {
        background: linear-gradient(90deg, #DC2626 0%, #EF4444 100%);
    }
    /* Circulo decorativo canto direito */
    .kpi-card::after {
        content: '';
        position: absolute;
        bottom: -20px; right: -20px;
        width: 80px; height: 80px;
        background: rgba(3,54,119,0.04);
        border-radius: 50%;
        pointer-events: none;
    }
    .kpi-card .label {
        font-size: 0.69rem;
        text-transform: uppercase;
        letter-spacing: 0.9px;
        color: #6B7280;
        font-weight: 700;
    }
    .kpi-card .num {
        font-size: 2.1rem;
        font-weight: 800;
        color: var(--azul);
        line-height: 1;
        margin: 0.5rem 0 0.3rem;
        letter-spacing: -1px;
    }
    .kpi-card .sub { font-size: 0.76rem; color: #9CA3AF; }
    .kpi-card .num.highlight { color: var(--dourado); }

    /* Badges semânticos */
    .kpi-badge {
        display: inline-block;
        padding: 0.18rem 0.6rem;
        border-radius: 50px;
        font-size: 0.66rem;
        font-weight: 700;
        margin-top: 0.5rem;
        letter-spacing: 0.3px;
    }
    .badge-red    { background: #FEE2E2; color: #DC2626; }
    .badge-green  { background: #DCFCE7; color: #16A34A; }
    .badge-orange { background: #FFE4C7; color: #9B5400; }
    .badge-blue   { background: #DBEAFE; color: #033677; }
    .badge-gold   { background: #FFF3C4; color: #9B5400; }

    /* ═══════════════════════════════════════════════════
       SECTION HEADERS v2.0
    ═══════════════════════════════════════════════════ */
    .section-hdr {
        display: flex;
        align-items: center;
        gap: 0.9rem;
        margin: 2.2rem 0 1.2rem;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid var(--nl-ceu-claro);
    }
    .section-icon {
        width: 42px; height: 42px;
        background: linear-gradient(135deg, var(--azul) 0%, #2678BC 100%);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        flex-shrink: 0;
        box-shadow: 0 4px 12px rgba(3,54,119,0.25);
    }
    .section-hdr h2 {
        font-size: 1.35rem;
        font-weight: 800;
        color: var(--azul);
        margin: 0;
        letter-spacing: -0.3px;
    }
    .section-hdr p { font-size: 0.8rem; color: #9CA3AF; margin: 0.12rem 0 0; }

    /* ═══════════════════════════════════════════════════
       RANKING v2.0 — faixa com acento esquerdo
    ═══════════════════════════════════════════════════ */
    .ranking-item {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 0.85rem 1rem;
        border-radius: 12px;
        background: linear-gradient(145deg, #f7faff 0%, #f0f5fc 100%);
        margin: 0.45rem 0;
        border: 1px solid rgba(209,228,245,0.6);
        border-left: 3px solid var(--border);
        transition: border-left-color 0.15s;
    }
    .rank-num {
        width: 30px; height: 30px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: 0.82rem; flex-shrink: 0;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    }
    .rank-1 { background: linear-gradient(135deg, #FFB700 0%, #FFD040 100%); color: #033677; }
    .rank-2 { background: linear-gradient(135deg, #9CA3AF 0%, #D1D5DB 100%); color: #1F2937; }
    .rank-3 { background: linear-gradient(135deg, #CD7F32 0%, #E09B50 100%); color: white; }
    .rank-other { background: #E5E7EB; color: #6B7280; box-shadow: none; }
    .rank-name { font-weight: 700; font-size: 0.88rem; color: #033677; }
    .rank-sub  { font-size: 0.72rem; color: #9CA3AF; margin-top: 1px; }
    .rank-value {
        text-align: right;
        font-weight: 800;
        font-size: 0.95rem;
        color: #033677;
        margin-left: auto;
        white-space: nowrap;
    }

    /* ═══════════════════════════════════════════════════
       CHART BOXES v2.0
    ═══════════════════════════════════════════════════ */
    .chart-box {
        background: white;
        border-radius: 18px;
        padding: 1.5rem;
        box-shadow: 0 4px 20px rgba(3,54,119,0.08), 0 1px 4px rgba(3,54,119,0.05);
        border: 1px solid rgba(209,228,245,0.7);
        margin-bottom: 1rem;
    }
    .chart-box h3 {
        font-size: 1rem;
        font-weight: 700;
        color: #033677;
        margin: 0 0 1rem;
        padding-bottom: 0.6rem;
        border-bottom: 1px solid var(--nl-ceu-claro);
    }

    /* ═══════════════════════════════════════════════════
       FUNIL
    ═══════════════════════════════════════════════════ */
    .funil-step {
        display: grid;
        grid-template-columns: 120px 55px 1fr 50px;
        gap: 0.4rem;
        align-items: center;
        padding: 0.35rem 0;
    }
    .funil-label { font-size: 0.82rem; font-weight: 700; color: #1F2937; }
    .funil-num { font-size: 0.88rem; font-weight: 800; text-align: right; }
    .funil-bar-bg { height: 20px; background: var(--bg); border-radius: 4px; overflow: hidden; }
    .funil-bar { height: 100%; border-radius: 4px; }
    .funil-pct { font-size: 0.75rem; font-weight: 700; text-align: right; }
    .funil-drop { font-size: 0.7rem; font-weight: 600; padding: 0.1rem 0 0.1rem 175px; }

    /* ═══════════════════════════════════════════════════
       ALERT / NL-ALERT
    ═══════════════════════════════════════════════════ */
    .nl-alert {
        border-radius: 12px;
        padding: 1rem 1.2rem;
        display: flex;
        gap: 0.8rem;
        align-items: flex-start;
        margin: 0.75rem 0;
    }
    .alert-red    { background: #FEF2F2; border-left: 4px solid #DC2626; }
    .alert-orange { background: #FFF7ED; border-left: 4px solid #EA580C; }
    .alert-green  { background: #F0FDF4; border-left: 4px solid #16A34A; }
    .alert-blue   { background: #EFF6FF; border-left: 4px solid #033677; }
    .alert-gold   { background: #FFFBEB; border-left: 4px solid #FFB700; }

    /* ═══════════════════════════════════════════════════
       FOOTER v2.0
    ═══════════════════════════════════════════════════ */
    .nl-footer {
        background: linear-gradient(135deg, #033677 0%, #001833 100%);
        color: rgba(255,255,255,0.5);
        text-align: center;
        padding: 1.5rem 2rem;
        border-radius: 18px;
        margin-top: 2rem;
        font-size: 0.78rem;
        border-top: 2px solid rgba(255,183,0,0.25);
    }
    .nl-footer strong { color: var(--dourado); }

    /* ═══════════════════════════════════════════════════
       SIDEBAR v2.0 — azul profundo com detalhe dourado
    ═══════════════════════════════════════════════════ */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #033677 0%, #022560 60%, #001833 100%);
        border-right: 2px solid rgba(255,183,0,0.35);
    }
    [data-testid="stSidebar"] * { color: rgba(255,255,255,0.92) !important; }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.12); margin: 0.5rem 0; }
    /* Selectbox e radio: highlight mais claro */
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background: rgba(255,255,255,0.08) !important;
        border-color: rgba(255,255,255,0.2) !important;
    }
    [data-testid="stSidebar"] label[data-baseweb="radio"] {
        padding: 0.35rem 0.5rem;
        border-radius: 8px;
        margin: 1px 0;
        transition: background 0.15s;
    }

    /* ═══════════════════════════════════════════════════
       BOTOES v2.0
    ═══════════════════════════════════════════════════ */
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #FFB700 0%, #FFD040 100%) !important;
        color: #033677 !important;
        border: none !important;
        font-weight: 800 !important;
        letter-spacing: 0.3px;
        box-shadow: 0 3px 10px rgba(255,183,0,0.35) !important;
        border-radius: 10px !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(90deg, #FFD040 0%, #FFE066 100%) !important;
        box-shadow: 0 5px 16px rgba(255,183,0,0.45) !important;
        transform: translateY(-1px);
    }
    .stButton > button[kind="secondary"] {
        background: transparent !important;
        color: #033677 !important;
        border: 1.5px solid #033677 !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: #F0F6FF !important;
        border-color: #033677 !important;
    }

    /* Sidebar botoes */
    [data-testid="stSidebar"] .stButton > button {
        border-radius: 10px !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        color: #033677 !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="secondary"] {
        color: rgba(255,255,255,0.85) !important;
        border-color: rgba(255,255,255,0.3) !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
        background: rgba(255,255,255,0.1) !important;
    }

    /* ═══════════════════════════════════════════════════
       STREAMLIT NATIVE OVERRIDES
    ═══════════════════════════════════════════════════ */
    /* Dataframe / tabelas */
    [data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

    /* Inputs */
    [data-testid="stTextInput"] input {
        border-radius: 10px !important;
        border-color: rgba(209,228,245,0.8) !important;
    }

    /* Info / Warning / Success / Error nativo */
    [data-testid="stAlert"] {
        border-radius: 12px !important;
        border: none !important;
    }

    /* Tabs (se usadas) */
    [data-baseweb="tab-list"] { gap: 4px; }
    [data-baseweb="tab"] {
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    /* Download button */
    [data-testid="stDownloadButton"] button {
        border-radius: 10px !important;
        font-weight: 700 !important;
    }

    /* ═══════════════════════════════════════════════════
       ESCONDE CHROME STREAMLIT
    ═══════════════════════════════════════════════════ */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    [data-testid="stSidebarNav"] { display: none !important; }

    /* ═══════════════════════════════════════════════════
       RESPONSIVO
    ═══════════════════════════════════════════════════ */
    @media(max-width: 768px) {
        .kpi-grid { grid-template-columns: repeat(2, 1fr); gap: 0.75rem; }
        .nl-header { padding: 1.5rem; }
        .nl-header h1 { font-size: 1.6rem; }
        .funil-step { grid-template-columns: 90px 45px 1fr 40px; }
    }
</style>
""", unsafe_allow_html=True)


def main():
    user = get_usuario_atual()

    with st.sidebar:
        st.markdown(
            f"""
            <div style="text-align:center;padding:0.4rem 0 0.6rem 0">
                <img src="{_LOGO_PRINCIPAL_URL}" alt="NL Imoveis"
                     style="max-width:140px;width:80%;height:auto;
                            filter:brightness(0) invert(1);opacity:0.95">
                <div style="font-family:'MultaPecunia','Georama',sans-serif;
                            font-size:0.72rem;color:rgba(255,255,255,0.7);
                            margin-top:0.5rem;letter-spacing:0.8px">
                    CRECI 1440 J · Natal/RN
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # Info do usuario logado
        if user:
            perfil_labels = {"admin": "Admin", "gerente": "Gerente", "corretor": "Corretor"}
            perfil_label = perfil_labels.get(user["perfil"], "Usuario")
            st.markdown(f"**{escape(user['nome'])}**")
            st.caption(f"{perfil_label} · {escape(user['email'])}")
            if st.button("Sair", use_container_width=True):
                logout()
                st.rerun()
            st.markdown("---")

        # Filtro de periodo global (a propria key salva em session_state)
        seletor_periodo()

        st.markdown("---")

        # Menu de navegacao
        paginas = [
            "Visao Geral",
            "Equipe Vendas",
            "Equipe Locacao",
            "Cadastrar Venda",
            "Origens de Leads",
            "Metas & Projecoes",
            "Minha Conta",
        ]
        if is_admin():
            paginas.insert(-1, "Gerenciar Usuarios")
            paginas.insert(-1, "Auditoria")

        pagina = st.radio(
            "Navegacao",
            paginas,
            index=0,
            label_visibility="collapsed"
        )

        st.markdown("---")

        # Botao de atualizar dados (limpa cache)
        if st.button("🔄 Atualizar dados", use_container_width=True,
                     help="Recarrega os dados mais recentes do Supabase (cache de 5 min)"):
            limpar_cache()
            st.success("Cache limpo! Dados sendo recarregados...")
            st.rerun()

        st.markdown("---")
        st.caption("Painel Estrategico v2.0")
        st.caption("🔄 Cache 5 min · Supabase + Jetimob")

    if pagina == "Visao Geral":
        from views import visao_geral
        visao_geral.render()
    elif pagina == "Equipe Vendas":
        from views import equipe_vendas
        equipe_vendas.render()
    elif pagina == "Cadastrar Venda":
        from views import cadastrar_venda
        cadastrar_venda.render()
    elif pagina == "Equipe Locacao":
        from views import equipe_locacao
        equipe_locacao.render()
    elif pagina == "Origens de Leads":
        from views import origens
        origens.render()
    elif pagina == "Metas & Projecoes":
        from views import metas
        metas.render()
    elif pagina == "Gerenciar Usuarios":
        from views import usuarios
        usuarios.render()
    elif pagina == "Auditoria":
        from views import auditoria_view
        auditoria_view.render()
    elif pagina == "Minha Conta":
        from views import minha_conta
        minha_conta.render()


if __name__ == "__main__":
    main()
