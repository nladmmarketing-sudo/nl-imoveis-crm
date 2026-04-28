"""
Filtros globais de periodo — aplicados em todas as paginas do dashboard.
Suporta atalhos (Hoje, Ultimo mes, etc) E mes/ano especifico.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta


_MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Marco", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


# Atalhos rapidos
ATALHOS = {
    "Hoje": 0,
    "Ultimos 7 dias": 7,
    "Ultimos 30 dias": 30,
    "Ultimos 90 dias": 90,
    "Este mes": "mes_atual",
    "Ultimo mes": "mes_anterior",
    "Tudo": None,
}


def _opcoes_meses_anos() -> list[str]:
    """
    Gera lista de meses individuais (ultimos 24 meses) + anos completos.
    Mostra do mais recente pro mais antigo.
    """
    hoje = datetime.now()
    opcoes = []

    # Meses individuais — 24 meses pra tras
    for i in range(24):
        ano = hoje.year
        mes = hoje.month - i
        while mes <= 0:
            mes += 12
            ano -= 1
        opcoes.append(f"{_MESES_PT[mes]}/{ano}")

    # Anos completos
    anos_unicos = sorted({datetime(hoje.year, hoje.month, 1).year - i for i in range(3)}, reverse=True)
    for a in anos_unicos:
        opcoes.append(f"Ano {a}")

    return opcoes


def todas_opcoes() -> list[str]:
    """Lista completa de opcoes do filtro: atalhos + meses + anos"""
    atalhos_keys = list(ATALHOS.keys())
    meses_anos = _opcoes_meses_anos()
    # Separador visual
    return atalhos_keys + ["── Meses ──"] + meses_anos


def seletor_periodo(key: str = "periodo_global") -> str:
    """Renderiza seletor de periodo no sidebar."""
    opcoes = todas_opcoes()
    periodo = st.selectbox(
        "📅 Periodo",
        opcoes,
        index=opcoes.index("Este mes"),  # Padrao: mes atual
        key=key,
        help="Filtra todos os dashboards pelo periodo selecionado",
    )
    # Se selecionar o separador, trata como "Tudo"
    if periodo == "── Meses ──":
        return "Tudo"
    return periodo


def _parse_periodo(periodo: str) -> dict:
    """
    Converte string do periodo num dict com instrucao do filtro.
    Retorna { tipo: 'atalho'|'mes'|'ano'|'tudo', ... }
    """
    if periodo in ATALHOS:
        return {"tipo": "atalho", "valor": ATALHOS[periodo]}

    # "Mes/Ano" tipo "Abril/2026"
    if "/" in periodo:
        partes = periodo.split("/")
        if len(partes) == 2:
            mes_nome, ano_str = partes
            mes_num = next((k for k, v in _MESES_PT.items() if v == mes_nome.strip()), None)
            try:
                ano_num = int(ano_str.strip())
                if mes_num:
                    return {"tipo": "mes", "ano": ano_num, "mes": mes_num}
            except ValueError:
                pass

    # "Ano XXXX"
    if periodo.startswith("Ano "):
        try:
            ano = int(periodo.replace("Ano ", "").strip())
            return {"tipo": "ano", "ano": ano}
        except ValueError:
            pass

    return {"tipo": "tudo"}


def aplicar_filtro(df: pd.DataFrame, periodo: str, coluna_data: str = "created_at") -> pd.DataFrame:
    """Filtra um DataFrame pelo periodo escolhido."""
    if df.empty or coluna_data not in df.columns:
        return df

    p = _parse_periodo(periodo)

    # Converte coluna pra datetime tz-naive
    df = df.copy()
    df["_data_filtro"] = pd.to_datetime(df[coluna_data], errors="coerce", utc=True)
    df["_data_filtro"] = df["_data_filtro"].dt.tz_localize(None)
    df = df.dropna(subset=["_data_filtro"])

    agora = datetime.now()

    if p["tipo"] == "tudo":
        resultado = df
    elif p["tipo"] == "ano":
        resultado = df[df["_data_filtro"].dt.year == p["ano"]]
    elif p["tipo"] == "mes":
        resultado = df[
            (df["_data_filtro"].dt.year == p["ano"]) &
            (df["_data_filtro"].dt.month == p["mes"])
        ]
    elif p["tipo"] == "atalho":
        valor = p["valor"]
        if valor is None:
            resultado = df
        elif valor == 0:
            resultado = df[df["_data_filtro"].dt.date == agora.date()]
        elif valor == "mes_atual":
            resultado = df[
                (df["_data_filtro"].dt.year == agora.year) &
                (df["_data_filtro"].dt.month == agora.month)
            ]
        elif valor == "mes_anterior":
            primeiro_mes = datetime(agora.year, agora.month, 1)
            ultimo_anterior = primeiro_mes - timedelta(days=1)
            resultado = df[
                (df["_data_filtro"].dt.year == ultimo_anterior.year) &
                (df["_data_filtro"].dt.month == ultimo_anterior.month)
            ]
        elif isinstance(valor, int):
            inicio = agora - timedelta(days=valor)
            resultado = df[df["_data_filtro"] >= inicio]
        else:
            resultado = df
    else:
        resultado = df

    return resultado.drop(columns=["_data_filtro"], errors="ignore")


def legenda_periodo(periodo: str) -> str:
    """Descricao amigavel pra exibir no header"""
    return periodo
