// Aba "Operações & UF": operação fiscal, natureza, UF e CFOP.
import { api } from '../api.js';
import { h } from '../dom.js';
import { brl, brlc, pct } from '../format.js';
import { apiFilters, state, toggleInList } from '../state.js';
import { card, segmented } from '../components/kpi.js';
import { table, MONEY_COLS, nonZero } from '../components/table.js';
import { bars } from '../components/charts.js';

let ufMetric = 'valor_total';
const UF_METRICS = [['valor_total', 'Valor total'], ['tributos', 'Tributos'], ['icms', 'ICMS'], ['difal', 'DIFAL'], ['ipi', 'IPI'], ['pis', 'PIS'], ['cofins', 'COFINS'], ['carga', 'Carga']];

export default {
  id: 'operations',
  label: 'Operações & UF',
  async render(root, ctx) {
    const d = await api.overview(apiFilters());

    const opCols = [{ key: 'fluxo', label: 'Movimento', align: 'l' }, { key: 'operacao', label: 'Operação', align: 'l' }, ...nonZero(MONEY_COLS, d.by_operacao)];
    const ops = card({
      title: 'Por operação fiscal', hint: 'CFOP 1/5 = interna, 2/6 = interestadual, 3/7 = exterior. Clique para filtrar.',
      body: table({ rows: d.by_operacao, columns: opCols, total: true, onRowClick: (r) => toggleInList('operacao', r.operacao), isActive: (r) => state.filters.operacao.includes(r.operacao) }),
    });

    const natRows = d.by_natureza;
    const elNat = h('div', { class: 'chart', style: { height: `${Math.max(220, natRows.length * 34 + 40)}px` } });
    const nat = card({ title: 'Por natureza', hint: 'Agrupamento gerencial do CFOP. Clique numa barra para filtrar.', body: elNat });

    const ufRows = [...d.by_uf].sort((a, b) => (b[ufMetric] || 0) - (a[ufMetric] || 0));
    const elUf = h('div', { class: 'chart tall', style: { height: `${Math.max(260, ufRows.length * 24 + 40)}px` } });
    const ufCard = card({
      title: 'Por UF', hint: 'Saídas: UF de destino · Entradas: UF de origem · EX = exterior. Clique para filtrar.',
      actions: segmented(UF_METRICS, ufMetric, (v) => { ufMetric = v; ctx.rerender(); }),
      body: elUf,
    });

    const ufTable = card({
      title: 'Valores e tributos por UF',
      body: table({
        rows: d.by_uf, total: true, sort: { key: 'valor_total', desc: true },
        columns: [{ key: 'uf_op', label: 'UF', align: 'l' }, ...nonZero(MONEY_COLS, d.by_uf)],
        onRowClick: (r) => toggleInList('uf', r.uf_op), isActive: (r) => state.filters.uf.includes(r.uf_op),
      }),
    });

    const cfop = card({
      title: 'Detalhe por CFOP', hint: 'Todos os filtros aplicados.',
      body: table({
        rows: d.by_cfop, total: true, sort: { key: 'cfop', desc: false },
        columns: [
          { key: 'cfop', label: 'CFOP', align: 'l' },
          { key: 'natureza_operacao', label: 'Descrição SAP', align: 'l' },
          { key: 'natureza', label: 'Natureza', align: 'l' },
          { key: 'operacao', label: 'Operação', align: 'l' },
          ...nonZero(MONEY_COLS, d.by_cfop),
        ],
      }),
    });

    root.replaceChildren(h('div', { class: 'view' }, ops, h('div', { class: 'grid-2' }, nat, ufCard), ufTable, cfop));

    bars(elNat, {
      horizontal: true, labels: true,
      categories: natRows.map((r) => `${r.natureza} · ${r.fluxo === 'Saída' ? 'S' : 'E'}`),
      series: [{ name: 'Valor total', color: 0, data: natRows.map((r) => r.valor_total) }],
      onClick: (p) => toggleInList('natureza', natRows[p.dataIndex].natureza),
    });
    const isPct = ufMetric === 'carga';
    bars(elUf, {
      horizontal: true, labels: true,
      categories: ufRows.map((r) => r.uf_op), selected: state.filters.uf.length === 1 ? state.filters.uf[0] : null,
      series: [{ name: UF_METRICS.find(([k]) => k === ufMetric)[1], color: 0, data: ufRows.map((r) => r[ufMetric] || 0) }],
      fmt: isPct ? (v) => pct(v) : brl, shortFmt: isPct ? (v) => pct(v, 0) : brlc,
      onClick: (p) => toggleInList('uf', ufRows[p.dataIndex].uf_op),
    });
  },
};
