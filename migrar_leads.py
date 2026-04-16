"""
Script de migracao: Jetimob API -> Supabase
Busca todos os leads da API Jetimob e insere na tabela leads_jetimob do Supabase
"""
import requests
import json
import time

# Jetimob API
JETIMOB_API_URL = "https://api.jetimob.com/leads/"
JETIMOB_PUBLIC_KEY = "7mMitUrfKuO1c7JaDoTDikmdm9oz5Pukpe89R9esViG6HioameNHvj0uIfg63sBb"
JETIMOB_PRIVATE_KEY = "l1QkXoOSiqSDHBnzZpaHg1obdQjePceSIIBJP0NHs1HkkXVyJBjcebVs9hV4CdsR"

# Supabase
SUPABASE_URL = "https://ybpicxohafsulmwxbewa.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlicGljeG9oYWZzdWxtd3hiZXdhIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NDk4NTk4MiwiZXhwIjoyMDkwNTYxOTgyfQ.-JJyBUDQmoUq0CGUczdOi7vuYALSdocv0JGcXP1XYCw"

HEADERS_SUPABASE = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}


def fetch_jetimob_leads():
    """Busca todos os leads da API Jetimob (retorna tudo de uma vez)"""
    url = f"{JETIMOB_API_URL}{JETIMOB_PUBLIC_KEY}"
    print(f"  Buscando de {url[:60]}...")

    resp = requests.get(url, headers={
        "Authorization-Key": JETIMOB_PRIVATE_KEY,
        "Content-Type": "application/json"
    }, timeout=60)

    if resp.status_code != 200:
        print(f"Erro HTTP {resp.status_code}: {resp.text[:200]}")
        return []

    data = resp.json()
    leads = data.get("result", [])
    total = data.get("total", len(leads))
    print(f"  API retornou {len(leads)} leads (total reportado: {total})")
    return leads


def normalize_lead(lead):
    """Converte lead do formato Jetimob para formato Supabase"""
    # Email
    email = ""
    if lead.get("emails") and len(lead["emails"]) > 0:
        em = lead["emails"][0]
        email = em.get("email", em) if isinstance(em, dict) else str(em)
    elif lead.get("email"):
        email = lead["email"]
    email = email.lower().strip() if email else None

    # Telefone
    telefone = ""
    if lead.get("phones") and len(lead["phones"]) > 0:
        ph = lead["phones"][0]
        telefone = ph.get("phone", ph.get("number", "")) if isinstance(ph, dict) else str(ph)
    elif lead.get("phone"):
        telefone = lead["phone"]

    # Corretor
    corretor = ""
    resp = lead.get("responsible") or {}
    if isinstance(resp, dict):
        corretor = resp.get("name", resp.get("full_name", ""))
    elif isinstance(resp, str):
        corretor = resp

    # Origem
    origem = lead.get("prospecting_source", lead.get("source", ""))

    # Produto/Imovel
    produto = ""
    prop = lead.get("property") or {}
    if isinstance(prop, dict) and prop:
        partes = []
        if prop.get("property_type"): partes.append(prop["property_type"])
        if prop.get("code"): partes.append(prop["code"])
        loc = prop.get("location", {}) or {}
        if isinstance(loc, dict) and loc.get("neighborhood"): partes.append(loc["neighborhood"])
        produto = " - ".join(partes)

    # Localizacao
    bairro = cidade = estado = ""
    loc = (prop.get("location", {}) or {}) if isinstance(prop, dict) else {}
    if isinstance(loc, dict):
        bairro = loc.get("neighborhood", "")
        cidade = loc.get("city", "")
        estado = loc.get("state_acronym", loc.get("state", ""))

    codigo_imovel = prop.get("code", "") if isinstance(prop, dict) else ""
    tipo_imovel = prop.get("property_type", "") if isinstance(prop, dict) else ""
    status = lead.get("status", lead.get("stage", ""))
    created = lead.get("created_at", lead.get("conversion_date", ""))

    return {
        "created_at": created if created else None,
        "nome": lead.get("full_name", lead.get("name", "")),
        "email": email,
        "telefone": telefone or None,
        "origem": origem or None,
        "produto": produto or None,
        "corretor": corretor or None,
        "status": status or None,
        "evento": lead.get("event", None),
        "bairro": bairro or None,
        "cidade": cidade or None,
        "estado": estado or None,
        "codigo_imovel": codigo_imovel or None,
        "tipo_imovel": tipo_imovel or None,
        "valor": None,
        "mensagem": lead.get("message", None),
        "jetimob_id": str(lead.get("id", "")) if lead.get("id") else None,
    }


def insert_to_supabase(leads_normalized):
    """Insere leads no Supabase em lotes"""
    batch_size = 500
    total_inserted = 0

    for i in range(0, len(leads_normalized), batch_size):
        batch = leads_normalized[i:i + batch_size]
        print(f"  Lote {i // batch_size + 1}: inserindo {len(batch)} leads...", end=" ")

        try:
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/leads_jetimob",
                headers=HEADERS_SUPABASE,
                json=batch,
                timeout=60
            )
            if resp.status_code in [200, 201]:
                total_inserted += len(batch)
                print(f"OK ({total_inserted} total)")
            else:
                print(f"Erro {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"Erro: {e}")

        time.sleep(0.3)

    return total_inserted


def main():
    print("=" * 60)
    print("MIGRACAO JETIMOB -> SUPABASE")
    print("=" * 60)

    print("\n[1/3] Buscando leads da API Jetimob...")
    leads = fetch_jetimob_leads()
    if not leads:
        print("Nenhum lead encontrado. Abortando.")
        return

    print(f"\n[2/3] Normalizando {len(leads)} leads...")
    normalized = []
    erros = 0
    for lead in leads:
        try:
            normalized.append(normalize_lead(lead))
        except Exception as e:
            erros += 1
    print(f"  Normalizados: {len(normalized)} | Erros: {erros}")

    print(f"\n[3/3] Inserindo no Supabase...")
    inserted = insert_to_supabase(normalized)

    print("\n" + "=" * 60)
    print(f"MIGRACAO CONCLUIDA!")
    print(f"  Leads da API: {len(leads)}")
    print(f"  Inseridos no Supabase: {inserted}")
    print("=" * 60)


if __name__ == "__main__":
    main()
