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
