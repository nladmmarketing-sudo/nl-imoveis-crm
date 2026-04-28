"""
Vendas Jetimob - KPIs, ranking e evolução OFICIAL das vendas (relatório Jetimob).

VENDAS: usa tabela `resumo_mensal_jetimob` (raspagem do relatório oficial do
Jetimob — bate 100% com o que Anderson vê na tela de relatórios do CRM).

LOCAÇÕES: usa `oportunidades_ganhas_jetimob` (sync kanban), pois o relatório
oficial só tem venda.

Detalhe (lista de cada venda individual): usa `oportunidades_ganhas_jetimob`.
"""
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.auth import escape, get_usuario_atual, is_corretor, pode_ver_tudo
from utils.supabase_client import get_supabase_client


_MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


@st.cache_data(ttl=300, show_spinner="Carregando resumo oficial Jetimob...")
def _fetch_resumo_mensal() -> pd.DataFrame:
    """Tabela resumo_mensal_jetimob — totais oficiais do Jetimob."""
    client = get_supabase_client()
    resp = (client.table("resumo_mensal_jetimob").select("*")
                  .order("mes_referencia", desc=True).execute())
    if not resp.data:
        return pd.DataFrame()
    df = pd.DataFrame(resp.data)
    df["mes_referencia"] = pd.to_datetime(df["mes_referencia"]).dt.date
    df["valor_reais"] = df["valor_total_cents"] / 100.0
    return df


@st.cache_data(ttl=300, show_spinner="Carregando ganhas Jetimob...")
def _fetch_ganhas() -> pd.DataFrame:
    """Tabela oportunidades_ganhas_jetimob — lista individual pra detalhe."""
    client = get_supabase_client()
    resp = (client.table("oportunidades_ganhas_jetimob").select("*")
                  .order("entrou_etapa_em", desc=True).execute())
    if not resp.data:
        return pd.DataFrame()
    df = pd.DataFrame(resp.data)
    df["entrou_etapa_em"] = pd.to_datetime(df["entrou_etapa_em"])
    df["valor_reais"] = df["valor_cents"] / 100.0
    return df


def _kpi_card(label: str, valor: str, sub: str, kind: str = "") -> str:
    cls = f"kpi-card {kind}".strip()
    return (
        f'<div class="{cls}">'
        f'  <div class="label">{escape(label)}</div>'
        f'  <div class="num">{escape(valor)}</div>'
        f'  <div class="sub">{escape(sub)}</div>'
        f'</div>'
    )


def _fmt_brl(v: float) -> str:
    return f"R$ {v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _resolver_mes_do_periodo(periodo: str) -> tuple[int, int, str]:
    """
    Converte periodo do filtro global em (ano, mes, label).
    Se for 'Mes/Ano' especifico, usa esse. Senao usa mes atual.
    """
    hoje = date.today()
    if periodo and "/" in periodo:
        partes = periodo.split("/")
        if len(partes) == 2:
            mes_nome, ano_str = partes
            mes_num = next((k for k, v in _MESES_PT.items() if v == mes_nome.strip()), None)
            try:
                ano = int(ano_str.strip())
                if mes_num:
                    return ano, mes_num, f"{_MESES_PT[mes_num]}/{ano}"
            except ValueError:
                pass
    if periodo == "Ultimo mes":
        primeiro = date(hoje.year, hoje.month, 1)
        ultimo_anterior = primeiro - pd.Timedelta(days=1)
        return ultimo_anterior.year, ultimo_anterior.month, f"{_MESES_PT[ultimo_anterior.month]}/{ultimo_anterior.year}"
    return hoje.year, hoje.month, f"{_MESES_PT[hoje.month]}/{hoje.year}"


