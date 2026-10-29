// Ponto de entrada do front: monta abas, filtros, ações do topo e roteia as views.
import { api } from './api.js';
import { h } from './dom.js';
import { month } from './format.js';
import { state, onChange, setMeta, setView, apiFilters } from './state.js';
import { renderFilters } from './components/filters.js';
import { openImporter, dropzone } from './components/importer.js';
import { rethemeAll, disposeAll } from './components/charts.js';
import { toast } from './components/toast.js';

import overview from './views/overview.js';
import operations from './views/operations.js';
import products from './views/products.js';
import reform from './views/reform.js';
import compliance from './views/compliance.js';
import data from './views/data.js';

const VIEWS = [overview, operations, products, reform, compliance, data];
const $ = (id) => document.getElementById(id);
const ctx = { openImporter: () => openImporter(afterImport), refresh: () => boot(), rerender: () => renderView() };

let renderSeq = 0;

async function renderView() {
  const view = VIEWS.find((v) => v.id === state.view) || VIEWS[0];
  const root = $('view');
  for (const t of $('tabs').children) t.setAttribute('aria-selected', String(t.dataset.view === view.id));

  if (state.meta?.empty && view.id !== 'data') { renderEmpty(root); return; }

  const seq = ++renderSeq;
  root.classList.add('loading');
  try {
    const tmp = h('div');
    await view.render(tmp, ctx);
    if (seq !== renderSeq) return; // outra renderização começou depois desta
    root.replaceChildren(...tmp.childNodes);
  } catch (e) {
    if (seq === renderSeq) root.replaceChildren(h('div', { class: 'card' }, h('p', { class: 'muted-row' }, `Não foi possível carregar esta aba: ${e.message}`)));
    console.error(e);
  } finally {
    if (seq === renderSeq) root.classList.remove('loading');
    disposeAll();
  }
}

function renderEmpty(root) {
  root.replaceChildren(h('div', { class: 'card empty' },
    h('h2', {}, 'Comece importando o relatório do SAP'),
    h('p', {}, 'Arraste uma ou várias planilhas (.xlsx/.csv). O painel encontra a aba “SAP”, classifica por CFOP e calcula tributos, carga efetiva, conformidade e o impacto da reforma.'),
    dropzone((files) => files.length && uploadDirect(files))));
}

async function uploadDirect(files) {
  toast(`Importando ${files.length} arquivo(s)…`);
  const { results } = await api.upload(files);
  results.filter((r) => r.status !== 'ok').forEach((r) => toast(`${r.filename}: ${r.message}`, r.status === 'error' ? 'error' : 'info', 7000));
  const ok = results.filter((r) => r.status === 'ok');
  if (ok.length) afterImport(`${ok.reduce((a, r) => a + r.rows_inserted, 0)} itens importados.`);
}

function afterImport(message) { toast(message); boot(); }

function renderTabs() {
  $('tabs').replaceChildren(...VIEWS.map((v) => h('button', {
    class: 'tab', role: 'tab', dataset: { view: v.id }, 'aria-selected': String(v.id === state.view), onclick: () => setView(v.id),
  }, v.label)));
}

function renderHeader() {
  const m = state.meta;
  if (!m || m.empty) { $('period-line').textContent = 'Importe o relatório do SAP para começar.'; return; }
  const per = m.periodos.length > 1 ? `${month(m.periodos[0])} a ${month(m.periodos[m.periodos.length - 1])}` : month(m.periodos[0]);
  $('period-line').textContent = `Lançamentos de ${per} · ${m.imports.length} lote(s) importado(s) · ${m.empresa}`;
}

function wireActions() {
  document.querySelector('[data-action="import"]').addEventListener('click', ctx.openImporter);

  const menuBtn = document.querySelector('[data-action="export-menu"]');
  const menu = $('export-menu');
  menuBtn.addEventListener('click', (e) => { e.stopPropagation(); menu.hidden = !menu.hidden; menuBtn.setAttribute('aria-expanded', String(!menu.hidden)); });
  document.addEventListener('click', () => { menu.hidden = true; menuBtn.setAttribute('aria-expanded', 'false'); });
  menu.querySelectorAll('[data-export]').forEach((b) => b.addEventListener('click', () => {
    if (state.meta?.empty) { toast('Não há dados para exportar.', 'error'); return; }
    window.location.href = api.exportUrl(apiFilters(), b.dataset.export);
    toast('Gerando arquivo com os filtros atuais…');
  }));

  document.querySelector('[data-action="theme"]').addEventListener('click', () => {
    const root = document.documentElement;
    const dark = root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    root.dataset.theme = dark ? 'light' : 'dark';
    try { localStorage.setItem('painel-theme', root.dataset.theme); } catch (_) {}
    rethemeAll();
  });
}

async function boot() {
  try {
    setMeta(await api.meta());
  } catch (_) { return; }
  renderHeader();
  renderTabs();
  renderFilters($('filters'));
  await renderView();
}

onChange((reason) => {
  if (reason === 'filters') { data.reset?.(); renderFilters($('filters')); }
  renderView();
});

wireActions();
boot();
