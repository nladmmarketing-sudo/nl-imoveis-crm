"""
Conexao com Supabase - NL Imoveis CRM
"""
import streamlit as st
from supabase import create_client, Client
import pandas as pd


@st.cache_resource
def get_supabase_client() -> Client:
    """Retorna cliente Supabase (cached)"""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def fetch_table(table_name: str, order_by: str = None, limit: int = None) -> pd.DataFrame:
    """Busca todos os registros de uma tabela e retorna DataFrame"""
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


def fetch_leads_jetimob(limit: int = None) -> pd.DataFrame:
    """Busca leads do Jetimob"""
    return fetch_table("leads_jetimob", order_by="created_at", limit=limit)


def fetch_vendas() -> pd.DataFrame:
    """Busca vendas"""
    return fetch_table("vendas_nl", order_by="data_venda")


def fetch_corretores_plantao() -> pd.DataFrame:
    """Busca escala de plantao"""
    return fetch_table("corretores_plantao", order_by="data")


def fetch_leads_bot() -> pd.DataFrame:
    """Busca leads do bot WhatsApp"""
    return fetch_table("leads", order_by="criado_em")


def count_table(table_name: str) -> int:
    """Conta registros de uma tabela"""
    client = get_supabase_client()
    response = client.table(table_name).select("id", count="exact").execute()
    return response.count or 0
