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
    """Busca vendas (cached 5min)"""
    client = get_supabase_client()
    response = client.table("vendas_nl").select("*").order("data_venda", desc=True).execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()


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
