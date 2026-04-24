# Sync Jetimob Ganhas → Supabase

Puxa oportunidades ganhas (venda + locação + temporada) do Jetimob e faz upsert
na tabela `oportunidades_ganhas_jetimob` do Supabase.

## Setup (1x só)

```bash
cd ~/Agencia/06-clientes/nl-imoveis/01-dashboard-jetimob/streamlit-app
source .venv/bin/activate
pip install -r scripts/requirements-sync.txt
playwright install chromium
```

No Supabase, rode o SQL `sql/add_oportunidades_ganhas.sql` (cria tabela + índices + views).

Depois faça login 1 vez:

```bash
python scripts/login_jetimob.py
# Logue no Jetimob na janela que abrir. Aperte ENTER no terminal quando tiver logado.
```

## Rodar sync

```bash
python scripts/sync_jetimob_ganhas.py
```

Saída esperada:
```
[ok] 68 corretores carregados
[ok] venda      →  22 ganhas (total kanban: 22)
[ok] locacao    →  19 ganhas (total kanban: 19)
[ok] temporada  →   0 ganhas (total kanban: 0)
[supabase] upsert de 41 linhas concluído
```

## Agendar diário (6h da manhã)

```bash
crontab -e
# adicione a linha:
0 6 * * * cd ~/Agencia/06-clientes/nl-imoveis/01-dashboard-jetimob/streamlit-app && .venv/bin/python scripts/sync_jetimob_ganhas.py >> /tmp/jetimob-sync.log 2>&1
```

## Se der erro "sessão expirou"

Rode `python scripts/login_jetimob.py` de novo pra re-autenticar.
