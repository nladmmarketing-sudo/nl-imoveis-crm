-- ============================================================
-- Tabela: resumo_mensal_jetimob
-- Fonte: scraping do RELATORIO OFICIAL do Jetimob
--        /relatorios/oportunidades/ganhas?period=X&contract=1
--
-- Propósito: fonte-de-verdade para números mensais de vendas
-- (bate 100% com o que o Jetimob mostra na tela de relatório).
--
-- A tabela oportunidades_ganhas_jetimob continua sendo a fonte
-- para a LISTA individual de oportunidades — esta tabela guarda
-- só o AGREGADO mensal oficial.
-- ============================================================

CREATE TABLE IF NOT EXISTS resumo_mensal_jetimob (
    mes_referencia    date     NOT NULL,                 -- primeiro dia do mes (2026-04-01)
    tipo              text     NOT NULL CHECK (tipo IN ('venda','locacao')),
    qtd_ganhas        int      NOT NULL DEFAULT 0,
    valor_total_cents bigint   NOT NULL DEFAULT 0,
    ranking_json      jsonb,                             -- [{pos, nome, qtd, valor_cents}]
    scraped_at        timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (mes_referencia, tipo)
);

CREATE INDEX IF NOT EXISTS idx_resumo_mes
    ON resumo_mensal_jetimob (mes_referencia DESC);
