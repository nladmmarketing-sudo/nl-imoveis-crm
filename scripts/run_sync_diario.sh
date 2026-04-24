#!/bin/zsh
# Wrapper que roda os 2 syncs do Jetimob em sequência.
# Chamado pelo cron às 6h da manhã.

set -eu

APP_DIR="$HOME/Agencia/06-clientes/nl-imoveis/01-dashboard-jetimob/streamlit-app"
LOG="/tmp/jetimob-sync.log"
PY="$APP_DIR/.venv/bin/python"

cd "$APP_DIR"

echo "================================================================" >> "$LOG"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando sync diário" >> "$LOG"

echo "[$(date '+%H:%M:%S')] --- sync_jetimob_ganhas (lista) ---" >> "$LOG"
"$PY" scripts/sync_jetimob_ganhas.py >> "$LOG" 2>&1 || echo "[FALHOU] sync_jetimob_ganhas" >> "$LOG"

echo "[$(date '+%H:%M:%S')] --- sync_relatorio_ganhas (totais oficiais) ---" >> "$LOG"
"$PY" scripts/sync_relatorio_ganhas.py >> "$LOG" 2>&1 || echo "[FALHOU] sync_relatorio_ganhas" >> "$LOG"

echo "[$(date '+%H:%M:%S')] Sync concluído" >> "$LOG"
