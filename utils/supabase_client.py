"""
Conexao com Supabase - NL Imoveis CRM
Com cache de 5 minutos para acelerar navegacao entre paginas.
"""
import streamlit as st
from supabase import create_client, Client
import pandas as pd


# Cache de 5 minutos (300 segundos) — tempo razoavel pra dados do CRM
CACHE_TTL = 300


@st.cache_resource
def get_supabase_client() -> Client:
    """Retorna cliente Supabase (cached). So criado uma vez por sessao."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


@st.cache_data(ttl=CACHE_TTL, show_spinner="Carregando dados...")
def fetch_table(table_name: str, order_by: str = None, limit: int = None) -> pd.DataFrame:
    """Busca todos os registros de uma tabela (cached 5min)"""
    client = get_supabase_client()
    query = client.table(table_name).select("*")
    if order_by:
        query = query.order(order_by, desc=True)
    if limit:
        query = query.limit(limit)
    response = query.execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL, show_spinner="Carregando leads...")
def fetch_leads_jetimob(limit: int = None) -> pd.DataFrame:
    """Busca leads do Jetimob (cached 5min)"""
    client = get_supabase_client()
    query = client.table("leads_jetimob").select("*").order("created_at", desc=True)
    if limit:
        query = query.limit(limit)
    response = query.execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL, show_spinner="Carregando vendas...")
def fetch_vendas() -> pd.DataFrame:
    """
    Vendas unificadas: cadastros manuais (vendas_nl) UNION oportunidades ganhas
    do Jetimob (oportunidades_ganhas_jetimob, etapa=Fechamento).

    Retorna um DataFrame com o schema do vendas_nl usado pelas views existentes:
      data_venda, nome_cliente, telefone, email, tipo_negocio (venda|locacao|temporada),
      valor (R$), corretor, origem_lead, codigo_imovel, bairro, comprou_com_nl,
      _source (origem do registro: 'manual' ou 'jetimob').
    """
    client = get_supabase_client()

    # Manual (cadastrado no app)
    manual = client.table("vendas_nl").select("*").order("data_venda", desc=True).execute()
    df_manual = pd.DataFrame(manual.data or [])
    if not df_manual.empty:
        df_manual["_source"] = "manual"

    # Jetimob (oportunidades ganhas em etapa Fechamento)
    jeti = (client.table("oportunidades_ganhas_jetimob")
                  .select("*").eq("etapa", "Fechamento")
                  .order("entrou_etapa_em", desc=True).execute())
    df_jeti = pd.DataFrame(jeti.data or [])
    if not df_jeti.empty:
        df_jeti = pd.DataFrame({
            "id":            ("jeti_" + df_jeti["jetimob_id"].astype(str)),
            "data_venda":    pd.to_datetime(df_jeti["entrou_etapa_em"]).dt.date.astype(str),
            "nome_cliente":  df_jeti["nome_cliente"],
            "telefone":      df_jeti["telefone_e164"],
            "email":         df_jeti["email"],
            "tipo_negocio":  df_jeti["contrato"],
            "valor":         df_jeti["valor_cents"] / 100.0,
            "corretor":      df_jeti["corretor_nome"],
            "origem_lead":   None,
            "codigo_imovel": None,
            "bairro":        None,
            "comprou_com_nl": True,
            "_source":       "jetimob",
        })

    # Junta (se algum DF estiver vazio, usa o outro)
    if df_manual.empty and df_jeti.empty:
        return pd.DataFrame()
    if df_manual.empty:
        return df_jeti
    if df_jeti.empty:
        return df_manual

    # Unifica colunas - preenche faltantes com None nos dois lados
    todas_cols = list(set(df_manual.columns) | set(df_jeti.columns))
    for c in todas_cols:
        if c not in df_manual.columns:
            df_manual[c] = None
        if c not in df_jeti.columns:
            df_jeti[c] = None
    return pd.concat([df_manual[todas_cols], df_jeti[todas_cols]], ignore_index=True)


@st.cache_data(ttl=CACHE_TTL, show_spinner="Carregando ganhas Jetimob...")
def fetch_ganhas_jetimob() -> pd.DataFrame:
    """
    Raw das oportunidades ganhas do Jetimob.
    Util pra views que precisam dos campos crus (etapa, step_id, scraped_at).
    """
    client = get_supabase_client()
    resp = (client.table("oportunidades_ganhas_jetimob")
                  .select("*")
                  .order("entrou_etapa_em", desc=True).execute())
    if not resp.data:
        return pd.DataFrame()
    df = pd.DataFrame(resp.data)
    df["entrou_etapa_em"] = pd.to_datetime(df["entrou_etapa_em"])
    df["valor_reais"] = df["valor_cents"] / 100.0
    return df


@st.cache_data(ttl=CACHE_TTL)
def fetch_corretores_plantao() -> pd.DataFrame:
    """Busca escala de plantao (cached 5min)"""
    client = get_supabase_client()
    response = client.table("corretores_plantao").select("*").order("data", desc=True).execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def fetch_leads_bot() -> pd.DataFrame:
    """Busca leads do bot WhatsApp (cached 5min)"""
    client = get_supabase_client()
    response = client.table("leads").select("*").order("criado_em", desc=True).execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def count_table(table_name: str) -> int:
    """Conta registros de uma tabela (cached 5min)"""
    client = get_supabase_client()
    response = client.table(table_name).select("id", count="exact").execute()
    return response.count or 0


def limpar_cache():
    """Forca recarga dos dados do Supabase (limpa todo cache de dados)"""
    st.cache_data.clear()
