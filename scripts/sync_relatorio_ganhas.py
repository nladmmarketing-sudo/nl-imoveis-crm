#!/usr/bin/env python3
"""
sync_relatorio_ganhas.py — Puxa os TOTAIS OFICIAIS do relatório Jetimob.

Fonte: /relatorios/oportunidades/ganhas?period[0]=X&period[1]=Y&contract=1
       (a mesma página que Anderson olharia manualmente no Jetimob)

Por que este script existe além de sync_jetimob_ganhas.py:
 - sync_jetimob_ganhas: pega a LISTA individual de oportunidades ganhas
   (pra drill-down cliente/telefone/corretor)
 - sync_relatorio_ganhas: pega os TOTAIS MENSAIS oficiais do Jetimob
   (pra o painel mostrar números que batem 100% com o que o Jetimob exibe)

Roda os últimos 6 meses + mês atual.
"""
from __future__ import annotations

import os
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright, Page

BASE_URL = "https://app.jetimob.com"
USER_DATA_DIR = Path.home() / ".jetimob-browser-profile"
MESES_HISTORICO = 15  # além do mês atual, puxa os 15 anteriores (cobre 2025 inteiro)

# Mapeamento contract → tipo no relatorio do Jetimob
TIPOS_CONTRATO = [
    (1, "venda"),
    (2, "locacao"),
]


def load_env() -> tuple[str, str]:
    supa_url = os.getenv("SUPABASE_URL")
    supa_key = os.getenv("SUPABASE_KEY")
    if supa_url and supa_key:
        return supa_url, supa_key
    secrets_path = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        try:
            import tomllib
            with secrets_path.open("rb") as f:
                cfg = tomllib.load(f)
        except ImportError:
            import toml
            cfg = toml.load(secrets_path)
        return cfg["supabase"]["url"], cfg["supabase"]["key"]
    sys.exit("ERRO: defina SUPABASE_URL/SUPABASE_KEY ou tenha .streamlit/secrets.toml")


def month_range(n_meses: int) -> list[tuple[date, date]]:
    """Retorna lista [(primeiro_dia, ultimo_dia)] dos últimos N meses + atual."""
    out = []
    hoje = date.today()
    for offset in range(n_meses + 1):  # 0 = atual, 1 = mes anterior...
        # Calcula o primeiro dia do mês offset
        ano = hoje.year
        mes = hoje.month - offset
        while mes <= 0:
            mes += 12
            ano -= 1
        primeiro = date(ano, mes, 1)
        # Último dia: primeiro_dia_do_prox_mes - 1
        if mes == 12:
            ultimo = date(ano + 1, 1, 1) - timedelta(days=1)
        else:
            ultimo = date(ano, mes + 1, 1) - timedelta(days=1)
        # No mês atual, limita ao dia de hoje (não faz sentido puxar além)
        if primeiro.year == hoje.year and primeiro.month == hoje.month:
            ultimo = hoje
        out.append((primeiro, ultimo))
    return sorted(out)  # mais antigo primeiro


def _brl_to_cents(s: str) -> int:
    """'1.110.000,00' -> 111000000"""
    s = s.replace(".", "").replace(",", ".")
    return int(round(float(s) * 100))


