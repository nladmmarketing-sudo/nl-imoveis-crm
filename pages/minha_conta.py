"""
Minha Conta - Alterar senha do proprio usuario
"""
import streamlit as st
from utils.auth import get_usuario_atual, alterar_senha, usuario_logado, escape


def render():
    if not usuario_logado():
        st.warning("Faca login para acessar.")
        return

    user = get_usuario_atual()

    st.markdown(f"""
    <div class="nl-header">
        <div class="badge">Minha Conta</div>
        <h1>Ola, <span>{escape(user['nome'].split()[0])}</span></h1>
        <div class="sub">{escape(user['email'])} · Perfil: {escape(user['perfil'].title())}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">🔐</div>
        <div>
            <h2>Alterar Senha</h2>
            <p>Troque sua senha periodicamente para manter o acesso seguro</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("form_alterar_senha", clear_on_submit=True):
        senha_atual = st.text_input("Senha atual", type="password")
        senha_nova = st.text_input("Nova senha", type="password",
                                    help="Minimo 8 caracteres, com letras e numeros")
        senha_confirma = st.text_input("Confirmar nova senha", type="password")
        submit = st.form_submit_button("Alterar Senha", use_container_width=True)

        if submit:
            if not senha_atual or not senha_nova or not senha_confirma:
                st.error("Preencha todos os campos.")
            elif senha_nova != senha_confirma:
                st.error("A confirmacao nao confere com a nova senha.")
            elif senha_atual == senha_nova:
                st.error("A nova senha nao pode ser igual a atual.")
            else:
                ok, msg = alterar_senha(user["id"], senha_atual, senha_nova)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    st.markdown("""
    <div class="nl-footer">
        <strong>NL Imoveis</strong> · Painel Estrategico · CRECI 1440 J · Natal/RN<br>
        Gestao de conta pessoal
    </div>
    """, unsafe_allow_html=True)
