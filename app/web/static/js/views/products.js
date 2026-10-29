// Aba "Produtos & parceiros": materiais, NCM, parceiros e concentração (curva ABC).
import { api } from '../api.js';
import { h } from '../dom.js';
import { brlc, int, pct } from '../format.js';
import { apiFilters, setFilter } from '../state.js';
import { card, stat } from '../components/kpi.js';
import { table } from '../components/table.js';
import { bars, lines } from '../components/charts.js';

const TAX_COLS = [
  { key: 'icms', label: 'ICMS', fmt: 'brl', sum: true },
  { key: 'difal', label: 'DIFAL', fmt: 'brl', sum: true },
  { key: 'ipi', label: 'IPI', fmt: 'brl', sum: true },
  { key: 'pis', label: 'PIS', fmt: 'brl', sum: true },
  { key: 'cofins', label: 'COFINS', fmt: 'brl', sum: true },
  { key: 'tributos', label: 'Tributos', fmt: 'brl', sum: true },
  { key: 'carga', label: 'Carga', fmt: 'pct' },
];

export default {
  id: 'products',
  label: 'Produtos & parceiros',
  async render(root) {
    const d = await api.products(apiFilters(), 500);
    const t = d.totais;
    const abc = d.abc_parceiros;
    const n80 = (abc.find((p) => p.share_acum >= 0.8) || abc[abc.length - 1] || { rank: 0 }).rank;
    const topMat = d.materiais[0];

    const stats = h('section', { class: 'card' }, h('div', { class: 'stat-row' },
      stat('Materiais', int(t.materiais), 'com movimento na seleção'),
      stat('Parceiros', int(t.parceiros), `${int(n80)} concentram 80% do valor`),
      stat('NCMs', int(t.ncm)),
      stat('Maior material', topMat ? brlc(topMat.valor_total) : '—', topMat ? topMat.material_desc : ''),
    ));

    const search = (v) => setFilter('busca', v);
    const mat = card({
      title: 'Materiais', hint: 'Carga = tributos ÷ valor total. Clique para buscar o material em todas as abas.',
      body: table({
        rows: d.materiais, total: true, sort: { key: 'valor_total', desc: true }, onRowClick: (r) => r.material && search(r.material),
        columns: [
          { key: 'material', label: 'Código', align: 'l' },
          { key: 'material_desc', label: 'Descrição', align: 'l' },
          { key: 'ncm', label: 'NCM', align: 'l' },
          { key: 'quantidade', label: 'Qtd.', fmt: 'num', sum: true },
          { key: 'preco_medio', label: 'Preço médio', fmt: 'brl' },
          { key: 'valor_total', label: 'Valor total', fmt: 'brl', bar: true, sum: true },
          ...TAX_COLS,
        ],
      }),
    });

    const elPar = h('div', { class: 'chart tall' });
    const topPar = d.parceiros.slice(0, 15);
    const par = card({ title: 'Maiores parceiros', hint: 'Top 15 por valor total. Clique para filtrar pelo parceiro.', body: elPar });

    const elAbc = h('div', { class: 'chart tall' });
    const abcCard = card({ title: 'Concentração (curva ABC)', hint: 'Participação acumulada no valor, do maior para o menor parceiro.', body: elAbc });

    const parTable = card({
      title: 'Parceiros',
      body: table({
        rows: d.parceiros, total: true, sort: { key: 'valor_total', desc: true }, onRowClick: (r) => search(r.parceiro_nome),
        columns: [
          { key: 'parceiro_nome', label: 'Parceiro', align: 'l' },
          { key: 'uf_op', label: 'UF', align: 'l' },
          { key: 'documentos', label: 'Docs', fmt: 'int', sum: true },
          { key: 'valor_total', label: 'Valor total', fmt: 'brl', bar: true, sum: true },
          ...TAX_COLS,
        ],
      }),
    });

    const ncm = card({
      title: 'Por NCM', hint: 'Útil para conferir enquadramento e alíquotas por classificação fiscal.',
      body: table({
        rows: d.ncm, total: true, sort: { key: 'valor_total', desc: true },
        columns: [{ key: 'ncm', label: 'NCM', align: 'l' }, { key: 'itens', label: 'Itens', fmt: 'int', sum: true }, { key: 'valor_total', label: 'Valor total', fmt: 'brl', bar: true, sum: true }, ...TAX_COLS],
      }),
    });

    root.replaceChildren(h('div', { class: 'view' }, stats, mat, h('div', { class: 'grid-2' }, par, abcCard), parTable, ncm));

    bars(elPar, {
      horizontal: true, labels: true,
      categories: topPar.map((p) => (p.parceiro_nome.length > 34 ? `${p.parceiro_nome.slice(0, 32)}…` : p.parceiro_nome)),
      series: [{ name: 'Valor total', color: 0, data: topPar.map((p) => p.valor_total) }],
      onClick: (p) => search(topPar[p.dataIndex].parceiro_nome),
    });
    lines(elAbc, {
      area: true, min: 0, max: 1, categories: abc.map((p) => String(p.rank)),
      series: [{ name: 'Acumulado', color: 0, data: abc.map((p) => p.share_acum) }],
      fmt: (v) => pct(v), shortFmt: (v) => pct(v, 0),
    });
  },
};
