"""
Vendas Jetimob - Oportunidades ganhas puxadas direto do Jetimob.
Mostra VGV, locações e ranking do mês vigente, atualizado pelo sync diário.
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


@st.cache_data(ttl=300, show_spinner="Carregando ganhas Jetimob...")
def _fetch_ganhas() -> pd.DataFrame:
    """Lê a tabela oportunidades_ganhas_jetimob do Supabase."""
    client = get_supabase_client()
    resp = (client.table("oportunidades_ganhas_jetimob")
                  .select("*")
                  .order("entrou_etapa_em", desc=True)
                  .execute())
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


def render() -> None:
    user = get_usuario_atual()
    if not user:
        st.warning("Sessao expirada. Faca login novamente.")
        st.stop()

    hoje = date.today()
    mes_label = f"{_MESES_PT[hoje.month]}/{hoje.year}"

    st.markdown(f"""
    <div class="nl-header">
        <div class="badge">Jetimob · Sync Diário</div>
        <h1>Vendas do <span>Mês</span></h1>
        <div class="sub">Oportunidades ganhas do Jetimob · <strong>{escape(mes_label)}</strong></div>
    </div>
    """, unsafe_allow_html=True)

    df = _fetch_ganhas()
    if df.empty:
        st.info("Nenhuma oportunidade ganha sincronizada ainda. "
                "Rode `python scripts/sync_jetimob_ganhas.py` pra popular.")
        return

    # Filtra por perfil — corretor só vê as próprias (usa corretor_nome_jetimob do usuário)
    if is_corretor() and not pode_ver_tudo():
        nome_jetimob = (user.get("corretor_nome_jetimob") or "").strip()
        if not nome_jetimob:
            st.error("Seu cadastro nao tem 'nome no Jetimob' configurado.")
            st.stop()
        df = df[df["corretor_nome"].str.strip().str.lower() == nome_jetimob.lower()]

    # Recorte: fechamentos do mês atual
    inicio_mes = pd.Timestamp(hoje.year, hoje.month, 1, tz="UTC")
    prox_mes = (inicio_mes + pd.offsets.MonthBegin(1))
    df_mes = df[(df["etapa"] == "Fechamento") &
                (df["entrou_etapa_em"] >= inicio_mes) &
                (df["entrou_etapa_em"] < prox_mes)]

    # KPIs
    df_v = df_mes[df_mes["contrato"] == "venda"]
    df_l = df_mes[df_mes["contrato"] == "locacao"]
    vgv = df_v["valor_reais"].sum()
    loc_valor = df_l["valor_reais"].sum()

    cols_kpi = "".join([
        _kpi_card("VGV do Mês", f"R$ {vgv:,.0f}".replace(",", "."),
                  f"{len(df_v)} venda(s)", "green"),
        _kpi_card("Locações do Mês", f"R$ {loc_valor:,.0f}".replace(",", "."),
                  f"{len(df_l)} locação(ões)", "azul"),
        _kpi_card("Total Fechamentos", str(len(df_mes)),
                  escape(mes_label)),
        _kpi_card("Ticket Médio Venda",
                  (f"R$ {(vgv / len(df_v)):,.0f}".replace(",", ".")
                   if len(df_v) else "—"),
                  "por venda fechada"),
    ])
    st.markdown(f'<div class="kpi-grid">{cols_kpi}</div>', unsafe_allow_html=True)

    # Ranking de corretores (mês)
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon" style="background:var(--nl-ouro-vivo);">🏆</div>
        <div><h2>Ranking do Mês</h2>
             <p>Fechamentos (venda + locação) no mês vigente</p></div>
    </div>
    """, unsafe_allow_html=True)

    if df_mes.empty:
        st.caption("Nenhum fechamento no mês ainda.")
    else:
        rk = (df_mes.groupby(["corretor_nome", "contrato"])
                    .agg(qtd=("jetimob_id", "count"), valor=("valor_reais", "sum"))
                    .reset_index())
        rk_tot = (rk.groupby("corretor_nome")["valor"].sum()
                    .sort_values(ascending=False).reset_index())
        linhas = []
        for idx, row in rk_tot.iterrows():
            pos = idx + 1
            rank_cls = "rank-1" if pos == 1 else "rank-2" if pos == 2 else "rank-3" if pos == 3 else "rank-other"
            detalhes_venda = rk[(rk["corretor_nome"] == row["corretor_nome"]) & (rk["contrato"] == "venda")]
            detalhes_loc = rk[(rk["corretor_nome"] == row["corretor_nome"]) & (rk["contrato"] == "locacao")]
            sub = []
            if not detalhes_venda.empty:
                q = int(detalhes_venda["qtd"].iloc[0])
                sub.append(f"{q} venda(s)")
            if not detalhes_loc.empty:
                q = int(detalhes_loc["qtd"].iloc[0])
                sub.append(f"{q} locação(ões)")
            linhas.append(
                f'<div class="ranking-item">'
                f'<div class="rank-num {rank_cls}">{pos}</div>'
                f'<div style="flex:1">'
                f'  <div class="rank-name">{escape(row["corretor_nome"])}</div>'
                f'  <div class="rank-sub">{" · ".join(sub)}</div>'
                f'</div>'
                f'<div class="rank-value">R$ {row["valor"]:,.0f}</div>'
                f'</div>'.replace(",", ".")
            )
        st.markdown("\n".join(linhas), unsafe_allow_html=True)

    # Evolução 6 meses
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">📈</div>
        <div><h2>Evolução — Últimos 6 meses</h2>
             <p>Comparativo histórico de fechamentos</p></div>
    </div>
    """, unsafe_allow_html=True)

    df_fech = df[df["etapa"] == "Fechamento"].copy()
    if df_fech.empty:
        st.caption("Sem histórico de fechamentos.")
    else:
        df_fech["mes"] = df_fech["entrou_etapa_em"].dt.strftime("%Y-%m")
        agg = (df_fech.groupby(["mes", "contrato"])["valor_reais"]
                      .sum().reset_index())
        fig = px.bar(agg, x="mes", y="valor_reais", color="contrato",
                     barmode="group",
                     color_discrete_map={"venda": "#033677", "locacao": "#FFB700"},
                     labels={"mes": "Mês", "valor_reais": "R$", "contrato": "Contrato"})
        fig.update_layout(height=360, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

    # Detalhe do mês
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon" style="background:var(--nl-azul-horizonte);">📋</div>
        <div><h2>Fechamentos do Mês — detalhe</h2>
             <p>Lista das oportunidades fechadas</p></div>
    </div>
    """, unsafe_allow_html=True)

    if df_mes.empty:
        st.caption("Nenhum fechamento no mês para mostrar.")
    else:
        cols_show = ["entrou_etapa_em", "contrato", "corretor_nome",
                     "nome_cliente", "valor_reais", "telefone_e164", "email"]
        tabela = df_mes[cols_show].copy()
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

    # Rodapé com info de sync
    ultimo_sync = df["scraped_at"].max() if "scraped_at" in df.columns else None
    if ultimo_sync:
        try:
            ts = pd.to_datetime(ultimo_sync).strftime("%d/%m/%Y %H:%M")
            st.caption(f"Última sincronização com Jetimob: {ts}")
        except Exception:
            pass
