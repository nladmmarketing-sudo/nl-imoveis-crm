"""
Filtros globais de periodo — aplicados em todas as paginas do dashboard.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta


PERIODOS = {
    "Hoje": 0,
    "Ultimos 7 dias": 7,
    "Ultimos 30 dias": 30,
    "Este mes": "mes_atual",
    "Ultimo mes": "mes_anterior",
    "Ultimos 90 dias": 90,
    "Ano atual": "ano_atual",
    "Tudo": None,
}


def seletor_periodo(key: str = "periodo_global") -> str:
    """
    Renderiza seletor de periodo no sidebar e retorna periodo escolhido.
    """
    periodo = st.selectbox(
        "📅 Periodo",
        list(PERIODOS.keys()),
        index=2,  # Padrao: Ultimos 30 dias
        key=key,
        help="Filtra todos os dashboards pelo periodo selecionado",
    )
    return periodo


def aplicar_filtro(df: pd.DataFrame, periodo: str, coluna_data: str = "created_at") -> pd.DataFrame:
    """
    Filtra um DataFrame pelo periodo escolhido.
    Usa a coluna de data passada (default: created_at).
    """
    if df.empty or coluna_data not in df.columns:
        return df

    valor = PERIODOS.get(periodo)

    # Converte coluna pra datetime
    df = df.copy()
    df["_data_filtro"] = pd.to_datetime(df[coluna_data], errors="coerce")
    df = df.dropna(subset=["_data_filtro"])

    agora = datetime.now()

    if valor is None:
        # "Tudo" — sem filtro
        resultado = df
    elif valor == 0:
        # Hoje
        hoje = agora.date()
        resultado = df[df["_data_filtro"].dt.date == hoje]
    elif valor == "mes_atual":
        resultado = df[
            (df["_data_filtro"].dt.year == agora.year) &
            (df["_data_filtro"].dt.month == agora.month)
        ]
    elif valor == "mes_anterior":
        primeiro_mes_atual = datetime(agora.year, agora.month, 1)
        ultimo_mes_anterior = primeiro_mes_atual - timedelta(days=1)
        resultado = df[
            (df["_data_filtro"].dt.year == ultimo_mes_anterior.year) &
            (df["_data_filtro"].dt.month == ultimo_mes_anterior.month)
        ]
    elif valor == "ano_atual":
        resultado = df[df["_data_filtro"].dt.year == agora.year]
    elif isinstance(valor, int):
        inicio = agora - timedelta(days=valor)
        resultado = df[df["_data_filtro"] >= inicio]
    else:
        resultado = df

    return resultado.drop(columns=["_data_filtro"], errors="ignore")


def legenda_periodo(periodo: str) -> str:
    """Descricao do periodo pra exibir no header"""
    return periodo
