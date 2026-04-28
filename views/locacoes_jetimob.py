"""
Locacoes Jetimob — SO LOCACOES (sync kanban Jetimob).

Diferente de vendas, o relatorio oficial do Jetimob nao tem locacoes.
Por isso usamos a tabela `oportunidades_ganhas_jetimob` (kanban) com filtro:
  contrato = 'locacao' AND etapa = 'Fechamento'
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


@st.cache_data(ttl=300, show_spinner="Carregando locacoes...")
def _fetch_ganhas() -> pd.DataFrame:
    client = get_supabase_client()
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
    if "ganha_em" in df.columns:
        df["ganha_em_dt"] = pd.to_datetime(df["ganha_em"], utc=True, errors="coerce")
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

    st.markdown(f"""
    <div class="nl-header">
        <div class="badge">Jetimob · Kanban</div>
        <h1>Locacoes do <span>Mês</span></h1>
        <div class="sub">Apenas LOCACOES · Periodo: <strong>{escape(mes_label)}</strong> · Mude no filtro do menu lateral</div>
    </div>
    """, unsafe_allow_html=True)

    df_ganhas = _fetch_ganhas()

    if df_ganhas.empty:
        st.info("Nenhum dado sincronizado ainda. Rode `scripts/sync_jetimob_ganhas.py`.")
        return

    # Filtra LOCACOES, etapa Fechamento
    df_loc = df_ganhas[(df_ganhas["contrato"] == "locacao")
                        & (df_ganhas["etapa"] == "Fechamento")].copy()

    # Filtro RBAC
    if is_corretor() and not pode_ver_tudo():
        nome_jetimob = (user.get("corretor_nome_jetimob") or "").strip()
        if nome_jetimob:
            df_loc = df_loc[df_loc["corretor_nome"].str.strip().str.lower() == nome_jetimob.lower()]

    # Filtro de mes pelo ganha_em
    ini = pd.Timestamp(ano_ref, mes_ref, 1, tz="UTC")
    fim = ini + pd.offsets.MonthBegin(1)

    if "ganha_em_dt" in df_loc.columns:
        df_mes = df_loc[(df_loc["ganha_em_dt"] >= ini) & (df_loc["ganha_em_dt"] < fim)]
    else:
        df_mes = df_loc[(df_loc["entrou_etapa_em"] >= ini) & (df_loc["entrou_etapa_em"] < fim)]

    qtd = len(df_mes)
    receita = float(df_mes["valor_reais"].sum()) if qtd else 0.0
    aluguel_medio = receita / qtd if qtd else 0.0

    # KPIs
    receita_total_periodo = float(df_loc["valor_reais"].sum()) if not df_loc.empty else 0.0
    cols_kpi = "".join([
        _kpi_card("Locacoes Fechadas", str(qtd),
                  f"em {escape(mes_label)}", "azul"),
        _kpi_card("Receita do Mes", _fmt_brl(receita),
                  "soma dos alugueis", "green"),
        _kpi_card("Aluguel Medio",
                  _fmt_brl(aluguel_medio) if aluguel_medio else "—",
                  "por locacao"),
        _kpi_card("Total no Historico",
                  _fmt_brl(receita_total_periodo),
                  f"{len(df_loc)} locacoes desde inicio do sync"),
    ])
    st.markdown(f'<div class="kpi-grid">{cols_kpi}</div>', unsafe_allow_html=True)

    # === Ranking ===
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon" style="background:#FFB700;">🏆</div>
        <div><h2>Ranking de Locacoes — Corretores</h2>
             <p>Performance no periodo selecionado</p></div>
    </div>
    """, unsafe_allow_html=True)

    if df_mes.empty:
        st.info(f"Sem locacoes registradas em {mes_label}.")
    else:
        rk = df_mes.groupby("corretor_nome").agg(
            qtd=("jetimob_id", "count"),
            valor=("valor_reais", "sum")
        ).reset_index().sort_values("valor", ascending=False)

        linhas = []
        for pos, (_, row) in enumerate(rk.iterrows(), 1):
            rank_cls = ("rank-1" if pos == 1 else "rank-2" if pos == 2
                        else "rank-3" if pos == 3 else "rank-other")
            linhas.append(
                f'<div class="ranking-item">'
                f'<div class="rank-num {rank_cls}">{pos}</div>'
                f'<div style="flex:1">'
                f'  <div class="rank-name">{escape(row["corretor_nome"])}</div>'
                f'  <div class="rank-sub">{int(row["qtd"])} locacao(es)</div>'
                f'</div>'
                f'<div class="rank-value">{_fmt_brl(float(row["valor"]))}</div>'
                f'</div>'
            )
        st.markdown("\n".join(linhas), unsafe_allow_html=True)

    # === Evolucao mensal ===
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">📈</div>
        <div><h2>Evolucao Mensal — Locacoes</h2>
             <p>Receita mensal de locacoes (kanban Jetimob)</p></div>
    </div>
    """, unsafe_allow_html=True)

    if df_loc.empty:
        st.caption("Sem locacoes sincronizadas.")
    else:
        df_evo = df_loc.copy()
        # Usa ganha_em se possivel
        if "ganha_em_dt" in df_evo.columns:
            df_evo["data_ref"] = df_evo["ganha_em_dt"]
        else:
            df_evo["data_ref"] = df_evo["entrou_etapa_em"]
        df_evo["mes"] = df_evo["data_ref"].dt.to_period("M").astype(str)
        monthly = df_evo.groupby("mes").agg(
            qtd=("jetimob_id", "count"),
            receita=("valor_reais", "sum")
        ).reset_index().sort_values("mes")

        if not monthly.empty:
            fig = px.bar(monthly, x="mes", y="receita",
                         color_discrete_sequence=["#FFB700"],
                         labels={"mes": "", "receita": "Receita (R$)"},
                         text=monthly["qtd"].apply(lambda n: f"{n} locacoes"))
            fig.update_traces(textposition="outside")
            fig.update_layout(height=360, margin=dict(l=0, r=0, t=30, b=0), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # === Detalhe ===
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon" style="background:#2678BC;">📋</div>
        <div><h2>Locacoes do Mes — Detalhe</h2>
             <p>Lista individual</p></div>
    </div>
    """, unsafe_allow_html=True)

    if df_mes.empty:
        st.caption("Nenhuma locacao no mes selecionado.")
    else:
        cols_show = ["entrou_etapa_em", "corretor_nome", "nome_cliente",
                     "valor_reais", "telefone_e164", "email"]
        tabela = df_mes[[c for c in cols_show if c in df_mes.columns]].copy()
        tabela["entrou_etapa_em"] = tabela["entrou_etapa_em"].dt.strftime("%d/%m/%Y")
        tabela = tabela.rename(columns={
            "entrou_etapa_em": "Data",
            "corretor_nome": "Corretor",
            "nome_cliente": "Cliente",
            "valor_reais": "Aluguel (R$)",
            "telefone_e164": "Telefone",
            "email": "Email",
        })
        if not pode_ver_tudo():
            tabela = tabela.drop(columns=["Telefone", "Email"], errors="ignore")
        st.dataframe(tabela, use_container_width=True, hide_index=True)

        csv = tabela.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Exportar (CSV)",
            data=csv,
            file_name=f"locacoes_{mes_label.replace('/', '_')}.csv",
            mime="text/csv",
            key="dl_locacoes_jetimob",
        )

    # Rodape
    ultimo_sync = df_loc["scraped_at"].max() if "scraped_at" in df_loc.columns and not df_loc.empty else None
    if ultimo_sync:
        try:
            ts = pd.to_datetime(ultimo_sync).strftime("%d/%m/%Y %H:%M")
            st.caption(f"🔄 Ultima sincronizacao: {ts}")
        except Exception:
            pass
