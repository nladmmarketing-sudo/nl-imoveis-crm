"""
Utilitarios de chart — aplica tema visual NL Imoveis em todos os graficos Plotly.
"""


# Paleta oficial NL Imoveis
NL_COLORS = [
    "#033677",  # Azul Noturno (primario)
    "#FFB700",  # Ouro Vivo (destaque)
    "#2678BC",  # Azul Horizonte
    "#16A34A",  # Verde sucesso
    "#FFDE76",  # Sol Dourado
    "#DC2626",  # Vermelho alerta
    "#EA580C",  # Laranja
    "#8B5CF6",  # Roxo
    "#06B6D4",  # Ciano
    "#CD7F32",  # Bronze
    "#9CA3AF",  # Cinza
    "#001833",  # Azul Profundo
]

NL_PLOTLY_LAYOUT = dict(
    font_family="Georama, -apple-system, Segoe UI, sans-serif",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=0, r=0, t=24, b=0),
    legend=dict(
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="#D1E4F5",
        borderwidth=1,
        font=dict(size=11),
    ),
    xaxis=dict(
        gridcolor="rgba(209,228,245,0.5)",
        linecolor="rgba(209,228,245,0.8)",
        tickfont=dict(size=11, color="#6B7280"),
        title_font=dict(size=11, color="#6B7280"),
        showgrid=True,
    ),
    yaxis=dict(
        gridcolor="rgba(209,228,245,0.5)",
        linecolor="rgba(209,228,245,0.8)",
        tickfont=dict(size=11, color="#6B7280"),
        title_font=dict(size=11, color="#6B7280"),
        showgrid=True,
    ),
    colorway=NL_COLORS,
    hoverlabel=dict(
        bgcolor="white",
        bordercolor="#033677",
        font_size=12,
        font_family="Georama, sans-serif",
    ),
)


def nl_theme(fig, height: int = 320) -> "go.Figure":
    """
    Aplica tema NL Imoveis a um grafico Plotly.

    Uso:
        fig = px.bar(df, ...)
        fig = nl_theme(fig, height=360)
        st.plotly_chart(fig, use_container_width=True)
    """
    layout = dict(NL_PLOTLY_LAYOUT)
    layout["height"] = height
    fig.update_layout(**layout)
    return fig


def nl_bar_config(fig, height: int = 320) -> "go.Figure":
    """Tema NL para graficos de barra — sem grade horizontal."""
    fig = nl_theme(fig, height)
    fig.update_layout(yaxis_showgrid=False)
    return fig
