"""
Vendas Jetimob — SO VENDAS (relatorio oficial Jetimob).
Para locacoes use a pagina 'Locacoes Jetimob'.

Fonte:
  - resumo_mensal_jetimob (totais mensais oficiais — bate 100% com Jetimob)
  - oportunidades_ganhas_jetimob (lista individual pra drill-down)
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
    client = get_supabase_client()
    # Paginacao
    todos = []
    inicio = 0
    while True:
        r = client.table("oportunidades_ganhas_jetimob").select("*").range(inicio, inicio+999).execute()
        if not r.data:
            break
        todos.extend(r.data)
        if len(r.data) < 1000:
            break
        inicio += 1000
    if not todos:
        return pd.DataFrame()
    df = pd.DataFrame(todos)
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
    """Converte periodo do filtro global em (ano, mes, label)."""
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
        <div class="sub">Apenas VENDAS · Periodo: <strong>{escape(mes_label)}</strong> · Mude no filtro do menu lateral</div>
    </div>
    """, unsafe_allow_html=True)

    df_resumo = _fetch_resumo_mensal()
    df_ganhas = _fetch_ganhas()

    if df_resumo.empty and df_ganhas.empty:
        st.info("Nenhum dado sincronizado ainda. Rode os scripts de sync.")
        return

    # === VENDAS do mes (relatorio oficial) ===
    resumo_mes = df_resumo[(df_resumo["mes_referencia"] == mes_atual_date)
                           & (df_resumo["tipo"] == "venda")]
    qtd_vendas = int(resumo_mes["qtd_ganhas"].iloc[0]) if not resumo_mes.empty else 0
    vgv = float(resumo_mes["valor_reais"].iloc[0]) if not resumo_mes.empty else 0.0
    ranking_vendas = (resumo_mes["ranking_json"].iloc[0]
                      if not resumo_mes.empty else []) or []

    ticket = vgv / qtd_vendas if qtd_vendas else 0

    # KPIs
    cols_kpi = "".join([
        _kpi_card("VGV do Mês", _fmt_brl(vgv),
                  f"Oficial Jetimob · {escape(mes_label)}", "green"),
        _kpi_card("Vendas Fechadas", str(qtd_vendas),
                  "no periodo selecionado", "azul"),
        _kpi_card("Ticket Médio",
                  _fmt_brl(ticket) if ticket else "—",
                  "por venda fechada"),
        _kpi_card("Total YTD",
                  _fmt_brl(float(df_resumo[df_resumo["tipo"] == "venda"]["valor_reais"].sum())),
                  f"{int(df_resumo[df_resumo['tipo'] == 'venda']['qtd_ganhas'].sum())} vendas no historico"),
    ])
    st.markdown(f'<div class="kpi-grid">{cols_kpi}</div>', unsafe_allow_html=True)

    # === Ranking Vendas ===
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon" style="background:#16A34A;">🏆</div>
        <div><h2>Ranking de Vendas — Corretores</h2>
             <p>Dados oficiais do relatorio Jetimob</p></div>
    </div>
    """, unsafe_allow_html=True)

    if not ranking_vendas:
        st.info(f"Sem vendas registradas em {mes_label}.")
    else:
        # Ordena por valor
        ranking_ordenado = sorted(ranking_vendas,
                                   key=lambda r: float(r.get("valor_cents", 0)),
                                   reverse=True)
        linhas = []
        for pos, rk in enumerate(ranking_ordenado, 1):
            rank_cls = ("rank-1" if pos == 1 else "rank-2" if pos == 2
                        else "rank-3" if pos == 3 else "rank-other")
            nome = rk.get("nome", "?")
            qtd = int(rk.get("qtd", 0))
            valor = float(rk.get("valor_cents", 0)) / 100.0
            linhas.append(
                f'<div class="ranking-item">'
                f'<div class="rank-num {rank_cls}">{pos}</div>'
                f'<div style="flex:1">'
                f'  <div class="rank-name">{escape(nome)}</div>'
                f'  <div class="rank-sub">{qtd} venda(s)</div>'
                f'</div>'
                f'<div class="rank-value">{_fmt_brl(valor)}</div>'
                f'</div>'
            )
        st.markdown("\n".join(linhas), unsafe_allow_html=True)

    # === Evolucao mensal de vendas ===
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">📈</div>
        <div><h2>Evolucao Historica — Vendas</h2>
             <p>VGV mensal oficial do Jetimob</p></div>
    </div>
    """, unsafe_allow_html=True)

    vendas_hist = df_resumo[df_resumo["tipo"] == "venda"].copy()
    if vendas_hist.empty:
        st.caption("Sem historico sincronizado.")
    else:
        vendas_hist = vendas_hist.sort_values("mes_referencia")
        vendas_hist["mes"] = vendas_hist["mes_referencia"].apply(
            lambda d: f"{_MESES_PT[d.month][:3]}/{str(d.year)[-2:]}")
        fig = px.bar(vendas_hist, x="mes", y="valor_reais",
                     color_discrete_sequence=["#033677"],
                     labels={"mes": "", "valor_reais": "VGV (R$)"},
                     text=vendas_hist["qtd_ganhas"].apply(lambda n: f"{n} vendas"))
        fig.update_traces(textposition="outside")
        fig.update_layout(height=360, margin=dict(l=0, r=0, t=30, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # === Detalhe das vendas do mes (kanban) ===
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon" style="background:#2678BC;">📋</div>
        <div><h2>Vendas do Mês — Detalhe</h2>
             <p>Lista individual (kanban Jetimob)</p></div>
    </div>
    """, unsafe_allow_html=True)

    if df_ganhas.empty:
        st.caption("Sem sync detalhado.")
    else:
        ini = pd.Timestamp(ano_ref, mes_ref, 1, tz="UTC")
        fim = ini + pd.offsets.MonthBegin(1)

        # SO VENDAS, etapa Fechamento
        df_v_mes = df_ganhas[(df_ganhas["contrato"] == "venda")
                              & (df_ganhas["etapa"] == "Fechamento")].copy()

        # Filtro corretor (RBAC)
        if is_corretor() and not pode_ver_tudo():
            nome_jetimob = (user.get("corretor_nome_jetimob") or "").strip()
            if nome_jetimob:
                df_v_mes = df_v_mes[
                    df_v_mes["corretor_nome"].str.strip().str.lower() == nome_jetimob.lower()
                ]

        # Filtro de data: ganha_em se disponivel, senao entrou_etapa_em
        if "ganha_em" in df_v_mes.columns:
            df_v_mes["ganha_em_dt"] = pd.to_datetime(df_v_mes["ganha_em"], utc=True, errors="coerce")
            df_detalhe = df_v_mes[(df_v_mes["ganha_em_dt"] >= ini) & (df_v_mes["ganha_em_dt"] < fim)]
        else:
            df_detalhe = df_v_mes[(df_v_mes["entrou_etapa_em"] >= ini)
                                   & (df_v_mes["entrou_etapa_em"] < fim)]

        if df_detalhe.empty:
            st.caption("Nenhuma venda detalhada no mes selecionado.")
        else:
            cols_show = ["entrou_etapa_em", "corretor_nome", "nome_cliente",
                         "valor_reais", "telefone_e164", "email"]
            tabela = df_detalhe[[c for c in cols_show if c in df_detalhe.columns]].copy()
            tabela["entrou_etapa_em"] = tabela["entrou_etapa_em"].dt.strftime("%d/%m/%Y")
            tabela = tabela.rename(columns={
                "entrou_etapa_em": "Data",
                "corretor_nome": "Corretor",
                "nome_cliente": "Cliente",
                "valor_reais": "Valor (R$)",
                "telefone_e164": "Telefone",
                "email": "Email",
            })
            if not pode_ver_tudo():
                tabela = tabela.drop(columns=["Telefone", "Email"], errors="ignore")
            st.dataframe(tabela, use_container_width=True, hide_index=True)

            # Export CSV
            csv = tabela.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Exportar (CSV)",
                data=csv,
                file_name=f"vendas_{mes_label.replace('/', '_')}.csv",
                mime="text/csv",
                key="dl_vendas_jetimob",
            )

    # Rodape com info de sync
    ultimo_sync = (df_resumo["scraped_at"].max()
                   if not df_resumo.empty and "scraped_at" in df_resumo.columns
                   else None)
    if ultimo_sync:
        try:
            ts = pd.to_datetime(ultimo_sync).strftime("%d/%m/%Y %H:%M")
            st.caption(f"🔄 Ultima sincronizacao: {ts}")
        except Exception:
            pass
