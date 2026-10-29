// Aba "Dados": lotes importados, explorador de itens e exportação.
import { api } from '../api.js';
import { h, icon, ICONS } from '../dom.js';
import { int } from '../format.js';
import { apiFilters } from '../state.js';
import { card } from '../components/kpi.js';
import { table } from '../components/table.js';
import { toast } from '../components/toast.js';

const pageState = { page: 1, sort: 'valor_total', desc: true };

const fmtDate = (s) => (s ? new Date(s).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—');
const fmtDay = (s) => (s ? s.split('-').reverse().join('/') : '—');

export default {
  id: 'data',
  label: 'Dados & importações',
  async render(root, ctx) {
    const [{ imports }, items] = await Promise.all([api.imports(), api.items(apiFilters(), { page: pageState.page, page_size: 50, sort: pageState.sort, desc: pageState.desc })]);

    const lots = card({
      title: 'Lotes importados', hint: 'Cada arquivo importado é um lote. Remover um lote apaga só os itens dele.',
      actions: h('button', { class: 'btn btn-primary', onclick: () => ctx.openImporter() }, icon(ICONS.upload), 'Importar planilhas'),
      body: table({
        rows: imports, empty: 'Nenhum arquivo importado ainda.',
        columns: [
          { key: 'id', label: '#', align: 'l' },
          { key: 'filename', label: 'Arquivo', align: 'l' },
          { key: 'sheet', label: 'Aba', align: 'l' },
          { key: 'periodo_ini', label: 'Lançamentos', align: 'l', fmt: (_, r) => `${fmtDay(r.periodo_ini)} a ${fmtDay(r.periodo_fim)}` },
          { key: 'rows_inserted', label: 'Itens', fmt: 'int' },
          { key: 'rows_duplicated', label: 'Duplicados ignorados', fmt: 'int' },
          { key: 'created_at', label: 'Importado em', align: 'l', fmt: fmtDate },
          { key: 'acao', label: '', fmt: (_, r) => h('button', {
            class: 'btn btn-ghost btn-danger', onclick: async (e) => {
              e.stopPropagation();
              if (!confirm(`Remover o lote #${r.id} (${r.filename})? Os itens dele saem da base.`)) return;
              await api.deleteImport(r.id); toast('Lote removido.'); ctx.refresh();
            },
          }, icon(ICONS.trash), 'Remover') },
        ],
      }),
    });

    const go = (p) => { pageState.page = p; ctx.rerender(); };
    const sortHeader = (key, label, align) => ({ key, label, align, fmt: align === 'l' ? 'text' : key === 'quantidade' ? 'num' : 'brl' });
    const cols = [
      sortHeader('data_lancamento', 'Lançamento', 'l'), sortHeader('numero_nfe', 'Nº NF', 'l'), sortHeader('modelo', 'Mod.', 'l'),
      sortHeader('cfop', 'CFOP', 'l'), sortHeader('natureza', 'Natureza', 'l'), sortHeader('parceiro_nome', 'Parceiro', 'l'),
      sortHeader('uf_op', 'UF', 'l'), sortHeader('material_desc', 'Material', 'l'), sortHeader('quantidade', 'Qtd.'),
      sortHeader('valor_total', 'Valor total'), sortHeader('icms', 'ICMS'), sortHeader('ipi', 'IPI'), sortHeader('pis', 'PIS'),
      sortHeader('cofins', 'COFINS'), sortHeader('difal', 'DIFAL'), sortHeader('cbs', 'CBS'), sortHeader('ibs', 'IBS'), sortHeader('tributos', 'Tributos'),
    ];
    const explorer = card({
      title: 'Itens', hint: `${int(items.total)} itens com os filtros atuais · ordenado por ${pageState.sort.replace('_', ' ')} na página. Use “Exportar” para levar tudo.`,
      body: [
        table({ rows: items.rows, columns: cols, maxHeight: '620px' }),
        h('div', { class: 'pager' },
          h('span', {}, `Página ${items.page} de ${items.pages}`),
          h('div', { class: 'actions' },
            h('select', { class: 'field', onchange: (e) => { const [s, dsc] = e.target.value.split(':'); Object.assign(pageState, { sort: s, desc: dsc === '1', page: 1 }); ctx.rerender(); } },
              [['valor_total:1', 'Maior valor'], ['tributos:1', 'Mais tributos'], ['data_lancamento:1', 'Mais recentes'], ['data_lancamento:0', 'Mais antigos']]
                .map(([v, l]) => h('option', { value: v, selected: `${pageState.sort}:${pageState.desc ? 1 : 0}` === v }, `Ordenar: ${l}`))),
            h('button', { class: 'btn', disabled: items.page <= 1, onclick: () => go(items.page - 1) }, '← Anterior'),
            h('button', { class: 'btn', disabled: items.page >= items.pages, onclick: () => go(items.page + 1) }, 'Próxima →'))),
      ],
    });

    root.replaceChildren(h('div', { class: 'view' }, lots, explorer));
  },
  reset() { pageState.page = 1; },
};
