"""
Auditoria — log de acoes do sistema (apenas admin)
"""
import streamlit as st
import pandas as pd
from utils.auth import is_admin
from utils.auditoria import listar_recentes, contar_registros, limpar_antigos, registrar


def render():
    if not is_admin():
        st.warning("Acesso restrito. Apenas administradores.")
        return

    st.markdown("""
    <div class="nl-header">
        <div class="badge">Administracao</div>
        <h1>Log de <span>Auditoria</span></h1>
        <div class="sub">Registro de acoes importantes no sistema</div>
    </div>
    """, unsafe_allow_html=True)

    # Stats das tabelas
    stats = contar_registros()

    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="label">Registros de Auditoria</div>
            <div class="num">{stats['auditoria']:,}</div>
            <div class="sub">Mantidos por 90 dias</div>
        </div>
        <div class="kpi-card azul">
            <div class="label">Tentativas de Login</div>
            <div class="num">{stats['login_attempts']:,}</div>
            <div class="sub">Mantidas por 30 dias</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Botao de limpeza manual
    col1, col2 = st.columns([3, 1])
    with col2:
        with st.popover("🧹 Limpar antigos"):
            st.caption("Apaga registros com mais de 90d (auditoria) e 30d (login_attempts)")
            if st.button("Confirmar limpeza", key="btn_limpar", type="primary"):
                resultado = limpar_antigos()
                registrar("limpeza_manual",
                          f"apagou {resultado['auditoria']} de auditoria e {resultado['login_attempts']} de login_attempts")
                st.success(f"Limpeza concluida. Auditoria: -{resultado['auditoria']}, Login: -{resultado['login_attempts']}")
                st.rerun()

    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">📋</div>
        <div>
            <h2>Ultimas Acoes</h2>
            <p>200 acoes mais recentes registradas no sistema</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    logs = listar_recentes(limit=200)

    if not logs:
        st.info("Nenhuma acao registrada ainda.")
        return

    df = pd.DataFrame(logs)
    df["criado_em"] = pd.to_datetime(df["criado_em"]).dt.strftime("%d/%m/%Y %H:%M:%S")

    # Coluna amigavel
    acoes_map = {
        "login_sucesso": "Login OK",
        "login_falha": "Login falhou",
        "logout": "Saiu",
        "cadastrou_usuario": "Cadastrou usuario",
        "desativou_usuario": "Desativou usuario",
        "ativou_usuario": "Ativou usuario",
        "resetou_senha": "Resetou senha",
        "alterou_senha": "Alterou propria senha",
        "alterou_metas": "Alterou metas",
        "alterou_perfil": "Alterou perfil de usuario",
    }
    df["acao_label"] = df["acao"].map(lambda x: acoes_map.get(x, x))

    df_display = df[["criado_em", "usuario_email", "acao_label", "detalhes"]].copy()
    df_display.columns = ["Data/Hora", "Usuario", "Acao", "Detalhes"]

    # Filtro por tipo de acao
    col1, col2 = st.columns([3, 1])
    with col1:
        busca = st.text_input("🔍 Buscar (usuario, acao, detalhes)", placeholder="Digite pra filtrar...")
    with col2:
        acoes_unicas = ["Todas"] + sorted(df["acao_label"].unique().tolist())
        filtro_acao = st.selectbox("Tipo de acao", acoes_unicas)

    if busca:
        mask = (
            df_display["Usuario"].str.contains(busca, case=False, na=False) |
            df_display["Acao"].str.contains(busca, case=False, na=False) |
            df_display["Detalhes"].str.contains(busca, case=False, na=False)
        )
        df_display = df_display[mask]

    if filtro_acao != "Todas":
        df_display = df_display[df_display["Acao"] == filtro_acao]

    st.dataframe(df_display, use_container_width=True, hide_index=True, height=500)

    # Export CSV
    csv = df_display.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Exportar CSV",
        data=csv,
        file_name=f"auditoria_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )

    st.markdown(f"""
    <div style="margin-top:1rem;padding:0.8rem 1.2rem;background:#EAF3FB;border-radius:10px;font-size:0.82rem;color:#1C3882">
        <strong>{len(df_display)} registro(s)</strong> exibido(s) de {len(df)} total
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="nl-footer">
        <strong>NL Imoveis</strong> · Painel Estrategico · Log de Auditoria<br>
        Registros sao mantidos por 90 dias
    </div>
    """, unsafe_allow_html=True)
