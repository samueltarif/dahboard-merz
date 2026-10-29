// Aba "Visão geral": indicadores, tributos, leitura rápida, débito x crédito e tendências.
import { api } from '../api.js';
import { h } from '../dom.js';
import { brl, brlc, day, int, pct } from '../format.js';
import { apiFilters, setFilter, state } from '../state.js';
import { card, kpi, legend } from '../components/kpi.js';
import { table, MONEY_COLS, nonZero } from '../components/table.js';
import { bars, seriesColor } from '../components/charts.js';

const OPS = [['Interna', 0], ['Interestadual', 1], ['Exterior', 2]];
let metric = 'tributos'; // tributo escolhido nos cartões -> usado no gráfico diário

function describe(f) {
  const parts = [];
  parts.push(f.fluxo ? (f.fluxo === 'Saída' ? 'saídas' : 'entradas') : 'entradas e saídas');
  if (f.operacao.length) parts.push(`operação ${f.operacao.join(' + ').toLowerCase()}`);
  if (f.natureza.length) parts.push(`natureza ${f.natureza.join(', ').toLowerCase()}`);
  if (f.uf.length) parts.push(`UF ${f.uf.join(', ')}`);
  return parts.join(' · ');
}

function taxTiles(taxes, onPick) {
  const consumo = taxes.filter((t) => Math.abs(t.value) > 0.004); // esconde tributos zerados na seleção
  const max = Math.max(...consumo.map((t) => t.value), 1);
  const tile = (t) => h('button', {
    class: `tax ${t.value ? '' : 'is-zero'}`, 'aria-pressed': String(metric === t.key), title: t.hint || t.label,
    onclick: () => onPick(metric === t.key ? 'tributos' : t.key),
  },
  h('span', { class: 't-label' }, t.label, t.group === 'reforma' ? h('span', { class: 'tag' }, '2026') : (t.share ? h('span', {}, pct(t.share, 0)) : null)),
  h('span', { class: 't-value' }, brl(t.value)),
  h('span', { class: 't-bar' }, h('i', { style: { width: `${(t.value / max) * 100}%` } })));
  return h('section', { class: 'taxes', 'aria-label': 'Tributos — clique para ver a evolução diária' }, consumo.map(tile));
}

export default {
  id: 'overview',
  label: 'Visão geral',
  async render(root, ctx) {
    const f = apiFilters();
    const d = await api.overview(f);
    const k = d.kpis;
    const taxLabel = (key) => (key === 'tributos' ? 'Tributos sobre consumo' : d.taxes.find((t) => t.key === key)?.label || key);

    const kpis = h('section', { class: 'kpis' },
      kpi({ label: 'Valor total c/ impostos', value: brlc(k.valor_total.value), full: brl(k.valor_total.value), spark: k.valor_total.spark, delta: k.valor_total.delta,
        note: `Produtos ${brlc(k.valor_produtos)} · NET Sales ${brlc(k.net_sales)}` }),
      kpi({ label: 'Tributos sobre consumo', value: brlc(k.tributos.value), full: brl(k.tributos.value), spark: k.tributos.spark, delta: k.tributos.delta, deltaGoodWhenUp: false,
        note: `IBS + CBS (fase de teste): ${brl(k.tributos_reforma)}` }),
      kpi({ label: 'Carga efetiva', value: pct(k.carga.value), spark: k.carga.spark,
        note: 'Tributos ÷ valor total dos documentos. Sem créditos ou compensações.' }),
      kpi({ label: 'Documentos', value: int(k.documentos.value), spark: k.documentos.spark,
        note: `${int(k.itens)} itens · ${int(k.parceiros)} parceiros · ticket médio ${brlc(k.ticket_medio)}` }));

    const insights = card({
      title: 'Leitura rápida', hint: 'Pontos que merecem atenção na seleção atual.',
      body: d.insights.length ? h('ul', { class: 'insights' }, d.insights.map((n) => h('li', { class: n.tone }, n.text))) : h('p', { class: 'muted-row' }, 'Sem dados na seleção.'),
    });

    const apur = card({
      title: 'Débitos × créditos destacados',
      hint: 'Saídas geram débito; entradas, crédito. Uso e consumo não gera crédito de ICMS/IPI. Estimativa gerencial — não substitui a apuração (SPED).',
      body: table({
        rows: d.apuracao, total: false,
        columns: [
          { key: 'label', label: 'Tributo', align: 'l' },
          { key: 'debito', label: 'Débitos', fmt: 'brl' },
          { key: 'credito', label: 'Créditos', fmt: 'brl' },
          { key: 'sem_credito', label: 'Sem crédito', fmt: 'brl', cls: () => 'muted' },
          { key: 'saldo', label: 'Saldo', fmt: 'brl', cls: (v) => (v > 0 ? 'pos' : 'neg') },
        ],
      }),
    });

    const fluxCols = [{ key: 'fluxo', label: 'Movimento', align: 'l' }, ...nonZero(MONEY_COLS, d.flux)];
    const flux = card({
      title: 'Entradas × saídas',
      hint: 'Totais para os demais filtros. Clique numa linha para filtrar o movimento.',
      body: table({ rows: d.flux, columns: fluxCols, onRowClick: (r) => setFilter('fluxo', state.filters.fluxo === r.fluxo ? '' : r.fluxo), isActive: (r) => r.fluxo === state.filters.fluxo }),
    });

    // Tributos por operação (barras agrupadas: categoria = tributo, série = operação)
    const taxKeys = d.taxes.filter((t) => t.group === 'consumo' && t.value > 0).map((t) => t.key);
    const opsPresent = OPS.filter(([op]) => d.by_operacao.some((r) => r.operacao === op));
    const sumBy = (op, key) => d.by_operacao.filter((r) => r.operacao === op).reduce((a, r) => a + (r[key] || 0), 0);
    const elTax = h('div', { class: 'chart' });
    const taxChart = card({
      title: 'Tributos por operação', hint: 'Cada tributo dividido por tipo de operação.',
      body: [legend(opsPresent.map(([op, c]) => [op, seriesColor(c)])), elTax],
    });

    const elDay = h('div', { class: 'chart' });
    const dayChart = card({ title: `Por dia de lançamento — ${taxLabel(metric)}`, hint: 'Clique nos cartões de tributo acima para trocar a métrica.', body: elDay });

    root.replaceChildren(h('div', { class: 'view' },
      h('p', { class: 'lede' }, 'Seleção: ', h('b', {}, describe(state.filters)), ' — valor total de ', h('b', {}, brl(k.valor_total.value)),
        ' em ', h('b', {}, int(k.documentos.value)), ' documentos, com ', h('b', {}, brl(k.tributos.value)), ' de tributos destacados (', h('b', {}, pct(k.carga.value)), ').'),
      kpis,
      taxTiles(d.taxes, (key) => { metric = key; ctx.rerender(); }),
      h('div', { class: 'grid-2' }, insights, apur),
      flux,
      h('div', { class: 'grid-2' }, taxChart, dayChart)));

    bars(elTax, {
      categories: taxKeys.map((key) => d.taxes.find((t) => t.key === key).label),
      series: opsPresent.map(([op, c]) => ({ name: op, color: c, data: taxKeys.map((key) => sumBy(op, key)) })),
    });
    const tl = d.timeline;
    bars(elDay, { categories: tl.map((r) => day(r.dia)), series: [{ name: taxLabel(metric), color: 0, data: tl.map((r) => r[metric] || 0) }] });
  },
};
