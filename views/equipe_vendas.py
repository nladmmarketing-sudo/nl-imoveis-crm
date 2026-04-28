"""
Equipe Vendas — pagina unificada (antiga Equipe Vendas + Vendas do Mes Jetimob).

Estrutura:
  1. KPIs (oficial Jetimob — bate 100% com o relatorio)
  2. Ranking de corretores (oficial)
  3. Evolucao historica mensal
  4. Detalhe das vendas do periodo (kanban + manuais)
  5. Charts: por bairro e por origem
"""
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.auth import (
    escape, filtrar_por_perfil, get_usuario_atual, is_corretor, pode_ver_tudo
)
from utils.filtros import aplicar_filtro
from utils.supabase_client import (
    get_supabase_client, fetch_leads_jetimob, fetch_vendas
)


_MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Marco", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


@st.cache_data(ttl=300, show_spinner="Carregando resumo oficial...")
def _fetch_resumo_mensal() -> pd.DataFrame:
    """Resumo oficial Jetimob (totais mensais com ranking)"""
    client = get_supabase_client()
    resp = (client.table("resumo_mensal_jetimob").select("*")
                  .order("mes_referencia", desc=True).execute())
    if not resp.data:
        return pd.DataFrame()
    df = pd.DataFrame(resp.data)
    df["mes_referencia"] = pd.to_datetime(df["mes_referencia"]).dt.date
    df["valor_reais"] = df["valor_total_cents"] / 100.0
    return df


