-- ================================================
-- Mapeamento explicito entre usuario do dashboard e nome do corretor no Jetimob
-- ================================================
-- Criado para resolver o problema de IDOR no perfil "corretor":
-- A coluna `corretor` em leads_jetimob e vendas_nl vem do Jetimob como texto livre
-- (nome do corretor), o que pode divergir do `usuarios.nome` por homonimia,
-- acentos, abreviacoes, case ou espacos. Match por nome direto e fragil.
--
-- Esta coluna armazena o nome EXATO como aparece no Jetimob, preenchido
-- manualmente pelo admin no cadastro/edicao de usuario. O match no codigo
-- usa normalizacao (NFKD + casefold) sobre os dois lados, mas o admin deve
-- preencher o mais proximo possivel do valor real.
-- ================================================

ALTER TABLE usuarios
  ADD COLUMN IF NOT EXISTS corretor_nome_jetimob text;

COMMENT ON COLUMN usuarios.corretor_nome_jetimob IS
  'Nome exato como aparece na coluna `corretor` das tabelas leads_jetimob e vendas_nl. Match e case-insensitive e ignora acentos. Obrigatorio para perfil corretor (validado no codigo). Nullable para outros perfis.';

-- ================================================
-- Verificacao pos-execucao
-- ================================================
-- Conferir que a coluna foi criada:
--   SELECT column_name, data_type, is_nullable
--   FROM information_schema.columns
--   WHERE table_name = 'usuarios' AND column_name = 'corretor_nome_jetimob';
--
-- Listar corretores que ainda precisam de mapeamento (apos migration):
--   SELECT id, nome, email FROM usuarios
--   WHERE perfil = 'corretor' AND (corretor_nome_jetimob IS NULL OR corretor_nome_jetimob = '');
--
-- Para preencher manualmente (exemplo):
--   UPDATE usuarios SET corretor_nome_jetimob = 'Maria Silva Santos'
--   WHERE email = 'maria@nlimoveis.com.br';

-- ================================================
-- ROLLBACK (se precisar desfazer)
-- ================================================
-- ALTER TABLE usuarios DROP COLUMN IF EXISTS corretor_nome_jetimob;
