// Cliente da API. Toda chamada HTTP do front passa por aqui.
import { toast } from './components/toast.js';
import { ator } from './state.js';

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

/** Quem está agindo (sem login por enquanto). O nome vai codificado: cabeçalho HTTP não aceita todo acento. */
const atorHeaders = () => ({ 'X-Usuario': encodeURIComponent(ator.nome || ''), 'X-Papel': ator.papel || '' });

async function request(method, path, { params, body, json, headers } = {}) {
  let res;
  const hdrs = { ...(headers || {}) };
  if (json !== undefined) { hdrs['Content-Type'] = 'application/json'; body = JSON.stringify(json); }
  try {
    res = await fetch(`/api${path}${query(params)}`, { method, body, headers: hdrs });
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

  apuracao: {
    opcoes: () => request('GET', '/apuracao/opcoes'),
    competencias: (uf) => request('GET', '/apuracao/competencias', { params: { uf } }),
    painel: (competencia, uf) => request('GET', '/apuracao', { params: { competencia, uf }, headers: atorHeaders() }),
    criar: (body) => request('POST', '/apuracao/lancamentos', { json: body, headers: atorHeaders() }),
    alterar: (id, body) => request('PUT', `/apuracao/lancamentos/${id}`, { json: body, headers: atorHeaders() }),
    excluir: (id) => request('DELETE', `/apuracao/lancamentos/${id}`, { headers: atorHeaders() }),
    saldo: (body) => request('PUT', '/apuracao/saldos', { json: body, headers: atorHeaders() }),
    status: (body) => request('POST', '/apuracao/status', { json: body, headers: atorHeaders() }),
    exportUrl: (competencia, uf) => `/api/apuracao/export${query({ competencia, uf })}`,
  },
};
