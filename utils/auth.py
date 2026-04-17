"""
Sistema de Autenticacao - NL Imoveis CRM
Login com bcrypt, rate limiting, timeout de sessao e controle de perfis.
"""
import re
import time
import html
import streamlit as st
import bcrypt
from datetime import datetime, timedelta, timezone
from utils.supabase_client import get_supabase_client


# --- Constantes de seguranca ---
SESSAO_DURACAO_HORAS = 8
MAX_TENTATIVAS_LOGIN = 5
BLOQUEIO_MINUTOS = 15
SENHA_MIN_LENGTH = 8


# ---------- UTILS ----------

def hash_senha(senha: str) -> str:
    """Gera hash bcrypt da senha"""
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Verifica se a senha confere com o hash"""
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
    except Exception:
        return False


def validar_senha_forte(senha: str) -> tuple[bool, str]:
    """
    Valida politica de senha: 8+ caracteres, 1 letra e 1 numero.
    Retorna (ok, mensagem_erro).
    """
    if len(senha) < SENHA_MIN_LENGTH:
        return False, f"Senha precisa ter no minimo {SENHA_MIN_LENGTH} caracteres."
    if not re.search(r"[A-Za-z]", senha):
        return False, "Senha precisa ter pelo menos uma letra."
    if not re.search(r"\d", senha):
        return False, "Senha precisa ter pelo menos um numero."
    return True, ""


def escape(valor) -> str:
    """HTML escape para prevenir XSS em markdown com unsafe_allow_html=True"""
    return html.escape(str(valor or ""))


# ---------- RATE LIMITING ----------

def _registrar_tentativa(email: str, sucesso: bool):
    """Registra tentativa de login na tabela de auditoria"""
    client = get_supabase_client()
    try:
        client.table("login_attempts").insert({
            "email": email.lower().strip(),
            "sucesso": sucesso,
        }).execute()
    except Exception:
        pass  # Nao falha o login se log der erro


def _conta_tentativas_recentes(email: str) -> int:
    """Conta tentativas falhas dos ultimos BLOQUEIO_MINUTOS"""
    client = get_supabase_client()
    try:
        desde = (datetime.now(timezone.utc) - timedelta(minutes=BLOQUEIO_MINUTOS)).isoformat()
        response = (
            client.table("login_attempts")
            .select("id", count="exact")
            .eq("email", email.lower().strip())
            .eq("sucesso", False)
            .gte("criado_em", desde)
            .execute()
        )
        return response.count or 0
    except Exception:
        return 0


def _email_bloqueado(email: str) -> bool:
    """Verifica se email excedeu limite de tentativas"""
    return _conta_tentativas_recentes(email) >= MAX_TENTATIVAS_LOGIN


# ---------- AUTENTICACAO ----------

def autenticar_usuario(email: str, senha: str) -> tuple[dict | None, str]:
    """
    Busca usuario por email e verifica senha.
    Retorna (dict_usuario, mensagem_erro). Usuario None se falhar.
    """
    email = email.lower().strip()

    # Rate limiting
    if _email_bloqueado(email):
        return None, f"Muitas tentativas erradas. Aguarde {BLOQUEIO_MINUTOS} minutos."

    client = get_supabase_client()
    try:
        response = (
            client.table("usuarios")
            .select("*")
            .eq("email", email)
            .eq("ativo", True)
            .execute()
        )

        if response.data and len(response.data) > 0:
            user = response.data[0]
            if verificar_senha(senha, user["senha_hash"]):
                _registrar_tentativa(email, sucesso=True)
                return user, ""

        # Mensagem generica (nao revela se email existe)
        _registrar_tentativa(email, sucesso=False)
        # Delay constante pra evitar timing attack
        time.sleep(0.3)
        return None, "Email ou senha incorretos."
    except Exception:
        return None, "Nao foi possivel autenticar. Tente novamente."


def cadastrar_usuario(nome: str, email: str, senha: str, perfil: str = "corretor") -> tuple[bool, str]:
    """Cadastra novo usuario. Retorna (sucesso, mensagem)."""
    nome = nome.strip()
    email = email.lower().strip()

    if not nome or not email or not senha:
        return False, "Preencha todos os campos."

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return False, "Email invalido."

    ok, msg = validar_senha_forte(senha)
    if not ok:
        return False, msg

    if perfil not in ("admin", "gerente", "corretor"):
        return False, "Perfil invalido."

    client = get_supabase_client()
    try:
        response = (
            client.table("usuarios")
            .insert({
                "nome": nome,
                "email": email,
                "senha_hash": hash_senha(senha),
                "perfil": perfil,
                "ativo": True,
            })
            .execute()
        )
        if response.data:
            return True, "Usuario cadastrado com sucesso."
        return False, "Nao foi possivel cadastrar."
    except Exception as e:
        msg = str(e).lower()
        if "duplicate" in msg or "unique" in msg:
            return False, "Este email ja esta cadastrado."
        return False, "Erro ao cadastrar. Tente novamente."


def alterar_senha(user_id: int, senha_atual: str, senha_nova: str) -> tuple[bool, str]:
    """Altera senha do proprio usuario (requer senha atual)"""
    ok, msg = validar_senha_forte(senha_nova)
    if not ok:
        return False, msg

    client = get_supabase_client()
    try:
        response = client.table("usuarios").select("*").eq("id", user_id).execute()
        if not response.data:
            return False, "Usuario nao encontrado."

        user = response.data[0]
        if not verificar_senha(senha_atual, user["senha_hash"]):
            return False, "Senha atual incorreta."

        novo_hash = hash_senha(senha_nova)
        client.table("usuarios").update({"senha_hash": novo_hash}).eq("id", user_id).execute()
        return True, "Senha alterada com sucesso."
    except Exception:
        return False, "Erro ao alterar senha."


def resetar_senha_por_gerente(user_id: int, senha_nova: str) -> tuple[bool, str]:
    """Gerente reseta senha de outro usuario"""
    ok, msg = validar_senha_forte(senha_nova)
    if not ok:
        return False, msg
    client = get_supabase_client()
    try:
        novo_hash = hash_senha(senha_nova)
        client.table("usuarios").update({"senha_hash": novo_hash}).eq("id", user_id).execute()
        return True, "Senha resetada."
    except Exception:
        return False, "Erro ao resetar senha."


def listar_usuarios() -> list:
    """Lista todos os usuarios (sem senha_hash)"""
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
    client = get_supabase_client()
    try:
        response = client.table("usuarios").update({"ativo": ativo}).eq("id", user_id).execute()
        return bool(response.data)
    except Exception:
        return False


# ---------- SESSAO ----------

def usuario_logado() -> bool:
    """Verifica autenticacao + timeout de sessao"""
    if not st.session_state.get("autenticado", False):
        return False

    # Verifica timeout
    inicio = st.session_state.get("sessao_inicio")
    if inicio is None:
        logout()
        return False

    if datetime.now(timezone.utc) - inicio > timedelta(hours=SESSAO_DURACAO_HORAS):
        logout()
        st.warning(f"Sua sessao expirou ({SESSAO_DURACAO_HORAS}h). Faca login novamente.")
        return False

    return True


def get_usuario_atual() -> dict | None:
    if usuario_logado():
        return st.session_state.get("usuario", None)
    return None


def is_admin() -> bool:
    """Admin = Anderson = quem pode alterar tudo"""
    user = get_usuario_atual()
    return user is not None and user.get("perfil") == "admin"


def is_gerente() -> bool:
    """Gerente = quem visualiza o painel (inclui admin que ve tudo tambem)"""
    user = get_usuario_atual()
    return user is not None and user.get("perfil") in ("admin", "gerente")


def is_corretor() -> bool:
    """Corretor = acesso restrito (sem dados sensiveis de todos os leads)"""
    user = get_usuario_atual()
    return user is not None and user.get("perfil") == "corretor"


def logout():
    try:
        # Registra logout no log antes de limpar sessao
        user = st.session_state.get("usuario")
        if user:
            from utils.supabase_client import get_supabase_client
            client = get_supabase_client()
            client.table("auditoria").insert({
                "usuario_id": user.get("id"),
                "usuario_email": user.get("email", ""),
                "acao": "logout",
                "detalhes": "",
            }).execute()
    except Exception:
        pass
    st.session_state["autenticado"] = False
    st.session_state["usuario"] = None
    st.session_state["sessao_inicio"] = None


# ---------- RENDER ----------

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
                user, erro = autenticar_usuario(email, senha)
                if user:
                    st.session_state["autenticado"] = True
                    st.session_state["sessao_inicio"] = datetime.now(timezone.utc)
                    st.session_state["usuario"] = {
                        "id": user["id"],
                        "nome": user["nome"],
                        "email": user["email"],
                        "perfil": user["perfil"],
                    }
                    # Registra login no log de auditoria
                    try:
                        client = get_supabase_client()
                        client.table("auditoria").insert({
                            "usuario_id": user["id"],
                            "usuario_email": user["email"],
                            "acao": "login_sucesso",
                            "detalhes": f"perfil: {user['perfil']}",
                        }).execute()
                    except Exception:
                        pass
                    st.rerun()
                else:
                    # Registra tentativa falha
                    try:
                        client = get_supabase_client()
                        client.table("auditoria").insert({
                            "usuario_email": email.lower().strip() or "sem_email",
                            "acao": "login_falha",
                            "detalhes": erro,
                        }).execute()
                    except Exception:
                        pass
                    st.error(erro)

    st.markdown("""
    <div style="text-align:center;margin-top:2rem;color:#9CA3AF;font-size:0.75rem">
        Acesso restrito a equipe NL Imoveis<br>
        Solicite seu cadastro ao gerente
    </div>
    """, unsafe_allow_html=True)
