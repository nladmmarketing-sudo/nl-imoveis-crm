"""
Configuracoes persistentes do painel (metas, parametros, etc)
Tabela: config (chave TEXT PRIMARY KEY, valor TEXT, atualizado_em TIMESTAMPTZ)
"""
from utils.supabase_client import get_supabase_client


def get_config(chave: str, default=None) -> str:
    """Le um valor de configuracao"""
    try:
        client = get_supabase_client()
        r = client.table("config").select("valor").eq("chave", chave).execute()
        if r.data and len(r.data) > 0:
            return r.data[0]["valor"]
    except Exception:
        pass
    return default


def set_config(chave: str, valor) -> bool:
    """Grava ou atualiza um valor de configuracao"""
    try:
        client = get_supabase_client()
        client.table("config").upsert({
            "chave": chave,
            "valor": str(valor),
        }, on_conflict="chave").execute()
        return True
    except Exception:
        return False


def get_config_int(chave: str, default: int = 0) -> int:
    """Le configuracao como inteiro"""
    v = get_config(chave, default)
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default
