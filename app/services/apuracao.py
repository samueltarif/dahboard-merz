"""Apuração mensal com ajustes manuais: quadro, conciliação, checklist e fluxo de validação.

Débitos e créditos "pelas notas" vêm da base SAP (mesma regra da Visão geral).
Os lançamentos manuais (estornos e ajustes), o saldo credor anterior e o valor
declarado na apuração oficial vêm da aba "Apuração & ajustes".

Sem login por enquanto: quem age é identificado pelo nome e papel que a tela envia.
Quando houver login, só `Ator` passa a vir do token; as regras continuam aqui.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass

import pandas as pd

from app.domain import apuracao as regras
from app.repositories import apuracao_repo as repo
from app.repositories import imports_repo
from app.services import compliance, dataset, metrics
from app.services.metrics import brl


class PermissaoNegada(Exception):
    """Ação não permitida para o papel ou para o status do mês."""


class DadoInvalido(ValueError):
    """Entrada recusada por regra de negócio (mensagem pronta para a tela)."""


@dataclass(frozen=True)
class Ator:
    nome: str
    papel: str   # lancador | validador | leitor

    def exigir_identificacao(self) -> None:
        if self.papel not in regras.PAPEIS:
            raise PermissaoNegada("Escolha seu papel (lançador, validador ou leitor) no topo da aba.")
        if not self.nome.strip():
            raise PermissaoNegada("Informe seu nome no topo da aba para registrar quem fez a alteração.")


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------
def _r(v: float) -> float:
    return round(float(v), 2)


def _sap_por_periodo() -> dict[str, dict[str, tuple[float, float]]]:
    """{competência: {tributo: (débito, crédito)}} a partir da base SAP inteira."""
    df = dataset.get_dataset()
    out: dict[str, dict[str, tuple[float, float]]] = {}
    if df.empty:
        return out
    for periodo, part in df.groupby("periodo"):
        if not regras.competencia_valida(periodo):
            continue
        out[periodo] = {a["key"]: (a["debito"], a["credito"]) for a in metrics.apuracao(part)}
    return out


def _status(competencia: str, uf: str) -> dict:
    st = repo.status(competencia, uf) or {"status": "rascunho"}
    st["label"] = regras.STATUS.get(st["status"], st["status"])
    return st


def competencias(uf: str) -> list[dict]:
    """Meses disponíveis (com base SAP ou com algo lançado), do mais recente ao mais antigo."""
    sap = set(_sap_por_periodo())
    manual = {r["competencia"] for r in repo.lancamentos(uf=uf)} | {r["competencia"] for r in repo.saldos(uf)}
    st = {r["competencia"]: r["status"] for r in repo.todos_status(uf)}
    comps = sorted(sap | manual | set(st), reverse=True)
    return [{"competencia": c, "tem_base_sap": c in sap, "status": st.get(c, "rascunho"),
             "status_label": regras.STATUS.get(st.get(c, "rascunho"))} for c in comps]


def _situacao(dif: float | None, observacao: str | None, tem_movimento: bool) -> str:
    if dif is None:
        return "sem_declarado" if tem_movimento else "sem_movimento"
    if abs(dif) <= regras.TOLERANCIA:
        return "confere"
    return "justificada" if (observacao or "").strip() else "divergente"


def quadros(uf: str, ate: str | None = None) -> dict[str, list[dict]]:
    """Quadro de apuração de todos os meses até `ate`, transportando o saldo credor mês a mês."""
    sap = _sap_por_periodo()
    lanc = repo.lancamentos(uf=uf)
    sal = {(r["competencia"], r["tributo"]): r for r in repo.saldos(uf)}

    ajustes: dict[tuple[str, str, str], float] = {}
    for l in lanc:
        k = (l["competencia"], l["tributo"], l["tipo"])
        ajustes[k] = ajustes.get(k, 0.0) + float(l["valor"] or 0)

    meses = sorted(set(sap) | {l["competencia"] for l in lanc} | {c for c, _ in sal})
    if ate:
        meses = [m for m in meses if m <= ate]

    out: dict[str, list[dict]] = {}
    transporte: dict[str, tuple[str, float]] = {}   # tributo -> (competência de origem, saldo credor)
    for comp in meses:
        anterior = regras.competencia_anterior(comp)
        linhas_mes = []
        for trib in regras.TRIBUTOS:
            deb_sap, cred_sap = sap.get(comp, {}).get(trib, (0.0, 0.0))
            aj = {t.key: ajustes.get((comp, trib, t.key), 0.0) for t in regras.TIPOS}
            s = sal.get((comp, trib), {})

            if s.get("saldo_credor_anterior") is not None:
                saldo_ant, origem, de = float(s["saldo_credor_anterior"]), "informado", None
            elif trib in transporte and transporte[trib][0] == anterior:
                saldo_ant, origem, de = transporte[trib][1], "transportado", anterior
            else:
                saldo_ant, origem, de = 0.0, "zero", None

            total_deb = deb_sap + aj["ajuste_debito"] + aj["estorno_credito"]
            subtotal_cred = cred_sap + aj["ajuste_credito"] + aj["estorno_debito"]
            total_cred = subtotal_cred + saldo_ant
            resultado = total_deb - total_cred
            linhas = {
                "debito_saidas": deb_sap, "ajuste_debito": aj["ajuste_debito"], "estorno_credito": aj["estorno_credito"],
                "total_debitos": total_deb, "credito_entradas": cred_sap, "ajuste_credito": aj["ajuste_credito"],
                "estorno_debito": aj["estorno_debito"], "subtotal_creditos": subtotal_cred,
                "saldo_credor_anterior": saldo_ant, "total_creditos": total_cred,
                "saldo_devedor": max(resultado, 0.0), "saldo_credor": max(-resultado, 0.0),
            }
            declarado = s.get("valor_declarado")
            dif = None if declarado is None else _r(resultado - float(declarado))
            tem_mov = any(abs(v) > 0.004 for v in linhas.values())
            linhas_mes.append({
                "tributo": trib, "label": regras.TRIBUTO_LABEL[trib],
                "linhas": {k: _r(v) for k, v in linhas.items()},
                "saldo_anterior_origem": origem, "saldo_anterior_de": de,
                "resultado": _r(resultado), "declarado": None if declarado is None else _r(declarado),
                "diferenca": dif, "observacao": s.get("observacao") or "",
                "situacao": _situacao(dif, s.get("observacao"), tem_mov), "tem_movimento": tem_mov,
                "ajustes": _r(sum(aj.values())),
            })
            transporte[trib] = (comp, max(-resultado, 0.0))
        out[comp] = linhas_mes
    return out


def quadro(competencia: str, uf: str) -> list[dict]:
    q = quadros(uf, ate=competencia).get(competencia)
    if q is not None:
        return q
    # mês sem nada lançado ainda: devolve zerado (com transporte do mês anterior, se houver)
    vazio = quadros(uf, ate=competencia)
    anterior = vazio.get(regras.competencia_anterior(competencia), [])
    credor = {t["tributo"]: t["linhas"]["saldo_credor"] for t in anterior}
    out = []
    for trib in regras.TRIBUTOS:
        sa = credor.get(trib, 0.0)
        linhas = {k: 0.0 for k, _, _ in regras.LINHAS}
        linhas.update(saldo_credor_anterior=sa, subtotal_creditos=0.0, total_creditos=sa, saldo_credor=sa)
        out.append({"tributo": trib, "label": regras.TRIBUTO_LABEL[trib], "linhas": linhas,
                    "saldo_anterior_origem": "transportado" if sa else "zero",
                    "saldo_anterior_de": regras.competencia_anterior(competencia) if sa else None,
                    "resultado": _r(-sa), "declarado": None, "diferenca": None, "observacao": "",
                    "situacao": "sem_movimento" if not sa else "sem_declarado", "tem_movimento": bool(sa), "ajustes": 0.0})
    return out


def checklist(competencia: str, uf: str, q: list[dict], st: dict) -> list[dict]:
    """Itens para conferir antes de validar o mês. status: ok | atencao | pendente | erro."""
    df = dataset.get_dataset()
    part = df[df["periodo"].eq(competencia)] if not df.empty else df
    itens: list[dict] = []

    if part.empty:
        itens.append({"id": "base", "titulo": "Base SAP do mês", "status": "pendente",
                      "detalhe": "Nenhum item do SAP com lançamento neste mês. Importe o relatório antes de conferir."})
    else:
        ultimo = pd.to_datetime(part["data_lancamento"]).max()
        fim = calendar.monthrange(ultimo.year, ultimo.month)[1]
        lotes = [i for i in imports_repo.list_imports()
                 if str(i.get("periodo_ini") or "")[:7] <= competencia <= str(i.get("periodo_fim") or "")[:7]]
        parcial = ultimo.day < fim - 4
        n = lambda v: f"{v:,}".replace(",", ".")  # noqa: E731  (milhar no padrão brasileiro)
        itens.append({
            "id": "base", "titulo": "Base SAP do mês", "status": "atencao" if parcial else "ok",
            "detalhe": f"{n(len(part))} itens · {n(part['doc_key'].nunique())} documentos · "
                       f"{part['dia'].nunique()} dias com movimento · último lançamento em {ultimo:%d/%m} · {len(lotes)} lote(s)"
                       + (". A base parece não cobrir o mês inteiro: confira se faltou importar o final do mês." if parcial else "."),
        })
        cp = compliance.run(part, sample=1)["resumo"]
        itens.append({
            "id": "conformidade", "titulo": "Conformidade das notas",
            "status": "ok" if cp["regras_com_alerta"] == 0 else "atencao",
            "detalhe": "Nenhuma regra com alerta." if cp["regras_com_alerta"] == 0 else
            f"{cp['regras_com_alerta']} regra(s) com alerta em {cp['itens_com_alerta']} item(ns). Veja a aba Conformidade filtrando este mês.",
        })

    com_mov = [t for t in q if t["tem_movimento"]]
    sem_decl = [t["label"] for t in com_mov if t["declarado"] is None]
    itens.append({
        "id": "declarado", "titulo": "Valor da apuração oficial informado",
        "status": "pendente" if sem_decl else "ok",
        "detalhe": f"Falta informar: {', '.join(sem_decl)}." if sem_decl else
        "Todos os tributos com movimento têm o valor da apuração oficial (GIA/SPED) para comparar.",
    })

    diverg = [t for t in q if t["situacao"] == "divergente"]
    justif = [t for t in q if t["situacao"] == "justificada"]
    if diverg:
        det = "; ".join(f"{t['label']}: diferença de {brl(t['diferenca'])} sem justificativa" for t in diverg)
        itens.append({"id": "diferencas", "titulo": "Diferenças entre painel e apuração oficial", "status": "erro", "detalhe": det + "."})
    elif not any(t["declarado"] is not None for t in q):
        itens.append({"id": "diferencas", "titulo": "Diferenças entre painel e apuração oficial", "status": "pendente",
                      "detalhe": "Ainda não há valor oficial para comparar."})
    else:
        det = ("Diferenças justificadas: " + "; ".join(f"{t['label']} {brl(t['diferenca'])} ({t['observacao']})" for t in justif) + ".") if justif \
            else "Painel e apuração oficial conferem (tolerância de R$ 0,05)."
        itens.append({"id": "diferencas", "titulo": "Diferenças entre painel e apuração oficial", "status": "ok", "detalhe": det})

    zerados = [t["label"] for t in com_mov if t["saldo_anterior_origem"] == "zero"]
    itens.append({
        "id": "saldo_anterior", "titulo": "Saldo credor do período anterior",
        "status": "atencao" if zerados else "ok",
        "detalhe": f"Considerado zero (não informado nem transportado) para: {', '.join(zerados)}. Se havia saldo credor, informe no quadro."
        if zerados else "Informado ou transportado do mês anterior para todos os tributos com movimento.",
    })

    lanc = repo.lancamentos(competencia, uf)
    itens.append({
        "id": "ajustes", "titulo": "Ajustes manuais", "status": "ok",
        "detalhe": f"{len(lanc)} lançamento(s), todos com descrição." if lanc else "Nenhum ajuste manual neste mês.",
    })

    feito = st["status"] == "validado"
    itens.append({
        "id": "validacao", "titulo": "Validação do mês", "status": "ok" if feito else "pendente",
        "detalhe": f"Validado por {st.get('validado_por')}." if feito else f"Status atual: {st['label']}.",
    })
    return itens


def painel(competencia: str, uf: str, ator: Ator) -> dict:
    _validar_chave(competencia, uf)
    st = _status(competencia, uf)
    q = quadro(competencia, uf)
    return {
        "competencia": competencia, "uf": uf, "status": st, "quadro": q,
        "linhas": [{"key": k, "label": l, "estilo": e} for k, l, e in regras.LINHAS],
        "lancamentos": [_lanc_out(l) for l in repo.lancamentos(competencia, uf)],
        "checklist": checklist(competencia, uf, q, st),
        "historico": repo.historico(competencia, uf)[:200],
        "permissoes": {"editar": regras.pode_editar(ator.papel, st["status"]),
                       "acoes": regras.acoes_permitidas(ator.papel, st["status"])},
    }


def opcoes() -> dict:
    """Listas para os seletores da tela."""
    return {
        "tipos": [t.__dict__ for t in regras.TIPOS],
        "tributos": [{"key": k, "label": v} for k, v in regras.TRIBUTO_LABEL.items()],
        "papeis": [{"key": k, "label": v} for k, v in regras.PAPEIS.items()],
        "status": regras.STATUS, "acoes": regras.ACAO_LABEL, "ufs": list(regras.UFS),
    }


def _lanc_out(l: dict) -> dict:
    return {**l, "tipo_label": regras.TIPO_BY_KEY[l["tipo"]].label if l["tipo"] in regras.TIPO_BY_KEY else l["tipo"],
            "tributo_label": regras.TRIBUTO_LABEL.get(l["tributo"], l["tributo"]),
            "lado": regras.TIPO_BY_KEY[l["tipo"]].lado if l["tipo"] in regras.TIPO_BY_KEY else ""}


# ---------------------------------------------------------------------------
# Escrita (sempre com checagem de papel e status)
# ---------------------------------------------------------------------------
def _validar_chave(competencia: str, uf: str) -> None:
    if not regras.competencia_valida(competencia):
        raise DadoInvalido("Competência inválida. Use o formato AAAA-MM.")
    if uf not in regras.UFS:
        raise DadoInvalido("UF inválida.")


def _exigir_edicao(competencia: str, uf: str, ator: Ator) -> None:
    ator.exigir_identificacao()
    if ator.papel == "leitor":
        raise PermissaoNegada("O papel Leitor só consulta e exporta. Troque o papel no topo da aba para lançar.")
    st = _status(competencia, uf)
    if st["status"] not in regras.EDITAVEL:
        raise PermissaoNegada(f"O mês está “{st['label']}” e não pode ser alterado. "
                              "O validador precisa devolver para correção antes.")


def _validar_lancamento(d: dict) -> dict:
    if d["tributo"] not in regras.TRIBUTOS:
        raise DadoInvalido("Tributo inválido.")
    if d["tipo"] not in regras.TIPO_BY_KEY:
        raise DadoInvalido("Tipo de lançamento inválido.")
    valor = round(float(d["valor"]), 2)
    if valor <= 0:
        raise DadoInvalido("Informe um valor maior que zero. O tipo do lançamento já diz se ele soma a débitos ou créditos.")
    desc = (d.get("descricao") or "").strip()
    if len(desc) < 3:
        raise DadoInvalido("Descreva o motivo do lançamento (é o que a validação e a auditoria vão ler).")
    return {"tributo": d["tributo"], "tipo": d["tipo"], "valor": valor, "descricao": desc[:500],
            "referencia": (d.get("referencia") or "").strip()[:120] or None}


def _resumo(l: dict) -> str:
    return f"{regras.TIPO_BY_KEY[l['tipo']].label} · {regras.TRIBUTO_LABEL[l['tributo']]} · {brl(l['valor'])} — {l['descricao']}"


def criar_lancamento(competencia: str, uf: str, dados: dict, ator: Ator) -> dict:
    _validar_chave(competencia, uf)
    _exigir_edicao(competencia, uf, ator)
    vals = _validar_lancamento(dados)
    row = repo.criar_lancamento({"competencia": competencia, "uf": uf, **vals,
                                 "criado_por": ator.nome.strip()[:120], "criado_em": repo.now()})
    repo.registrar(competencia, uf, "lancamento_criado", _resumo(vals), ator.nome, ator.papel)
    return _lanc_out(row)


def _lancamento_existente(lanc_id: int) -> dict:
    atual = repo.lancamento(lanc_id)
    if not atual:
        raise DadoInvalido("Lançamento não encontrado (pode ter sido excluído por outra pessoa).")
    return atual


def alterar_lancamento(lanc_id: int, dados: dict, ator: Ator) -> None:
    atual = _lancamento_existente(lanc_id)
    _exigir_edicao(atual["competencia"], atual["uf"], ator)
    vals = _validar_lancamento(dados)
    repo.alterar_lancamento(lanc_id, {**vals, "atualizado_por": ator.nome.strip()[:120], "atualizado_em": repo.now()})
    repo.registrar(atual["competencia"], atual["uf"], "lancamento_alterado",
                   f"Antes: {_resumo(atual)} | Depois: {_resumo(vals)}", ator.nome, ator.papel)


def excluir_lancamento(lanc_id: int, ator: Ator) -> None:
    atual = _lancamento_existente(lanc_id)
    _exigir_edicao(atual["competencia"], atual["uf"], ator)
    repo.excluir_lancamento(lanc_id)
    repo.registrar(atual["competencia"], atual["uf"], "lancamento_excluido", _resumo(atual), ator.nome, ator.papel)


def gravar_saldo(competencia: str, uf: str, tributo: str, dados: dict, ator: Ator) -> None:
    """dados: qualquer subconjunto de saldo_credor_anterior, valor_declarado, observacao (None limpa o campo)."""
    _validar_chave(competencia, uf)
    if tributo not in regras.TRIBUTOS:
        raise DadoInvalido("Tributo inválido.")
    _exigir_edicao(competencia, uf, ator)
    vals: dict = {}
    if "saldo_credor_anterior" in dados:
        v = dados["saldo_credor_anterior"]
        if v is not None and float(v) < 0:
            raise DadoInvalido("O saldo credor anterior não pode ser negativo.")
        vals["saldo_credor_anterior"] = None if v is None else round(float(v), 2)
    if "valor_declarado" in dados:
        v = dados["valor_declarado"]
        vals["valor_declarado"] = None if v is None else round(float(v), 2)
    if "observacao" in dados:
        vals["observacao"] = ((dados["observacao"] or "").strip()[:1000]) or None
    if not vals:
        return
    repo.gravar_saldo(competencia, uf, tributo, {**vals, "atualizado_por": ator.nome.strip()[:120], "atualizado_em": repo.now()})

    def txt(k, v):
        if k == "observacao":
            return f"justificativa: {v or '(vazia)'}"
        if v is None:
            return f"{'saldo anterior' if k == 'saldo_credor_anterior' else 'valor declarado'}: (vazio)"
        if k == "valor_declarado":
            return f"valor declarado: {brl(abs(v))} {'a recolher' if v >= 0 else 'credor'}"
        return f"saldo credor anterior: {brl(v)}"
    repo.registrar(competencia, uf, "saldo_alterado",
                   f"{regras.TRIBUTO_LABEL[tributo]} · " + "; ".join(txt(k, v) for k, v in vals.items()), ator.nome, ator.papel)


def mudar_status(competencia: str, uf: str, acao: str, motivo: str | None, ator: Ator) -> dict:
    _validar_chave(competencia, uf)
    ator.exigir_identificacao()
    if acao not in regras.TRANSICOES:
        raise DadoInvalido("Ação inválida.")
    papeis, origem, destino = regras.TRANSICOES[acao]
    st = _status(competencia, uf)
    if ator.papel not in papeis:
        quem = " ou ".join(regras.PAPEIS[p] for p in papeis)
        raise PermissaoNegada(f"“{regras.ACAO_LABEL[acao]}” é feito pelo papel {quem}.")
    if st["status"] not in origem:
        raise PermissaoNegada(f"Não dá para “{regras.ACAO_LABEL[acao].lower()}” com o mês “{st['label']}”.")

    motivo = (motivo or "").strip()
    if acao in ("enviar", "validar"):
        diverg = [t for t in quadro(competencia, uf) if t["situacao"] == "divergente"]
        if diverg:
            nomes = ", ".join(f"{t['label']} ({brl(t['diferenca'])})" for t in diverg)
            raise DadoInvalido(f"Há diferença sem justificativa em {nomes}. Escreva a justificativa ou corrija antes de continuar.")
    if acao == "devolver" and len(motivo) < 3:
        raise DadoInvalido("Explique o que precisa ser corrigido ao devolver.")

    agora = repo.now()
    vals: dict = {"status": destino}
    if acao == "enviar":
        vals.update(enviado_por=ator.nome.strip()[:120], enviado_em=agora, motivo_devolucao=None)
    elif acao == "validar":
        vals.update(validado_por=ator.nome.strip()[:120], validado_em=agora)
    else:
        vals.update(motivo_devolucao=motivo[:1000], validado_por=None, validado_em=None)
    repo.gravar_status(competencia, uf, vals)
    repo.registrar(competencia, uf, acao, motivo or regras.STATUS[destino], ator.nome, ator.papel)
    return _status(competencia, uf)
