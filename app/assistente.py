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

import re
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


def _contem(texto: str, palavra: str) -> bool:
    """
    A palavra aparece no texto, COMECANDO uma palavra?

    POR QUE NAO USAR SO "palavra in texto":
    porque "api" esta dentro de "cAPItal". Buscando so por pedaco, a
    pergunta "o que e capital segurado?" cairia na regra da API.

    O \\b do comeco significa "borda de palavra": so encontra "api" se
    ele comecar uma palavra. Nao colocamos \\b no fim de proposito,
    para "inadimpl" continuar encontrando "inadimplencia".
    """
    return re.search(r"\b" + re.escape(palavra), texto) is not None


def _alguma(texto: str, palavras: list[str]) -> bool:
    """Alguma destas palavras aparece no texto?"""
    return any(_contem(texto, p) for p in palavras)


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


# ===============================================================
# CONVERSA (cumprimentos, apresentacao, agradecimento)
# ===============================================================
# Estas funcoes recebem db so para terem todas a mesma forma, mesmo
# quando nao precisam consultar o banco. O "_" no nome do parametro
# e a forma de dizer "recebo, mas nao uso".


def _cumprimento(_db) -> str:
    return (
        "Olá! 👋 Tudo bem por aqui, obrigado por perguntar.<br><br>"
        "Sou o assistente da <b>Central Inteligente de Seguros</b>. "
        "Posso consultar a carteira para você e explicar os termos do "
        "seguro de risco.<br><br>"
        "O que você precisa saber?"
    )


def _apresentacao(_db) -> str:
    return (
        "Sou o <b>assistente da Central Inteligente de Seguros</b>, o sistema "
        "que o Sebrae Previdência usa para administrar o seguro de risco "
        "(morte e invalidez) junto com a corretora e a seguradora.<br><br>"
        "<b>O que eu faço:</b>"
        "<table>"
        "<tr><th>Consulto os dados</th><th>Explico os termos</th></tr>"
        "<tr><td>apólices e renovações</td><td>o que é apólice, prêmio, capital</td></tr>"
        "<tr><td>sinistros e pendências</td><td>o que é sinistro, DPS, carência</td></tr>"
        "<tr><td>comissões e inadimplência</td><td>quem é estipulante, corretora, seguradora</td></tr>"
        "<tr><td>pagamentos e propostas</td><td>como funciona a esteira</td></tr>"
        "</table>"
        "Tudo que eu respondo sobre números vem <b>do banco de dados, "
        "consultado na hora</b> — nada é inventado."
    )


def _agradecimento(_db) -> str:
    return "Por nada! 🙂 Se precisar de mais alguma coisa sobre a carteira, é só chamar."


def _despedida(_db) -> str:
    return "Até logo! 👋 Quando precisar, estarei por aqui."


def _ajuda(_db) -> str:
    return (
        "Posso ajudar com estes assuntos:<br><br>"
        "<b>📊 Números da carteira</b><br>"
        "apólices, renovações, capital segurado, prêmio, vidas cobertas<br><br>"
        "<b>💰 Financeiro</b><br>"
        "pagamentos, boletos, comissões, inadimplência, convênios<br><br>"
        "<b>📋 Operação</b><br>"
        "sinistros, pendências, esteira de propostas<br><br>"
        "<b>📖 Conceitos de seguro</b><br>"
        "o que é apólice, prêmio, capital segurado, sinistro, DPS, carência, "
        "beneficiário, estipulante, subscrição, invalidez…<br><br>"
        "<b>⚙️ Sobre o sistema</b><br>"
        "como enviar planilha, como funciona o acesso, o que cada perfil vê<br><br>"
        "Experimente: <i>“o que é capital segurado?”</i> ou "
        "<i>“quais apólices vencem este mês?”</i>"
    )


