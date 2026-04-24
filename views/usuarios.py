"""
Gerenciar Usuarios - Cadastro e controle de acesso (apenas admin)

IMPORTANTE - ROLLOUT pos-migration:
Apos rodar sql/add_corretor_mapping.sql, todos os corretores existentes terao
corretor_nome_jetimob = NULL. Eles nao conseguirao usar Visao Geral, Equipe Vendas
ou Equipe Locacao ate que o admin preencha o campo via popover "Editar nome Jetimob"
abaixo. Antes de deploy em producao: liste corretores sem mapeamento e preencha um
a um com o nome EXATO como aparece no Jetimob.
"""
import streamlit as st
from utils.auth import (
    is_admin, cadastrar_usuario, listar_usuarios,
    atualizar_status_usuario, get_usuario_atual,
    resetar_senha_por_gerente, atualizar_corretor_jetimob, escape
)
from utils.auditoria import registrar
from utils.supabase_client import get_supabase_client


# Estilos inline para badges — compatibilidade com Streamlit 1.50+
# (classes CSS customizadas sao as vezes escapadas dentro de st.columns)
_BADGE_BASE = (
    "display:inline-block;padding:0.2rem 0.6rem;border-radius:50px;"
    "font-size:0.68rem;font-weight:700;margin-top:0.4rem;"
)
_BADGE_COLORS = {
    # Semanticos universais (mantidos)
    "badge-red":    "background:#FEE2E2;color:#DC2626",
    "badge-green":  "background:#DCFCE7;color:#16A34A",
    # Paleta NL (Manual da Marca 28/01/2025)
    "badge-orange": "background:#FFE4C7;color:#9B5400",  # Terra Fertil
    "badge-blue":   "background:#DBEAFE;color:#033677",  # Azul Noturno
    "badge-gold":   "background:#FFDE76;color:#9B5400",  # Sol Dourado + Terra Fertil
}

def _badge_style(cls: str) -> str:
    return _BADGE_BASE + _BADGE_COLORS.get(cls, _BADGE_COLORS["badge-blue"])


def alterar_perfil(user_id: int, novo_perfil: str) -> bool:
    client = get_supabase_client()
    try:
        client.table("usuarios").update({"perfil": novo_perfil}).eq("id", user_id).execute()
        return True
    except Exception:
        return False


