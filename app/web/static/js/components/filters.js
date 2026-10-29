// Barra de filtros (mesmo padrão de "chips" do painel de referência).
import { h, debounce } from '../dom.js';
import { month } from '../format.js';
import { state, setFilter, toggleInList, resetFilters, hasFilters } from '../state.js';

const chip = (label, pressed, onclick, cls = '') =>
  h('button', { type: 'button', class: `chip ${cls}`, 'aria-pressed': String(pressed), onclick }, label);

function group(title, children, cls = '') {
  return h('div', { class: `f-group ${cls}` }, h('h3', {}, title), h('div', { class: 'f-row' }, children));
}

export function renderFilters(root) {
  const m = state.meta;
  const f = state.filters;
  if (!m || m.empty) { root.hidden = true; return; }
  root.hidden = false;

  const naturezas = f.fluxo ? m.naturezas[f.fluxo] || [] : [...new Set([...(m.naturezas['Saída'] || []), ...(m.naturezas['Entrada'] || [])])];

  const periodSelect = (key, placeholder) => h('select', {
    class: 'field', 'aria-label': placeholder, onchange: (e) => setFilter(key, e.target.value),
  }, h('option', { value: '' }, placeholder), m.periodos.map((p) => h('option', { value: p, selected: f[key] === p }, month(p))));

  const search = h('input', {
    class: 'field search', type: 'search', placeholder: 'Buscar parceiro, material, NCM, CFOP, nº NF…', value: f.busca,
    oninput: debounce((e) => setFilter('busca', e.target.value.trim()), 400),
  });

  const parts = [
    group('Movimento', [
      chip('Todos', !f.fluxo, () => setFilter('fluxo', ''), 'chip-lg'),
      chip('Saídas', f.fluxo === 'Saída', () => setFilter('fluxo', 'Saída'), 'chip-lg'),
      chip('Entradas', f.fluxo === 'Entrada', () => setFilter('fluxo', 'Entrada'), 'chip-lg'),
    ]),
    group('Operação', m.operacoes.map((o) => chip(o, f.operacao.includes(o), () => toggleInList('operacao', o)))),
    group('Documento', m.modelos.map((md) => chip(md === '55' ? 'NF-e (55)' : md === '57' ? 'CT-e (57)' : md, f.modelo.includes(md), () => toggleInList('modelo', md)))),
    m.periodos.length > 1 ? group('Período', [periodSelect('periodo_ini', 'De'), periodSelect('periodo_fim', 'Até')]) : null,
    m.imports.length > 1 ? group('Lote importado', [h('select', {
      class: 'field', onchange: (e) => setFilter('imports', e.target.value ? [e.target.value] : []),
    }, h('option', { value: '' }, 'Todos os lotes'), m.imports.map((i) => h('option', { value: String(i.id), selected: f.imports.includes(String(i.id)) }, `#${i.id} · ${i.filename}`)))]) : null,
    group('Natureza', naturezas.map((n) => chip(n, f.natureza.includes(n), () => toggleInList('natureza', n))), 'f-wide'),
    group(`UF${f.uf.length ? ` · ${f.uf.join(', ')}` : ''}`, m.ufs.map((u) => chip(u, f.uf.includes(u), () => toggleInList('uf', u), 'chip-uf')), 'f-wide'),
    h('div', { class: 'f-end f-wide' }, search,
      hasFilters() ? h('button', { class: 'btn btn-ghost', onclick: resetFilters }, 'Limpar filtros ✕') : null),
  ];
  const typing = document.activeElement?.classList.contains('search');
  root.replaceChildren(...parts.filter(Boolean)); // grupos opcionais podem vir null
  if (typing) { search.focus(); search.setSelectionRange(search.value.length, search.value.length); }
}