# ===============================================================
# CONCEITOS DE SEGURO (o glossario)
# ===============================================================
# Cada item: (palavras que disparam, titulo, explicacao).
# Escrito em linguagem simples, do jeito que se explicaria para alguem
# que nunca trabalhou com seguros.
GLOSSARIO = [
    (
        ["apolice", "o que e apolice"],
        "Apólice",
        "É o <b>contrato do seguro</b>. Nela está escrito quem está segurado, "
        "quais riscos estão cobertos, de quanto é a indenização e até quando "
        "vale. Na Central, cada apólice tem um número no formato <b>AP-0000</b>.",
    ),
    (
        ["premio", "quanto custa o seguro", "mensalidade"],
        "Prêmio",
        "É <b>o valor que se paga pelo seguro</b> — a mensalidade. O nome confunde: "
        "não é um prêmio que se ganha, é o que se paga. Quem recebe dinheiro em "
        "caso de sinistro recebe a <b>indenização</b>, que é outra coisa.<br><br>"
        "Na nossa carteira o prêmio fica em torno de <b>0,04% do capital "
        "segurado por mês</b>: um capital de R$ 150.000 custa cerca de R$ 60,70.",
    ),
    (
        ["capital segurado", "indenizacao", "o que e capital"],
        "Capital segurado",
        "É <b>quanto a seguradora paga</b> se o risco acontecer. Se alguém tem "
        "capital de R$ 250.000 por morte, os beneficiários recebem esse valor.<br><br>"
        "Quem tem cobertura de <b>Morte + Invalidez</b> tem o mesmo capital nas "
        "duas coberturas — não é metade para cada.",
    ),
    (
        ["sinistro", "o que e sinistro"],
        "Sinistro",
        "É <b>o acontecimento que aciona o seguro</b>: no nosso caso, o falecimento "
        "ou a invalidez do participante. Quando ocorre, abre-se um processo "
        "(protocolo <b>SIN-0000</b>), a documentação é analisada e, estando tudo "
        "certo, a indenização é liberada.",
    ),
    (
        ["dps", "declaracao de saude"],
        "DPS — Declaração Pessoal de Saúde",
        "É o <b>questionário de saúde</b> que a pessoa preenche ao contratar. "
        "Serve para a seguradora avaliar o risco. Se a DPS não vier assinada, a "
        "proposta fica <b>pendente</b> na esteira e não vira apólice.",
    ),
    (
        ["carencia"],
        "Carência",
        "É o <b>tempo de espera</b> entre contratar e o seguro passar a valer para "
        "determinada situação. Durante a carência, aquele risco específico ainda "
        "não está coberto.",
    ),
    (
        ["beneficiario", "quem recebe"],
        "Beneficiário",
        "É <b>quem recebe a indenização</b> quando o segurado falece. Pode ser "
        "indicado pelo próprio participante; se não houver indicação, segue-se a "
        "ordem prevista na lei.",
    ),
    (
        ["estipulante", "quem e o estipulante"],
        "Estipulante",
        "É <b>quem contrata o seguro em nome de um grupo</b>. Aqui, o "
        "<b>Sebrae Previdência</b>: ele representa os participantes junto à "
        "seguradora, acompanha a operação e recebe <b>10% do prêmio</b> como "
        "repasse. No sistema, é o perfil com acesso a tudo.",
    ),
    (
        ["corretora", "o que faz a corretora"],
        "Corretora",
        "É <b>quem intermedeia</b> entre o estipulante e a seguradora: envia a "
        "movimentação mensal, emite os boletos por convênio e cuida das propostas. "
        "Recebe <b>15% do prêmio</b>. No sistema, não tem acesso a Sinistros.",
    ),
    (
        ["seguradora", "icatu", "o que faz a seguradora"],
        "Seguradora",
        "É <b>quem assume o risco e paga a indenização</b> — aqui, a <b>ICATU</b>. "
        "Fica com <b>75% do prêmio</b>, que cobre o risco e a operação. No sistema, "
        "não tem acesso a Comissões nem a Inadimplência.",
    ),
    (
        ["subscricao", "esteira", "aceitacao", "como funciona a esteira"],
        "Esteira de subscrição",
        "É o <b>caminho que uma proposta percorre até virar apólice</b>:<br><br>"
        "<b>1. Proposta recebida</b> → chegou o pedido<br>"
        "<b>2. Em análise</b> → a seguradora avalia o risco (subscrição)<br>"
        "<b>3. Aceita</b> → aprovada, falta emitir a apólice<br>"
        "<b>4. Pendente</b> → falta documento, ou foi recusada<br><br>"
        "Uma proposta pode ser recusada por <b>risco agravado</b> — quando a "
        "análise indica risco acima do que a seguradora aceita.",
    ),
    (
        ["invalidez"],
        "Invalidez",
        "Cobertura que paga a indenização quando o participante fica "
        "<b>permanentemente incapaz de trabalhar</b>. Exige laudo médico. É uma "
        "das duas coberturas do ramo de risco, junto com Morte.",
    ),
    (
        ["competencia", "o que e competencia"],
        "Competência",
        "É o <b>mês de referência</b> dos dados de pagamento, no formato "
        "<b>MM/AAAA</b>. A movimentação de julho de 2026 tem competência "
        "<b>07/2026</b>. Cada planilha enviada substitui a competência inteira.",
    ),
    (
        ["convenio", "convenios", "fenacon", "opbb", "corecon", "fenasebrae"],
        "Convênios",
        "São as <b>entidades parceiras</b> cujos associados participam do seguro. "
        "Os boletos são emitidos separados por convênio. Na Central hoje: "
        "<b>FENACON</b>, <b>OPBB</b>, <b>CORECON</b> e <b>FenaSebrae</b>.",
    ),
    (
        ["regua de cobranca", "regua"],
        "Régua de cobrança",
        "É a <b>escada de ações conforme o atraso aumenta</b>:<br><br>"
        "<b>1 a 15 dias</b> → aviso amigável por e-mail<br>"
        "<b>16 a 45 dias</b> → notificação de pendência<br>"
        "<b>46 a 90 dias</b> → alerta de suspensão<br>"
        "<b>mais de 90 dias</b> → risco de cancelamento",
    ),
    (
        ["ramo", "ramos", "produtos", "modulo 101"],
        "Ramos e módulos",
        "<b>Ramo</b> é o tipo de seguro. A Central opera hoje o ramo de "
        "<b>risco (morte e invalidez)</b>, identificado como <b>módulo 101</b> na "
        "planilha. Auto, Viagem, Bike e Residencial estão no roadmap.<br><br>"
        "O <b>código sub</b> (01, 02, 03) separa subgrupos dentro do módulo.",
    ),
    (
        ["morte"],
        "Cobertura de Morte",
        "Paga a indenização aos <b>beneficiários</b> quando o participante falece. "
        "É a cobertura mais comum da carteira. Pode ser contratada sozinha ou "
        "junto com Invalidez.",
    ),
]


