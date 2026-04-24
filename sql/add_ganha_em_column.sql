-- ============================================================
-- Adiciona coluna `ganha_em` (data em que a oportunidade foi marcada
-- como ganha no Jetimob — corresponde a opportunity.updated_at)
--
-- Motivo: o campo entrou_etapa_em reflete "quando o card mudou de etapa"
-- e não quando a oportunidade foi ganha. Muitas vendas são marcadas
-- como ganhas SEM mover o card para Fechamento (ficam em Lead/Proposta).
-- Para bater com o relatório oficial do Jetimob precisamos do updated_at.
-- ============================================================

ALTER TABLE oportunidades_ganhas_jetimob
    ADD COLUMN IF NOT EXISTS ganha_em timestamptz;

CREATE INDEX IF NOT EXISTS idx_ganhas_ganha_em
    ON oportunidades_ganhas_jetimob (ganha_em DESC);

-- Atualiza views para usar ganha_em (DROP primeiro porque CREATE OR REPLACE
-- não permite renomear colunas existentes)
DROP VIEW IF EXISTS vendas_mes_atual;
DROP VIEW IF EXISTS ranking_corretores_mes;

CREATE VIEW vendas_mes_atual AS
SELECT
    jetimob_id, contrato, nome_cliente, telefone_e164, email,
    (valor_cents::numeric / 100) AS valor_reais,
    corretor_id, corretor_nome,
    ganha_em::date AS data_ganha
FROM oportunidades_ganhas_jetimob
WHERE ganha_em IS NOT NULL
  AND ganha_em >= date_trunc('month', now())
  AND ganha_em <  date_trunc('month', now()) + interval '1 month';

CREATE VIEW ranking_corretores_mes AS
SELECT
    corretor_id,
    corretor_nome,
    contrato,
    COUNT(*)                               AS qtd_ganhas,
    SUM(valor_cents)::numeric / 100        AS valor_reais
FROM oportunidades_ganhas_jetimob
WHERE ganha_em IS NOT NULL
  AND ganha_em >= date_trunc('month', now())
  AND ganha_em <  date_trunc('month', now()) + interval '1 month'
GROUP BY corretor_id, corretor_nome, contrato
ORDER BY valor_reais DESC;
