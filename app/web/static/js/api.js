// Cliente da API. Toda chamada HTTP do front passa por aqui.
import { toast } from './components/toast.js';

export class ApiError extends Error {}

function query(params = {}) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v == null || v === '' || (Array.isArray(v) && !v.length)) continue;
    q.set(k, Array.isArray(v) ? v.join(',') : String(v));
  }
  const s = q.toString();
  return s ? `?${s}` : '';
}

async function request(method, path, { params, body } = {}) {
  let res;
  try {
    res = await fetch(`/api${path}${query(params)}`, { method, body });
  } catch (e) {
    toast('Servidor indisponível. Verifique se o painel está rodando.', 'error');
    throw new ApiError('offline');
  }
  if (!res.ok) {
    let msg = `Erro ${res.status}`;
    try { const j = await res.json(); msg = j.detail?.[0]?.msg || j.detail || msg; } catch (_) {}
    toast(String(msg), 'error');
    throw new ApiError(msg);
  }
  return res.json();
}

export const api = {
  meta: () => request('GET', '/meta'),
  overview: (f) => request('GET', '/overview', { params: f }),
  products: (f, limit = 25) => request('GET', '/products', { params: { ...f, limit } }),
  reform: (f, rates) => request('GET', '/reform', { params: { ...f, ...rates } }),
  compliance: (f) => request('GET', '/compliance', { params: f }),
  items: (f, opts) => request('GET', '/items', { params: { ...f, ...opts } }),
  imports: () => request('GET', '/imports'),
  deleteImport: (id) => request('DELETE', `/imports/${id}`),
  upload: (files) => {
    const fd = new FormData();
    for (const f of files) fd.append('files', f, f.name);
    return request('POST', '/imports', { body: fd });
  },
  exportUrl: (f, formato) => `/api/export${query({ ...f, formato })}`,
};
