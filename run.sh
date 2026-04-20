#!/bin/bash
# Script pra rodar o Streamlit app localmente
# Uso: ./run.sh

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Venv nao encontrado. Criando..."
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
else
  source .venv/bin/activate
fi

echo ""
echo "============================================"
echo " Streamlit rodando em http://localhost:8501"
echo " Para parar: Ctrl+C"
echo "============================================"
echo ""

streamlit run app.py
