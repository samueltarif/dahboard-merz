import { h } from '../dom.js';

export function toast(message, kind = 'info', ms = 4200) {
  const box = document.getElementById('toasts');
  if (!box) return;
  const el = h('div', { class: `toast ${kind}` }, message);
  box.append(el);
  setTimeout(() => el.remove(), ms);
}
