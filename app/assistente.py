"""
assistente.py
-------------
O "assistente" da Central.

COMO ELE FUNCIONA, SEM MISTERIO:
Ele NAO e inteligencia artificial. E uma lista de regras. Cada regra tem
um conjunto de palavras-chave e uma funcao que monta a resposta.

Quando chega uma pergunta:
  1. deixamos tudo em minusculo e sem acento
  2. procuramos qual regra tem alguma palavra-chave dentro da pergunta
  3. rodamos a funcao daquela regra, que CONSULTA O BANCO na hora
  4. se nenhuma regra combinar, respondemos o que sabemos fazer

A vantagem de consultar o banco e que a resposta nunca fica velha:
se uma apolice mudar de status, a resposta muda junto.
"""

import unicodedata
from datetime import date

from sqlalchemy import func

from app.models import Claim, Commission, Delinquency, Payment, Pendency, Policy, Proposal


# ---------------------------------------------------------------
# AJUDANTES
# ---------------------------------------------------------------
def _sem_acento(texto: str) -> str:
    """
    Tira os acentos e deixa minusculo, para 'Apólice' e 'apolice'
    serem tratados como a mesma palavra.
    """
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def _reais(valor: float, casas: int = 2) -> str:
    """Formata no padrao brasileiro: 1234.5 vira 'R$ 1.234,50'."""
    texto = f"{valor:,.{casas}f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------
# AS RESPOSTAS
# ---------------------------------------------------------------
# Cada funcao recebe a sessao do banco e devolve um texto em HTML.


def _renovacoes(db) -> str:
    hoje = date.today()
    apolices = (
        db.query(Policy)
        .filter(Policy.status == "A renovar")
        .order_by(Policy.data_vencimento)
        .all()
    )

    if not apolices:
        return "Não há nenhuma apólice com renovação nos próximos 30 dias. 🎉"

    linhas = "".join(
        f"<tr><td>{a.numero_apolice}</td><td>{a.participante}</td>"
        f"<td>{a.data_vencimento.strftime('%d/%m')} "
        f"({a.dias_para_vencer(hoje)} dias)</td></tr>"
        for a in apolices
    )
    return (
        f"Encontrei <b>{len(apolices)} apólices</b> com renovação nos "
        f"próximos 30 dias:<table><tr><th>Apólice</th><th>Participante</th>"
        f"<th>Vencimento</th></tr>{linhas}</table>"
    )


def _capital(db) -> str:
    total = db.query(func.sum(Policy.capital_total)).filter(
        Policy.status == "Ativa"
    ).scalar() or 0
    ativas = db.query(Policy).filter(Policy.status == "Ativa").count()

    por_cobertura = (
        db.query(Policy.cobertura, func.count(Policy.id))
        .filter(Policy.status == "Ativa")
        .group_by(Policy.cobertura)
        .order_by(func.count(Policy.id).desc())
        .all()
    )

    detalhe = ""
    if por_cobertura:
        maior, qtd = por_cobertura[0]
        pct = round(qtd * 100 / ativas) if ativas else 0
        detalhe = f" A maior concentração está em <b>{maior}</b> ({pct}%)."

    return (
        f"O <b>capital segurado total</b> da carteira é {_reais(total, 0)}, "
        f"distribuído em <b>{ativas} apólices ativas</b>.{detalhe}"
    )


def _sinistros(db) -> str:
    total = db.query(Claim).count()
    if total == 0:
        return "Não há sinistros registrados no momento."

    pendentes = db.query(Claim).filter(Claim.documentacao_ok.is_(False)).all()
    hoje = date.today()
    dias = [c.dias_em_aberto(hoje) for c in db.query(Claim).all()]
    media = round(sum(dias) / len(dias), 1)

    texto = (
        f"Há <b>{total} sinistros em andamento</b>. O tempo médio em aberto "
        f"é de <b>{str(media).replace('.', ',')} dias</b>."
    )
    if pendentes:
        lista = ", ".join(f"{c.protocolo} ({c.documentacao.lower()})" for c in pendentes)
        texto += f"<br><br>⚠️ <b>{len(pendentes)}</b> com documentação pendente: {lista}."
    return texto


