// Aba "Apuração & ajustes": quadro do mês com lançamentos manuais, conciliação com a
// apuração oficial, checklist de validação e fluxo lançador → validador → leitor.
// Regras e permissões ficam no servidor (app/services/apuracao.py); aqui é só a tela.
import { api } from '../api.js';
import { h, icon, ICONS } from '../dom.js';
import { brl, dec, dateTime, month, parseNum } from '../format.js';
import { ator, setAtor, state } from '../state.js';
import { card } from '../components/kpi.js';
import { table } from '../components/table.js';
import { toast } from '../components/toast.js';

const st = { comp: null, uf: null, opcoes: null, editing: null, draft: null };

const STATUS_PILL = { rascunho: 'info', em_validacao: 'media', devolvido: 'alta', validado: 'ok' };
const CHECK_PILL = { ok: ['ok', 'OK'], atencao: ['media', 'Atenção'], pendente: ['info', 'Pendente'], erro: ['alta', 'Erro'] };
const SITUACAO = {
  confere: ['ok', 'Confere'], justificada: ['media', 'Justificada'], divergente: ['alta', 'Sem justificativa'],
  sem_declarado: ['info', 'Sem valor oficial'], sem_movimento: ['info', 'Sem movimento'],
};
const ACAO_HIST = {
  lancamento_criado: 'Lançamento incluído', lancamento_alterado: 'Lançamento alterado', lancamento_excluido: 'Lançamento excluído',
  saldo_alterado: 'Quadro alterado', enviar: 'Enviado para validação', validar: 'Mês validado', devolver: 'Devolvido para correção',
};
const ORIGEM = { informado: 'informado', transportado: 'transportado', zero: 'não informado' };

const pill = ([cls, label]) => h('span', { class: `pill ${cls}` }, label);
const currentMonth = () => new Date().toISOString().slice(0, 7);

/** Garante nome e papel antes de gravar. Devolve false (e avisa) se faltar algo. */
function identificado() {
  if (!ator.nome.trim()) {
    toast('Informe seu nome em “Você está como” para registrar quem fez a alteração.', 'error');
    document.querySelector('.ap-actor input')?.focus();
    return false;
  }
  return true;
}

async function salvar(fn, ok, ctx) {
  if (!identificado()) return;
  try {
    await fn();
    if (ok) toast(ok);
    // Ao sair de um campo com Tab, o foco já está no próximo: devolve o foco a ele depois de redesenhar.
    const next = document.activeElement?.getAttribute('aria-label');
    await ctx.rerender();
    if (next) document.querySelector(`#view [aria-label="${CSS.escape(next)}"]`)?.focus();
  } catch (_) { /* a API já mostrou o erro */ }
}

