"""
Log de auditoria — registra acoes importantes no sistema
Tabela: auditoria (id, usuario_id, usuario_email, acao, detalhes, criado_em)
"""
from utils.supabase_client import get_supabase_client
from utils.auth import get_usuario_atual


def registrar(acao: str, detalhes: str = ""):
    """
    Registra uma acao no log de auditoria.
    Exemplos:
        registrar('login', 'sucesso')
        registrar('cadastrou_usuario', 'Joane')
        registrar('alterou_meta', 'meta_vgv: 3000000 -> 4000000')
        registrar('desativou_usuario', 'user_id=5')
    """
    user = get_usuario_atual()
    try:
        client = get_supabase_client()
        client.table("auditoria").insert({
            "usuario_id": user["id"] if user else None,
            "usuario_email": user["email"] if user else "anonimo",
            "acao": acao[:100],
            "detalhes": detalhes[:500],
        }).execute()
    except Exception:
        pass  # Nao trava o app se log falhar


def listar_recentes(limit: int = 100) -> list:
    """Lista ultimas N acoes do log"""
    client = get_supabase_client()
    try:
        response = (
            client.table("auditoria")
            .select("*")
            .order("criado_em", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception:
        return []


def contar_registros() -> dict:
    """Conta registros nas tabelas de auditoria e login_attempts"""
    client = get_supabase_client()
    try:
        r1 = client.table("auditoria").select("id", count="exact").execute()
        r2 = client.table("login_attempts").select("id", count="exact").execute()
        return {
            "auditoria": r1.count or 0,
            "login_attempts": r2.count or 0,
        }
    except Exception:
        return {"auditoria": 0, "login_attempts": 0}


def limpar_antigos(dias_auditoria: int = 90, dias_login: int = 30) -> dict:
    """
    Apaga registros antigos das tabelas.
    Retorna dict com quantidade apagada de cada tabela.
    """
    from datetime import datetime, timedelta, timezone
    client = get_supabase_client()
    resultado = {"auditoria": 0, "login_attempts": 0}

    try:
        # Conta antes
        antes_aud = client.table("auditoria").select("id", count="exact").execute().count or 0
        antes_log = client.table("login_attempts").select("id", count="exact").execute().count or 0

        # Apaga auditoria antiga
        corte_aud = (datetime.now(timezone.utc) - timedelta(days=dias_auditoria)).isoformat()
        client.table("auditoria").delete().lt("criado_em", corte_aud).execute()

        # Apaga login_attempts antigos
        corte_log = (datetime.now(timezone.utc) - timedelta(days=dias_login)).isoformat()
        client.table("login_attempts").delete().lt("criado_em", corte_log).execute()

        # Conta depois
        depois_aud = client.table("auditoria").select("id", count="exact").execute().count or 0
        depois_log = client.table("login_attempts").select("id", count="exact").execute().count or 0

        resultado["auditoria"] = antes_aud - depois_aud
        resultado["login_attempts"] = antes_log - depois_log
    except Exception:
        pass

    return resultado