def _inadimplencia(db) -> str:
    registros = db.query(Delinquency).order_by(Delinquency.dias_atraso.desc()).all()
    if not registros:
        return "Não há participantes inadimplentes. 🎉"

    total = sum(d.valor for d in registros)
    em_risco = [d for d in registros if d.dias_atraso > 90]

    linhas = "".join(
        f"<tr><td>{d.participante}</td><td>{d.numero_apolice}</td>"
        f"<td>{d.dias_atraso} dias</td><td>{_reais(d.valor)}</td></tr>"
        for d in registros[:5]
    )
    return (
        f"Há <b>{len(registros)} participantes inadimplentes</b>, somando "
        f"<b>{_reais(total)}</b> em atraso. <b>{len(em_risco)}</b> estão em "
        f"risco de cancelamento (mais de 90 dias).<table>"
        f"<tr><th>Participante</th><th>Apólice</th><th>Atraso</th><th>Valor</th></tr>"
        f"{linhas}</table>"
    )


def _comissoes(db) -> str:
    ultima = (
        db.query(Commission.competencia)
        .order_by(Commission.competencia.desc())
        .first()
    )
    if ultima is None:
        return "Ainda não há comissões registradas."

    competencia = ultima[0]
    registros = db.query(Commission).filter(Commission.competencia == competencia).all()
    premio = registros[0].premio_total if registros else 0

    linhas = "".join(
        f"<tr><td>{c.quem}</td><td>{int(c.percentual)}%</td>"
        f"<td>{_reais(c.valor, 0)}</td></tr>"
        for c in registros
    )
    return (
        f"Na competência <b>{competencia}</b>, sobre o prêmio de "
        f"<b>{_reais(premio, 0)}</b>, a divisão de comissões é:<table>"
        f"<tr><th>Agente</th><th>%</th><th>Valor</th></tr>{linhas}</table>"
    )


def _pendencias(db) -> str:
    abertas = [p for p in db.query(Pendency).all() if not p.resolvida]
    if not abertas:
        return "Não há pendências em aberto. 🎉"

    abertas.sort(key=lambda p: (p.peso_prioridade(), p.prazo or date.max))
    linhas = "".join(
        f"<tr><td>{p.prioridade}</td><td>{p.titulo}</td>"
        f"<td>{p.prazo.strftime('%d/%m') if p.prazo else '—'}</td></tr>"
        for p in abertas[:3]
    )
    altas = sum(1 for p in abertas if p.prioridade == "Alta")
    return (
        f"Há <b>{len(abertas)} pendências abertas</b>, sendo <b>{altas}</b> de "
        f"prioridade alta. As mais críticas:<table>"
        f"<tr><th>Prioridade</th><th>Pendência</th><th>Prazo</th></tr>{linhas}</table>"
    )


def _pagamentos(db) -> str:
    registros = db.query(Payment).all()
    if not registros:
        return "Não há movimentações carregadas."

    competencia = registros[0].competencia
    total_premio = sum(p.premio for p in registros)

    contagem: dict[str, int] = {}
    for p in registros:
        contagem[p.status] = contagem.get(p.status, 0) + 1

    resumo = ", ".join(f"<b>{qtd}</b> {status.lower()}" for status, qtd in contagem.items())
    atrasados = [p.segurado for p in registros if p.status == "Em atraso"]

    texto = (
        f"Na competência <b>{competencia}</b> a base tem "
        f"<b>{len(registros)} segurados</b>, com prêmio total de "
        f"<b>{_reais(total_premio)}</b>.<br>Pagamentos: {resumo}."
    )
    if atrasados:
        texto += f"<br><br>⚠️ Em atraso: <b>{', '.join(atrasados)}</b>."
    return texto


