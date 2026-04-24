"""
Cadastrar Venda - Form pra registrar fechamentos de venda ou locacao.
Acesso: admin, gerente, marketing livre; corretor cadastra so as proprias.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from utils.auth import (
    get_usuario_atual, is_admin, is_gerente, is_corretor, pode_ver_tudo, escape
)
from utils.supabase_client import (
    get_supabase_client, limpar_cache, fetch_vendas, fetch_leads_jetimob
)
from utils.auditoria import registrar


TIPOS_IMOVEL = [
    "Apartamento", "Casa", "Terreno", "Sala",
    "Loja", "Galpao", "Cobertura", "Flat", "Kitnet", "Sobrado",
]
ORIGENS_LEAD = [
    "VivaReal", "ZAP Imoveis", "OLX", "ImovelWeb",
    "Chaves na Mao", "Facebook Ads", "Instagram", "Google Ads",
    "Site NL", "WhatsApp", "Indicacao", "App Jetimob", "Outros",
]
TIPOS_NEGOCIO_UI = ["Venda", "Locacao"]
TIPOS_NEGOCIO_DB = {"Venda": "venda", "Locacao": "aluguel"}
CORRETOR_MANUAL = "— Digitar manualmente —"


def _lista_corretores() -> list[str]:
    """Distinct de vendas_nl.corretor UNION leads_jetimob.corretor (usa cache existente)."""
    nomes: set[str] = set()
    try:
        df_v = fetch_vendas()
        if not df_v.empty and "corretor" in df_v.columns:
            nomes.update(df_v["corretor"].dropna().astype(str).map(str.strip).tolist())
    except Exception:
        pass
    try:
        df_l = fetch_leads_jetimob()
        if not df_l.empty and "corretor" in df_l.columns:
            nomes.update(df_l["corretor"].dropna().astype(str).map(str.strip).tolist())
    except Exception:
        pass
    return sorted(n for n in nomes if n)


def _formatar_brl(v) -> str:
    """Formata numero em R$ 1.234.567,89 (locale BR)."""
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def _inserir_venda(payload: dict) -> tuple[bool, str]:
    client = get_supabase_client()
    try:
        resp = client.table("vendas_nl").insert(payload).execute()
        if resp.data:
            return True, ""
        return False, "Insert retornou sem dados."
    except Exception as e:
        return False, str(e)[:300]


def _excluir_venda(venda_id: int) -> bool:
    client = get_supabase_client()
    try:
        resp = client.table("vendas_nl").delete().eq("id", venda_id).execute()
        return bool(resp.data)
    except Exception:
        return False


def render():
    # Guard de sessao + mapeamento (defesa em profundidade)
    user = get_usuario_atual()
    if not user:
        st.warning("Sessao expirada. Faca login novamente.")
        st.stop()
    if is_corretor() and not (user.get("corretor_nome_jetimob") or "").strip():
        st.error("Seu cadastro nao tem 'nome no Jetimob' configurado. Contate o admin.")
        st.stop()

    st.markdown("""
    <div class="nl-header">
        <div class="badge">Cadastro</div>
        <h1>Cadastrar <span>Venda</span></h1>
        <div class="sub">Registre fechamentos de venda ou locacao</div>
    </div>
    """, unsafe_allow_html=True)

    # ---------- FORMULARIO ----------
    corretores = _lista_corretores()
    hoje = date.today()

    with st.form("form_cadastrar_venda", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_venda = st.date_input(
                "Data do fechamento",
                value=hoje,
                max_value=hoje,
                format="DD/MM/YYYY",
            )
            nome_cliente = st.text_input(
                "Nome do cliente *",
                placeholder="Ex: Maria Silva Santos",
            )
            tipo_imovel = st.selectbox("Tipo de imovel", TIPOS_IMOVEL, index=0)
            bairro = st.text_input("Bairro *", placeholder="Ex: Ponta Negra")
            codigo_imovel = st.text_input(
                "Codigo do imovel (Jetimob)",
                placeholder="Opcional — ex: NL1234",
            )

        with col2:
            tipo_negocio_ui = st.radio(
                "Tipo de negocio", TIPOS_NEGOCIO_UI, index=0, horizontal=True,
            )
            valor = st.number_input(
                "Valor (R$) *", min_value=0.0, step=1000.0, format="%.2f", value=0.0,
            )

            # Corretor — logica por perfil
            corretor_manual = ""
            if is_corretor():
                corretor_forcado = (user.get("corretor_nome_jetimob") or "").strip()
                st.text_input(
                    "Corretor responsavel",
                    value=corretor_forcado,
                    disabled=True,
                    help="Corretores so podem cadastrar proprias vendas.",
                )
                corretor_escolha = corretor_forcado
            else:
                opcoes = [CORRETOR_MANUAL] + corretores
                corretor_escolha = st.selectbox(
                    "Corretor responsavel *",
                    opcoes,
                    index=0,
                    help="Selecione da lista ou digite manualmente se for corretor novo.",
                )
                if corretor_escolha == CORRETOR_MANUAL:
                    corretor_manual = st.text_input(
                        "Nome do novo corretor *",
                        placeholder="Nome como aparece no Jetimob",
                    )

            origem_lead = st.selectbox(
                "Origem do lead",
                ORIGENS_LEAD,
                index=ORIGENS_LEAD.index("Site NL"),
            )

        submit = st.form_submit_button(
            "Registrar Venda", type="primary", use_container_width=True,
        )

        if submit:
            # Resolve corretor final (defesa em profundidade: corretor nao consegue burlar)
            if is_corretor():
                corretor_final = (user.get("corretor_nome_jetimob") or "").strip()
            elif corretor_escolha == CORRETOR_MANUAL:
                corretor_final = (corretor_manual or "").strip()
            else:
                corretor_final = (corretor_escolha or "").strip()

            erros = []
            if data_venda > hoje:
                erros.append("Data de fechamento nao pode ser futura.")
            if not (nome_cliente or "").strip():
                erros.append("Nome do cliente e obrigatorio.")
            if not (bairro or "").strip():
                erros.append("Bairro e obrigatorio.")
            if valor <= 0:
                erros.append("Valor precisa ser maior que zero.")
            if not corretor_final:
                erros.append("Corretor responsavel e obrigatorio.")
            if tipo_negocio_ui not in TIPOS_NEGOCIO_UI:
                erros.append("Tipo de negocio invalido.")

            if erros:
                for e in erros:
                    st.error(e)
            else:
                payload = {
                    "data_venda": data_venda.isoformat(),
                    "nome_cliente": nome_cliente.strip()[:200],
                    "tipo_imovel": tipo_imovel,
                    "codigo_imovel": (codigo_imovel or "").strip()[:50] or None,
                    "bairro": bairro.strip()[:100],
                    "valor": float(valor),
                    "corretor": corretor_final[:100],
                    "origem_lead": origem_lead,
                    "tipo_negocio": TIPOS_NEGOCIO_DB[tipo_negocio_ui],
                }

                ok, msg = _inserir_venda(payload)
                if ok:
                    registrar(
                        "cadastrou_venda",
                        f"{payload['nome_cliente']} · {payload['tipo_negocio']} · "
                        f"{_formatar_brl(payload['valor'])} · corretor={payload['corretor']}",
                    )
                    limpar_cache()
                    st.success(
                        f"{tipo_negocio_ui} registrada: "
                        f"{escape(payload['nome_cliente'])} · "
                        f"{_formatar_brl(payload['valor'])} · "
                        f"{escape(payload['corretor'])}"
                    )
                    st.balloons()
                else:
                    st.error(f"Erro ao registrar venda: {escape(msg)}")

    # ---------- ULTIMAS VENDAS ----------
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">📋</div>
        <div>
            <h2>Ultimas Vendas Cadastradas</h2>
            <p>As 10 mais recentes — busca rapida por cliente, bairro, corretor</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    df = fetch_vendas()
    if df.empty:
        st.info("Nenhuma venda cadastrada ainda.")
        return

    df_top = df.copy().head(10)

    busca = st.text_input(
        "🔍 Buscar",
        placeholder="cliente, bairro, corretor, codigo...",
        key="busca_ultimas_vendas",
    )
    if busca:
        mask = pd.Series([False] * len(df_top))
        for col in df_top.columns:
            mask |= df_top[col].astype(str).str.contains(busca, case=False, na=False)
        df_top = df_top[mask]

    # Formatar pra exibicao
    display = df_top.copy()
    if "data_venda" in display.columns:
        display["data_venda"] = pd.to_datetime(
            display["data_venda"], errors="coerce"
        ).dt.strftime("%d/%m/%Y")
    if "valor" in display.columns:
        display["valor"] = display["valor"].apply(_formatar_brl)

    cols_render = [
        ("data_venda", "Data"),
        ("nome_cliente", "Cliente"),
        ("tipo_imovel", "Imovel"),
        ("bairro", "Bairro"),
        ("valor", "Valor"),
        ("corretor", "Corretor"),
        ("origem_lead", "Origem"),
        ("tipo_negocio", "Tipo"),
    ]
    available = [c for c, _ in cols_render if c in display.columns]
    rename = {c: label for c, label in cols_render if c in display.columns}
    st.dataframe(
        display[available].rename(columns=rename),
        use_container_width=True,
        hide_index=True,
    )

    # Excluir (apenas admin, com confirmacao via popover)
    if is_admin() and not df_top.empty:
        st.markdown("#### Excluir venda (admin)")
        for _, row in df_top.iterrows():
            vid = row.get("id")
            if vid is None:
                continue
            try:
                rotulo_data = pd.to_datetime(row.get("data_venda")).strftime("%d/%m/%Y")
            except Exception:
                rotulo_data = str(row.get("data_venda") or "-")
            rotulo = (
                f"#{int(vid)} · {rotulo_data} · "
                f"{row.get('nome_cliente') or '(sem nome)'} · "
                f"{_formatar_brl(row.get('valor') or 0)}"
            )
            col_desc, col_btn = st.columns([5, 1])
            with col_desc:
                st.caption(rotulo)
            with col_btn:
                with st.popover(f"Excluir #{int(vid)}"):
                    st.warning(f"Excluir venda #{int(vid)}?")
                    st.caption(rotulo)
                    if st.button("Confirmar exclusao", key=f"del_v_{vid}", type="primary"):
                        if _excluir_venda(int(vid)):
                            registrar(
                                "excluiu_venda",
                                f"id={vid} · {row.get('nome_cliente')}",
                            )
                            limpar_cache()
                            st.success("Venda excluida.")
                            st.rerun()
                        else:
                            st.error("Nao foi possivel excluir.")

    st.markdown("""
    <div class="nl-footer">
        <strong>NL Imoveis</strong> · Painel Estrategico · CRECI 1440 J · Natal/RN<br>
        Cadastro de vendas e locacoes
    </div>
    """, unsafe_allow_html=True)
