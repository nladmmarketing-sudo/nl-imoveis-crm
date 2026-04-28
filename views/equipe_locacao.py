"""
Equipe Locacao — pagina unificada (antiga Equipe Locacao + Locacoes do Mes).

Estrutura:
  1. KPIs (kanban Jetimob — relatorio oficial nao tem locacao)
  2. Ranking de corretores
  3. Evolucao mensal de receita
  4. Detalhe das locacoes do periodo
  5. Charts: por bairro e por origem
"""
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.auth import (
    escape, filtrar_por_perfil, get_usuario_atual, is_corretor, pode_ver_tudo
)
from utils.filtros import aplicar_filtro, aplicar_filtro_periodo_anterior, periodo_anterior
from utils.supabase_client import (
    get_supabase_client, fetch_leads_jetimob, fetch_vendas
)
from utils.components import kpi_card_v2, alert_box, calc_trend, sparkline_pts, render_kpi_grid


_MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Marco", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


@st.cache_data(ttl=300, show_spinner="Carregando ganhas Jetimob...")
def _fetch_ganhas() -> pd.DataFrame:
    """Oportunidades ganhas do kanban (paginado)."""
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


def render():
    user = get_usuario_atual()
    if not user:
        st.warning("Sessao expirada. Faca login novamente.")
        st.stop()
    if is_corretor() and not (user.get("corretor_nome_jetimob") or "").strip():
        st.error("Seu cadastro nao tem 'nome no Jetimob' configurado. Contate o admin.")
        st.stop()

    periodo = st.session_state.get("periodo_global", "Este mes")
    ano_ref, mes_ref, mes_label = _resolver_mes_do_periodo(periodo)

    st.markdown(f"""
    <div class="nl-header">
        <div class="badge">Equipe de Locacao</div>
        <h1>Performance <span>Locacao</span></h1>
        <div class="sub">Dados do kanban Jetimob · Periodo: <strong>{escape(mes_label)}</strong></div>
    </div>
    """, unsafe_allow_html=True)

    # Carrega dados
    df_ganhas = _fetch_ganhas()
    df_vendas_unif = filtrar_por_perfil(fetch_vendas(), "corretor")
    df_leads_all = filtrar_por_perfil(fetch_leads_jetimob(), "corretor")

    df_leads = aplicar_filtro(df_leads_all, periodo, "created_at")

    # Filtra LOCACOES, etapa Fechamento (kanban)
    df_loc = df_ganhas[(df_ganhas["contrato"] == "locacao")
                        & (df_ganhas["etapa"] == "Fechamento")].copy() if not df_ganhas.empty else pd.DataFrame()

    # Filtro RBAC adicional (defesa em profundidade)
    if is_corretor() and not pode_ver_tudo() and not df_loc.empty:
        nome_jetimob = (user.get("corretor_nome_jetimob") or "").strip()
        if nome_jetimob:
            df_loc = df_loc[df_loc["corretor_nome"].str.strip().str.lower() == nome_jetimob.lower()]

    # Filtro de mes
    ini = pd.Timestamp(ano_ref, mes_ref, 1, tz="UTC")
    fim = ini + pd.offsets.MonthBegin(1)

    if not df_loc.empty:
        if "ganha_em_dt" in df_loc.columns:
            df_mes = df_loc[(df_loc["ganha_em_dt"] >= ini) & (df_loc["ganha_em_dt"] < fim)]
        else:
            df_mes = df_loc[(df_loc["entrou_etapa_em"] >= ini) & (df_loc["entrou_etapa_em"] < fim)]
    else:
        df_mes = pd.DataFrame()

    qtd = len(df_mes)
    receita = float(df_mes["valor_reais"].sum()) if qtd else 0.0
    aluguel_medio = receita / qtd if qtd else 0.0
    receita_total_historico = float(df_loc["valor_reais"].sum()) if not df_loc.empty else 0.0

    # === Calcula periodo anterior ===
    per_ant_label = periodo_anterior(periodo)

    # Mes anterior
    if mes_ref == 1:
        mes_ant_num, ano_ant_num = 12, ano_ref - 1
    else:
        mes_ant_num, ano_ant_num = mes_ref - 1, ano_ref

    if not df_loc.empty:
        ini_ant = pd.Timestamp(ano_ant_num, mes_ant_num, 1, tz="UTC")
        fim_ant = ini_ant + pd.offsets.MonthBegin(1)
        if "ganha_em_dt" in df_loc.columns:
            df_mes_ant = df_loc[(df_loc["ganha_em_dt"] >= ini_ant) & (df_loc["ganha_em_dt"] < fim_ant)]
        else:
            df_mes_ant = df_loc[(df_loc["entrou_etapa_em"] >= ini_ant) & (df_loc["entrou_etapa_em"] < fim_ant)]
    else:
        df_mes_ant = pd.DataFrame()

    qtd_ant = len(df_mes_ant)
    receita_ant = float(df_mes_ant["valor_reais"].sum()) if qtd_ant else 0.0
    aluguel_medio_ant = receita_ant / qtd_ant if qtd_ant else 0

    # Trends
    t_qtd, d_qtd = calc_trend(qtd, qtd_ant)
    t_rec, d_rec = calc_trend(receita, receita_ant)
    t_alug, d_alug = calc_trend(aluguel_medio, aluguel_medio_ant)

    # Sparklines (locacoes diarias ultimos 30 dias)
    df_l_all = df_vendas_unif.copy()
    if "tipo_negocio" in df_l_all.columns:
        df_l_all = df_l_all[df_l_all["tipo_negocio"] == "aluguel"]
    spark_loc = sparkline_pts(df_l_all, "data_venda", dias=30) if not df_l_all.empty else []
    spark_rec = sparkline_pts(df_l_all, "data_venda", dias=30, col_valor="valor") if not df_l_all.empty else []

    # === Alertas ===
    if receita > receita_ant * 1.15 and receita_ant > 0:
        st.markdown(alert_box(
            "Locacoes em alta!",
            f"Receita cresceu {((receita/receita_ant - 1)*100):.0f}% vs {per_ant_label}.",
            tipo="green", icon="🚀"
        ), unsafe_allow_html=True)
    elif receita_ant > 0 and receita < receita_ant * 0.85:
        st.markdown(alert_box(
            "Receita de locacao em queda",
            f"Receita caiu {((1 - receita/receita_ant)*100):.0f}% vs {per_ant_label}.",
            tipo="red", icon="⚠️"
        ), unsafe_allow_html=True)

    # === KPIs v2.0 (grid em 1 markdown) ===
    cards = [
        kpi_card_v2("Locacoes Fechadas", str(qtd),
                    f"vs {qtd_ant} em {per_ant_label}",
                    icon="🔑", color="azul",
                    trend=t_qtd, trend_dir=d_qtd,
                    sparkline_pts_data=spark_loc),
        kpi_card_v2("Receita do Periodo", _fmt_brl(receita),
                    f"vs {_fmt_brl(receita_ant)} em {per_ant_label}",
                    icon="💵", color="green",
                    trend=t_rec, trend_dir=d_rec,
                    sparkline_pts_data=spark_rec),
        kpi_card_v2("Aluguel Medio", _fmt_brl(aluguel_medio) if aluguel_medio else "—",
                    f"vs {_fmt_brl(aluguel_medio_ant)} anterior",
                    icon="📊", color="dourado",
                    trend=t_alug, trend_dir=d_alug),
        kpi_card_v2("Total Historico", _fmt_brl(receita_total_historico),
                    f"{len(df_loc)} locacoes registradas",
                    icon="📈", color="purple"),
    ]
    st.markdown(render_kpi_grid(cards), unsafe_allow_html=True)

    # =========================================================
    # Ranking
    # =========================================================
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

    # =========================================================
    # Evolucao mensal de receita
    # =========================================================
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">📈</div>
        <div><h2>Evolucao Historica — Locacoes</h2>
             <p>Receita mensal de locacoes (kanban Jetimob)</p></div>
    </div>
    """, unsafe_allow_html=True)

    if df_loc.empty:
        st.caption("Sem locacoes sincronizadas.")
    else:
        df_evo = df_loc.copy()
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

    # =========================================================
    # Detalhe + busca + export
    # =========================================================
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon" style="background:#2678BC;">📋</div>
        <div><h2>Locacoes do Periodo — Detalhe</h2>
             <p>Lista individual</p></div>
    </div>
    """, unsafe_allow_html=True)

    if df_mes.empty:
        st.caption("Nenhuma locacao no periodo selecionado.")
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

        busca = st.text_input("🔍 Buscar (cliente, corretor)", placeholder="Digite pra filtrar...", key="busca_locacao")
        if busca:
            mask = pd.Series([False] * len(tabela))
            for col in tabela.columns:
                mask |= tabela[col].astype(str).str.contains(busca, case=False, na=False)
            tabela = tabela[mask]

        st.dataframe(tabela, use_container_width=True, hide_index=True)

        csv = tabela.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Exportar (CSV)",
            data=csv,
            file_name=f"locacoes_{mes_label.replace('/', '_')}.csv",
            mime="text/csv",
            key="dl_locacao",
        )

    # =========================================================
    # Charts: bairro + origem (extras de vendas_nl unificadas)
    # =========================================================
    if not df_vendas_unif.empty:
        df_l_unif = aplicar_filtro(df_vendas_unif, periodo, "data_venda")
        if "tipo_negocio" in df_l_unif.columns:
            df_l_unif = df_l_unif[df_l_unif["tipo_negocio"] == "aluguel"]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="chart-box"><h3>Locacoes por Bairro</h3>', unsafe_allow_html=True)
            if not df_l_unif.empty and "bairro" in df_l_unif.columns:
                bairro_data = df_l_unif[df_l_unif["bairro"].notna() & (df_l_unif["bairro"] != "")]
                if not bairro_data.empty:
                    bc = bairro_data["bairro"].value_counts().head(10).reset_index()
                    bc.columns = ["Bairro", "Locacoes"]
                    fig = px.bar(bc, x="Locacoes", y="Bairro", orientation="h",
                                 color_discrete_sequence=["#FFB700"])
                    fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0),
                                      yaxis=dict(autorange="reversed"),
                                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.caption("Sem dados de bairro.")
            else:
                st.caption("Bairro disponivel apenas em locacoes manuais.")
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-box"><h3>Locacoes por Origem</h3>', unsafe_allow_html=True)
            if not df_l_unif.empty and "origem_lead" in df_l_unif.columns:
                orig_data = df_l_unif[df_l_unif["origem_lead"].notna()]
                if not orig_data.empty:
                    oc = orig_data["origem_lead"].value_counts().reset_index()
                    oc.columns = ["Origem", "Locacoes"]
                    fig2 = px.pie(oc, values="Locacoes", names="Origem", hole=0.4,
                                  color_discrete_sequence=["#FFB700", "#033677", "#2678BC", "#FFDE76", "#16A34A"])
                    fig2.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0))
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.caption("Sem dados de origem.")
            else:
                st.caption("Origem disponivel apenas em locacoes manuais.")
            st.markdown('</div>', unsafe_allow_html=True)

    # Rodape
    if not df_loc.empty and "scraped_at" in df_loc.columns:
        try:
            ts = pd.to_datetime(df_loc["scraped_at"].max()).strftime("%d/%m/%Y %H:%M")
            st.caption(f"🔄 Ultima sincronizacao: {ts}")
        except Exception:
            pass