def _fmt_brl(v: float) -> str:
    return f"R$ {v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _resolver_mes_do_periodo(periodo: str) -> tuple[int, int, str]:
    """Converte 'Abril/2026' em (2026, 4, 'Abril/2026'). Default: mes atual."""
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
    mes_atual_date = date(ano_ref, mes_ref, 1)

    st.markdown(f"""
    <div class="nl-header">
        <div class="badge">Equipe de Vendas</div>
        <h1>Performance <span>Vendas</span></h1>
        <div class="sub">Dados oficiais Jetimob · Periodo: <strong>{escape(mes_label)}</strong></div>
    </div>
    """, unsafe_allow_html=True)

    # ---- Carregar fontes ----
    df_resumo = _fetch_resumo_mensal()
    df_vendas_unif = filtrar_por_perfil(fetch_vendas(), "corretor")
    df_leads_all = filtrar_por_perfil(fetch_leads_jetimob(), "corretor")

    # Filtra leads pelo periodo
    df_leads = aplicar_filtro(df_leads_all, periodo, "created_at")

    # =========================================================
    # KPIs (fonte oficial Jetimob — quando disponivel)
    # =========================================================
    if not df_resumo.empty:
        resumo_mes = df_resumo[(df_resumo["mes_referencia"] == mes_atual_date)
                                & (df_resumo["tipo"] == "venda")]
        qtd_vendas_oficial = int(resumo_mes["qtd_ganhas"].iloc[0]) if not resumo_mes.empty else 0
        vgv_oficial = float(resumo_mes["valor_reais"].iloc[0]) if not resumo_mes.empty else 0.0
        ranking_oficial = (resumo_mes["ranking_json"].iloc[0] if not resumo_mes.empty else []) or []
    else:
        qtd_vendas_oficial = 0
        vgv_oficial = 0.0
        ranking_oficial = []

    # Fallback: se nao tem resumo oficial, usa kanban (UNION com vendas_nl)
    if qtd_vendas_oficial == 0 and not df_vendas_unif.empty:
        df_v = aplicar_filtro(df_vendas_unif, periodo, "data_venda")
        if "tipo_negocio" in df_v.columns:
            df_v = df_v[df_v["tipo_negocio"] == "venda"]
        if not df_v.empty:
            qtd_vendas_oficial = len(df_v)
            vgv_oficial = float(df_v["valor"].sum()) if "valor" in df_v.columns else 0.0

    ticket = vgv_oficial / qtd_vendas_oficial if qtd_vendas_oficial else 0
    total_ytd_vgv = float(df_resumo[df_resumo["tipo"] == "venda"]["valor_reais"].sum()) if not df_resumo.empty else 0.0
    total_ytd_qtd = int(df_resumo[df_resumo["tipo"] == "venda"]["qtd_ganhas"].sum()) if not df_resumo.empty else 0

    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card green">
            <div class="label">VGV do Periodo</div>
            <div class="num" style="color:#16A34A">{_fmt_brl(vgv_oficial)}</div>
            <div class="sub">{escape(mes_label)} · Oficial Jetimob</div>
        </div>
        <div class="kpi-card azul">
            <div class="label">Vendas Fechadas</div>
            <div class="num">{qtd_vendas_oficial}</div>
            <div class="sub">no periodo selecionado</div>
        </div>
        <div class="kpi-card">
            <div class="label">Ticket Medio</div>
            <div class="num">{_fmt_brl(ticket) if ticket else '—'}</div>
            <div class="sub">por venda fechada</div>
        </div>
        <div class="kpi-card">
            <div class="label">Total Historico</div>
            <div class="num">{_fmt_brl(total_ytd_vgv)}</div>
            <div class="sub">{total_ytd_qtd} vendas no historico sync</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # =========================================================
    # Ranking Vendas (oficial Jetimob)
    # =========================================================
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon" style="background:#16A34A;">🏆</div>
        <div><h2>Ranking de Vendas — Corretores</h2>
             <p>Performance individual no periodo (relatorio oficial Jetimob)</p></div>
    </div>
    """, unsafe_allow_html=True)

    # Tenta ranking oficial primeiro; se vazio, usa UNION (kanban + manual)
    if ranking_oficial:
        ranking_ord = sorted(ranking_oficial,
                             key=lambda r: float(r.get("valor_cents", 0)),
                             reverse=True)
        linhas = []
        for pos, rk in enumerate(ranking_ord, 1):
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
    elif not df_vendas_unif.empty:
        df_v = aplicar_filtro(df_vendas_unif, periodo, "data_venda")
        if "tipo_negocio" in df_v.columns:
            df_v = df_v[df_v["tipo_negocio"] == "venda"]
        if not df_v.empty and "corretor" in df_v.columns:
            perf = df_v[df_v["corretor"].notna() & (df_v["corretor"] != "")].groupby("corretor").agg(
                qtd=("nome_cliente", "count"),
                valor=("valor", "sum")
            ).reset_index().sort_values("valor", ascending=False)
            linhas = []
            for pos, (_, row) in enumerate(perf.iterrows(), 1):
                rank_cls = ("rank-1" if pos == 1 else "rank-2" if pos == 2
                            else "rank-3" if pos == 3 else "rank-other")
                linhas.append(
                    f'<div class="ranking-item">'
                    f'<div class="rank-num {rank_cls}">{pos}</div>'
                    f'<div style="flex:1">'
                    f'  <div class="rank-name">{escape(row["corretor"])}</div>'
                    f'  <div class="rank-sub">{int(row["qtd"])} venda(s)</div>'
                    f'</div>'
                    f'<div class="rank-value">{_fmt_brl(float(row["valor"]))}</div>'
                    f'</div>'
                )
            st.markdown("\n".join(linhas), unsafe_allow_html=True)
        else:
            st.info(f"Nenhuma venda registrada em {mes_label}.")
    else:
        st.info(f"Nenhuma venda registrada em {mes_label}.")

    # =========================================================
    # Evolucao mensal — VGV oficial
    # =========================================================
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">📈</div>
        <div><h2>Evolucao Historica — Vendas</h2>
             <p>VGV mensal oficial Jetimob</p></div>
    </div>
    """, unsafe_allow_html=True)

    vendas_hist = df_resumo[df_resumo["tipo"] == "venda"].copy() if not df_resumo.empty else pd.DataFrame()
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

    # =========================================================
    # Detalhe das vendas + busca + export (kanban + manuais)
    # =========================================================
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon" style="background:#2678BC;">📋</div>
        <div><h2>Vendas do Periodo — Detalhe</h2>
             <p>Lista individual (manual + kanban Jetimob)</p></div>
    </div>
    """, unsafe_allow_html=True)

    if df_vendas_unif.empty:
        st.caption("Nenhuma venda registrada.")
    else:
        df_v = aplicar_filtro(df_vendas_unif, periodo, "data_venda")
        if "tipo_negocio" in df_v.columns:
            df_v = df_v[df_v["tipo_negocio"] == "venda"]

        if df_v.empty:
            st.info(f"Sem vendas em {mes_label}.")
        else:
            cols = ["data_venda", "nome_cliente", "tipo_imovel", "codigo_imovel",
                    "bairro", "valor", "corretor", "origem_lead"]
            available = [c for c in cols if c in df_v.columns]
            display = df_v[available].copy()
            display = display.rename(columns={
                "data_venda": "Data", "nome_cliente": "Cliente", "tipo_imovel": "Imovel",
                "codigo_imovel": "Codigo", "bairro": "Bairro", "valor": "Valor (R$)",
                "corretor": "Corretor", "origem_lead": "Origem",
            })

            busca = st.text_input("🔍 Buscar (cliente, codigo, bairro, corretor)",
                                   placeholder="Digite pra filtrar...", key="busca_vendas")
            if busca:
                mask = pd.Series([False] * len(display))
                for col in display.columns:
                    mask |= display[col].astype(str).str.contains(busca, case=False, na=False)
                display = display[mask]

            st.dataframe(display, use_container_width=True, hide_index=True)

            csv = display.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Exportar (CSV)",
                data=csv,
                file_name=f"vendas_{mes_label.replace('/', '_')}.csv",
                mime="text/csv",
                key="dl_vendas",
            )

    # =========================================================
    # Charts: bairro + origem (visualizacao adicional)
    # =========================================================
    if not df_vendas_unif.empty:
        df_v = aplicar_filtro(df_vendas_unif, periodo, "data_venda")
        if "tipo_negocio" in df_v.columns:
            df_v = df_v[df_v["tipo_negocio"] == "venda"]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="chart-box"><h3>Vendas por Bairro</h3>', unsafe_allow_html=True)
            if not df_v.empty and "bairro" in df_v.columns:
                bairro_data = df_v[df_v["bairro"].notna() & (df_v["bairro"] != "")]
                if not bairro_data.empty:
                    bc = bairro_data["bairro"].value_counts().head(10).reset_index()
                    bc.columns = ["Bairro", "Vendas"]
                    fig = px.bar(bc, x="Vendas", y="Bairro", orientation="h",
                                 color_discrete_sequence=["#033677"])
                    fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0),
                                      yaxis=dict(autorange="reversed"),
                                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.caption("Sem dados de bairro nas vendas do periodo.")
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-box"><h3>Vendas por Origem</h3>', unsafe_allow_html=True)
            if not df_v.empty and "origem_lead" in df_v.columns:
                orig_data = df_v[df_v["origem_lead"].notna()]
                if not orig_data.empty:
                    oc = orig_data["origem_lead"].value_counts().reset_index()
                    oc.columns = ["Origem", "Vendas"]
                    fig2 = px.pie(oc, values="Vendas", names="Origem", hole=0.4,
                                  color_discrete_sequence=["#033677", "#FFB700", "#2678BC", "#FFDE76", "#16A34A"])
                    fig2.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0))
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.caption("Sem dados de origem.")
            st.markdown('</div>', unsafe_allow_html=True)

    # Rodape
    if not df_resumo.empty and "scraped_at" in df_resumo.columns:
        try:
            ts = pd.to_datetime(df_resumo["scraped_at"].max()).strftime("%d/%m/%Y %H:%M")
            st.caption(f"🔄 Ultima sincronizacao oficial: {ts}")
        except Exception:
            pass
