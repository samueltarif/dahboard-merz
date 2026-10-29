// Tabela genérica: colunas declarativas, ordenação, linha clicável, rodapé com totais.
import { h } from '../dom.js';
import { FORMATS } from '../format.js';

/**
 * @param {{
 *   columns: {key: string, label: string, fmt?: string|function, align?: 'l'|'r', bar?: boolean, wrap?: boolean, sum?: boolean, cls?: function}[],
 *   rows: object[], sort?: {key: string, desc: boolean}, onRowClick?: (row)=>void, isActive?: (row)=>boolean,
 *   total?: boolean, maxHeight?: string, empty?: string
 * }} cfg
 */
export function table(cfg) {
  const st = { sort: cfg.sort || null };
  const wrap = h('div', { class: 'table-wrap', style: cfg.maxHeight ? { maxHeight: cfg.maxHeight } : null });

  const fmtOf = (c) => (typeof c.fmt === 'function' ? c.fmt : FORMATS[c.fmt || 'text']);
  const maxOf = (key) => Math.max(1, ...cfg.rows.map((r) => Math.abs(Number(r[key]) || 0)));

  function sorted() {
    if (!st.sort) return cfg.rows;
    const { key, desc } = st.sort;
    return [...cfg.rows].sort((a, b) => {
      const x = a[key], y = b[key];
      const r = typeof x === 'number' && typeof y === 'number' ? x - y : String(x ?? '').localeCompare(String(y ?? ''), 'pt-BR', { numeric: true });
      return desc ? -r : r;
    });
  }

  function cell(c, row, maxes) {
    const v = row[c.key];
    const txt = fmtOf(c)(v, row);
    const cls = [c.align === 'l' ? 'l' : '', c.wrap ? 'wrap' : '', c.cls ? c.cls(v, row) : ''].filter(Boolean).join(' ');
    if (c.bar) {
      const w = Math.round((Math.abs(Number(v) || 0) / maxes[c.key]) * 64);
      return h('td', { class: cls }, h('span', { class: 'inline-bar' }, h('i', { style: { width: `${w}px` } }), txt));
    }
    return h('td', { class: cls || null, title: c.wrap ? null : (typeof txt === 'string' && txt.length > 40 ? txt : null) }, txt);
  }

  function render() {
    const maxes = Object.fromEntries(cfg.columns.filter((c) => c.bar).map((c) => [c.key, maxOf(c.key)]));
    const thead = h('thead', {}, h('tr', {}, cfg.columns.map((c) => h('th', {
      class: [c.align === 'l' ? 'l' : '', 'sortable'].join(' '),
      'aria-sort': st.sort?.key === c.key ? (st.sort.desc ? 'descending' : 'ascending') : 'none',
      onclick: () => {
        st.sort = { key: c.key, desc: st.sort?.key === c.key ? !st.sort.desc : (c.fmt !== 'text' && c.align !== 'l') };
        render();
      },
    }, c.label))));
    const body = h('tbody', {}, sorted().map((row) => h('tr', {
      class: [cfg.onRowClick ? 'clickable' : '', cfg.isActive?.(row) ? 'on' : ''].join(' ') || null,
      onclick: cfg.onRowClick ? () => cfg.onRowClick(row) : null,
    }, cfg.columns.map((c) => cell(c, row, maxes)))));

    const parts = [thead, body];
    if (cfg.total && cfg.rows.length > 1) {
      parts.push(h('tfoot', {}, h('tr', {}, cfg.columns.map((c, i) => {
        if (i === 0) return h('td', { class: 'l' }, 'Total');
        if (!c.sum) return h('td', {});
        const s = cfg.rows.reduce((a, r) => a + (Number(r[c.key]) || 0), 0);
        return h('td', {}, fmtOf(c)(s));
      }))));
    }
    if (!cfg.rows.length) {
      wrap.replaceChildren(h('p', { class: 'muted-row' }, cfg.empty || 'Nenhum registro para os filtros selecionados.'));
      return;
    }
    wrap.replaceChildren(h('table', { class: 't' }, parts));
  }

  render();
  return wrap;
}

/** Colunas padrão de valor + tributos, reaproveitadas por várias tabelas. */
export const MONEY_COLS = [
  { key: 'documentos', label: 'Docs', fmt: 'int', sum: true },
  { key: 'valor_total', label: 'Valor total', fmt: 'brl', bar: true, sum: true },
  { key: 'icms', label: 'ICMS', fmt: 'brl', sum: true },
  { key: 'difal', label: 'DIFAL', fmt: 'brl', sum: true },
  { key: 'fcp', label: 'FCP', fmt: 'brl', sum: true },
  { key: 'ipi', label: 'IPI', fmt: 'brl', sum: true },
  { key: 'pis', label: 'PIS', fmt: 'brl', sum: true },
  { key: 'cofins', label: 'COFINS', fmt: 'brl', sum: true },
  { key: 'ii', label: 'II', fmt: 'brl', sum: true },
  { key: 'tributos', label: 'Tributos', fmt: 'brl', sum: true },
  { key: 'carga', label: 'Carga', fmt: 'pct' },
];

/** Remove colunas de tributo zeradas para a tabela não ficar poluída. */
export function nonZero(cols, rows) {
  const always = new Set(['documentos', 'valor_total', 'tributos', 'carga']);
  return cols.filter((c) => always.has(c.key) || !('sum' in c) || rows.some((r) => Math.abs(Number(r[c.key]) || 0) > 0.004));
}