// ---------------------------------------------------------------------------
// Topo: mês, UF, status, ações e "você está como"
// ---------------------------------------------------------------------------
function topBar(d, comps, ctx) {
  const statusOf = Object.fromEntries(comps.map((c) => [c.competencia, c.status]));
  const months = h('div', { class: 'ap-months', role: 'tablist', 'aria-label': 'Competência' },
    comps.map((c) => h('button', {
      type: 'button', class: 'ap-month', role: 'tab', 'aria-selected': String(c.competencia === st.comp),
      onclick: () => { st.comp = c.competencia; st.editing = null; ctx.rerender(); },
    }, h('i', { class: `dot ${STATUS_PILL[statusOf[c.competencia]] || 'info'}` }), month(c.competencia),
      h('small', {}, c.status_label))));

  const outro = h('input', {
    class: 'field', type: 'month', 'aria-label': 'Abrir outro mês', title: 'Abrir outro mês',
    value: comps.some((c) => c.competencia === st.comp) ? '' : st.comp,
    onchange: (e) => { if (e.target.value) { st.comp = e.target.value; st.editing = null; ctx.rerender(); } },
  });

  const uf = h('select', { class: 'field', 'aria-label': 'UF do estabelecimento', onchange: (e) => { st.uf = e.target.value; st.comp = null; ctx.rerender(); } },
    st.opcoes.ufs.map((u) => h('option', { value: u, selected: u === st.uf }, u)));

  const s = d.status;
  const quem = s.status === 'validado' ? `Validado por ${s.validado_por} em ${dateTime(s.validado_em)}`
    : s.status === 'em_validacao' ? `Enviado por ${s.enviado_por} em ${dateTime(s.enviado_em)}`
      : s.status === 'devolvido' ? 'Corrija e envie de novo para validação' : 'Lançamentos e quadro abertos para edição';

  const acoes = d.permissoes.acoes.map((a) => {
    const cls = a === 'devolver' ? 'btn btn-ghost btn-danger' : 'btn btn-primary';
    const ic = a === 'devolver' ? ICONS.x : ICONS.check;
    return h('button', { class: cls, onclick: () => (a === 'devolver' ? devolver(ctx) : mudar(a, null, ctx)) }, icon(ic), st.opcoes.acoes[a]);
  });

  const nome = h('input', {
    class: 'field', type: 'text', placeholder: 'Seu nome', value: ator.nome, maxlength: '120', 'aria-label': 'Seu nome',
    onchange: (e) => setAtor({ nome: e.target.value.trim() }),
  });
  const papel = h('div', { class: 'seg', role: 'group', 'aria-label': 'Papel' }, st.opcoes.papeis.map((p) => h('button', {
    type: 'button', 'aria-pressed': String(ator.papel === p.key), onclick: () => { setAtor({ papel: p.key }); ctx.rerender(); },
  }, p.label)));

  return h('section', { class: 'card ap-bar' },
    h('div', { class: 'ap-row' },
      h('div', { class: 'ap-field' }, h('span', { class: 'ap-label' }, 'Competência'), h('div', { class: 'ap-months-wrap' }, months, h('label', { class: 'ap-outro' }, 'outro mês', outro))),
      h('div', { class: 'ap-field' }, h('span', { class: 'ap-label' }, 'UF'), uf)),
    h('div', { class: 'ap-row ap-status' },
      h('div', { class: 'ap-st' },
        h('h2', {}, `Apuração ${st.uf} · ${month(st.comp)}`),
        h('div', { class: 'ap-st-line' }, pill([STATUS_PILL[s.status], s.label]), h('span', {}, quem))),
      h('div', { class: 'actions' },
        h('a', { class: 'btn', href: api.apuracao.exportUrl(st.comp, st.uf), onclick: () => toast('Gerando Excel do mês…') },
          icon(['M12 3v12m0 0 5-5m-5 5-5-5', 'M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2']), 'Exportar mês'),
        acoes)),
    s.status === 'devolvido' && s.motivo_devolucao
      ? h('div', { class: 'banner bad' }, icon(ICONS.alert), h('div', {}, h('b', {}, 'Devolvido para correção: '), s.motivo_devolucao)) : null,
    h('div', { class: 'ap-row ap-actor' },
      h('span', { class: 'ap-label' }, 'Você está como'), nome, papel,
      h('span', { class: 'foot-note' }, 'Sem login por enquanto: nome e papel ficam salvos neste navegador e vão para o histórico. Lançador lança e envia; validador valida ou devolve; leitor só consulta e exporta.')));
}

async function mudar(acao, motivo, ctx) {
  await salvar(() => api.apuracao.status({ competencia: st.comp, uf: st.uf, acao, motivo }),
    { enviar: 'Mês enviado para validação.', validar: 'Mês validado.', devolver: 'Mês devolvido para correção.' }[acao], ctx);
}

