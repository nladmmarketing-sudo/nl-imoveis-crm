"""
Conexao com Supabase - NL Imoveis CRM
Com cache de 5 minutos para acelerar navegacao entre paginas.
Tambem com paginacao automatica pra contornar limite de 1000 registros do Supabase.
"""
import streamlit as st
from supabase import create_client, Client
import pandas as pd


# Cache de 5 minutos (300 segundos) — tempo razoavel pra dados do CRM
CACHE_TTL = 300

# Tamanho da pagina pra fetch paginado (Supabase limita a 1000 por query)
PAGE_SIZE = 1000


@st.cache_resource
def get_supabase_client() -> Client:
    """Retorna cliente Supabase (cached). So criado uma vez por sessao."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def _fetch_all_paginated(table_name: str, order_by: str | None = None,
                         desc: bool = True, filter_eq: dict | None = None) -> list:
    """
    Busca TODOS os registros de uma tabela usando paginacao.
    Necessario porque Supabase limita queries a 1000 registros.
    """
    client = get_supabase_client()
    todos = []
    inicio = 0

    while True:
        query = client.table(table_name).select("*")
        if filter_eq:
            for col, val in filter_eq.items():
                query = query.eq(col, val)
        if order_by:
            query = query.order(order_by, desc=desc)

        # Range pega de inicio ate inicio+PAGE_SIZE-1 (inclusivo)
        query = query.range(inicio, inicio + PAGE_SIZE - 1)
        response = query.execute()

        if not response.data:
            break

        todos.extend(response.data)

        # Se retornou menos que PAGE_SIZE, acabou
        if len(response.data) < PAGE_SIZE:
            break

        inicio += PAGE_SIZE

    return todos


@st.cache_data(ttl=CACHE_TTL, show_spinner="Carregando dados...")
def fetch_table(table_name: str, order_by: str = None, limit: int = None) -> pd.DataFrame:
    """Busca registros de uma tabela. Se limit for None, busca TODOS (paginado)."""
    if limit is None:
        # Sem limite explicito: paginacao para pegar todos
        data = _fetch_all_paginated(table_name, order_by=order_by, desc=True)
        return pd.DataFrame(data) if data else pd.DataFrame()

    client = get_supabase_client()
    query = client.table(table_name).select("*")
    if order_by:
        query = query.order(order_by, desc=True)
    query = query.limit(limit)
    response = query.execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL, show_spinner="Carregando leads...")
def fetch_leads_jetimob(limit: int = None) -> pd.DataFrame:
    """Busca leads do Jetimob (cached 5min). Sem limit, busca TODOS via paginacao."""
    if limit is None:
        # Paginacao para pegar todos os ~18k leads
        data = _fetch_all_paginated("leads_jetimob", order_by="created_at", desc=True)
        return pd.DataFrame(data) if data else pd.DataFrame()

    client = get_supabase_client()
    query = client.table("leads_jetimob").select("*").order("created_at", desc=True).limit(limit)
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
    manual_data = _fetch_all_paginated("vendas_nl", order_by="data_venda", desc=True)
    df_manual = pd.DataFrame(manual_data) if manual_data else pd.DataFrame()
    if not df_manual.empty:
        df_manual["_source"] = "manual"

    # Jetimob (oportunidades ganhas em etapa Fechamento)
    jeti_data = _fetch_all_paginated(
        "oportunidades_ganhas_jetimob",
        order_by="entrou_etapa_em",
        desc=True,
        filter_eq={"etapa": "Fechamento"},
    )
    df_jeti = pd.DataFrame(jeti_data) if jeti_data else pd.DataFrame()
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
    """Raw das oportunidades ganhas do Jetimob (paginado)."""
    data = _fetch_all_paginated("oportunidades_ganhas_jetimob",
                                 order_by="entrou_etapa_em", desc=True)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df["entrou_etapa_em"] = pd.to_datetime(df["entrou_etapa_em"])
    df["valor_reais"] = df["valor_cents"] / 100.0
    return df


@st.cache_data(ttl=CACHE_TTL)
def fetch_corretores_plantao() -> pd.DataFrame:
    """Busca escala de plantao (cached 5min)"""
    data = _fetch_all_paginated("corretores_plantao", order_by="data", desc=True)
    return pd.DataFrame(data) if data else pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def fetch_leads_bot() -> pd.DataFrame:
    """Busca leads do bot WhatsApp (cached 5min)"""
    data = _fetch_all_paginated("leads", order_by="criado_em", desc=True)
    return pd.DataFrame(data) if data else pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def count_table(table_name: str) -> int:
    """Conta registros de uma tabela (cached 5min)"""
    client = get_supabase_client()
    response = client.table(table_name).select("id", count="exact").execute()
    return response.count or 0


def limpar_cache():
    """Forca recarga dos dados do Supabase (limpa todo cache de dados)"""
    st.cache_data.clear()
