// Formatação pt-BR. Use sempre estas funções para exibir números.
const brlF = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const brlC = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', notation: 'compact', maximumFractionDigits: 1 });
const intF = new Intl.NumberFormat('pt-BR');
const numF = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 });

export const brl = (v) => brlF.format(Number(v) || 0);
export const brlc = (v) => brlC.format(Number(v) || 0);
export const int = (v) => intF.format(Math.round(Number(v) || 0));
export const num = (v) => numF.format(Number(v) || 0);
export const pct = (v, digits = 1) =>
  new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: digits, minimumFractionDigits: digits }).format(Number(v) || 0);

/** "2026-09" -> "set/2026" */
export const month = (p) => {
  if (!p || !/^\d{4}-\d{2}$/.test(p)) return p || '—';
  const d = new Date(Number(p.slice(0, 4)), Number(p.slice(5, 7)) - 1, 1);
  return d.toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' }).replace('. de ', '/').replace(' de ', '/');
};
/** "2026-09-15" -> "15/09" */
export const day = (d) => (d && d.length >= 10 ? `${d.slice(8, 10)}/${d.slice(5, 7)}` : d || '—');

// Usado pelas tabelas (que chamam fmt(valor, linha)): cada função recebe só o valor.
export const FORMATS = {
  brl: (v) => brl(v), brlc: (v) => brlc(v), int: (v) => int(v), num: (v) => num(v), pct: (v) => pct(v),
  month: (v) => month(v), day: (v) => day(v), text: (v) => (v ?? '—'),
};