def _esteira(db) -> str:
    registros = db.query(Proposal).all()
    if not registros:
        return "Não há propostas na esteira."

    nomes = {
        "recebida": "propostas recebidas",
        "analise": "em análise",
        "aceita": "aceitas (aguardando emissão)",
        "pendente": "pendentes",
    }
    contagem: dict[str, int] = {}
    for p in registros:
        contagem[p.etapa] = contagem.get(p.etapa, 0) + 1

    partes = [f"<b>{contagem.get(k, 0)}</b> {v}" for k, v in nomes.items()]
    recusadas = [p for p in registros if p.recusada]

    texto = "Na <b>esteira de aceitação</b> há hoje: " + ", ".join(partes) + "."
    pendentes = [p for p in registros if p.etapa == "pendente" and not p.recusada]
    if pendentes:
        p = pendentes[0]
        texto += f"<br><br>A pendência ativa é a <b>{p.numero} ({p.participante})</b>: {p.observacao}."
    if recusadas:
        texto += f"<br>Foram recusadas <b>{len(recusadas)}</b> proposta(s)."
    return texto


def _apolices_carteira(db) -> str:
    total = db.query(Policy).count()
    por_status = (
        db.query(Policy.status, func.count(Policy.id)).group_by(Policy.status).all()
    )
    linhas = "".join(f"<tr><td>{s}</td><td>{q}</td></tr>" for s, q in por_status)
    return (
        f"A carteira tem <b>{total} apólices</b>, assim distribuídas:"
        f"<table><tr><th>Status</th><th>Quantidade</th></tr>{linhas}</table>"
    )


# ---------------------------------------------------------------
# A TABELA DE REGRAS
# ---------------------------------------------------------------
# A ordem importa: a primeira regra que combinar e a que responde.
# Por isso as mais especificas vem antes das mais genericas.
REGRAS = [
    (["vence", "vencem", "renova", "renovacao", "renovacoes"], _renovacoes),
    (["capital", "segurado total", "quanto vale"], _capital),
    (["sinistro", "obito", "falecimento", "invalidez confirmada"], _sinistros),
    (["inadimpl", "atraso", "atrasado", "devendo", "cobranca"], _inadimplencia),
    (["comissao", "comissoes", "repasse", "premio arrecadado"], _comissoes),
    (["pendencia", "pendencias", "falta", "faltando"], _pendencias),
    (["pagamento", "movimentacao", "pagou", "a pagar", "planilha"], _pagamentos),
    (["esteira", "proposta", "propostas", "subscricao", "aceitacao"], _esteira),
    (["apolice", "apolices", "carteira"], _apolices_carteira),
]

# As perguntas prontas que aparecem como botoes na tela.
SUGESTOES = [
    "Quais apólices vencem este mês?",
    "Qual o capital segurado total?",
    "Como estão os sinistros?",
    "Quem está inadimplente?",
    "Como ficaram as comissões?",
    "Quais pendências estão abertas?",
]

RESPOSTA_PADRAO = (
    "Não entendi a pergunta. 🤔<br><br>"
    "Sei responder sobre: <b>apólices e carteira</b>, <b>renovações</b>, "
    "<b>capital segurado</b>, <b>sinistros</b>, <b>inadimplência</b>, "
    "<b>comissões</b>, <b>pendências</b>, <b>pagamentos</b> e <b>esteira de propostas</b>."
    "<br><br>Tente, por exemplo: <i>“quais apólices vencem este mês?”</i>"
)


def responder(db, pergunta: str) -> str:
    """
    Recebe a pergunta e devolve a resposta em HTML.

    Esta e a unica funcao que o main.py precisa chamar.
    """
    if not pergunta or not pergunta.strip():
        return "Digite uma pergunta para eu poder ajudar. 🙂"

    texto = _sem_acento(pergunta)

    for palavras_chave, funcao in REGRAS:
        if any(palavra in texto for palavra in palavras_chave):
            return funcao(db)

    return RESPOSTA_PADRAO
