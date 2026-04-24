"""
Sistema de Autenticacao - NL Imoveis CRM
Login com bcrypt, rate limiting, timeout de sessao e controle de perfis.
"""
from __future__ import annotations  # compatibilidade Python 3.9 com type hints X | None
import base64
import re
import time
import html
import unicodedata
from pathlib import Path
import streamlit as st
import bcrypt
import pandas as pd
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


def cadastrar_usuario(
    nome: str,
    email: str,
    senha: str,
    perfil: str = "corretor",
    corretor_nome_jetimob: str | None = None,
) -> tuple[bool, str]:
    """Cadastra novo usuario. Retorna (sucesso, mensagem)."""
    nome = nome.strip()
    email = email.lower().strip()
    nome_jt = (corretor_nome_jetimob or "").strip() or None

    if not nome or not email or not senha:
        return False, "Preencha todos os campos."

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return False, "Email invalido."

    ok, msg = validar_senha_forte(senha)
    if not ok:
        return False, msg

    if perfil not in ("admin", "gerente", "corretor", "marketing"):
        return False, "Perfil invalido."

    if perfil == "corretor" and not nome_jt:
        return False, "Para perfil corretor, informe o nome exato como aparece no Jetimob."

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
                "corretor_nome_jetimob": nome_jt,
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
            .select("id, nome, email, perfil, ativo, criado_em, corretor_nome_jetimob")
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


def atualizar_corretor_jetimob(user_id: int, nome_jetimob: str) -> bool:
    """Atualiza o nome do corretor no Jetimob para um usuario."""
    client = get_supabase_client()
    try:
        valor = (nome_jetimob or "").strip() or None
        response = (
            client.table("usuarios")
            .update({"corretor_nome_jetimob": valor})
            .eq("id", user_id)
            .execute()
        )
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


def is_marketing() -> bool:
    """Marketing = monitora todo o dashboard (visibilidade igual a gerente)"""
    user = get_usuario_atual()
    return user is not None and user.get("perfil") == "marketing"


def pode_ver_tudo() -> bool:
    """True para admin, gerente e marketing. False para corretor / nao-logado."""
    return is_admin() or is_gerente() or is_marketing()


def _normalize(s) -> str:
    """Normaliza string para comparacao: NFKD + remove acentos + strip + casefold.
    'Joao Silva ' e 'JOAO  SILVA' viram iguais; 'Joao' e 'João' tambem.
    """
    return (
        unicodedata.normalize("NFKD", str(s or ""))
        .encode("ASCII", "ignore")
        .decode()
        .strip()
        .casefold()
    )


def filtrar_por_perfil(df: pd.DataFrame, coluna_corretor: str = "corretor") -> pd.DataFrame:
    """
    Aplica filtro de visibilidade por perfil (defesa em profundidade no backend).
    - Admin/Gerente/Marketing: retorna df inalterado
    - Corretor: retorna apenas linhas onde coluna_corretor casa com corretor_nome_jetimob
      (comparacao normalizada: ignora case, acento, espaco)
    - Corretor sem mapeamento, sem usuario logado, perfil desconhecido,
      ou coluna ausente: retorna DataFrame vazio (fail-closed)
    """
    user = get_usuario_atual()
    if user is None:
        return df.iloc[0:0]

    perfil = (user.get("perfil") or "").lower()
    if perfil in ("admin", "gerente", "marketing"):
        return df

    if perfil == "corretor":
        nome_jt = (user.get("corretor_nome_jetimob") or "").strip()
        if not nome_jt:
            return df.iloc[0:0]
        if df.empty:
            return df
        if coluna_corretor not in df.columns:
            # Fail-closed: coluna esperada nao existe, nao da pra filtrar com seguranca
            return df.iloc[0:0]
        alvo = _normalize(nome_jt)
        return df[df[coluna_corretor].apply(_normalize) == alvo]

    # Perfil desconhecido — fail-closed
    return df.iloc[0:0]


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

@st.cache_data(show_spinner=False)
def _logo_login_data_url() -> str:
    path = Path(__file__).resolve().parent.parent / "assets" / "brand" / "logo" / "nl-logo-principal.png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def render_login():
    """Renderiza pagina de login"""
    st.markdown("""
    <style>
        [data-testid="stSidebar"] { display: none; }
        .main .block-container { max-width: 480px; padding-top: 3rem; }
    </style>
    """, unsafe_allow_html=True)

    logo_url = _logo_login_data_url()
    st.markdown(f"""
    <div style="text-align:center;margin-bottom:2rem">
        <div style="background:linear-gradient(135deg,#033677,#001833);padding:2.2rem 2rem 1.8rem;border-radius:16px;margin-bottom:1.5rem">
            <img src="{logo_url}" alt="NL Imoveis"
                 style="max-width:220px;width:70%;height:auto;
                        filter:brightness(0) invert(1);margin-bottom:0.8rem">
            <p style="color:#FFB700;margin:0.3rem 0 0;font-size:0.8rem;font-weight:600;letter-spacing:1.5px">PAINEL ESTRATEGICO</p>
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
                        "corretor_nome_jetimob": user.get("corretor_nome_jetimob"),
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
