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

# CSS de componentes (string normal, mantem o layout original)
st.markdown("""
<style>
    /* Header */
    .nl-header {
        background: linear-gradient(135deg, #033677 0%, #022757 60%, #001833 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        color: white;
        position: relative;
        overflow: hidden;
    }
    .nl-header::after {
        content: '';
        position: absolute;
        top: -50%;
        right: -10%;
        width: 300px;
        height: 300px;
        background: rgba(240,165,0,0.08);
        border-radius: 50%;
    }
    .nl-header .badge {
        display: inline-block;
        background: var(--dourado);
        color: var(--azul);
        padding: 0.25rem 0.8rem;
        border-radius: 50px;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 0.8rem;
    }
    .nl-header h1 { color: white; margin: 0; font-size: 2rem; font-weight: 800; }
    .nl-header h1 span { color: var(--dourado); }
    .nl-header .sub { color: rgba(255,255,255,0.65); font-size: 0.9rem; margin-top: 0.3rem; }

    /* KPI Cards */
    .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
    .kpi-card {
        background: white;
        border-radius: 14px;
        padding: 1.3rem 1.5rem;
        box-shadow: 0 2px 12px rgba(28,56,130,0.08);
        border: 1px solid var(--border);
        position: relative;
        overflow: hidden;
    }
    .kpi-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--dourado); }
    .kpi-card.azul::before { background: var(--azul); }
    .kpi-card.green::before { background: var(--green); }
    .kpi-card.red::before { background: var(--red); }
    .kpi-card .label {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: var(--gray);
        font-weight: 600;
    }
    .kpi-card .num {
        font-size: 2rem;
        font-weight: 800;
        color: var(--azul);
        line-height: 1;
        margin: 0.4rem 0;
    }
    .kpi-card .sub { font-size: 0.78rem; color: var(--gray); }
    .kpi-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 50px;
        font-size: 0.68rem;
        font-weight: 700;
        margin-top: 0.4rem;
    }
    .badge-red { background: #FEE2E2; color: #DC2626; }         /* semantico erro */
    .badge-green { background: #DCFCE7; color: #16A34A; }       /* semantico sucesso */
    .badge-orange { background: #FFE4C7; color: #9B5400; }      /* Terra Fertil */
    .badge-blue { background: #DBEAFE; color: #033677; }        /* Azul Noturno */
    .badge-gold { background: #FFDE76; color: #9B5400; }        /* Sol Dourado + Terra Fertil */

    /* Section headers */
    .section-hdr {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        margin: 2rem 0 1.2rem 0;
    }
    .section-icon {
        width: 40px;
        height: 40px;
        background: var(--azul);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        flex-shrink: 0;
    }
    .section-hdr h2 { font-size: 1.4rem; font-weight: 800; color: var(--azul); margin: 0; }
    .section-hdr p { font-size: 0.82rem; color: var(--gray); margin: 0.15rem 0 0 0; }

    /* Ranking */
    .ranking-item {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 0.75rem 1rem;
        border-radius: 10px;
        background: var(--bg);
        margin: 0.4rem 0;
    }
    .rank-num {
        width: 28px; height: 28px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: 0.85rem; flex-shrink: 0;
    }
    .rank-1 { background: var(--dourado); color: var(--azul); }
    .rank-2 { background: #C0C0C0; color: #333; }
    .rank-3 { background: #CD7F32; color: #fff; }
    .rank-other { background: var(--border); color: var(--gray); }
    .rank-name { font-weight: 700; font-size: 0.88rem; color: var(--azul); }
    .rank-sub { font-size: 0.72rem; color: var(--gray); }
    .rank-value { text-align: right; font-weight: 800; font-size: 0.95rem; color: var(--azul); }

    /* Funil */
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

    /* Alert */
    .nl-alert {
        border-radius: 12px;
        padding: 1rem 1.2rem;
        display: flex;
        gap: 0.8rem;
        align-items: flex-start;
        margin: 0.75rem 0;
    }
    .alert-red { background: #FEE2E2; border-left: 4px solid #DC2626; }
    .alert-orange { background: #FFE4C7; border-left: 4px solid #9B5400; }   /* Terra Fertil */
    .alert-green { background: #DCFCE7; border-left: 4px solid #16A34A; }
    .alert-blue { background: #DBEAFE; border-left: 4px solid #033677; }     /* Azul Noturno */
    .alert-gold { background: #FFDE76; border-left: 4px solid #FFB700; }     /* Sol Dourado + Ouro Vivo */

    /* Chart box */
    .chart-box {
        background: white;
        border-radius: 14px;
        padding: 1.5rem;
        box-shadow: 0 2px 12px rgba(28,56,130,0.08);
        border: 1px solid var(--border);
    }
    .chart-box h3 { font-size: 1rem; font-weight: 700; color: var(--azul); margin-bottom: 0.5rem; }

    /* Footer */
    .nl-footer {
        background: var(--azul);
        color: rgba(255,255,255,0.6);
        text-align: center;
        padding: 1.5rem;
        border-radius: 14px;
        margin-top: 2rem;
        font-size: 0.8rem;
    }
    .nl-footer strong { color: var(--dourado); }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: var(--nl-azul-noturno);
        border-right: 3px solid var(--nl-ouro-vivo);
    }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.15); }

    /* Hide streamlit chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Esconde apenas o menu automatico (seguro, nao afeta outros elementos) */
    [data-testid="stSidebarNav"] { display: none !important; }

    /* Botoes - padrao NL */
    .stButton > button[kind="primary"] {
        background-color: var(--nl-ouro-vivo) !important;
        color: var(--nl-azul-noturno) !important;
        border: none !important;
        font-weight: 700 !important;
        letter-spacing: 0.3px;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: var(--nl-sol-dourado) !important;
        color: var(--nl-azul-noturno) !important;
        border: none !important;
    }
    .stButton > button[kind="secondary"] {
        background-color: transparent !important;
        color: var(--nl-azul-noturno) !important;
        border: 1.5px solid var(--nl-azul-noturno) !important;
        font-weight: 600 !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background-color: var(--nl-ceu-claro) !important;
        color: var(--nl-azul-noturno) !important;
        border-color: var(--nl-azul-noturno) !important;
    }

    /* Override: sidebar escura — primario mantem texto azul, secundario fica outline branco */
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        color: var(--nl-azul-noturno) !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="secondary"] {
        color: white !important;
        border-color: rgba(255,255,255,0.4) !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
        background-color: rgba(255,255,255,0.08) !important;
        color: white !important;
    }

    /* KPI: numero destacavel em Ouro Vivo (opt-in com .highlight) */
    .kpi-card .num.highlight { color: var(--nl-ouro-vivo); }

    @media(max-width: 768px) {
        .kpi-grid { grid-template-columns: repeat(2, 1fr); }
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
            "Vendas do Mes (Jetimob)",
            "Locacoes do Mes (Jetimob)",
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
        st.caption("Painel Estrategico v1.2")
        st.caption("Cache: 5 min · Supabase + Jetimob")

    if pagina == "Visao Geral":
        from views import visao_geral
        visao_geral.render()
    elif pagina == "Vendas do Mes (Jetimob)":
        from views import vendas_jetimob
        vendas_jetimob.render()
    elif pagina == "Locacoes do Mes (Jetimob)":
        from views import locacoes_jetimob
        locacoes_jetimob.render()
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