def parse_relatorio(text: str) -> dict:
    """
    Extrai qtd, valor total e ranking do innerText da página de relatório.
    Formato esperado (exemplo real do Jetimob):
        'Oportunidades ganhas
         3  -40%
         Oportunidades
         ganhas entre 01/04/2026 e 24/04/2026
         R$ 1.110.000,00  -46.32%
         Valor ganho
         ...
         Ganhas por responsável
         Ranking...
         1
         Ione Ferreira dos Santos
         R$ 760.000,00   18.75%
         2   100%
         ...
         Ganhas por origem
         ...'
    """
    out = {"qtd": 0, "valor_cents": 0, "ranking": []}

    # Qtd total
    m = re.search(r"(\d+)\s+[-+]?[\d.]*%?\s*Oportunidades\s+ganhas\s+entre", text)
    if m:
        out["qtd"] = int(m.group(1))

    # Valor total
    m = re.search(r"R\$\s+([\d.]+,\d{2})\s+[-+]?[\d.]*%?\s*Valor\s+ganho", text)
    if m:
        out["valor_cents"] = _brl_to_cents(m.group(1))

    # Ranking: bloco entre "Ganhas por responsável" e "Ganhas por origem"
    bloco = re.search(r"Ganhas por responsável(.*?)(?:Ganhas por origem|$)",
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


def fetch_mes(page: Page, ini: date, fim: date, contract: int) -> dict:
    url = (f"{BASE_URL}/relatorios/oportunidades/ganhas"
           f"?period%5B0%5D={ini.isoformat()}T03:00:00.000Z"
           f"&period%5B1%5D={fim.isoformat()}T23:59:59.999Z"
           f"&contract={contract}")
    page.goto(url, wait_until="domcontentloaded", timeout=25_000)

    # Aguarda os dados renderizarem. A página mostra "Sem dados suficientes" OU
    # um texto "ganhas entre DD/MM/YYYY e DD/MM/YYYY" — esperar um dos dois.
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
        pass  # segue com o que tiver

    # Pequena folga extra pra JS popular valores
    time.sleep(2)
    text = page.evaluate("() => document.body.innerText")

    if "ganhas entre" not in text:
        # Nenhum dado no período
        return {"qtd": 0, "valor_cents": 0, "ranking": []}
    return parse_relatorio(text)


def main() -> None:
    supa_url, supa_key = load_env()

    if not USER_DATA_DIR.exists():
        sys.exit(f"ERRO: profile não encontrado em {USER_DATA_DIR}. "
                 "Rode scripts/login_jetimob.py uma vez antes.")

    meses = month_range(MESES_HISTORICO)
    print(f"[info] puxando {len(meses)} meses: "
          f"{meses[0][0]} → {meses[-1][1]}")

    resultados = []  # linhas pra upsert

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(USER_DATA_DIR), headless=True,
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()
        # Warm-up: abre uma vez pra fazer o login carregar
        page.goto(f"{BASE_URL}/oportunidades?contrato=venda&status=ganhas",
                  wait_until="domcontentloaded", timeout=20_000)
        time.sleep(1)

        from datetime import datetime, timezone
        for ini, fim in meses:
            for contract_code, tipo in TIPOS_CONTRATO:
                try:
                    dados = fetch_mes(page, ini, fim, contract=contract_code)
                    print(f"[{tipo:<8}] {ini.strftime('%Y-%m')}: "
                          f"{dados['qtd']:>3} ganhas · "
                          f"R$ {dados['valor_cents']/100:>12,.2f}")
                    resultados.append({
                        "mes_referencia":    ini.isoformat(),
                        "tipo":              tipo,
                        "qtd_ganhas":        dados["qtd"],
                        "valor_total_cents": dados["valor_cents"],
                        "ranking_json":      dados["ranking"],
                        "scraped_at":        datetime.now(timezone.utc).isoformat(),
                    })
                except Exception as e:
                    print(f"[{tipo:<8}] {ini.strftime('%Y-%m')}: ERRO {e}")

        ctx.close()

    # Upsert com retry + proteção: nunca sobrescreve dados positivos com zero
    # (defesa contra falhas momentâneas no scraping/Jetimob)
    from supabase import create_client
    client = create_client(supa_url, supa_key)

    # Carrega valores existentes para comparar
    existing = {}
    try:
        resp = client.table("resumo_mensal_jetimob").select(
            "mes_referencia,tipo,qtd_ganhas,valor_total_cents,ranking_json"
        ).execute()
        for r in resp.data or []:
            key = (r["mes_referencia"][:10], r["tipo"])
            existing[key] = r
    except Exception as e:
        print(f"[warn] nao conseguiu carregar existentes: {e}")

    ok = 0
    skipped = 0
    for row in resultados:
        key = (row["mes_referencia"], row["tipo"])
        prev = existing.get(key)
        # PROTECAO: se ja tem dados positivos e a coleta atual veio 0,
        # algo deu errado no scraping — pula o upsert
        if (prev and (prev.get("qtd_ganhas", 0) or 0) > 0
                and row["qtd_ganhas"] == 0):
            print(f"[skip] {row['mes_referencia']} [{row['tipo']}]: "
                  f"banco tem {prev['qtd_ganhas']} ops mas scraping veio 0 — "
                  f"NAO sobrescreve (proteção)")
            skipped += 1
            continue
        for tentativa in range(3):
            try:
                client.table("resumo_mensal_jetimob") \
                      .upsert(row, on_conflict="mes_referencia,tipo") \
                      .execute()
                ok += 1
                break
            except Exception as e:
                if tentativa < 2:
                    time.sleep(3)
                else:
                    print(f"[ERRO] {row['mes_referencia']} {row['tipo']}: {e}")
    print(f"[supabase] upsert: {ok}/{len(resultados)} linhas concluído"
          + (f" (pulou {skipped} por protecao anti-zero)" if skipped else ""))


if __name__ == "__main__":
    main()
