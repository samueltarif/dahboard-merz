// Aba "Conformidade": regras de validação item a item com a lista dos itens afetados.
import { api } from '../api.js';
import { h } from '../dom.js';
import { brl, int } from '../format.js';
import { apiFilters } from '../state.js';
import { card, stat } from '../components/kpi.js';
import { table } from '../components/table.js';

const LABEL = {
  numero_nfe: 'Nº NF', serie: 'Série', modelo: 'Mod.', cfop: 'CFOP', fluxo: 'Mov.', parceiro_nome: 'Parceiro', uf_op: 'UF',
  material_desc: 'Material', valor_total: 'Valor total', icms_base: 'Base ICMS', icms_aliq: 'Alíq. ICMS', icms_valor: 'ICMS',
  ipi_base: 'Base IPI', ipi_aliq: 'Alíq. IPI', ipi_valor: 'IPI', pis_base: 'Base PIS', pis_aliq: 'Alíq. PIS', pis_valor: 'PIS',
  cofins_base: 'Base COFINS', cofins_aliq: 'Alíq. COFINS', cofins_valor: 'COFINS', ibs_base: 'Base IBS', ibs_aliq: 'Alíq. IBS',
  ibs_red: 'Red. IBS %', ibs_valor: 'IBS', cbs_base: 'Base CBS', cbs_aliq: 'Alíq. CBS', cbs_red: 'Red. CBS %', cbs_valor: 'CBS',
  cst_icms: 'CST ICMS', tx_difal: 'DIFAL', origem_material: 'Origem', valor: 'Valor produtos', data_documento: 'Data doc.', data_lancamento: 'Lançamento',
};
const TEXT = new Set(['numero_nfe', 'serie', 'modelo', 'cfop', 'fluxo', 'parceiro_nome', 'uf_op', 'material_desc', 'cst_icms', 'origem_material', 'data_documento', 'data_lancamento']);
const RATE = /_aliq$|_red$/;

function columnsFor(cols) {
  return cols.map((c) => ({
    key: c.startsWith('tx_') ? c.slice(3) : c,
    label: LABEL[c] || c,
    align: TEXT.has(c) ? 'l' : 'r',
    fmt: TEXT.has(c) ? 'text' : RATE.test(c) ? 'num' : 'brl',
  }));
}

export default {
  id: 'compliance',
  label: 'Conformidade',
  async render(root) {
    const d = await api.compliance(apiFilters());
    const r = d.resumo;

    const summary = h('section', { class: 'card' }, h('div', { class: 'stat-row' },
      stat('Itens analisados', int(r.itens_analisados)),
      stat('Regras aplicadas', int(r.regras)),
      stat('Regras com alerta', int(r.regras_com_alerta), r.regras_com_alerta ? 'veja os detalhes abaixo' : 'nenhuma inconsistência'),
      stat('Itens com alerta', int(r.itens_com_alerta), 'exceto regras informativas')));

    const list = d.checks.map((c) => {
      const status = c.count === 0 ? h('span', { class: 'pill ok' }, 'OK') : h('span', { class: `pill ${c.severity}` }, c.severity === 'media' ? 'média' : c.severity);
      return h('details', { class: 'check' },
        h('summary', {}, status,
          h('div', {}, h('div', { class: 'c-title' }, c.title), h('div', { class: 'c-detail' }, c.detail)),
          h('div', { class: 'c-count' }, int(c.count)),
          h('div', { class: 'c-val' }, c.count ? `${int(c.documentos)} docs · ${brl(c.valor)}` : '—')),
        c.count
          ? [table({ rows: c.rows, columns: columnsFor(c.columns), maxHeight: '340px' }),
            c.count > c.rows.length ? h('p', { class: 'foot-note' }, `Mostrando ${c.rows.length} de ${int(c.count)}. A exportação em Excel traz a lista completa.`) : null]
          : h('p', { class: 'muted-row' }, 'Nenhum item viola esta regra.'));
    });

    root.replaceChildren(h('div', { class: 'view' }, summary,
      card({ title: 'Regras de validação', hint: 'Recalcula tributos e confere CST, DIFAL, alíquota de importados e base de PIS/COFINS. Clique numa regra para ver os itens.', body: list }),
      h('p', { class: 'foot-note' }, 'Tolerância de R$ 0,05 para arredondamento. Novas regras: app/services/compliance.py (lista CHECKS).')));
  },
};