function devolver(ctx) {
  if (!identificado()) return;
  const txt = h('textarea', { class: 'field ap-textarea', rows: '4', placeholder: 'O que precisa ser corrigido?', maxlength: '1000' });
  const close = () => back.remove();
  const back = h('div', { class: 'modal-back', onclick: (e) => { if (e.target === back) close(); } },
    h('div', { class: 'modal', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Devolver para correção' },
      h('div', { class: 'modal-head' }, h('h2', {}, 'Devolver para correção'),
        h('button', { class: 'btn btn-icon btn-ghost', 'aria-label': 'Fechar', onclick: close }, icon(ICONS.x))),
      h('p', { class: 'hint' }, `O mês ${month(st.comp)} volta a ficar editável e o motivo aparece no topo da aba para quem lançou.`),
      txt,
      h('div', { class: 'modal-foot' },
        h('button', { class: 'btn', onclick: close }, 'Cancelar'),
        h('button', { class: 'btn btn-primary', onclick: async () => {
          if (txt.value.trim().length < 3) { toast('Explique o que precisa ser corrigido.', 'error'); return; }
          close(); await mudar('devolver', txt.value.trim(), ctx);
        } }, 'Devolver'))));
  document.body.append(back);
  txt.focus();
}

// ---------------------------------------------------------------------------
// Resumo por tributo
// ---------------------------------------------------------------------------
function tiles(d) {
  return h('section', { class: 'kpis' }, d.quadro.map((t) => {
    const devedor = t.resultado >= 0;
    const nota = t.declarado == null
      ? 'Apuração oficial ainda não informada.'
      : t.situacao === 'confere' ? `Confere com a apuração oficial (${brl(Math.abs(t.declarado))}).`
        : `Oficial ${brl(Math.abs(t.declarado))} · diferença ${brl(t.diferenca)}`;
    return h('article', { class: `kpi ap-tile ${t.situacao}` },
      h('div', { class: 'kpi-body' },
        h('div', { class: 'kpi-label' }, `${t.label} · ${t.tem_movimento ? (devedor ? 'a recolher' : 'saldo credor') : 'sem movimento'}`),
        h('span', { class: 'kpi-value' }, brl(Math.abs(t.resultado))),
        h('div', { class: 'kpi-full' }, t.ajustes ? `inclui ${brl(t.ajustes)} em ajustes manuais` : 'sem ajustes manuais')),
      h('div', { class: 'kpi-note' }, pill(SITUACAO[t.situacao]), ' ', nota));
  }));
}

// ---------------------------------------------------------------------------
// Checklist
// ---------------------------------------------------------------------------
function checklist(d) {
  const pend = d.checklist.filter((c) => c.status !== 'ok').length;
  return card({
    title: 'Checklist de validação',
    hint: pend ? `${pend} item(ns) para olhar antes de validar o mês.` : 'Tudo certo para validar o mês.',
    body: h('ul', { class: 'ap-check' }, d.checklist.map((c) => h('li', {},
      pill(CHECK_PILL[c.status]), h('div', {}, h('b', {}, c.titulo), h('p', {}, c.detalhe))))),
  });
}

// ---------------------------------------------------------------------------
// Quadro de apuração + conciliação com a apuração oficial
// ---------------------------------------------------------------------------
function moneyInput(value, { placeholder, onSave, label }) {
  const el = h('input', {
    class: 'field ap-num', type: 'text', inputmode: 'decimal', value: dec(value), placeholder: placeholder || '', 'aria-label': label,
    onchange: () => {
      const v = parseNum(el.value);
      if (Number.isNaN(v)) { toast('Valor inválido. Use o formato 1.234,56.', 'error'); el.value = dec(value); return; }
      onSave(v);
    },
  });
  return el;
}

function quadro(d, ctx) {
  const edit = d.permissoes.editar;
  const salvarSaldo = (trib, campos) => salvar(() => api.apuracao.saldo({ competencia: st.comp, uf: st.uf, tributo: trib, ...campos }), null, ctx);

  const head = h('thead', {}, h('tr', {}, h('th', { class: 'l' }, ''), d.quadro.map((t) => h('th', {}, t.label))));
  const rows = d.linhas.map((ln) => h('tr', { class: ln.estilo ? `is-${ln.estilo}` : null },
    h('td', { class: 'l' }, ln.label),
    d.quadro.map((t) => {
      const v = t.linhas[ln.key];
      if (ln.key !== 'saldo_credor_anterior') return h('td', { class: Math.abs(v) < 0.005 ? 'muted' : null }, brl(v));
      const origem = h('small', { class: 'ap-origem' }, t.saldo_anterior_origem === 'transportado' ? `transportado de ${month(t.saldo_anterior_de)}` : ORIGEM[t.saldo_anterior_origem]);
      if (!edit) return h('td', {}, brl(v), origem);
      return h('td', {}, moneyInput(t.saldo_anterior_origem === 'informado' ? v : null, {
        label: `Saldo credor anterior ${t.label}`, placeholder: dec(v),
        onSave: (val) => salvarSaldo(t.tributo, { saldo_credor_anterior: val }),
      }), origem);
    })));

  // Conciliação: valor oficial (GIA/SPED), diferença e justificativa
  const oficial = h('tr', { class: 'is-sep' }, h('td', { class: 'l' }, 'Apuração oficial (GIA/SPED)'), d.quadro.map((t) => {
    if (!edit) return h('td', {}, t.declarado == null ? '—' : `${brl(Math.abs(t.declarado))} ${t.declarado >= 0 ? 'a recolher' : 'credor'}`);
    const sinal = h('select', { class: 'field ap-sinal', 'aria-label': `Natureza do valor oficial ${t.label}` },
      h('option', { value: '1', selected: (t.declarado ?? 1) >= 0 }, 'a recolher'), h('option', { value: '-1', selected: (t.declarado ?? 1) < 0 }, 'credor'));
    const valor = moneyInput(t.declarado == null ? null : Math.abs(t.declarado), {
      label: `Valor oficial ${t.label}`, placeholder: '0,00',
      onSave: (val) => salvarSaldo(t.tributo, { valor_declarado: val == null ? null : val * Number(sinal.value) }),
    });
    sinal.addEventListener('change', () => { const v = parseNum(valor.value); if (v != null && !Number.isNaN(v)) salvarSaldo(t.tributo, { valor_declarado: v * Number(sinal.value) }); });
    return h('td', {}, h('div', { class: 'ap-pair' }, valor, sinal));
  }));
  const dif = h('tr', {}, h('td', { class: 'l' }, 'Diferença (painel − oficial)'), d.quadro.map((t) => h('td', {},
    t.diferenca == null ? h('span', { class: 'muted' }, '—') : brl(t.diferenca), ' ', pill(SITUACAO[t.situacao]))));
  const just = h('tr', {}, h('td', { class: 'l' }, 'Justificativa da diferença'), d.quadro.map((t) => {
    if (!edit) return h('td', { class: 'wrap ap-just' }, t.observacao || '—');
    const el = h('textarea', {
      class: `field ap-textarea ${t.situacao === 'divergente' ? 'is-bad' : ''}`, rows: '2', maxlength: '1000',
      placeholder: t.diferenca ? 'Explique a diferença' : 'Opcional', 'aria-label': `Justificativa ${t.label}`,
      onchange: () => salvarSaldo(t.tributo, { observacao: el.value.trim() || null }),
    });
    el.value = t.observacao;
    return h('td', { class: 'ap-just' }, el);
  }));

  return card({
    title: 'Quadro de apuração e conciliação',
    hint: 'Débitos e créditos pelas notas vêm da base SAP do mês inteiro (os filtros do topo não se aplicam aqui). Ajustes vêm dos lançamentos abaixo. '
      + 'O saldo credor anterior é transportado do mês anterior; digite um valor para substituir, ou apague para voltar ao automático.',
    body: h('div', { class: 'table-wrap ap-q' }, h('table', { class: 't' }, head, h('tbody', {}, rows, oficial, dif, just))),
  });
}

// ---------------------------------------------------------------------------
// Lançamentos manuais
// ---------------------------------------------------------------------------
function lancamentos(d, ctx) {
  const edit = d.permissoes.editar;
  const editing = st.editing ? d.lancamentos.find((l) => l.id === st.editing) : null;
  const base = st.draft || editing || { tipo: 'estorno_credito', tributo: 'icms', valor: null, descricao: '', referencia: '' };

  const tipo = h('select', { class: 'field', 'aria-label': 'Tipo' },
    h('optgroup', { label: 'Somam aos débitos' }, st.opcoes.tipos.filter((t) => t.lado === 'debito').map((t) => h('option', { value: t.key, selected: t.key === base.tipo }, t.label))),
    h('optgroup', { label: 'Somam aos créditos' }, st.opcoes.tipos.filter((t) => t.lado === 'credito').map((t) => h('option', { value: t.key, selected: t.key === base.tipo }, t.label))));
  const dica = h('p', { class: 'foot-note ap-dica' });
  const showHint = () => { dica.textContent = st.opcoes.tipos.find((t) => t.key === tipo.value)?.hint || ''; };
  tipo.addEventListener('change', showHint); showHint();

  const trib = h('select', { class: 'field', 'aria-label': 'Tributo' }, st.opcoes.tributos.map((t) => h('option', { value: t.key, selected: t.key === base.tributo }, t.label)));
  const valor = h('input', { class: 'field ap-num', type: 'text', inputmode: 'decimal', placeholder: '0,00', value: dec(base.valor), 'aria-label': 'Valor' });
  const ref = h('input', { class: 'field', type: 'text', maxlength: '120', placeholder: 'Ex.: SP000207, processo, NF', value: base.referencia || '', 'aria-label': 'Referência' });
  const desc = h('input', { class: 'field', type: 'text', maxlength: '500', placeholder: 'Motivo do lançamento (obrigatório)', value: base.descricao || '', 'aria-label': 'Descrição' });

  const enviar = async () => {
    const v = parseNum(valor.value);
    if (v == null || Number.isNaN(v) || v <= 0) { toast('Informe um valor maior que zero (ex.: 1.234,56).', 'error'); valor.focus(); return; }
    if (desc.value.trim().length < 3) { toast('Descreva o motivo do lançamento.', 'error'); desc.focus(); return; }
    const body = { tipo: tipo.value, tributo: trib.value, valor: v, descricao: desc.value.trim(), referencia: ref.value.trim() || null };
    st.draft = body;   // mantém o que foi digitado se a API recusar
    if (editing) await salvar(() => api.apuracao.alterar(editing.id, body), 'Lançamento alterado.', ctx);
    else await salvar(() => api.apuracao.criar({ competencia: st.comp, uf: st.uf, ...body }), 'Lançamento incluído.', ctx);
  };
  const cancelar = () => { st.editing = null; st.draft = null; ctx.rerender(); };

  const form = edit ? h('form', { class: 'ap-form', onsubmit: (e) => { e.preventDefault(); enviar(); } },
    h('label', { class: 'param' }, 'Tipo', tipo),
    h('label', { class: 'param' }, 'Tributo', trib),
    h('label', { class: 'param' }, 'Valor (R$)', valor),
    h('label', { class: 'param' }, 'Referência', ref),
    h('label', { class: 'param ap-desc' }, 'Descrição', desc),
    h('div', { class: 'ap-form-actions' },
      editing ? h('button', { type: 'button', class: 'btn', onclick: cancelar }, 'Cancelar') : null,
      h('button', { type: 'submit', class: 'btn btn-primary' }, icon(editing ? ICONS.check : ['M12 5v14M5 12h14']), editing ? 'Salvar alteração' : 'Incluir lançamento')),
    dica) : null;

  const lado = (l) => h('span', { class: `tag ap-lado ${l.lado}` }, l.lado === 'debito' ? '+ débito' : '+ crédito');
  const cols = [
    { key: 'tipo_label', label: 'Tipo', align: 'l', fmt: (v, r) => h('span', { class: 'ap-tipo' }, v, lado(r)) },
    { key: 'tributo_label', label: 'Tributo', align: 'l' },
    { key: 'valor', label: 'Valor', fmt: 'brl', sum: true },
    { key: 'descricao', label: 'Descrição', align: 'l', wrap: true },
    { key: 'referencia', label: 'Referência', align: 'l' },
    { key: 'criado_por', label: 'Lançado por', align: 'l', fmt: (v, r) => h('span', { class: 'ap-who' }, v, h('small', {}, dateTime(r.atualizado_em || r.criado_em), r.atualizado_por ? ` · alterado por ${r.atualizado_por}` : '')) },
  ];
  if (edit) {
    cols.push({ key: 'id', label: '', fmt: (_, r) => h('span', { class: 'ap-row-actions' },
      h('button', { class: 'btn btn-ghost', onclick: () => { st.editing = r.id; st.draft = null; ctx.rerender(); } }, 'Editar'),
      h('button', { class: 'btn btn-ghost btn-danger', 'aria-label': 'Excluir lançamento', onclick: async () => {
        if (!confirm(`Excluir o lançamento “${r.tipo_label} · ${r.tributo_label} · ${brl(r.valor)}”?`)) return;
        await salvar(() => api.apuracao.excluir(r.id), 'Lançamento excluído.', ctx);
      } }, icon(ICONS.trash))) });
  }

  return card({
    title: 'Lançamentos manuais',
    hint: edit ? 'Estornos e ajustes que não vêm das notas do SAP. Informe sempre o valor positivo: o tipo já diz se soma a débitos ou a créditos.'
      : 'Somente leitura: o mês não está em edição ou seu papel não permite lançar.',
    body: [form, table({
      rows: d.lancamentos, columns: cols, total: true, empty: 'Nenhum ajuste manual neste mês.',
      isActive: (r) => r.id === st.editing,
    })],
  });
}

// ---------------------------------------------------------------------------
// Histórico
// ---------------------------------------------------------------------------
function historico(d) {
  const papel = Object.fromEntries(st.opcoes.papeis.map((p) => [p.key, p.label]));
  return h('details', { class: 'card ap-hist' },
    h('summary', {}, h('h2', {}, 'Histórico do mês'), h('span', { class: 'hint' }, `${d.historico.length} registro(s) · quem fez o quê e quando`)),
    d.historico.length
      ? h('ol', { class: 'ap-timeline' }, d.historico.map((e) => h('li', {},
        h('time', {}, dateTime(e.criado_em)),
        h('div', {}, h('b', {}, ACAO_HIST[e.acao] || e.acao), h('span', { class: 'muted' }, ` · ${e.usuario} (${papel[e.papel] || e.papel})`),
          e.detalhe ? h('p', {}, e.detalhe) : null))))
      : h('p', { class: 'muted-row' }, 'Nada registrado ainda.'));
}

export default {
  id: 'apuracao',
  label: 'Apuração & ajustes',
  hideFilters: true,
  allowEmpty: true,
  async render(root, ctx) {
    st.opcoes ||= await api.apuracao.opcoes();
    st.uf ||= state.meta?.uf_estabelecimento || 'SP';
    const { competencias: comps } = await api.apuracao.competencias(st.uf);
    if (!st.comp) st.comp = comps.find((c) => c.tem_base_sap)?.competencia || comps[0]?.competencia || currentMonth();
    const d = await api.apuracao.painel(st.comp, st.uf);
    if (st.editing && !d.lancamentos.some((l) => l.id === st.editing)) st.editing = null;
    st.draft = null;

    const list = comps.some((c) => c.competencia === st.comp) ? comps
      : [...comps, { competencia: st.comp, status: d.status.status, status_label: d.status.label }].sort((a, b) => b.competencia.localeCompare(a.competencia));

    root.replaceChildren(h('div', { class: 'view' },
      topBar(d, list, ctx), tiles(d), checklist(d), quadro(d, ctx),
      lancamentos(d, ctx), historico(d),
      h('p', { class: 'foot-note' }, 'Visão gerencial para conferência: não substitui a escrituração (SPED/GIA). Diferenças de até R$ 0,05 contam como arredondamento.')));
  },
  reset() { st.editing = null; st.draft = null; },
};