def render():
    if not is_admin():
        st.warning("Acesso restrito. Apenas administradores podem gerenciar usuarios.")
        return

    st.markdown("""
    <div class="nl-header">
        <div class="badge">Administracao</div>
        <h1>Gerenciar <span>Usuarios</span></h1>
        <div class="sub">Cadastro e controle de acesso ao painel</div>
    </div>
    """, unsafe_allow_html=True)

    # --- Cadastrar novo usuario ---
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
            corretor_jt = st.text_input(
                "Nome exato no Jetimob",
                placeholder="Ex: Maria Silva Santos",
                help="Obrigatorio se perfil = corretor. Deve ser o nome IDENTICO ao que aparece na coluna 'corretor' do Jetimob (case-insensitive, ignora acentos)."
            )
        with col2:
            senha = st.text_input("Senha inicial", type="password",
                                   help="Minimo 8 caracteres, com letras e numeros")
            perfil = st.selectbox(
                "Perfil de acesso",
                ["gerente", "corretor", "marketing", "admin"],
                help="Admin: tudo · Gerente/Marketing: ve tudo · Corretor: so os proprios dados"
            )

        submit = st.form_submit_button("Cadastrar Usuario", use_container_width=True)

        if submit:
            ok, msg = cadastrar_usuario(nome, email, senha, perfil, corretor_jt)
            if ok:
                registrar("cadastrou_usuario", f"{nome} ({email}) perfil={perfil}")
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    # --- Lista de usuarios ---
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
    user_atual = get_usuario_atual()

    if usuarios:
        for user in usuarios:
            status_text = "Ativo" if user["ativo"] else "Inativo"
            badge_cls = "badge-green" if user["ativo"] else "badge-red"
            perfil_badges = {
                "admin": "badge-red",
                "gerente": "badge-gold",
                "corretor": "badge-blue",
                "marketing": "badge-orange",
            }
            perfil_badge = perfil_badges.get(user["perfil"], "badge-blue")
            is_self = user_atual and user["id"] == user_atual["id"]
            nome_safe = escape(user['nome'])
            email_safe = escape(user['email'])
            perfil_safe = escape(user['perfil'].title())
            inicial = escape(user['nome'][0].upper()) if user.get('nome') else "?"

            col1, col2, col3, col4, col5 = st.columns([4, 1, 1, 1, 1])
            with col1:
                # Mostra warning se for corretor sem mapeamento Jetimob
                aviso_jt = ""
                if user["perfil"] == "corretor" and not user.get("corretor_nome_jetimob"):
                    aviso_jt = f'<span style="{_badge_style("badge-red")}" title="Sem nome Jetimob">⚠</span>'
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:1rem;padding:0.6rem 1rem;background:white;border-radius:10px;border:1px solid #D1E4F5;margin:0.3rem 0">
                    <div style="width:36px;height:36px;background:#F3F6FA;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;color:#033677;font-size:0.85rem">{inicial}</div>
                    <div style="flex:1">
                        <div style="font-weight:700;color:#033677;font-size:0.88rem">{nome_safe}{" (voce)" if is_self else ""}</div>
                        <div style="font-size:0.75rem;color:#6B7280">{email_safe}</div>
                    </div>
                    {aviso_jt}
                    <span style="{_badge_style(perfil_badge)}">{perfil_safe}</span>
                    <span style="{_badge_style(badge_cls)}">{status_text}</span>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                if is_self:
                    st.caption("—")
                elif user["ativo"]:
                    if st.button("Desativar", key=f"desat_{user['id']}"):
                        atualizar_status_usuario(user["id"], False)
                        registrar("desativou_usuario", f"{user['nome']} ({user['email']})")
                        st.rerun()
                else:
                    if st.button("Ativar", key=f"ativ_{user['id']}", type="primary"):
                        atualizar_status_usuario(user["id"], True)
                        registrar("ativou_usuario", f"{user['nome']} ({user['email']})")
                        st.rerun()
            with col3:
                if not is_self:
                    with st.popover("Resetar senha"):
                        st.caption(f"Resetar senha de {user['nome']}")
                        nova = st.text_input("Nova senha", type="password", key=f"rs_{user['id']}",
                                             help="Minimo 8 caracteres, com letras e numeros")
                        if st.button("Confirmar", key=f"rsb_{user['id']}"):
                            ok, msg = resetar_senha_por_gerente(user["id"], nova)
                            if ok:
                                registrar("resetou_senha", f"{user['nome']} ({user['email']})")
                                st.success(msg)
                            else:
                                st.error(msg)
            with col4:
                if not is_self:
                    with st.popover("Alterar perfil"):
                        st.caption(f"Perfil atual: {user['perfil']}")
                        perfis = ["gerente", "corretor", "marketing", "admin"]
                        idx = perfis.index(user["perfil"]) if user["perfil"] in perfis else 0
                        novo = st.selectbox("Novo perfil", perfis, index=idx, key=f"perf_{user['id']}")
                        if st.button("Salvar perfil", key=f"perfb_{user['id']}"):
                            if alterar_perfil(user["id"], novo):
                                registrar("alterou_perfil", f"{user['nome']}: {user['perfil']} -> {novo}")
                                st.success("Perfil atualizado.")
                                st.rerun()
                            else:
                                st.error("Erro ao alterar perfil.")
            with col5:
                if not is_self:
                    with st.popover("Editar nome Jetimob"):
                        atual_jt = user.get("corretor_nome_jetimob") or ""
                        st.caption(f"Atual: {atual_jt or '(nao definido)'}")
                        novo_jt = st.text_input(
                            "Nome exato no Jetimob",
                            value=atual_jt,
                            key=f"jt_{user['id']}",
                            help="Como aparece na coluna 'corretor' do Jetimob. Match ignora case e acentos."
                        )
                        if st.button("Salvar nome Jetimob", key=f"jtb_{user['id']}"):
                            if atualizar_corretor_jetimob(user["id"], novo_jt):
                                registrar("alterou_nome_jetimob", f"{user['nome']}: '{atual_jt}' -> '{novo_jt}'")
                                st.success("Nome Jetimob atualizado.")
                                st.rerun()
                            else:
                                st.error("Erro ao atualizar nome Jetimob.")

        # Resumo
        admins = len([u for u in usuarios if u["perfil"] == "admin"])
        gerentes = len([u for u in usuarios if u["perfil"] == "gerente"])
        corretores = len([u for u in usuarios if u["perfil"] == "corretor"])
        marketing = len([u for u in usuarios if u["perfil"] == "marketing"])
        ativos = len([u for u in usuarios if u["ativo"]])
        sem_jt = len([u for u in usuarios if u["perfil"] == "corretor" and not u.get("corretor_nome_jetimob")])

        aviso_sem_jt = (
            f' · <span style="color:#DC2626;font-weight:700">⚠ {sem_jt} corretor(es) sem nome Jetimob</span>'
            if sem_jt > 0 else ""
        )

        st.markdown(f"""
        <div style="margin-top:1rem;padding:0.8rem 1.2rem;background:#F3F6FA;border-radius:10px;font-size:0.82rem;color:#033677">
            <strong>{ativos} ativos</strong> de {len(usuarios)} · {admins} admin(s) · {gerentes} gerente(s) · {marketing} marketing · {corretores} corretor(es){aviso_sem_jt}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Nenhum usuario cadastrado ainda.")

    st.markdown("""
    <div class="nl-footer">
        <strong>NL Imoveis</strong> · Painel Estrategico · CRECI 1440 J · Natal/RN<br>
        Gerenciamento de acesso · Apenas admin
    </div>
    """, unsafe_allow_html=True)