def render() -> None:
    user = get_usuario_atual()
    if not user:
        st.warning("Sessao expirada. Faca login novamente.")
        st.stop()

    periodo_global = st.session_state.get("periodo_global", "Este mes")
    ano_ref, mes_ref, mes_label = _resolver_mes_do_periodo(periodo_global)
    mes_atual_date = date(ano_ref, mes_ref, 1)

    st.markdown(f"""
    <div class="nl-header">
        <div class="badge">Jetimob · Oficial</div>
        <h1>Vendas do <span>Mês</span></h1>
        <div class="sub">Dados oficiais do Jetimob · Periodo: <strong>{escape(mes_label)}</strong> · Mude no filtro do menu lateral</div>
    </div>
    """, unsafe_allow_html=True)

    # =========================================================
    # Fonte-de-verdade: VENDAS vem do resumo oficial
    # =========================================================
    df_resumo = _fetch_resumo_mensal()
    df_ganhas = _fetch_ganhas()

    if df_resumo.empty and df_ganhas.empty:
        st.info("Nenhum dado sincronizado ainda. "
                "Rode `scripts/sync_relatorio_ganhas.py` + `scripts/sync_jetimob_ganhas.py`.")
        return

    # Filtra resumo do mês atual (venda)
    resumo_mes = df_resumo[(df_resumo["mes_referencia"] == mes_atual_date)
                           & (df_resumo["tipo"] == "venda")]

    qtd_vendas = int(resumo_mes["qtd_ganhas"].iloc[0]) if not resumo_mes.empty else 0
    vgv = float(resumo_mes["valor_reais"].iloc[0]) if not resumo_mes.empty else 0.0
    ranking_vendas = (resumo_mes["ranking_json"].iloc[0]
                      if not resumo_mes.empty else []) or []

    # Locações do mês (sync kanban, pois relatório oficial não tem)
    if not df_ganhas.empty:
        ini = pd.Timestamp(ano_ref, mes_ref, 1, tz="UTC")
        fim = ini + pd.offsets.MonthBegin(1)
        df_l_mes = df_ganhas[(df_ganhas["contrato"] == "locacao")
                             & (df_ganhas["etapa"] == "Fechamento")
                             & (df_ganhas["entrou_etapa_em"] >= ini)
                             & (df_ganhas["entrou_etapa_em"] < fim)]
    else:
        df_l_mes = pd.DataFrame()

    qtd_loc = len(df_l_mes)
    valor_loc = float(df_l_mes["valor_reais"].sum()) if qtd_loc else 0.0

    # KPIs
    ticket = vgv / qtd_vendas if qtd_vendas else 0
    cols_kpi = "".join([
        _kpi_card("VGV do Mês", _fmt_brl(vgv),
                  f"{qtd_vendas} venda(s) · Oficial Jetimob", "green"),
        _kpi_card("Locações do Mês", _fmt_brl(valor_loc),
                  f"{qtd_loc} locação(ões)", "azul"),
        _kpi_card("Total Fechamentos", str(qtd_vendas + qtd_loc),
                  escape(mes_label)),
        _kpi_card("Ticket Médio Venda",
                  _fmt_brl(ticket) if ticket else "—",
                  "por venda fechada"),
    ])
    st.markdown(f'<div class="kpi-grid">{cols_kpi}</div>', unsafe_allow_html=True)

    # =========================================================
    # Ranking — Vendas (oficial) + Locações (kanban)
    # =========================================================
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon" style="background:var(--nl-ouro-vivo);">🏆</div>
        <div><h2>Ranking do Mês</h2>
             <p>Vendas: dados oficiais do Jetimob · Locações: kanban</p></div>
    </div>
    """, unsafe_allow_html=True)

    # Consolida: por corretor, somar vendas+locações
    consolidado: dict[str, dict] = {}
    for rk in ranking_vendas:
        nome = rk["nome"]
        consolidado.setdefault(nome, {"venda_q": 0, "venda_v": 0.0,
                                      "loc_q": 0, "loc_v": 0.0})
        consolidado[nome]["venda_q"] += int(rk.get("qtd", 0))
        consolidado[nome]["venda_v"] += float(rk.get("valor_cents", 0)) / 100.0

    if not df_l_mes.empty:
        rk_loc = df_l_mes.groupby("corretor_nome").agg(
            qtd=("jetimob_id", "count"), valor=("valor_reais", "sum")
        ).reset_index()
        for _, row in rk_loc.iterrows():
            nome = row["corretor_nome"]
            consolidado.setdefault(nome, {"venda_q": 0, "venda_v": 0.0,
                                          "loc_q": 0, "loc_v": 0.0})
            consolidado[nome]["loc_q"] += int(row["qtd"])
            consolidado[nome]["loc_v"] += float(row["valor"])

    # Ordena por valor total (venda+locação)
    ordenado = sorted(consolidado.items(),
                      key=lambda kv: kv[1]["venda_v"] + kv[1]["loc_v"],
                      reverse=True)

    if not ordenado:
        st.caption("Nenhum fechamento no mês ainda.")
    else:
        linhas = []
        for pos, (nome, d) in enumerate(ordenado, 1):
            rank_cls = ("rank-1" if pos == 1 else "rank-2" if pos == 2
                        else "rank-3" if pos == 3 else "rank-other")
            sub = []
            if d["venda_q"]:
                sub.append(f"{d['venda_q']} venda(s)")
            if d["loc_q"]:
                sub.append(f"{d['loc_q']} locação(ões)")
            total = d["venda_v"] + d["loc_v"]
            linhas.append(
                f'<div class="ranking-item">'
                f'<div class="rank-num {rank_cls}">{pos}</div>'
                f'<div style="flex:1">'
                f'  <div class="rank-name">{escape(nome)}</div>'
                f'  <div class="rank-sub">{" · ".join(sub)}</div>'
                f'</div>'
                f'<div class="rank-value">{_fmt_brl(total)}</div>'
                f'</div>'
            )
        st.markdown("\n".join(linhas), unsafe_allow_html=True)

    # =========================================================
    # Evolução últimos 6 meses — dados oficiais
    # =========================================================
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">📈</div>
        <div><h2>Evolução Histórica — Vendas</h2>
             <p>VGV mensal oficial do Jetimob</p></div>
    </div>
    """, unsafe_allow_html=True)

    vendas_hist = df_resumo[df_resumo["tipo"] == "venda"].copy()
    if vendas_hist.empty:
        st.caption("Sem histórico sincronizado.")
    else:
        vendas_hist = vendas_hist.sort_values("mes_referencia")
        vendas_hist["mes"] = vendas_hist["mes_referencia"].apply(
            lambda d: f"{_MESES_PT[d.month][:3]}/{str(d.year)[-2:]}")
        fig = px.bar(vendas_hist, x="mes", y="valor_reais",
                     color_discrete_sequence=["#033677"],
                     labels={"mes": "", "valor_reais": "VGV (R$)"},
                     text=vendas_hist["qtd_ganhas"].apply(lambda n: f"{n} vendas"))
        fig.update_traces(textposition="outside")
        fig.update_layout(height=360, margin=dict(l=0, r=0, t=30, b=0),
                          showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # =========================================================
    # Detalhe do mês (lista individual das vendas)
    # =========================================================
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon" style="background:var(--nl-azul-horizonte);">📋</div>
        <div><h2>Fechamentos do Mês — detalhe</h2>
             <p>Lista individual (do kanban Jetimob)</p></div>
    </div>
    """, unsafe_allow_html=True)

    # Pra detalhe, usa o kanban mas mostra só quem tem ganha_em no mês (quando disponível)
    # OU que entrou em Fechamento no mês
    if df_ganhas.empty:
        st.caption("Sem sync detalhado.")
    else:
        ini = pd.Timestamp(ano_ref, mes_ref, 1, tz="UTC")
        fim = ini + pd.offsets.MonthBegin(1)

        # Filtro corretor
        if is_corretor() and not pode_ver_tudo():
            nome_jetimob = (user.get("corretor_nome_jetimob") or "").strip()
            if not nome_jetimob:
                st.error("Seu cadastro nao tem 'nome no Jetimob' configurado.")
                st.stop()
            df_ganhas = df_ganhas[
                df_ganhas["corretor_nome"].str.strip().str.lower() == nome_jetimob.lower()
            ]

        # Pega ganha_em se disponivel, senao entrou_etapa_em
        if "ganha_em" in df_ganhas.columns:
            df_ganhas["ganha_em_dt"] = pd.to_datetime(
                df_ganhas["ganha_em"], utc=True, errors="coerce"
            )
            filtro = ((df_ganhas["ganha_em_dt"] >= ini)
                      & (df_ganhas["ganha_em_dt"] < fim))
            df_detalhe = df_ganhas[filtro]
        else:
            df_detalhe = df_ganhas[(df_ganhas["entrou_etapa_em"] >= ini)
                                   & (df_ganhas["entrou_etapa_em"] < fim)]

        if df_detalhe.empty:
            st.caption("Nenhum fechamento detalhado no mês.")
        else:
            cols_show = ["entrou_etapa_em", "contrato", "corretor_nome",
                         "nome_cliente", "valor_reais", "telefone_e164", "email"]
            tabela = df_detalhe[[c for c in cols_show if c in df_detalhe.columns]].copy()
            tabela["entrou_etapa_em"] = tabela["entrou_etapa_em"].dt.strftime("%d/%m/%Y")
            tabela = tabela.rename(columns={
                "entrou_etapa_em": "Data",
                "contrato": "Tipo",
                "corretor_nome": "Corretor",
                "nome_cliente": "Cliente",
                "valor_reais": "Valor (R$)",
                "telefone_e164": "Telefone",
                "email": "Email",
            })
            if not pode_ver_tudo():
                tabela = tabela.drop(columns=["Telefone", "Email"], errors="ignore")
            st.dataframe(tabela, use_container_width=True, hide_index=True)

    # Rodapé
    ultimo_sync = (df_resumo["scraped_at"].max()
                   if not df_resumo.empty and "scraped_at" in df_resumo.columns
                   else None)
    if ultimo_sync:
        try:
            ts = pd.to_datetime(ultimo_sync).strftime("%d/%m/%Y %H:%M")
            st.caption(f"🔄 Última sincronização: {ts}")
        except Exception:
            pass
