-- Aba "Apuração & ajustes": lançamentos manuais, saldos, status do mês e histórico.
-- Rode no SQL Editor do Supabase depois da 0001 (ou deixe o app criar sozinho no SQLite/Postgres).
-- Seguro para rodar mais de uma vez (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS apuracao_lancamentos (
	id SERIAL NOT NULL,
	competencia VARCHAR(7) NOT NULL,
	uf VARCHAR(2) NOT NULL,
	tributo VARCHAR(20) NOT NULL,
	tipo VARCHAR(30) NOT NULL,
	valor FLOAT NOT NULL,
	descricao VARCHAR(500) NOT NULL,
	referencia VARCHAR(120),
	criado_por VARCHAR(120) NOT NULL,
	criado_em TIMESTAMP WITH TIME ZONE NOT NULL,
	atualizado_por VARCHAR(120),
	atualizado_em TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS ix_apuracao_lancamentos_comp_uf ON apuracao_lancamentos (competencia, uf);

CREATE TABLE IF NOT EXISTS apuracao_saldos (
	id SERIAL NOT NULL,
	competencia VARCHAR(7) NOT NULL,
	uf VARCHAR(2) NOT NULL,
	tributo VARCHAR(20) NOT NULL,
	saldo_credor_anterior FLOAT,
	valor_declarado FLOAT,
	observacao VARCHAR(1000),
	atualizado_por VARCHAR(120),
	atualizado_em TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT uq_apuracao_saldos UNIQUE (competencia, uf, tributo)
);

CREATE TABLE IF NOT EXISTS apuracao_competencias (
	id SERIAL NOT NULL,
	competencia VARCHAR(7) NOT NULL,
	uf VARCHAR(2) NOT NULL,
	status VARCHAR(20) NOT NULL DEFAULT 'rascunho',
	enviado_por VARCHAR(120),
	enviado_em TIMESTAMP WITH TIME ZONE,
	validado_por VARCHAR(120),
	validado_em TIMESTAMP WITH TIME ZONE,
	motivo_devolucao VARCHAR(1000),
	atualizado_em TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT uq_apuracao_competencias UNIQUE (competencia, uf)
);

CREATE TABLE IF NOT EXISTS apuracao_historico (
	id SERIAL NOT NULL,
	competencia VARCHAR(7) NOT NULL,
	uf VARCHAR(2) NOT NULL,
	acao VARCHAR(40) NOT NULL,
	detalhe VARCHAR(1000),
	usuario VARCHAR(120) NOT NULL,
	papel VARCHAR(20) NOT NULL,
	criado_em TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS ix_apuracao_historico_comp_uf ON apuracao_historico (competencia, uf);

-- Segurança: igual à 0001. Só o servidor do painel (chave service_role) lê e grava.
alter table apuracao_lancamentos enable row level security;
alter table apuracao_saldos enable row level security;
alter table apuracao_competencias enable row level security;
alter table apuracao_historico enable row level security;
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'service_role') then
    revoke all on table apuracao_lancamentos, apuracao_saldos, apuracao_competencias, apuracao_historico from anon, authenticated;
    grant all on table apuracao_lancamentos, apuracao_saldos, apuracao_competencias, apuracao_historico to service_role;
    grant usage, select on all sequences in schema public to service_role;
  end if;
end $$;

-- Quando houver login (Supabase Auth), o papel virá da conta. Exemplo de política futura:
-- create policy "leitura autenticada" on apuracao_lancamentos for select to authenticated using (true);
-- create policy "lancador grava" on apuracao_lancamentos for insert to authenticated
--   with check ((auth.jwt() -> 'app_metadata' ->> 'papel') in ('lancador', 'validador'));
