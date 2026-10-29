// Cartões de indicador (adaptação do "Insight Cards" do 21st.dev ao design system do painel).
import { h } from '../dom.js';

function spark(values = []) {
  if (values.length < 2) return null;
  const pts = values.slice(-24);
  const max = Math.max(...pts.map(Math.abs), 1e-9);
  return h('span', { class: 'spark', 'aria-hidden': 'true' },
    pts.map((v, i) => h('i', { style: { height: `${Math.max(10, (Math.abs(v) / max) * 100)}%`, animationDelay: `${i * 18}ms` } })));
}

/**
 * @param {{label: string, value: string, full?: string, spark?: number[], delta?: number|null, note?: string|Node, deltaGoodWhenUp?: boolean}} k
 */
export function kpi(k) {
  let delta = null;
  if (k.delta != null && Number.isFinite(k.delta)) {
    const up = k.delta >= 0;
    const good = k.deltaGoodWhenUp === false ? !up : up;
    delta = h('span', { class: `kpi-delta ${good ? 'up' : 'down'}` }, `${up ? '▲' : '▼'} ${Math.abs(k.delta).toLocaleString('pt-BR')}% vs mês anterior`);
  }
  return h('article', { class: 'kpi' },
    h('div', { class: 'kpi-top' },
      h('div', { class: 'kpi-body' },
        h('div', { class: 'kpi-label' }, k.label),
        h('span', { class: 'kpi-value' }, k.value),
        k.full ? h('div', { class: 'kpi-full' }, k.full) : null,
        delta),
      spark(k.spark)),
    k.note ? h('div', { class: 'kpi-note' }, k.note) : null);
}

export function stat(label, value, note) {
  return h('div', { class: 'stat' }, h('div', { class: 's-label' }, label), h('div', { class: 's-value' }, value), note ? h('div', { class: 's-note' }, note) : null);
}

export function card({ title, hint, actions, body, cls }) {
  return h('section', { class: `card ${cls || ''}` },
    h('div', { class: 'card-head' }, h('div', {}, h('h2', {}, title), hint ? h('p', { class: 'hint' }, hint) : null), actions || null),
    body);
}

export function legend(items) {
  return h('div', { class: 'legend' }, items.map(([label, color]) => h('span', {}, h('i', { class: 'sw', style: { background: color } }), label)));
}

/** Controle segmentado (ex.: escolher métrica do gráfico). */
export function segmented(options, current, onPick) {
  return h('div', { class: 'seg', role: 'group' }, options.map(([value, label]) => h('button', {
    type: 'button', 'aria-pressed': String(value === current), onclick: () => onPick(value),
  }, label)));
}
