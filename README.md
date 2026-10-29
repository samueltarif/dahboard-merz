# Painel Tributário — base SAP

Dashboard em Python para analisar tributos a partir do relatório fiscal do SAP (aba **SAP**,
layout J1BNFE): ICMS, DIFAL, FCP, IPI, PIS, COFINS, II, ISS e IBS/CBS da reforma.

- Importa **uma ou várias planilhas** de uma vez (.xlsx, .xlsm, .csv), detecta a aba SAP sozinho e ignora itens repetidos.
- Exporta **Excel completo** (14 abas formatadas) ou **CSV** da base filtrada — os dois podem ser reimportados.
- Salva em **SQLite local**, **Postgres no Docker** ou **Supabase** (API REST ou conexão direta), configurado pelo `.env`.

## Como rodar

### Windows (mais simples)
1. Instale o Python 3.10+ (python.org, marque *Add to PATH*).
2. Dê duplo clique em `iniciar.bat`. Na primeira vez ele cria o ambiente e instala as dependências.
3. O navegador abre em http://127.0.0.1:8000. Clique em **Importar planilhas**.

### Manual (qualquer sistema)
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
python run.py
```

### Docker (painel + Postgres)
```bash
docker compose up -d --build     # painel em http://localhost:8000, Postgres em localhost:5432
docker compose down              # para (os dados ficam no volume pgdata)
```

### Supabase
O painel fala com o Supabase de dois jeitos. O `.env` decide qual:

**A) API REST com a chave de servidor (configurado hoje)**
1. No Supabase, abra **SQL Editor → New query**, cole o conteúdo de `supabase/migrations/0001_init.sql` e clique **Run** (uma vez só; pode repetir sem problema).
2. No `.env`: `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` (Settings → API Keys).
3. `python run.py` — o terminal mostra `Banco: Supabase (API) https://...`.

**B) Conexão direta ao Postgres**: preencha `DATABASE_URL` com a URI de *Connect → Session pooler*
(precisa da senha do banco). As tabelas são criadas sozinhas. Se `DATABASE_URL` existir, ela tem prioridade.

Segurança: a chave de servidor fica só no `.env` e no servidor Python; o navegador nunca a recebe.
As tabelas têm RLS ligado e nenhuma política, então a chave `anon`/publishable não lê nem grava nada.
`SUPABASE_ANON_KEY` e `SUPABASE_JWT_SECRET` ficam guardadas para quando houver login.

## Abas do painel

| Aba | O que mostra |
|---|---|
| **Visão geral** | Valor total, tributos, carga efetiva, documentos (com mini-gráfico e variação mensal), cartões por tributo, leitura rápida, débitos × créditos, entradas × saídas, tributos por operação, evolução diária |
| **Operações & UF** | Operação fiscal (interna/interestadual/exterior), natureza, ranking por UF com troca de métrica, detalhe por CFOP |
| **Produtos & parceiros** | Materiais (preço médio e carga), maiores parceiros, curva ABC de concentração, NCM |
| **Reforma tributária** | IBS/CBS destacados em 2026 e simulação do cenário pleno com alíquotas editáveis, por CST e por material |
| **Conformidade** | 13 regras: recálculo de ICMS/IPI/PIS/COFINS/IBS/CBS, CST × valor, DIFAL ausente, 4% de importados, exclusão do ICMS da base PIS/COFINS, chave ausente, documentos de outro mês |
| **Dados & importações** | Lotes importados (com remoção), explorador de itens paginado |

Todos os filtros (movimento, operação, documento, natureza, UF, período, lote e busca) valem para
todas as abas e para a exportação, e ficam na URL — dá para salvar um link já filtrado.

## Estrutura do código

```
app/
  config.py                 configurações (lê .env)
  main.py                   cria o FastAPI e serve a página
  domain/                   REGRAS DE NEGÓCIO (sem banco, sem HTTP)
    columns.py              mapa coluna SAP -> campo interno  <- única fonte da verdade
    cfop.py                 movimento / operação / natureza por CFOP
    taxes.py                lista de tributos exibidos
  importers/sap.py          lê .xlsx/.csv e normaliza (função pura, testável)
  db/                       engine (SQLite/Postgres/Supabase) e tabelas
  repositories/             acesso a dados: imports_repo (fachada), sql_repo, supabase_repo
  services/                 cálculos: dataset (cache), filtros, métricas,
                            conformidade, reforma, importação, exportação
  api/routes.py             rotas HTTP finas (validam e chamam serviços)
  web/
    templates/index.html    casca da página
    static/css/tokens.css   DESIGN TOKENS (cores, fontes, espaçamentos, paleta dos gráficos)
    static/css/app.css      componentes
    static/js/              api.js, state.js, format.js, dom.js
      components/           gráficos, tabela, KPI, filtros, importador
      views/                um arquivo por aba
tests/                      pytest com planilha sintética (não versiona dados reais)
supabase/migrations/        SQL do esquema
```

### Onde mexer quando…

| Situação | Arquivo |
|---|---|
| O SAP mudou o nome de uma coluna | `app/domain/columns.py` (acrescente em `aliases`) |
| Um CFOP está na natureza errada | `app/domain/cfop.py` (tabelas `NATUREZA_*`) — vale para o histórico, sem reimportar |
| Incluir um tributo novo | `app/domain/taxes.py` (+ coluna em `columns.py` se vier do SAP) |
| Nova regra de conformidade | `app/services/compliance.py` (lista `CHECKS`) |
| Mudar cores/fontes | `app/web/static/css/tokens.css` |
| Nova aba | crie `static/js/views/minha-aba.js` e registre em `static/js/main.js` (`VIEWS`) |

Erros: o servidor registra o traceback completo no terminal; a tela mostra a mensagem em português.
Cada arquivo importado é processado separadamente, então um arquivo ruim não bloqueia os outros.

## Testes
```bash
pip install -r requirements-dev.txt
pytest
```

## Observações fiscais
- **Débitos × créditos** é uma visão gerencial dos valores destacados (não substitui a apuração/SPED).
  Uso e consumo não gera crédito de ICMS/IPI.
- **Reforma**: alíquotas de referência ainda não estão fixadas; os padrões (CBS 8,8% e IBS 17,7%) são estimativas editáveis.
  A redução de alíquota por item vem do próprio SAP (cClassTrib).
- Itens com `Estornado = X` são descartados na importação.

## Git
`data/`, `.env` e planilhas (`*.xlsx`, `*.csv`) estão no `.gitignore` — dados fiscais não vão para o repositório.
```bash
git init && git add . && git commit -m "Painel tributário: primeira versão"
git remote add origin <url-do-repo> && git push -u origin main
```
