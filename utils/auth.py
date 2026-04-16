"""
Sistema de Autenticacao - NL Imoveis CRM
Controle de acesso por email/senha com perfis (gerente, corretor)
"""
import streamlit as st
import bcrypt
from utils.supabase_client import get_supabase_client


def hash_senha(senha: str) -> str:
    """Gera hash bcrypt da senha"""
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Verifica se a senha confere com o hash"""
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
    except Exception:
        return False


def autenticar_usuario(email: str, senha: str) -> dict | None:
    """
    Busca usuario por email e verifica senha.
    Retorna dict com dados do usuario ou None se falhar.
    """
    client = get_supabase_client()
    try:
        response = (
            client.table("usuarios")
            .select("*")
            .eq("email", email.lower().strip())
            .eq("ativo", True)
            .execute()
        )
        if response.data and len(response.data) > 0:
            user = response.data[0]
            if verificar_senha(senha, user["senha_hash"]):
                return user
    except Exception as e:
        st.error(f"Erro ao autenticar: {e}")
    return None


def cadastrar_usuario(nome: str, email: str, senha: str, perfil: str = "corretor") -> bool:
    """Cadastra novo usuario no sistema"""
    client = get_supabase_client()
    try:
        response = (
            client.table("usuarios")
            .insert({
                "nome": nome.strip(),
                "email": email.lower().strip(),
                "senha_hash": hash_senha(senha),
                "perfil": perfil,
                "ativo": True,
            })
            .execute()
        )
        return bool(response.data)
    except Exception as e:
        if "duplicate key" in str(e) or "unique" in str(e).lower():
            st.error("Este email ja esta cadastrado.")
        else:
            st.error(f"Erro ao cadastrar: {e}")
        return False


def listar_usuarios() -> list:
    """Lista todos os usuarios (para gerente)"""
    client = get_supabase_client()
    try:
        response = (
            client.table("usuarios")
            .select("id, nome, email, perfil, ativo, criado_em")
            .order("criado_em", desc=True)
            .execute()
        )
        return response.data or []
    except Exception:
        return []


def atualizar_status_usuario(user_id: int, ativo: bool) -> bool:
    """Ativa ou desativa usuario"""
    client = get_supabase_client()
    try:
        response = (
            client.table("usuarios")
            .update({"ativo": ativo})
            .eq("id", user_id)
            .execute()
        )
        return bool(response.data)
    except Exception:
        return False


def usuario_logado() -> bool:
    """Verifica se ha usuario logado na sessao"""
    return st.session_state.get("autenticado", False)


def get_usuario_atual() -> dict | None:
    """Retorna dados do usuario logado"""
    if usuario_logado():
        return st.session_state.get("usuario", None)
    return None


def is_gerente() -> bool:
    """Verifica se o usuario logado e gerente"""
    user = get_usuario_atual()
    return user is not None and user.get("perfil") == "gerente"


def logout():
    """Desloga o usuario"""
    st.session_state["autenticado"] = False
    st.session_state["usuario"] = None


def render_login():
    """Renderiza pagina de login"""
    st.markdown("""
    <style>
        [data-testid="stSidebar"] { display: none; }
        .main .block-container { max-width: 480px; padding-top: 3rem; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center;margin-bottom:2rem">
        <div style="background:linear-gradient(135deg,#1C3882,#0f1f4f);padding:2rem;border-radius:16px;margin-bottom:1.5rem">
            <h1 style="color:white;margin:0;font-size:1.8rem;font-weight:800">NL IMOVEIS</h1>
            <p style="color:#F0A500;margin:0.3rem 0 0;font-size:0.85rem;font-weight:600">PAINEL ESTRATEGICO</p>
            <p style="color:rgba(255,255,255,0.5);margin:0.2rem 0 0;font-size:0.72rem">CRECI 1440 J · Natal/RN</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        st.markdown("#### Acesso ao Painel")
        email = st.text_input("Email", placeholder="seu@email.com")
        senha = st.text_input("Senha", type="password", placeholder="Sua senha")
        submit = st.form_submit_button("Entrar", use_container_width=True)

        if submit:
            if not email or not senha:
                st.error("Preencha email e senha.")
            else:
                user = autenticar_usuario(email, senha)
                if user:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario"] = {
                        "id": user["id"],
                        "nome": user["nome"],
                        "email": user["email"],
                        "perfil": user["perfil"],
                    }
                    st.rerun()
                else:
                    st.error("Email ou senha incorretos.")

    st.markdown("""
    <div style="text-align:center;margin-top:2rem;color:#9CA3AF;font-size:0.75rem">
        Acesso restrito a equipe NL Imoveis<br>
        Solicite seu cadastro ao gerente
    </div>
    """, unsafe_allow_html=True)
