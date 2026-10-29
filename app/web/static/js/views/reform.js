// Aba "Reforma tributária": IBS/CBS destacados em 2026 e simulação do cenário pleno.
import { api } from '../api.js';
import { h } from '../dom.js';
import { brl, brlc, pct } from '../format.js';
import { apiFilters, state } from '../state.js';
import { card, kpi, legend } from '../components/kpi.js';
import { table } from '../components/table.js';
import { bars, seriesColor } from '../components/charts.js';

const rates = { cbs_aliq: 8.8, ibs_aliq: 17.7 };

export default {
  id: 'reform',
  label: 'Reforma tributária',
  async render(root, ctx) {
    const f = apiFilters();
    if (!f.fluxo) f.fluxo = 'Saída'; // a simulação faz sentido sobre as saídas (débitos)
    const d = await api.reform(f, rates);
    const t = d.teste_2026 || {};
    const s = d.simulacao || {};

    const input = (key, label) => h('label', { class: 'param' }, label,
      h('input', { class: 'field', type: 'number', min: '0', max: '50', step: '0.1', value: rates[key],
        onchange: (e) => { rates[key] = Math.max(0, Math.min(50, Number(e.target.value) || 0)); ctx.rerender(); } }));

    const tiles = h('section', { class: 'kpis' },
      kpi({ label: 'IBS + CBS destacados (2026)', value: brl(t.total), note: `CBS ${brl(t.cbs)} · IBS ${brl(t.ibs)} — fase de teste (CBS 0,9% e IBS 0,1%), compensáveis com PIS/COFINS.` }),
      kpi({ label: 'Tributos que serão substituídos', value: brlc(s.atual_substituidos), full: brl(s.atual_substituidos), note: `ICMS, DIFAL, FCP, PIS, COFINS e ISS · carga atual ${pct(s.carga_atual)}` }),
      kpi({ label: 'IBS + CBS simulados', value: brlc(s.total), full: brl(s.total), note: `CBS ${pct(rates.cbs_aliq / 100)} + IBS ${pct(rates.ibs_aliq / 100)} com as reduções por item · carga ${pct(s.carga_simulada)}` }),
      kpi({ label: 'Variação estimada', value: `${s.variacao > 0 ? '+' : ''}${brlc(s.variacao)}`, full: `${s.variacao_pct > 0 ? '+' : ''}${pct(s.variacao_pct)} sobre a carga atual`,
        note: 'Positivo = mais tributo no cenário pleno (2033).' }));

    const params = card({
      title: 'Parâmetros da simulação',
      hint: 'Alíquotas de referência ainda não fixadas pelo Senado. Os valores padrão são estimativas usuais (≈26,5% somados); ajuste à vontade. A redução de alíquota de cada item (cClassTrib) vem do SAP.',
      body: h('div', { class: 'params' }, input('cbs_aliq', 'CBS (%)'), input('ibs_aliq', 'IBS (%)'),
        h('span', { class: 'foot-note' }, `Escopo: ${state.filters.fluxo ? state.filters.fluxo.toLowerCase() + 's' : 'saídas'} com os filtros atuais. IPI (${brl(s.ipi)}) fica fora da comparação: vira Imposto Seletivo/zero na maior parte dos casos.`)),
    });

    const elCmp = h('div', { class: 'chart' });
    const cmp = card({ title: 'Atual × simulado por CST de IBS/CBS', hint: '000 tributação integral · 200 alíquota reduzida · 410 imunidade/não incidência.',
      body: [legend([['Atual (substituídos)', seriesColor(0)], ['IBS + CBS simulado', seriesColor(1)]]), elCmp] });

    const cst = card({
      title: 'Resumo por CST',
      body: table({
        rows: d.por_cst, total: true,
        columns: [
          { key: 'cst_desc', label: 'CST IBS/CBS', align: 'l' }, { key: 'itens', label: 'Itens', fmt: 'int', sum: true },
          { key: 'valor_total', label: 'Valor total', fmt: 'brl', bar: true, sum: true }, { key: 'base', label: 'Base IBS/CBS', fmt: 'brl', sum: true },
          { key: 'ibs_cbs_2026', label: 'Destacado 2026', fmt: 'brl', sum: true }, { key: 'atual', label: 'Atual', fmt: 'brl', sum: true },
          { key: 'simulado', label: 'Simulado', fmt: 'brl', sum: true },
        ],
      }),
    });

    const mat = card({
      title: 'Impacto por material', hint: 'Os 20 maiores materiais. Redução = percentual de redução de alíquota aplicado pelo SAP.',
      body: table({
        rows: d.por_material, total: true, sort: { key: 'valor_total', desc: true },
        columns: [
          { key: 'material_desc', label: 'Material', align: 'l' }, { key: 'class_trib', label: 'cClassTrib', align: 'l' },
          { key: 'reducao', label: 'Redução', fmt: (v) => `${Number(v || 0).toLocaleString('pt-BR')}%` },
          { key: 'valor_total', label: 'Valor total', fmt: 'brl', bar: true, sum: true },
          { key: 'atual', label: 'Atual', fmt: 'brl', sum: true }, { key: 'simulado', label: 'Simulado', fmt: 'brl', sum: true },
          { key: 'variacao', label: 'Variação', fmt: 'brl', sum: true, cls: (v) => (v > 0 ? 'pos' : 'neg') },
        ],
      }),
    });

    root.replaceChildren(h('div', { class: 'view' }, params, tiles, cmp, cst, mat,
      h('p', { class: 'foot-note' }, 'Base legal: EC 132/2023 e LC 214/2025. Simulação gerencial: não considera créditos de IBS/CBS nas aquisições, regimes específicos nem a transição 2029–2032.')));

    bars(elCmp, {
      categories: d.por_cst.map((r) => r.cst_desc),
      series: [{ name: 'Atual (substituídos)', color: 0, data: d.por_cst.map((r) => r.atual) }, { name: 'IBS + CBS simulado', color: 1, data: d.por_cst.map((r) => r.simulado) }],
    });
  },
};