def _responder_glossario(titulo: str, explicacao: str):
    """Monta a resposta de um conceito. Devolve uma funcao, para a
    tabela de regras funcionar igual às outras."""

    def resposta(_db):
        return f"<b>{titulo}</b><br><br>{explicacao}"

    return resposta


# ===============================================================
# SOBRE O PROPRIO SISTEMA
# ===============================================================
def _como_enviar_planilha(_db) -> str:
    return (
        "Para <b>enviar a planilha de movimentação</b>:<br><br>"
        "1. abra o menu <b>Movimentação &amp; Pgto.</b><br>"
        "2. no primeiro painel, escolha o arquivo <b>.xlsx</b><br>"
        "3. clique em <b>Enviar e processar</b><br><br>"
        "A planilha <b>substitui a competência inteira</b>: ao enviar a base de "
        "08/2026, tudo que existia daquele mês é trocado. Por isso dá para "
        "reenviar uma planilha corrigida sem duplicar nada.<br><br>"
        "Se alguma linha tiver problema, eu aviso o <b>número da linha</b> e o "
        "banco nem chega a ser alterado."
    )


def _sobre_acesso(_db) -> str:
    return (
        "O acesso ao sistema funciona assim:<br><br>"
        "Cada <b>categoria</b> tem a sua senha — Estipulante, Corretora e "
        "Seguradora. Você escolhe a categoria, informa <b>seu e-mail</b> e a "
        "senha daquela categoria. O e-mail identifica quem entrou e fica "
        "registrado com data, hora e IP.<br><br>"
        "<b>O que cada categoria vê:</b>"
        "<table>"
        "<tr><th>Categoria</th><th>Não acessa</th></tr>"
        "<tr><td>Estipulante</td><td>— (vê tudo)</td></tr>"
        "<tr><td>Corretora</td><td>Sinistros</td></tr>"
        "<tr><td>Seguradora</td><td>Comissões e Inadimplência</td></tr>"
        "</table>"
        "O estipulante pode ainda restringir quais e-mails têm permissão de "
        "entrar, na tela <b>Controle de Acesso</b>."
    )


