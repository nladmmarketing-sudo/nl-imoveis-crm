#!/usr/bin/env python3
"""
login_jetimob.py — Roda UMA VEZ pra salvar a sessão do Jetimob no disco.

Abre o Chromium visível, você loga manualmente, confirma no terminal.
A pasta ~/.jetimob-browser-profile guarda cookies/localStorage pra que
sync_jetimob_ganhas.py rode depois em headless.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

USER_DATA_DIR = Path.home() / ".jetimob-browser-profile"
BASE_URL = "https://app.jetimob.com"


def main() -> None:
    USER_DATA_DIR.mkdir(exist_ok=True)
    print(f"[info] usando profile em {USER_DATA_DIR}")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(USER_DATA_DIR),
            headless=False,
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()
        page.goto(f"{BASE_URL}/oportunidades?contrato=venda&status=ganhas")

        print("\n" + "=" * 60)
        print(" Faça login no Jetimob na janela do Chromium que abriu.")
        print(" O script detecta o login automaticamente e fecha sozinho.")
        print(" Timeout: 5 minutos.")
        print("=" * 60)

        # Espera a URL conter /oportunidades (sinal de login feito)
        try:
            page.wait_for_url("**/oportunidades**", timeout=300_000)
            # Espera a página carregar completamente
            page.wait_for_load_state("networkidle", timeout=30_000)
            print("[ok] login detectado, salvando sessão...")
        except Exception as e:
            print(f"[timeout] {e}")

        ctx.close()
        print("[ok] sessão salva. Agora pode rodar sync_jetimob_ganhas.py")


if __name__ == "__main__":
    main()
