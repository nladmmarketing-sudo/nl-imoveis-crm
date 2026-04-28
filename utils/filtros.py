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


def _opcoes_ano_atual() -> list[str]:
    """Todos os 12 meses do ano atual (Janeiro/2026, Fevereiro/2026, ..., Dezembro/2026)."""
    ano = datetime.now().year
    return [f"{_MESES_PT[m]}/{ano}" for m in range(1, 13)]


def _opcoes_ano_anterior() -> list[str]:
    """Todos os 12 meses do ano anterior."""
    ano = datetime.now().year - 1
    return [f"{_MESES_PT[m]}/{ano}" for m in range(1, 13)]


def todas_opcoes() -> list[str]:
    """
    Lista completa do filtro de periodo:
    - Atalhos rapidos (Hoje, 7d, 30d, mes atual, etc)
    - Todos os meses do ano atual
    - Anos completos (atual + anterior)
    - Todos os meses do ano anterior (historico)
    """
    ano_atual = datetime.now().year
    ano_anterior = ano_atual - 1

    atalhos_keys = list(ATALHOS.keys())
    return (
        atalhos_keys
        + [f"── {ano_atual} ──"]
        + _opcoes_ano_atual()
        + [f"── Anos ──"]
        + [f"Ano {ano_atual}", f"Ano {ano_anterior}"]
        + [f"── {ano_anterior} ──"]
        + _opcoes_ano_anterior()
    )


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
    # Se selecionar um separador (── XXX ──), trata como "Tudo"
    if periodo and periodo.startswith("──"):
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


def periodo_anterior(periodo: str) -> str:
    """
    Retorna o periodo anterior para comparativos.
    Exemplos:
      'Abril/2026' → 'Marco/2026'
      'Janeiro/2026' → 'Dezembro/2025'
      'Este mes' → 'Ultimo mes'
      'Ultimos 30 dias' → 'periodo de 30-60 dias atras'
      'Ano 2026' → 'Ano 2025'
      'Tudo' → 'Tudo' (sem comparativo)
    """
    if not periodo or periodo.startswith("──"):
        return "Tudo"

    p = _parse_periodo(periodo)

    if p["tipo"] == "tudo":
        return "Tudo"

    if p["tipo"] == "ano":
        return f"Ano {p['ano'] - 1}"

    if p["tipo"] == "mes":
        ano, mes = p["ano"], p["mes"]
        if mes == 1:
            mes_ant, ano_ant = 12, ano - 1
        else:
            mes_ant, ano_ant = mes - 1, ano
        return f"{_MESES_PT[mes_ant]}/{ano_ant}"

    if p["tipo"] == "atalho":
        valor = p["valor"]
        if valor is None:
            return "Tudo"
        if valor == "mes_atual":
            return "Ultimo mes"
        if valor == "mes_anterior":
            # Mes antes do anterior — usa a logica de mes anterior aplicada 2x
            hoje = datetime.now()
            primeiro_atual = datetime(hoje.year, hoje.month, 1)
            ultimo_anterior = primeiro_atual - timedelta(days=1)
            primeiro_anterior = datetime(ultimo_anterior.year, ultimo_anterior.month, 1)
            ultimo_pre_anterior = primeiro_anterior - timedelta(days=1)
            return f"{_MESES_PT[ultimo_pre_anterior.month]}/{ultimo_pre_anterior.year}"
        if isinstance(valor, int):
            # Para "Ultimos N dias", retornamos um marcador especial
            return f"_dias_anteriores_{valor}"

    return "Tudo"


def aplicar_filtro_periodo_anterior(df: pd.DataFrame, periodo: str,
                                     coluna_data: str = "created_at") -> pd.DataFrame:
    """
    Aplica filtro pegando o periodo IMEDIATAMENTE ANTERIOR.
    Para 'Ultimos 30 dias': pega de 60 a 30 dias atras (mesma duracao).
    """
    if df.empty or coluna_data not in df.columns:
        return df

    df = df.copy()
    df["_data_filtro"] = pd.to_datetime(df[coluna_data], errors="coerce", utc=True)
    df["_data_filtro"] = df["_data_filtro"].dt.tz_localize(None)
    df = df.dropna(subset=["_data_filtro"])

    p = _parse_periodo(periodo)
    agora = datetime.now()

    if p["tipo"] == "atalho" and isinstance(p.get("valor"), int):
        dias = p["valor"]
        if dias == 0:
            # ontem
            ontem = (agora - timedelta(days=1)).date()
            resultado = df[df["_data_filtro"].dt.date == ontem]
        else:
            inicio = agora - timedelta(days=dias * 2)
            fim = agora - timedelta(days=dias)
            resultado = df[(df["_data_filtro"] >= inicio) & (df["_data_filtro"] < fim)]
    else:
        # Para mes/ano: usa periodo_anterior + aplicar_filtro
        anterior = periodo_anterior(periodo)
        if anterior.startswith("_dias_anteriores_") or anterior == "Tudo":
            return df.iloc[0:0]  # Sem comparativo
        return aplicar_filtro(df, anterior, coluna_data)

    return resultado.drop(columns=["_data_filtro"], errors="ignore")