def _sobre_api(_db) -> str:
    return (
        "A <b>API da Central</b> permite que outros sistemas consultem e enviem "
        "dados sem ninguém digitar.<br><br>"
        "Já funcionam endereços para <b>apólices, movimentação, sinistros, "
        "comissões, inadimplência e indicadores</b>, além do envio de "
        "movimentação pela corretora.<br><br>"
        "A documentação completa fica em <b>/docs</b>, e todo pedido precisa "
        "enviar a chave de acesso no cabeçalho <code>X-API-Key</code>.<br><br>"
        "A conexão <i>com</i> ICATU, corretora e Trust Prev depende de esses "
        "sistemas liberarem credenciais e da homologação de segurança."
    )


def _sobre_central(_db) -> str:
    return (
        "A <b>Central Inteligente de Seguros</b> reúne em um só lugar a operação "
        "do seguro de risco (morte e invalidez) do Sebrae Previdência.<br><br>"
        "Antes, a informação ficava espalhada entre planilhas, e-mails e os "
        "sistemas da corretora e da seguradora. A Central junta tudo: "
        "<b>carteira de apólices, esteira de propostas, movimentação e "
        "pagamentos, comissões, inadimplência, sinistros e pendências</b>.<br><br>"
        "Ela conecta os <b>três lados</b> da operação:<br>"
        "🏢 <b>Estipulante</b> (Sebrae Previdência) — representa os participantes<br>"
        "🤝 <b>Corretora</b> — intermedeia e opera a movimentação<br>"
        "🛡️ <b>Seguradora</b> (ICATU) — assume o risco e paga as indenizações"
    )


# ===============================================================
# A TABELA DE REGRAS
# ===============================================================
# A ordem importa: a PRIMEIRA regra que combinar e a que responde.
# Por isso a conversa vem antes dos dados, e os conceitos vem depois —
# assim "o que e apolice?" cai no glossario, e "quantas apolices temos?"
# cai na consulta ao banco.

REGRAS_CONVERSA = [
    (["ola", "oi ", "oi!", "oi?", "bom dia", "boa tarde", "boa noite",
      "tudo bem", "tudo bom", "como vai", "e ai", "hey", "hello"], _cumprimento),
    (["quem e voce", "quem es voce", "o que voce e", "voce e um robo",
      "voce e uma ia", "se apresente", "qual seu nome", "quem voce e"], _apresentacao),
    (["obrigad", "valeu", "agradec", "muito bom", "otimo trabalho"], _agradecimento),
    (["tchau", "ate logo", "ate mais", "adeus", "falou"], _despedida),
    (["ajuda", "o que voce sabe", "o que voce faz", "o que posso perguntar",
      "me ajuda", "socorro", "opcoes"], _ajuda),
]

REGRAS_SISTEMA = [
    (["enviar planilha", "mandar planilha", "subir planilha", "upload",
      "importar planilha", "como envio"], _como_enviar_planilha),
    (["acesso", "login", "entrar no sistema", "senha", "permissao",
      "quem pode ver", "perfil"], _sobre_acesso),
    (["api", "integracao", "integrar", "conectar sistema"], _sobre_api),
    (["central", "o que e a central", "sobre o sistema", "para que serve",
      "objetivo", "como funciona o sistema"], _sobre_central),
]

