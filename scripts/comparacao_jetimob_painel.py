#!/usr/bin/env python3
"""
comparacao_jetimob_painel.py — Compara o que está no Jetimob com o que o painel mostra.

Para CADA mês de Jan/2025 até hoje:
  - Busca no Jetimob: venda (contract=1) + locacao (contract=2)
  - Pega: total qtd, valor total, ranking de corretores
  - Compara com:
      * resumo_mensal_jetimob (Supabase) — fonte oficial
      * oportunidades_ganhas_jetimob (Supabase) — kanban
  - Gera relatorio CSV com diferenças
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright, Page
from supabase import create_client

BASE_URL = "https://app.jetimob.com"
USER_DATA_DIR = Path.home() / ".jetimob-browser-profile"
PROJECT_DIR = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_DIR / "exports_auditoria"
OUTPUT_DIR.mkdir(exist_ok=True)

# Mapeamento de contract code → tipo
TIPOS = [
    (1, "venda"),
    (2, "locacao"),
]

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Marco", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def load_env():
    secrets = PROJECT_DIR / ".streamlit" / "secrets.toml"
    try:
        import tomllib
        with secrets.open("rb") as f:
            cfg = tomllib.load(f)
    except ImportError:
        import toml
        cfg = toml.load(secrets)
    return cfg["supabase"]["url"], cfg["supabase"]["key"]


def gerar_meses() -> list[tuple[date, date]]:
    """Gera (primeiro, ultimo) para Jan/2025 até mes atual."""
    out = []
    hoje = date.today()
    for ano in [2025, 2026]:
        for mes in range(1, 13):
            primeiro = date(ano, mes, 1)
            if primeiro > hoje:
                break
            if mes == 12:
                ultimo = date(ano + 1, 1, 1) - timedelta(days=1)
            else:
                ultimo = date(ano, mes + 1, 1) - timedelta(days=1)
            if primeiro.year == hoje.year and primeiro.month == hoje.month:
                ultimo = hoje
            out.append((primeiro, ultimo))
    return out


def _brl_to_cents(s: str) -> int:
    s = s.replace(".", "").replace(",", ".")
    return int(round(float(s) * 100))


def parse_relatorio(text: str) -> dict:
    """Extrai qtd, valor, ranking do innerText da pagina."""
    out = {"qtd": 0, "valor_cents": 0, "ranking": []}

    m = re.search(r"(\d+)\s+[-+]?[\d.]*%?\s*Oportunidades\s+ganhas\s+entre", text)
    if m:
        out["qtd"] = int(m.group(1))

    m = re.search(r"R\$\s+([\d.]+,\d{2})\s+[-+]?[\d.]*%?\s*Valor\s+ganho", text)
    if m:
        out["valor_cents"] = _brl_to_cents(m.group(1))

    bloco = re.search(r"Ganhas por respons[áa]vel(.*?)(?:Ganhas por origem|$)",
                      text, re.DOTALL)
    if bloco:
        chunks = re.findall(
            r"(\d+)\s+([A-ZÀ-ÿ][^\n]+?)\s+R\$\s+([\d.]+,\d{2})[^\n]*\n\s*(\d+)",
            bloco.group(1),
        )
        for pos, nome, valor, qtd in chunks:
            out["ranking"].append({
                "pos": int(pos),
                "nome": nome.strip(),
                "qtd": int(qtd),
                "valor_cents": _brl_to_cents(valor),
            })
    return out


def fetch_mes_jetimob(page: Page, ini: date, fim: date, contract: int) -> dict:
    url = (f"{BASE_URL}/relatorios/oportunidades/ganhas"
           f"?period%5B0%5D={ini.isoformat()}T03:00:00.000Z"
           f"&period%5B1%5D={fim.isoformat()}T23:59:59.999Z"
           f"&contract={contract}")
    page.goto(url, wait_until="domcontentloaded", timeout=30_000)
    try:
        page.wait_for_function(
            """() => {
                const t = document.body.innerText;
                return /ganhas entre \\d{2}\\/\\d{2}\\/\\d{4}/.test(t)
                    || (t.match(/Sem dados suficientes/g) || []).length >= 3;
            }""",
            timeout=20_000,
        )
    except Exception:
        pass
    time.sleep(2)
    text = page.evaluate("() => document.body.innerText")
    if "ganhas entre" not in text:
        return {"qtd": 0, "valor_cents": 0, "ranking": []}
    return parse_relatorio(text)


def main():
    supa_url, supa_key = load_env()
    client = create_client(supa_url, supa_key)

    if not USER_DATA_DIR.exists():
        sys.exit(f"ERRO: profile nao existe em {USER_DATA_DIR}. "
                 "Rode scripts/login_jetimob.py uma vez antes.")

    meses = gerar_meses()
    print(f"\n📊 Comparacao Jetimob × Painel — {len(meses)} meses ({meses[0][0]} → {meses[-1][1]})")
    print("=" * 90)

    # Carrega dados do Supabase pra comparacao
    print("\n[1/3] Carregando dados do Supabase...")
    resumo_resp = client.table("resumo_mensal_jetimob").select("*").execute()
    df_resumo_supa = {f"{r['mes_referencia'][:7]}_{r['tipo']}": r for r in (resumo_resp.data or [])}

    # Kanban
    todos_kanban = []
    inicio = 0
    while True:
        r = client.table("oportunidades_ganhas_jetimob").select("*").range(inicio, inicio+999).execute()
        if not r.data:
            break
        todos_kanban.extend(r.data)
        if len(r.data) < 1000:
            break
        inicio += 1000
    print(f"  ✓ resumo_mensal_jetimob: {len(df_resumo_supa)} entradas")
    print(f"  ✓ oportunidades_ganhas_jetimob: {len(todos_kanban)} registros")

    print("\n[2/3] Acessando Jetimob (navegador visivel)...")
    relatorio = []  # linhas do CSV final

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(USER_DATA_DIR),
            headless=False,  # Visivel pra Anderson acompanhar
            viewport={"width": 1380, "height": 900},
        )
        page = ctx.new_page()
        # Warm-up
        page.goto(f"{BASE_URL}/oportunidades?contrato=venda&status=ganhas",
                  wait_until="domcontentloaded", timeout=30_000)
        time.sleep(2)

        # Verifica login
        if "Login" in (page.title() or "") or "redirect=" in page.url:
            ctx.close()
            sys.exit("ERRO: sessao Jetimob expirou. Rode login_jetimob.py de novo.")

        for ini, fim in meses:
            mes_label = f"{MESES_PT[ini.month]}/{ini.year}"
            mes_key = f"{ini.year}-{ini.month:02d}"
            for contract_code, tipo in TIPOS:
                try:
                    dados = fetch_mes_jetimob(page, ini, fim, contract_code)
                except Exception as e:
                    print(f"  ✗ {mes_label} [{tipo}]: ERRO {e}")
                    dados = {"qtd": 0, "valor_cents": 0, "ranking": []}

                # Comparacao com Supabase
                supa_key_lookup = f"{mes_key}_{tipo}"
                supa = df_resumo_supa.get(supa_key_lookup)
                supa_qtd = supa.get("qtd_ganhas", 0) if supa else None
                supa_valor = (supa.get("valor_total_cents", 0) or 0) / 100 if supa else None

                # Kanban: filtra por mes/tipo (apenas Fechamento)
                kanban_mes = [
                    k for k in todos_kanban
                    if k.get("contrato") == tipo
                    and k.get("etapa") == "Fechamento"
                    and k.get("ganha_em")
                    and k["ganha_em"][:7] == mes_key
                ]
                kanban_qtd = len(kanban_mes)
                kanban_valor = sum((k.get("valor_cents", 0) or 0) for k in kanban_mes) / 100

                jeti_valor = dados["valor_cents"] / 100

                # Diferencas
                diff_supa = "✓" if supa and supa_qtd == dados["qtd"] and abs(supa_valor - jeti_valor) < 1 else "❌"
                diff_kanban = "✓" if kanban_qtd == dados["qtd"] else "❌"

                ranking_str = " | ".join(
                    f"{r['nome']}={r['qtd']}/R${r['valor_cents']/100:.0f}"
                    for r in dados["ranking"]
                )

                print(
                    f"  {mes_label:18} [{tipo:7}] "
                    f"Jeti: {dados['qtd']:>3}/R${jeti_valor:>10,.0f}  "
                    f"Supa: {('—' if supa_qtd is None else f'{supa_qtd}/R${supa_valor:.0f}'):20} "
                    f"Kanban: {kanban_qtd}/R${kanban_valor:.0f} {diff_supa}{diff_kanban}"
                )

                relatorio.append({
                    "mes": mes_label,
                    "ano_mes": mes_key,
                    "tipo": tipo,
                    # Jetimob (FONTE DE VERDADE)
                    "jetimob_qtd": dados["qtd"],
                    "jetimob_valor_total": jeti_valor,
                    "jetimob_ranking": ranking_str,
                    # Supabase resumo (oficial sincronizado)
                    "supabase_qtd": supa_qtd if supa_qtd is not None else "SEM SYNC",
                    "supabase_valor": supa_valor if supa_valor is not None else "SEM SYNC",
                    # Supabase kanban (registros individuais)
                    "kanban_qtd": kanban_qtd,
                    "kanban_valor": kanban_valor,
                    # Diferencas
                    "diff_supa_qtd": (dados["qtd"] - supa_qtd) if supa_qtd is not None else "—",
                    "diff_kanban_qtd": dados["qtd"] - kanban_qtd,
                    "status_sync_oficial": "OK" if supa_qtd is not None else "FALTA SYNC",
                })

        ctx.close()

    print("\n[3/3] Salvando relatorio...")

    # Salva CSV
    import csv
    csv_path = OUTPUT_DIR / "comparacao_jetimob_painel.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        if relatorio:
            writer = csv.DictWriter(f, fieldnames=relatorio[0].keys())
            writer.writeheader()
            writer.writerows(relatorio)
    print(f"  ✓ CSV salvo: {csv_path}")

    # Imprime resumo
    print("\n" + "=" * 90)
    print("📋 RESUMO DAS DIFERENCAS")
    print("=" * 90)

    sem_sync = [r for r in relatorio if r["status_sync_oficial"] == "FALTA SYNC" and r["jetimob_qtd"] > 0]
    if sem_sync:
        print(f"\n⚠️  {len(sem_sync)} meses TEM dados no Jetimob mas NAO foram sincronizados:")
        for r in sem_sync:
            print(f"    {r['mes']:18} [{r['tipo']:7}] Jetimob: {r['jetimob_qtd']} ops / R${r['jetimob_valor_total']:,.0f}")

    discrepancias = [r for r in relatorio
                      if r["status_sync_oficial"] == "OK"
                      and r["diff_supa_qtd"] != 0]
    if discrepancias:
        print(f"\n⚠️  {len(discrepancias)} meses com DIFERENCA entre Jetimob e Painel:")
        for r in discrepancias:
            print(f"    {r['mes']:18} [{r['tipo']:7}] "
                  f"Jeti={r['jetimob_qtd']} vs Painel={r['supabase_qtd']} "
                  f"(diff: {r['diff_supa_qtd']:+d})")

    if not sem_sync and not discrepancias:
        print("\n✅ TUDO BATE! Painel reflete corretamente o Jetimob.")

    print(f"\n✅ Relatorio completo em: {csv_path}")


if __name__ == "__main__":
    main()
