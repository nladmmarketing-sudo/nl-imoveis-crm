#!/usr/bin/env python3
"""
sync_jetimob_ganhas.py — Sync de oportunidades GANHAS do Jetimob → Supabase.

Puxa via scraping autenticado (API interna /api/oportunidades/kanban?status=ganhas)
para os 3 tipos de contrato (venda, locacao, temporada) e faz upsert por jetimob_id.

Primeiro uso:  rode `login_jetimob.py` uma vez pra salvar a sessão.
Depois:        este script roda headless usando a sessão salva.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright, Page
from supabase import create_client

# ----- Configuração -----
BASE_URL = "https://app.jetimob.com"
USER_DATA_DIR = Path.home() / ".jetimob-browser-profile"
CONTRATOS = ("venda", "locacao", "temporada")


def load_env() -> tuple[str, str]:
    """Carrega SUPABASE_URL e SUPABASE_KEY de .streamlit/secrets.toml OU env."""
    supa_url = os.getenv("SUPABASE_URL")
    supa_key = os.getenv("SUPABASE_KEY")
    if supa_url and supa_key:
        return supa_url, supa_key

    secrets_path = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        try:
            import tomllib  # Python 3.11+
            with secrets_path.open("rb") as f:
                cfg = tomllib.load(f)
        except ImportError:
            import toml  # fallback para Python < 3.11
            cfg = toml.load(secrets_path)
        return cfg["supabase"]["url"], cfg["supabase"]["key"]
    sys.exit("ERRO: defina SUPABASE_URL/SUPABASE_KEY ou tenha .streamlit/secrets.toml")


def fetch_ganhas(page: Page, contrato: str) -> dict:
    """Chama a API interna do Jetimob e retorna o JSON bruto."""
    url = (
        f"{BASE_URL}/api/oportunidades/kanban"
        f"?busca=&contrato={contrato}&responsavel=&status=ganhas"
        f"&atualizacao=&etapa=&temperatura=&fonte_prospeccao=&portal="
        f"&rede_social=&createdDate=&updatedDate=&agendamento=&labels="
        f"&headquarter=&page=1"
    )
    payload = page.evaluate(
        """async (u) => {
            const r = await fetch(u, { credentials: 'include',
                                       headers: { 'Accept': 'application/json' }});
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return await r.json();
        }""",
        url,
    )
    return payload["data"]


def fetch_brokers(page: Page) -> dict[int, str]:
    """Retorna map id → nome do corretor."""
    data = page.evaluate(
        """async () => {
            const r = await fetch('/api/corretores', { credentials: 'include' });
            return await r.json();
        }"""
    )
    return {b["id"]: b["name"] for b in data["data"]["brokers"]}


def flatten_opportunities(raw: dict, contrato: str, brokers: dict[int, str],
                          scraped_at: str) -> list[dict]:
    """Achata a resposta kanban em linhas prontas pro Supabase."""
    rows: list[dict] = []
    opps = raw.get("opportunities")
    # Quando não há items, Jetimob devolve objeto ao invés de array
    if isinstance(opps, dict):
        opps = list(opps.values())

    for etapa in opps or []:
        items = etapa.get("items") or []
        if isinstance(items, dict):
            items = list(items.values())
        for it in items:
            phone = it.get("phone") or {}
            corretor_id = it["owned_by"]
            rows.append({
                "jetimob_id":      it["opportunity_id"],
                "contrato":        contrato,
                "etapa":           etapa["name"],
                "step_id":         etapa["step_id"],
                "nome_cliente":    it.get("name") or "",
                "telefone_e164":   phone.get("e164"),
                "telefone_ddd":    phone.get("ddd"),
                "is_whatsapp":     bool(phone.get("is_whatsapp")),
                "email":           it.get("email"),
                "valor_cents":     int(it.get("maxValue") or 0),
                "corretor_id":     corretor_id,
                "corretor_nome":   brokers.get(corretor_id, f"id={corretor_id}"),
                "status_jetimob":  it.get("status", 1),
                "criado_em":       it["opportunity_created_at"],
                "entrou_etapa_em": it["step_created_at"],
                "scraped_at":      scraped_at,
            })
    return rows


def enrich_ganha_em(page: Page, rows: list[dict]) -> None:
    """
    Para cada oportunidade ganha, busca `opportunity.updated_at` do Jetimob
    e grava como `ganha_em` (data em que foi marcada como ganha).

    O endpoint /api/oportunidades/kanban não retorna esse campo, então
    precisamos chamar /api/oportunidades/{id} para cada uma.
    """
    ids = [r["jetimob_id"] for r in rows]
    if not ids:
        return

    # Busca todas em paralelo via Promise.all no browser
    updated_map = page.evaluate(
        """async (ids) => {
            const results = await Promise.all(ids.map(async id => {
                try {
                    const r = await fetch('/api/oportunidades/' + id, { credentials: 'include' });
                    const j = await r.json();
                    return [id, j.data?.opportunity?.updated_at || null];
                } catch (e) {
                    return [id, null];
                }
            }));
            return Object.fromEntries(results);
        }""",
        ids,
    )
    for r in rows:
        r["ganha_em"] = updated_map.get(str(r["jetimob_id"])) or updated_map.get(r["jetimob_id"])


def upsert_supabase(rows: list[dict], supa_url: str, supa_key: str) -> int:
    """Upsert por jetimob_id. Retorna quantidade afetada."""
    if not rows:
        return 0
    client = create_client(supa_url, supa_key)
    # Upsert em lotes de 100
    total = 0
    for i in range(0, len(rows), 100):
        chunk = rows[i:i + 100]
        resp = client.table("oportunidades_ganhas_jetimob") \
                     .upsert(chunk, on_conflict="jetimob_id") \
                     .execute()
        total += len(resp.data or [])
    return total


def main() -> None:
    supa_url, supa_key = load_env()
    scraped_at = datetime.now(timezone.utc).isoformat()

    if not USER_DATA_DIR.exists():
        sys.exit(f"ERRO: profile não encontrado em {USER_DATA_DIR}. "
                 "Rode scripts/login_jetimob.py uma vez antes.")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(USER_DATA_DIR),
            headless=True,
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()
        page.goto(f"{BASE_URL}/oportunidades?contrato=venda&status=ganhas",
                  wait_until="domcontentloaded", timeout=30_000)

        # Se redirecionou pra login OU não tem cookie de sessão, aborta
        logged_in = page.evaluate("""async () => {
            const r = await fetch('/api/check', { credentials: 'include' });
            if (!r.ok) return false;
            const txt = await r.text();
            return txt.trim().startsWith('{') || txt.trim().startsWith('[');
        }""")
        if (not logged_in
                or "Login" in (page.title() or "")
                or "redirect=" in page.url):
            ctx.close()
            sys.exit("ERRO: sessão expirou. Rode scripts/login_jetimob.py de novo.")

        brokers = fetch_brokers(page)
        print(f"[ok] {len(brokers)} corretores carregados")

        all_rows: list[dict] = []
        for contrato in CONTRATOS:
            raw = fetch_ganhas(page, contrato)
            rows = flatten_opportunities(raw, contrato, brokers, scraped_at)
            print(f"[ok] {contrato:<10} → {len(rows):>3} ganhas "
                  f"(total kanban: {raw.get('total_items')})")
            all_rows.extend(rows)

        # Enriquece com opportunity.updated_at (data real do ganho)
        enrich_ganha_em(page, all_rows)
        ganhas_com_data = sum(1 for r in all_rows if r.get("ganha_em"))
        print(f"[ok] ganha_em preenchido para {ganhas_com_data}/{len(all_rows)}")

        ctx.close()

    affected = upsert_supabase(all_rows, supa_url, supa_key)
    print(f"[supabase] upsert de {affected} linhas concluído")


if __name__ == "__main__":
    main()