REGRAS_DADOS = [
    (["vence", "vencem", "renova", "renovacao", "renovacoes"], _renovacoes),
    (["capital total", "capital segurado total", "quanto vale a carteira",
      "soma do capital"], _capital),
    (["sinistro", "obito", "falecimento"], _sinistros),
    (["inadimpl", "atraso", "atrasado", "devendo", "cobranca", "devedor"], _inadimplencia),
    (["comissao", "comissoes", "repasse", "premio arrecadado"], _comissoes),
    (["pendencia", "pendencias", "faltando", "em aberto"], _pendencias),
    (["pagamento", "movimentacao", "pagou", "a pagar", "segurados"], _pagamentos),
    (["esteira", "proposta", "propostas", "subscricao"], _esteira),
    (["quantas apolices", "apolices", "carteira", "capital"], _apolices_carteira),
]

# O glossario e montado a partir da lista GLOSSARIO, para nao repetirmos
# codigo. Cada conceito vira uma regra igual as outras.
REGRAS_CONCEITOS = [
    (palavras, _responder_glossario(titulo, explicacao))
    for palavras, titulo, explicacao in GLOSSARIO
]

# ---------------------------------------------------------------
# CONCEITO OU CONSULTA?
# ---------------------------------------------------------------
# A palavra "apolice" aparece em duas perguntas bem diferentes:
#
#   "o que e uma apolice?"        -> quer a EXPLICACAO (glossario)
#   "quais apolices vencem?"      -> quer os DADOS (banco)
#
# Para escolher certo, olhamos se a pergunta pede uma definicao.
# Se pedir, o glossario responde primeiro. Se nao, o banco responde
# primeiro. E a mesma coisa que uma pessoa faria ao ouvir a pergunta.
PALAVRAS_DE_DEFINICAO = [
    "o que e", "o que sao", "que e um", "que e uma", "que significa",
    "significa", "explica", "explique", "explicar", "defina", "definicao",
    "conceito", "me fala sobre", "me diga o que", "quem e o", "quem e a",
    "o que faz", "para que serve", "como funciona a esteira",
]


def _quer_uma_definicao(texto: str) -> bool:
    """A pergunta está pedindo uma explicação, e não números?"""
    return _alguma(texto, PALAVRAS_DE_DEFINICAO)


# ===============================================================
# ASSUNTOS QUE NAO SAO DA CENTRAL
# ===============================================================
# Quando a pergunta cai claramente fora do assunto, respondemos algo
# especifico em vez do texto generico de "nao entendi". Fica mais
# educado e deixa claro qual e o limite do assistente.
FORA_DO_ASSUNTO = [
    (["que horas", "que dia e hoje", "hora certa", "data de hoje"],
     "o horário ou a data"),
    # Cuidado: NAO colocar so "tempo" aqui. Existe "tempo médio de
    # análise" na nossa operação, e a pergunta seria recusada por engano.
    (["chuva", "chove", "chover", "chovendo", "clima", "temperatura",
      "previsao do tempo", "tempo hoje", "tempo amanha", "faz sol"],
     "previsão do tempo"),
    (["receita", "comida", "bolo", "cozinhar", "almoco", "jantar"],
     "receitas e culinária"),
    (["futebol", "jogo", "campeonato", "time", "placar", "copa"],
     "esportes"),
    (["piada", "conta uma piada", "me faz rir", "engracad"],
     "piadas"),
    (["politica", "eleicao", "presidente", "governo", "votar"],
     "política"),
    (["musica", "filme", "serie", "netflix", "cantor", "banda"],
     "entretenimento"),
    (["dolar", "bitcoin", "bolsa de valores", "acoes da", "investimento em",
      "cripto"], "investimentos e mercado financeiro"),
    (["quanto e", "calcul", "raiz quadrada", "multiplic", "dividir por"],
     "contas de matemática"),
    (["traduz", "traducao", "em ingles", "em espanhol"],
     "traduções"),
    (["remedio", "sintoma", "tratamento", "dor de", "dor no", "dor na",
      "estou doente", "o que tomo", "o que tomar", "receita medica"],
     "orientação médica"),
    (["advogado", "processo judicial", "acao na justica", "juridico"],
     "orientação jurídica"),
]


