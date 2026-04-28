"""
Componentes visuais reutilizaveis — v2.0
KPI cards modernos com sparklines, trend arrows e alertas inteligentes.
"""
from __future__ import annotations
import pandas as pd
from datetime import datetime, timedelta
from utils.auth import escape


# =========================================================
# SPARKLINES (mini-graficos SVG)
# =========================================================
def sparkline_svg(pts: list[float], color: str = "azul", height: int = 24) -> str:
    """Mini-grafico SVG inline pra dentro de KPI card."""
    if not pts or len(pts) < 2:
        return ""

    max_v = max(pts) if max(pts) != 0 else 1
    min_v = min(pts)
    delta = max_v - min_v if max_v != min_v else 1

    width = 100
    coords = []
    n = len(pts)
    for i, v in enumerate(pts):
        x = (i / (n - 1)) * width
        y = height - ((v - min_v) / delta) * height
        coords.append(f"{x:.1f},{y:.1f}")

    line_path = "M" + " L".join(coords)
    area_path = f"M0,{height} L" + " L".join(coords) + f" L{width},{height} Z"

    color_map = {
        "azul": "#033677",
        "dourado": "#FFB700",
        "green": "#16A34A",
        "red": "#DC2626",
        "purple": "#8B5CF6",
        "azul-light": "#2678BC",
    }
    css_color = color_map.get(color, "#033677")

    return (
        f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" '
        f'style="width:100%;height:{height}px;margin-top:0.5rem;display:block">'
        f'<path d="{area_path}" fill="{css_color}" opacity="0.15"/>'
        f'<path d="{line_path}" stroke="{css_color}" stroke-width="2" fill="none"/>'
        f'</svg>'
    )


def sparkline_pts(df: pd.DataFrame, col_data: str, dias: int = 30,
                   col_valor: str | None = None) -> list[float]:
    """
    Gera lista de N pontos diarios para sparkline.
    - Se col_valor for None: conta registros por dia
    - Se col_valor for dado: soma valores por dia
    """
    if df.empty or col_data not in df.columns:
        return []
    df = df.copy()
    df["_d"] = pd.to_datetime(df[col_data], errors="coerce", utc=True).dt.tz_localize(None).dt.date
    df = df.dropna(subset=["_d"])
    fim = datetime.now().date()
    inicio = fim - timedelta(days=dias)
    df = df[(df["_d"] >= inicio) & (df["_d"] <= fim)]

    if col_valor and col_valor in df.columns:
        daily = df.groupby("_d")[col_valor].sum()
    else:
        daily = df.groupby("_d").size()

    all_days = pd.date_range(inicio, fim, freq="D").date
    daily = daily.reindex(all_days, fill_value=0)
    return daily.astype(float).tolist()


# =========================================================
# TREND (calculo de variacao vs periodo anterior)
# =========================================================
def calc_trend(atual: float, anterior: float) -> tuple[str | None, str]:
    """
    Calcula seta de tendencia.
    Retorna (texto, direcao) — direcao: 'up'/'down'/'flat'/None
    """
    if anterior == 0:
        if atual > 0:
            return "Novo", "up"
        return None, "flat"
    pct = ((atual - anterior) / anterior) * 100
    if abs(pct) < 1:
        return f"= {pct:.0f}%", "flat"
    if pct > 0:
        return f"↑ {pct:.0f}%", "up"
    return f"↓ {abs(pct):.0f}%", "down"


# =========================================================
# KPI CARD v2.0 (com icone, sparkline, trend)
# =========================================================
def kpi_card_v2(label: str, valor: str, sub: str = "",
                icon: str = "📊", color: str = "azul",
                trend: str | None = None, trend_dir: str = "flat",
                sparkline_pts_data: list[float] | None = None) -> str:
    """
    Card KPI moderno (em uma linha pra markdown nao quebrar).
    """
    trend_html = f'<span class="kpi-trend-v2 {trend_dir}">{escape(trend)}</span>' if trend else ""
    spark_html = ""
    if sparkline_pts_data and len(sparkline_pts_data) > 1:
        spark_html = sparkline_svg(sparkline_pts_data, color)

    # IMPORTANTE: tudo em UMA LINHA pra markdown nao tratar como code block
    return (
        f'<div class="kpi-card-v2 {color}">'
        f'<div class="kpi-top-v2">'
        f'<div class="kpi-icon-v2 {color}">{icon}</div>'
        f'{trend_html}'
        f'</div>'
        f'<div class="kpi-label-v2">{escape(label)}</div>'
        f'<div class="kpi-value-v2">{escape(valor)}</div>'
        f'<div class="kpi-sub-v2">{escape(sub)}</div>'
        f'{spark_html}'
        f'</div>'
    )


def render_kpi_grid(cards: list[str]) -> str:
    """
    Constroi a grid completa em UMA UNICA STRING (pra emitir com 1 st.markdown).
    Sem isso, Streamlit quebra a grid porque envolve cada st.markdown em um container.
    """
    cards_html = "".join(cards)
    return f'<div class="kpi-grid-v2">{cards_html}</div>'


# =========================================================
# ALERTA INTELIGENTE (caixa colorida com icone)
# =========================================================
def alert_box(titulo: str, mensagem: str, tipo: str = "azul", icon: str = "ℹ️") -> str:
    """
    Alerta colorido.
    tipo: azul / green / red / orange / dourado
    """
    return f"""
    <div class="alert-v2 {tipo}">
        <div class="alert-ico-v2">{icon}</div>
        <div class="alert-content-v2">
            <strong>{escape(titulo)}</strong>
            <span>{escape(mensagem)}</span>
        </div>
    </div>
    """


