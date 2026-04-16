"""
CRM Dashboard - NL Imoveis
Painel de gestao de leads, corretores e vendas
"""
import streamlit as st

st.set_page_config(
    page_title="CRM NL Imoveis",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    /* Header */
    .main-header {
        background: linear-gradient(135deg, #1B4F72 0%, #2E86C1 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .main-header h1 { color: white; margin: 0; font-size: 1.8rem; }
    .main-header p { color: #D6EAF8; margin: 0.3rem 0 0 0; font-size: 0.95rem; }

    /* KPI cards */
    .kpi-card {
        background: white;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid #2E86C1;
        text-align: center;
    }
    .kpi-card .number { font-size: 2rem; font-weight: 700; color: #1B4F72; }
    .kpi-card .label { font-size: 0.85rem; color: #5D6D7E; text-transform: uppercase; letter-spacing: 0.5px; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1B4F72 0%, #154360 100%);
    }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stSidebar"] .stSelectbox label { color: #D6EAF8 !important; }

    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Tables */
    .stDataFrame { border-radius: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)


def main():
    # Sidebar navigation
    with st.sidebar:
        st.image("https://via.placeholder.com/200x60/1B4F72/FFFFFF?text=NL+Imoveis", width=200)
        st.markdown("---")

        pagina = st.radio(
            "Navegacao",
            ["Visao Geral", "Leads Jetimob", "Corretores", "Vendas", "Bot WhatsApp"],
            index=0,
            label_visibility="collapsed"
        )
        st.markdown("---")
        st.caption("NL Imoveis - CRM v1.0")
        st.caption("CRECI 1440 J | Natal/RN")

    # Route pages
    if pagina == "Visao Geral":
        from pages import visao_geral
        visao_geral.render()
    elif pagina == "Leads Jetimob":
        from pages import leads_jetimob
        leads_jetimob.render()
    elif pagina == "Corretores":
        from pages import corretores
        corretores.render()
    elif pagina == "Vendas":
        from pages import vendas
        vendas.render()
    elif pagina == "Bot WhatsApp":
        from pages import bot_whatsapp
        bot_whatsapp.render()


if __name__ == "__main__":
    main()
