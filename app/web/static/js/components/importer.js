// Modal de importação com dropzone para um ou vários arquivos.
import { api } from '../api.js';
import { h, icon, ICONS } from '../dom.js';
import { int } from '../format.js';

const ACCEPT = '.xlsx,.xlsm,.csv';
const kb = (n) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);

/** Cria a área de soltar arquivos. `onFiles(File[])` é chamado a cada seleção. */
export function dropzone(onFiles) {
  const input = h('input', { type: 'file', accept: ACCEPT, multiple: true, hidden: true, onchange: (e) => { onFiles([...e.target.files]); e.target.value = ''; } });
  const zone = h('div', {
    class: 'drop', role: 'button', tabindex: '0', 'aria-label': 'Selecionar planilhas',
    onclick: () => input.click(),
    onkeydown: (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } },
    ondragover: (e) => { e.preventDefault(); zone.classList.add('over'); },
    ondragleave: () => zone.classList.remove('over'),
    ondrop: (e) => { e.preventDefault(); zone.classList.remove('over'); onFiles([...e.dataTransfer.files]); },
  },
  icon(ICONS.upload, 34),
  h('b', {}, 'Arraste as planilhas aqui'),
  h('span', {}, 'ou ', h('u', {}, 'escolha os arquivos'), ' · .xlsx, .xlsm ou .csv · um ou vários de uma vez'),
  h('span', {}, 'A aba “SAP” é detectada automaticamente; itens repetidos são ignorados.'),
  input);
  return zone;
}

function fileRow(file, status = 'pending', message = '', onRemove) {
  return h('li', { class: `file ${status}` },
    h('span', { class: 'ic' }, icon(status === 'ok' ? ICONS.check : status === 'error' ? ICONS.alert : ICONS.file)),
    h('div', { class: 'meta' }, h('b', {}, file.name), h('span', {}, message || kb(file.size))),
    onRemove ? h('button', { class: 'btn btn-ghost btn-icon', 'aria-label': `Remover ${file.name}`, onclick: onRemove }, icon(ICONS.trash)) : null);
}

/** Abre o modal; `onDone()` é chamado quando ao menos um arquivo entrou na base. */
export function openImporter(onDone) {
  let files = [];
  const list = h('ul', { class: 'files' });
  const send = h('button', { class: 'btn btn-primary', disabled: true }, 'Importar');
  const close = () => back.remove();

  const draw = () => {
    list.replaceChildren(...files.map((f, i) => fileRow(f, 'pending', '', () => { files.splice(i, 1); draw(); })));
    send.disabled = !files.length;
    send.textContent = files.length > 1 ? `Importar ${files.length} arquivos` : 'Importar';
  };

  const zone = dropzone((picked) => {
    const names = new Set(files.map((f) => f.name + f.size));
    files.push(...picked.filter((f) => !names.has(f.name + f.size)));
    draw();
  });

  send.addEventListener('click', async () => {
    send.disabled = true; send.textContent = 'Importando…'; zone.classList.add('loading');
    try {
      const { results } = await api.upload(files);
      list.replaceChildren(...results.map((r, i) => fileRow(files[i] || { name: r.filename, size: 0 }, r.status, r.message)));
      const ok = results.filter((r) => r.status === 'ok');
      const inserted = ok.reduce((a, r) => a + r.rows_inserted, 0);
      files = [];
      send.textContent = 'Concluído';
      zone.classList.remove('loading');
      if (ok.length) {
        onDone?.(`${int(inserted)} itens importados de ${ok.length} arquivo(s).`);
        setTimeout(close, results.every((r) => r.status === 'ok') ? 900 : 4000);
      }
    } catch (_) {
      zone.classList.remove('loading'); send.disabled = false; send.textContent = 'Tentar de novo';
    }
  });

  const back = h('div', { class: 'modal-back', onclick: (e) => { if (e.target === back) close(); } },
    h('div', { class: 'modal', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Importar planilhas' },
      h('div', { class: 'modal-head' },
        h('div', {}, h('h2', {}, 'Importar planilhas'), h('p', { class: 'hint' }, 'Relatório fiscal do SAP (layout J1BNFE). Cada arquivo vira um lote que pode ser removido depois.')),
        h('button', { class: 'btn btn-ghost btn-icon', 'aria-label': 'Fechar', onclick: close }, icon(ICONS.x))),
      zone, list,
      h('div', { class: 'modal-foot' }, h('button', { class: 'btn', onclick: close }, 'Cancelar'), send)));
  document.addEventListener('keydown', function esc(e) { if (e.key === 'Escape') { close(); document.removeEventListener('keydown', esc); } });
  document.body.append(back);
}
