-- Esquema do Painel Tributário para Supabase/Postgres.
-- Gerado a partir de app/db/models.py. Rode no SQL Editor do Supabase (ou deixe o app criar sozinho no 1º start).
-- Seguro para rodar mais de uma vez (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS imports (
	id SERIAL NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	sheet VARCHAR(120) NOT NULL, 
	file_hash VARCHAR(64) NOT NULL, 
	rows_read INTEGER NOT NULL, 
	rows_inserted INTEGER NOT NULL, 
	rows_duplicated INTEGER NOT NULL, 
	periodo_ini DATE, 
	periodo_fim DATE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (file_hash)
);

CREATE TABLE IF NOT EXISTS fiscal_items (
	id SERIAL NOT NULL, 
	import_id INTEGER NOT NULL, 
	empresa VARCHAR(255), 
	local_negocio VARCHAR(255), 
	data_documento DATE, 
	data_lancamento DATE, 
	categoria_nf VARCHAR(255), 
	numero_documento VARCHAR(255), 
	item_documento VARCHAR(255), 
	estornado VARCHAR(255), 
	direcao VARCHAR(255), 
	natureza_operacao VARCHAR(255), 
	cfop_raw VARCHAR(255), 
	modelo VARCHAR(255), 
	chave_acesso VARCHAR(255), 
	numero_nfe VARCHAR(255), 
	serie VARCHAR(255), 
	parceiro_id VARCHAR(255), 
	parceiro_nome VARCHAR(255), 
	parceiro_cnpj VARCHAR(255), 
	pais VARCHAR(255), 
	cidade VARCHAR(255), 
	uf VARCHAR(255), 
	pedido VARCHAR(255), 
	centro_lucro VARCHAR(255), 
	material VARCHAR(255), 
	material_desc VARCHAR(255), 
	quantidade FLOAT, 
	ncm VARCHAR(255), 
	origem_material VARCHAR(255), 
	net_sales FLOAT, 
	valor FLOAT, 
	frete FLOAT, 
	seguro FLOAT, 
	despesas FLOAT, 
	total FLOAT, 
	valor_total FLOAT, 
	cst_ipi VARCHAR(255), 
	ipi_base FLOAT, 
	ipi_aliq FLOAT, 
	ipi_valor FLOAT, 
	cst_icms VARCHAR(255), 
	icms_base FLOAT, 
	icms_aliq FLOAT, 
	icms_valor FLOAT, 
	icms_difal FLOAT, 
	icms_fcp_dest FLOAT, 
	fcp_valor FLOAT, 
	icms_st_valor FLOAT, 
	fcp_st_valor FLOAT, 
	cst_pis VARCHAR(255), 
	pis_base FLOAT, 
	pis_aliq FLOAT, 
	pis_valor FLOAT, 
	cst_cofins VARCHAR(255), 
	cofins_base FLOAT, 
	cofins_aliq FLOAT, 
	cofins_valor FLOAT, 
	ii_valor FLOAT, 
	iss_valor FLOAT, 
	issp_valor FLOAT, 
	pis_ret FLOAT, 
	cofins_ret FLOAT, 
	csll_ret FLOAT, 
	irrf_ret FLOAT, 
	cst_ibscbs VARCHAR(255), 
	class_trib VARCHAR(255), 
	ibs_base FLOAT, 
	ibs_valor FLOAT, 
	ibs_aliq FLOAT, 
	ibs_red FLOAT, 
	ibs_mun_valor FLOAT, 
	cbs_base FLOAT, 
	cbs_valor FLOAT, 
	cbs_aliq FLOAT, 
	cbs_red FLOAT, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_fiscal_items_natural_key UNIQUE (empresa, numero_documento, item_documento), 
	FOREIGN KEY(import_id) REFERENCES imports (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_fiscal_items_import_id ON fiscal_items (import_id);

-- Segurança (sem login por enquanto): só o servidor do painel, com a chave service_role, acessa.
-- RLS ligado e sem políticas = a chave anon/publishable NÃO lê nem grava nada.
alter table imports enable row level security;
alter table fiscal_items enable row level security;
-- (o bloco abaixo só roda no Supabase; no Postgres do Docker esses papéis não existem)
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'service_role') then
    revoke all on table imports, fiscal_items from anon, authenticated;
    grant all on table imports, fiscal_items to service_role;
    grant usage, select on all sequences in schema public to service_role;
  end if;
end $$;
-- Quando houver login (Supabase Auth), crie políticas aqui, ex.:
-- create policy "leitura autenticada" on fiscal_items for select to authenticated using (true);
