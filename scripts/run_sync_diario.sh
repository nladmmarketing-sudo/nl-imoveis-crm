#!/bin/zsh
# Wrapper que roda os 2 syncs do Jetimob em sequência.
# Rodado pelo cron 4 vezes ao dia (6h, 12h, 18h, 23h).
#
# Quando detecta sessão expirada:
#   1. Marca alerta na tabela auditoria do Supabase
#   2. Envia WhatsApp pra Anderson (via CallMeBot)

set -eu

APP_DIR="$HOME/Documents/Claude/Projects/Gerente de marketing NL imóveis/nl-imoveis-crm"
LOG="/tmp/jetimob-sync.log"
PY="$APP_DIR/.venv/bin/python"

cd "$APP_DIR"

echo "================================================================" >> "$LOG"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando sync diário" >> "$LOG"

# --- 1) Sync da lista de oportunidades (kanban) ---
echo "[$(date '+%H:%M:%S')] --- sync_jetimob_ganhas (lista) ---" >> "$LOG"
SYNC1_OUT=$("$PY" scripts/sync_jetimob_ganhas.py 2>&1) || true
echo "$SYNC1_OUT" >> "$LOG"

# --- 2) Sync do relatório oficial (totais) ---
echo "[$(date '+%H:%M:%S')] --- sync_relatorio_ganhas (totais oficiais) ---" >> "$LOG"
SYNC2_OUT=$("$PY" scripts/sync_relatorio_ganhas.py 2>&1) || true
echo "$SYNC2_OUT" >> "$LOG"

# --- Detecta sessão expirada e dispara alertas ---
if echo "$SYNC1_OUT $SYNC2_OUT" | grep -q "sessão expirou\|Login\|redirect="; then
    echo "[$(date '+%H:%M:%S')] ⚠️ SESSÃO JETIMOB EXPIROU - disparando alertas" >> "$LOG"

    "$PY" -c "
import sys
sys.path.insert(0, '$APP_DIR')

# 1) Marca alerta na auditoria (Supabase)
try:
    from utils.alertas import alerta_jetimob_expirou
    import toml
    from supabase import create_client
    cfg = toml.load('$APP_DIR/.streamlit/secrets.toml')
    c = create_client(cfg['supabase']['url'], cfg['supabase']['key'])
    c.table('auditoria').insert({
        'usuario_email': 'sistema-cron',
        'acao': 'jetimob_sessao_expirada',
        'detalhes': 'Sync cron falhou. Rodar scripts/login_jetimob.py manualmente.',
    }).execute()
    print('Alerta auditoria registrado')

    # 2) Envia EMAIL via SMTP
    enviado, msg_email = alerta_jetimob_expirou()
    print(f'Email enviado: {enviado} ({msg_email})')
except Exception as e:
    print(f'Erro alertas: {e}')
" >> "$LOG" 2>&1
fi

echo "[$(date '+%H:%M:%S')] Sync concluído" >> "$LOG"