def _recusar(assunto: str) -> str:
    """Resposta educada para o que esta fora do escopo."""
    return (
        f"Desculpe, não posso responder sobre <b>{assunto}</b>. 🙏<br><br>"
        "Sou o assistente da <b>Central Inteligente de Seguros</b> e só trato de "
        "assuntos ligados à operação do seguro: apólices, renovações, sinistros, "
        "comissões, inadimplência, pagamentos, propostas e os conceitos do ramo."
        "<br><br>Digite <b>ajuda</b> para ver tudo que eu sei responder."
    )


SUGESTOES = [
    "Olá, tudo bem?",
    "O que você faz?",
    "Quais apólices vencem este mês?",
    "O que é capital segurado?",
    "Quem está inadimplente?",
    "Como envio a planilha?",
]

RESPOSTA_PADRAO = (
    "Não consegui entender a pergunta. 🤔<br><br>"
    "Sou o assistente da <b>Central Inteligente de Seguros</b>. Posso consultar "
    "<b>apólices, renovações, sinistros, inadimplência, comissões, pendências, "
    "pagamentos e propostas</b>, e também explicar os <b>termos do seguro</b> "
    "(apólice, prêmio, capital segurado, DPS, carência…).<br><br>"
    "Tente reformular, ou digite <b>ajuda</b> para ver a lista completa."
)


def responder(db, pergunta: str) -> str:
    """
    Recebe a pergunta e devolve a resposta em HTML.

    Esta e a unica funcao que o main.py precisa chamar.

    A ordem da conferencia:
      1. a pergunta esta vazia?
      2. e um assunto que claramente nao e nosso? -> recusa educada
      3. combina com alguma regra? -> responde
      4. nenhuma das anteriores -> diz o que sabe fazer
    """
    if not pergunta or not pergunta.strip():
        return "Digite uma pergunta para eu poder ajudar. 🙂"

    # Espacos nas pontas ajudam a encontrar palavras no comeco e no fim.
    texto = " " + _sem_acento(pergunta).strip() + " "

    # 2. Fora do assunto — conferido ANTES das regras.
    for palavras, assunto in FORA_DO_ASSUNTO:
        if _alguma(texto, palavras):
            # Excecao: se a pergunta TAMBEM fala de algo nosso, ela e
            # nossa. "quanto e a comissao?" tem "quanto e", mas e sobre
            # comissao — entao deixamos as regras normais responderem.
            if not _fala_de_seguros(texto):
                return _recusar(assunto)

    # 3. As regras, na ordem certa.
    #    Conversa e sistema vem sempre primeiro. Depois, o glossario e o
    #    banco trocam de lugar conforme o tipo da pergunta.
    if _quer_uma_definicao(texto):
        ordem = REGRAS_CONVERSA + REGRAS_SISTEMA + REGRAS_CONCEITOS + REGRAS_DADOS
    else:
        ordem = REGRAS_CONVERSA + REGRAS_SISTEMA + REGRAS_DADOS + REGRAS_CONCEITOS

    for palavras_chave, funcao in ordem:
        if _alguma(texto, palavras_chave):
            return funcao(db)

    # 4. Nao reconheceu
    return RESPOSTA_PADRAO


# Palavras que provam que a pergunta e do nosso mundo, mesmo que ela
# contenha alguma expressao da lista de fora-do-assunto.
PALAVRAS_DO_NEGOCIO = [
    "apolice", "apolices", "seguro", "segurado", "premio", "capital",
    "sinistro", "cobertura", "carteira", "comissao", "comissoes",
    "inadimpl", "boleto", "convenio", "participante", "beneficiario",
    "corretora", "seguradora", "estipulante", "proposta", "esteira",
    "movimentacao", "competencia", "renovacao", "pendencia", "invalidez",
    "dps", "carencia", "vidas", "central", "planilha", "morte",
    "analise", "subscricao", "matricula", "indenizacao", "vigencia",
]


def _fala_de_seguros(texto: str) -> bool:
    """A pergunta menciona algo do nosso negócio?"""
    return _alguma(texto, PALAVRAS_DO_NEGOCIO)