# =========================================================
# FUNIL VISUAL (etapas progressivas)
# =========================================================
def funnel_step(num: int, nome: str, count: int, pct: float, total_steps: int = 5) -> str:
    """Etapa do funil — largura proporcional ao numero da etapa."""
    largura = max(25.0, 100.0 - (num - 1) * (75.0 / total_steps))
    cores = [
        "linear-gradient(90deg, #033677, #2678BC)",
        "linear-gradient(90deg, #2678BC, #4267B2)",
        "linear-gradient(90deg, #4267B2, #5B7DC1)",
        "linear-gradient(90deg, #FFB700, #FFD166)",
        "linear-gradient(90deg, #16A34A, #22C55E)",
    ]
    cor = cores[min(num - 1, len(cores) - 1)]
    color_text = "#001833" if num == 4 else "white"
    return f"""
    <div class="funnel-step-v2" style="width:{largura}%;background:{cor};color:{color_text};">
        <div class="funnel-num-v2">{num}</div>
        <div class="funnel-name-v2">{escape(nome)}</div>
        <div class="funnel-count-v2">{count:,}</div>
        <div class="funnel-pct-v2">{pct:.1f}%</div>
    </div>
    """


# =========================================================
# CSS V2.0 (injetar uma vez no app)
# =========================================================
CSS_V2 = """
<style>
/* === KPI CARD V2.0 === */
.kpi-card-v2 {
    background: white;
    border-radius: 14px;
    padding: 1.4rem;
    border: 1px solid #D1E4F5;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    transition: all 0.2s;
    position: relative;
    overflow: hidden;
}
.kpi-card-v2:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(3,54,119,0.12);
}
.kpi-card-v2::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: #033677;
}
.kpi-card-v2.azul::before { background: #033677; }
.kpi-card-v2.dourado::before { background: #FFB700; }
.kpi-card-v2.green::before { background: #16A34A; }
.kpi-card-v2.red::before { background: #DC2626; }
.kpi-card-v2.purple::before { background: #8B5CF6; }
.kpi-card-v2.azul-light::before { background: #2678BC; }

.kpi-top-v2 {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.8rem;
}
.kpi-icon-v2 {
    width: 38px; height: 38px;
    border-radius: 10px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
}
.kpi-icon-v2.azul { background: #DBEAFE; color: #033677; }
.kpi-icon-v2.dourado { background: #FFE9B0; color: #9B5400; }
.kpi-icon-v2.green { background: #DCFCE7; color: #16A34A; }
.kpi-icon-v2.red { background: #FEE2E2; color: #DC2626; }
.kpi-icon-v2.purple { background: #EDE9FE; color: #8B5CF6; }
.kpi-icon-v2.azul-light { background: #DBEAFE; color: #2678BC; }

.kpi-trend-v2 {
    font-size: 0.72rem;
    font-weight: 700;
    padding: 0.2rem 0.6rem;
    border-radius: 50px;
    white-space: nowrap;
    display: inline-block;
}
.kpi-trend-v2.up { background: #DCFCE7; color: #16A34A; }
.kpi-trend-v2.down { background: #FEE2E2; color: #DC2626; }
.kpi-trend-v2.flat { background: #F3F6FA; color: #6B7280; }

.kpi-label-v2 {
    font-size: 0.74rem;
    color: #6B7280;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 700;
    margin-bottom: 0.3rem;
}
.kpi-value-v2 {
    font-size: 1.7rem;
    font-weight: 800;
    color: #033677;
    line-height: 1.1;
}
.kpi-sub-v2 {
    font-size: 0.75rem;
    color: #6B7280;
    margin-top: 0.4rem;
}
.kpi-card-v2.green .kpi-value-v2 { color: #16A34A; }
.kpi-card-v2.red .kpi-value-v2 { color: #DC2626; }

/* === ALERT V2.0 === */
.alert-v2 {
    background: white;
    border-radius: 12px;
    padding: 0.9rem 1.2rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0.8rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    border: 1px solid #D1E4F5;
    border-left: 4px solid #FFB700;
}
.alert-v2.azul { border-left-color: #033677; }
.alert-v2.green { border-left-color: #16A34A; }
.alert-v2.red { border-left-color: #DC2626; }
.alert-v2.dourado { border-left-color: #FFB700; }
.alert-v2.orange { border-left-color: #EA580C; }
.alert-ico-v2 { font-size: 1.4rem; }
.alert-content-v2 strong {
    color: #033677;
    display: block;
    font-size: 0.92rem;
    margin-bottom: 0.15rem;
}
.alert-content-v2 span {
    font-size: 0.82rem;
    color: #374151;
}

/* === FUNNEL V2.0 === */
.funnel-v2 {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
}
.funnel-step-v2 {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.9rem 1.2rem;
    border-radius: 10px;
    transition: all 0.2s;
}
.funnel-num-v2 {
    width: 28px; height: 28px;
    background: rgba(255,255,255,0.25);
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 0.85rem;
}
.funnel-name-v2 { flex: 1; font-weight: 600; font-size: 0.9rem; }
.funnel-count-v2 { font-weight: 800; font-size: 1.05rem; }
.funnel-pct-v2 { font-size: 0.78rem; opacity: 0.85; min-width: 50px; text-align: right; }

/* === GRID V2.0 (5 colunas opcional) === */
.kpi-grid-v2 {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1.2rem;
    margin-bottom: 1.5rem;
}
@media(max-width: 768px) {
    .kpi-grid-v2 { grid-template-columns: repeat(2, 1fr); }
}
</style>
"""
