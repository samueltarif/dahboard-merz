// Estado global: filtros + metadados. Sincronizado com a URL (dá para salvar/compartilhar um link filtrado).

const DEFAULT = {
  fluxo: '', operacao: [], natureza: [], uf: [], modelo: [], imports: [], periodo_ini: '', periodo_fim: '', busca: '',
};
const LISTS = ['operacao', 'natureza', 'uf', 'modelo', 'imports'];

const listeners = new Set();

export const state = {
  filters: readUrl(),
  meta: null,
  view: new URLSearchParams(location.search).get('aba') || 'overview',
};

function readUrl() {
  const q = new URLSearchParams(location.search);
  const f = structuredClone(DEFAULT);
  for (const k of Object.keys(DEFAULT)) {
    const v = q.get(k);
    if (v == null) continue;
    f[k] = LISTS.includes(k) ? v.split(',').filter(Boolean) : v;
  }
  return f;
}

function writeUrl() {
  const q = new URLSearchParams();
  q.set('aba', state.view);
  for (const [k, v] of Object.entries(state.filters)) {
    if (Array.isArray(v) ? v.length : v) q.set(k, Array.isArray(v) ? v.join(',') : v);
  }
  history.replaceState(null, '', `?${q}`);
}

export function onChange(fn) { listeners.add(fn); return () => listeners.delete(fn); }
function emit(reason) { writeUrl(); listeners.forEach((fn) => fn(reason)); }

export function setFilter(key, value) {
  state.filters[key] = value;
  if (key === 'fluxo') state.filters.natureza = []; // naturezas dependem do movimento
  emit('filters');
}

export function toggleInList(key, value) {
  const list = state.filters[key];
  const i = list.indexOf(value);
  if (i >= 0) list.splice(i, 1); else list.push(value);
  emit('filters');
}

export function resetFilters() { state.filters = structuredClone(DEFAULT); emit('filters'); }
export function setView(view) { state.view = view; emit('view'); }
export function setMeta(meta) { state.meta = meta; }
export const hasFilters = () => Object.entries(state.filters).some(([, v]) => (Array.isArray(v) ? v.length : v));

/** Filtros no formato da API. */
export const apiFilters = () => ({ ...state.filters });
