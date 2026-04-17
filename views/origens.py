"""
Origens de Leads - Analise estrategica de canais
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.supabase_client import fetch_leads_jetimob
from utils.auth import escape
from utils.filtros import aplicar_filtro


def render():
    periodo = st.session_state.get("periodo_global", "Ultimos 30 dias")

    st.markdown(f"""
    <div class="nl-header">
        <div class="badge">Analise de Canais</div>
        <h1>Origens de <span>Leads</span></h1>
        <div class="sub">Distribuicao por canal · Periodo: <strong>{escape(periodo)}</strong></div>
    </div>
    """, unsafe_allow_html=True)

    df_all = fetch_leads_jetimob()
    df = aplicar_filtro(df_all, periodo, "created_at")

    if df.empty:
        st.warning(f"Nenhum lead no periodo '{periodo}'.")
        return

    total = len(df)
    com_origem = df[df["origem"].notna() & (df["origem"] != "")].shape[0]
    sem_origem = total - com_origem

    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="label">Total de Leads</div>
            <div class="num">{total:,}</div>
            <div class="sub">{escape(periodo)}</div>
        </div>
        <div class="kpi-card azul">
            <div class="label">Com Origem Identificada</div>
            <div class="num">{com_origem:,}</div>
            <div class="sub">{com_origem/total*100:.1f}% do total</div>
        </div>
        <div class="kpi-card {'red' if total > 0 and sem_origem/total > 0.3 else ''}">
            <div class="label">Sem Origem</div>
            <div class="num" style="color:{'#DC2626' if total > 0 and sem_origem/total > 0.3 else '#1C3882'}">{sem_origem:,}</div>
            <div class="sub">{sem_origem/total*100:.1f}% sem rastreamento</div>
            {'<span class="kpi-badge badge-red">Rastreamento precisa melhorar</span>' if total > 0 and sem_origem/total > 0.3 else ''}
        </div>
        <div class="kpi-card">
            <div class="label">Canais Ativos</div>
            <div class="num">{df["origem"].nunique()}</div>
            <div class="sub">origens distintas</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    df_origem = df[df["origem"].notna() & (df["origem"] != "")]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="chart-box"><h3>Distribuicao por Canal de Origem</h3>', unsafe_allow_html=True)
        if not df_origem.empty:
            oc = df_origem["origem"].value_counts().head(12).reset_index()
            oc.columns = ["Origem", "Leads"]
            fig = px.pie(oc, values="Leads", names="Origem", hole=0.4,
                         color_discrete_sequence=["#1C3882", "#F0A500", "#2a4fa8", "#FFD166",
                                                  "#16A34A", "#DC2626", "#EA580C", "#8B5CF6",
                                                  "#06B6D4", "#D1E4F5", "#9CA3AF", "#CD7F32"])
            fig.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="chart-box"><h3>Volume por Canal (Top 12)</h3>', unsafe_allow_html=True)
        if not df_origem.empty:
            oc2 = df_origem["origem"].value_counts().head(12).reset_index()
            oc2.columns = ["Origem", "Leads"]
            oc2["pct"] = (oc2["Leads"] / total * 100).round(1)
            fig2 = px.bar(oc2, x="Leads", y="Origem", orientation="h",
                          text=oc2.apply(lambda r: f"{r['Leads']:,} ({r['pct']}%)", axis=1),
                          color_discrete_sequence=["#1C3882"])
            fig2.update_layout(
                height=400, margin=dict(l=0, r=0, t=10, b=0),
                yaxis=dict(autorange="reversed"),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
            )
            fig2.update_traces(textposition="outside")
            st.plotly_chart(fig2, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Tabela detalhada
    st.markdown("""
    <div class="section-hdr">
        <div class="section-icon">📊</div>
        <div>
            <h2>Analise Estrategica por Canal</h2>
            <p>Volume, percentual e corretor por canal</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not df_origem.empty:
        tabela = df_origem["origem"].value_counts().reset_index()
        tabela.columns = ["Origem", "Leads"]
        tabela["% do Total"] = (tabela["Leads"] / total * 100).round(1).astype(str) + "%"

        with_corretor = df_origem[df_origem["corretor"].notna() & (df_origem["corretor"] != "")]
        if not with_corretor.empty:
            corretor_by_origem = with_corretor.groupby("origem").size().reset_index(name="Com Corretor")
            tabela = tabela.merge(corretor_by_origem, left_on="Origem", right_on="origem", how="left")
            tabela["Com Corretor"] = tabela["Com Corretor"].fillna(0).astype(int)
            tabela = tabela.drop(columns=["origem"], errors="ignore")

        st.dataframe(tabela, use_container_width=True, hide_index=True)

        csv = tabela.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Exportar (CSV)",
            data=csv,
            file_name=f"origens_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            key="dl_origens"
        )

    # Timeline por origem
    st.markdown('<div class="chart-box"><h3>Evolucao Mensal por Canal (Top 5)</h3>', unsafe_allow_html=True)
    if not df_origem.empty and "created_at" in df_origem.columns:
        df_origem_copy = df_origem.copy()
        df_origem_copy["mes"] = pd.to_datetime(df_origem_copy["created_at"], errors="coerce").dt.to_period("M").astype(str)
        top5 = df_origem_copy["origem"].value_counts().head(5).index.tolist()
        df_top5 = df_origem_copy[df_origem_copy["origem"].isin(top5)]
        if not df_top5.empty:
            monthly = df_top5.groupby(["mes", "origem"]).size().reset_index(name="Leads")
            fig3 = px.line(monthly, x="mes", y="Leads", color="origem",
                           color_discrete_sequence=["#1C3882", "#F0A500", "#16A34A", "#DC2626", "#8B5CF6"])
            fig3.update_layout(
                height=350, margin=dict(l=0, r=0, t=10, b=0),
                xaxis_title="", yaxis_title="Leads",
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                legend_title=""
            )
            st.plotly_chart(fig3, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
