-- ================================================
-- Jobs de limpeza automatica (cron)
-- Roda diariamente as 3h da manha (horario do Supabase)
-- ================================================

-- Habilita extensao pg_cron (caso ainda nao esteja ativa)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- ================================================
-- Job 1: limpa tentativas de login com mais de 30 dias
-- ================================================
SELECT cron.schedule(
    'limpar-login-attempts',
    '0 3 * * *',
    $$ DELETE FROM login_attempts WHERE criado_em < NOW() - INTERVAL '30 days' $$
);

-- ================================================
-- Job 2: limpa log de auditoria com mais de 90 dias
-- ================================================
SELECT cron.schedule(
    'limpar-auditoria',
    '5 3 * * *',
    $$ DELETE FROM auditoria WHERE criado_em < NOW() - INTERVAL '90 days' $$
);

-- ================================================
-- Verificar jobs agendados
-- ================================================
-- SELECT * FROM cron.job;

-- ================================================
-- Para remover um job (caso queira):
-- ================================================
-- SELECT cron.unschedule('limpar-login-attempts');
-- SELECT cron.unschedule('limpar-auditoria');
