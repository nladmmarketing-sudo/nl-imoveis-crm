"""
Gerenciar Usuarios - Cadastro e controle de acesso (apenas gerentes)
"""
import streamlit as st
import pandas as pd
from utils.auth import (
    is_gerente, cadastrar_usuario, listar_usuarios,
    atualizar_status_usuario, get_usuario_atual
)


def render():
    if not is_gerente():
        st.warning("Acesso restrito. Apenas gerentes podem gerenciar usuarios.")
        return

    st.markdown("""
    <div class="nl-header">
        <div class="badge">Administracao</div>
        <h1>Gerenciar <span>Usuarios</span></h1>
        <div class="sub">Cadastro e controle de acesso ao painel</div>
    </div>
    """, unsafe_allow_html=True)

    # Cadastrar novo usuario
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">➕</div>
        <div>
            <h2>Cadastrar Novo Usuario</h2>
            <p>Adicione membros da equipe ao sistema</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("form_novo_usuario", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome completo", placeholder="Ex: Maria Silva")
            email = st.text_input("Email", placeholder="email@nlimoveis.com.br")
        with col2:
            senha = st.text_input("Senha inicial", type="password", placeholder="Minimo 6 caracteres")
            perfil = st.selectbox("Perfil de acesso", ["corretor", "gerente"])

        submit = st.form_submit_button("Cadastrar Usuario", use_container_width=True)

        if submit:
            if not nome or not email or not senha:
                st.error("Preencha todos os campos.")
            elif len(senha) < 6:
                st.error("A senha deve ter no minimo 6 caracteres.")
            elif "@" not in email:
                st.error("Email invalido.")
            else:
                ok = cadastrar_usuario(nome, email, senha, perfil)
                if ok:
                    st.success(f"Usuario {nome} cadastrado com sucesso!")
                    st.rerun()

    # Lista de usuarios
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">👥</div>
        <div>
            <h2>Usuarios Cadastrados</h2>
            <p>Gerencie o acesso da equipe</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    usuarios = listar_usuarios()

    if usuarios:
        for user in usuarios:
            status_color = "#16A34A" if user["ativo"] else "#DC2626"
            status_text = "Ativo" if user["ativo"] else "Inativo"
            badge_cls = "badge-green" if user["ativo"] else "badge-red"
            perfil_badge = "badge-gold" if user["perfil"] == "gerente" else "badge-blue"

            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:1rem;padding:0.6rem 1rem;background:white;border-radius:10px;border:1px solid #D1E4F5;margin:0.3rem 0">
                    <div style="width:36px;height:36px;background:#EAF3FB;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;color:#1C3882;font-size:0.85rem">{user['nome'][0].upper()}</div>
                    <div style="flex:1">
                        <div style="font-weight:700;color:#1C3882;font-size:0.88rem">{user['nome']}</div>
                        <div style="font-size:0.75rem;color:#6B7280">{user['email']}</div>
                    </div>
                    <span class="kpi-badge {perfil_badge}">{user['perfil'].title()}</span>
                    <span class="kpi-badge {badge_cls}">{status_text}</span>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                if user["ativo"]:
                    if st.button("Desativar", key=f"desat_{user['id']}", type="secondary"):
                        atualizar_status_usuario(user["id"], False)
                        st.rerun()
                else:
                    if st.button("Ativar", key=f"ativ_{user['id']}", type="primary"):
                        atualizar_status_usuario(user["id"], True)
                        st.rerun()
            with col3:
                # Nao pode desativar a si mesmo
                user_atual = get_usuario_atual()
                if user_atual and user["id"] == user_atual["id"]:
                    st.caption("(voce)")

        st.markdown(f"""
        <div style="margin-top:1rem;padding:0.8rem 1.2rem;background:#EAF3FB;border-radius:10px;font-size:0.82rem;color:#1C3882">
            <strong>{len([u for u in usuarios if u['ativo']])} usuarios ativos</strong> de {len(usuarios)} cadastrados
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Nenhum usuario cadastrado ainda.")

    # Footer
    st.markdown("""
    <div class="nl-footer">
        <strong>NL Imoveis</strong> · Painel Estrategico · CRECI 1440 J · Natal/RN<br>
        Gerenciamento de acesso · Apenas gerentes
    </div>
    """, unsafe_allow_html=True)
