-- ============================================================
-- Tabela: oportunidades_ganhas_jetimob
-- Propósito: armazenar oportunidades ganhas (vendas + locações + temporadas)
--            puxadas do Jetimob via scraping automatizado
-- Fonte: /api/oportunidades/kanban?status=ganhas do Jetimob
-- Atualização: diária (cron 6h) — upsert por jetimob_id
-- ============================================================

CREATE TABLE IF NOT EXISTS oportunidades_ganhas_jetimob (
    jetimob_id       bigint PRIMARY KEY,           -- opportunity_id do Jetimob
    contrato         text NOT NULL CHECK (contrato IN ('venda','locacao','temporada')),
    etapa            text NOT NULL,                 -- Lead, Visita, Proposta, Fechamento, etc
    step_id          int NOT NULL,                  -- id da etapa no Jetimob
    nome_cliente     text NOT NULL,
    telefone_e164    text,
    telefone_ddd     text,
    is_whatsapp      boolean DEFAULT false,
    email            text,
    valor_cents      bigint NOT NULL DEFAULT 0,     -- valor em centavos
    corretor_id      int NOT NULL,
    corretor_nome    text,                          -- resolvido no momento do sync
    status_jetimob   int NOT NULL,                  -- 1 = ganha
    criado_em        timestamptz NOT NULL,          -- opportunity_created_at
    entrou_etapa_em  timestamptz NOT NULL,          -- step_created_at (quando entrou etapa atual)
    scraped_at       timestamptz NOT NULL DEFAULT now()
);

-- Índice pra queries por mês de fechamento (usado no painel)
CREATE INDEX IF NOT EXISTS idx_ganhas_fechamento_mes
    ON oportunidades_ganhas_jetimob (entrou_etapa_em DESC)
    WHERE etapa = 'Fechamento';

-- Índice por corretor (ranking mensal)
CREATE INDEX IF NOT EXISTS idx_ganhas_corretor
    ON oportunidades_ganhas_jetimob (corretor_id, entrou_etapa_em DESC);

-- Índice por contrato
CREATE INDEX IF NOT EXISTS idx_ganhas_contrato
    ON oportunidades_ganhas_jetimob (contrato, entrou_etapa_em DESC);

-- ============================================================
-- View: vendas_mes_atual
-- Mostra fechamentos (venda+locacao) do mês vigente
-- ============================================================
CREATE OR REPLACE VIEW vendas_mes_atual AS
SELECT
    jetimob_id, contrato, nome_cliente, telefone_e164, email,
    (valor_cents::numeric / 100) AS valor_reais,
    corretor_id, corretor_nome,
    entrou_etapa_em::date AS data_fechamento
FROM oportunidades_ganhas_jetimob
WHERE etapa = 'Fechamento'
  AND entrou_etapa_em >= date_trunc('month', now())
  AND entrou_etapa_em <  date_trunc('month', now()) + interval '1 month';

-- ============================================================
-- View: ranking_corretores_mes
-- Ranking de fechamentos do mês vigente por corretor
-- ============================================================
CREATE OR REPLACE VIEW ranking_corretores_mes AS
SELECT
    corretor_id,
    corretor_nome,
    contrato,
    COUNT(*)                               AS qtd_ganhas,
    SUM(valor_cents)::numeric / 100        AS valor_reais
FROM oportunidades_ganhas_jetimob
WHERE etapa = 'Fechamento'
  AND entrou_etapa_em >= date_trunc('month', now())
  AND entrou_etapa_em <  date_trunc('month', now()) + interval '1 month'
GROUP BY corretor_id, corretor_nome, contrato
ORDER BY valor_reais DESC;

-- ============================================================
-- Validação (rodar depois de inserir):
-- SELECT contrato, COUNT(*), SUM(valor_cents)/100 AS total_reais
-- FROM oportunidades_ganhas_jetimob
-- WHERE etapa = 'Fechamento'
--   AND entrou_etapa_em >= '2026-04-01' AND entrou_etapa_em < '2026-05-01'
-- GROUP BY contrato;
-- Esperado abril/2026: venda=1 (R$75k), locacao=10 (R$29k)
-- ============================================================
