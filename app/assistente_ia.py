"""
assistente_ia.py
----------------
O assistente com INTELIGENCIA ARTIFICIAL de verdade.

COMO FUNCIONA, EM UMA FRASE
---------------------------
A pergunta da pessoa e enviada ao Claude (o modelo de IA da Anthropic).
O Claude nao sabe nada da nossa carteira — entao damos a ele um conjunto
de FERRAMENTAS que consultam o nosso banco. Ele decide sozinho quais usar,
le o resultado e escreve a resposta em portugues.

A DIFERENCA PARA O assistente.py
--------------------------------
    assistente.py    -> regras de palavras-chave. Rapido, gratuito, mas
                        so entende o que foi previsto.
    assistente_ia.py -> IA de verdade. Entende qualquer jeito de perguntar,
                        conversa, faz contas, compara. Mas precisa de uma
                        chave paga da Anthropic.

Se nao houver chave configurada, o sistema usa o assistente.py sozinho.
Ninguem fica sem resposta.

PARA LIGAR
----------
1. crie uma chave em https://console.anthropic.com
2. coloque no arquivo .env:      ANTHROPIC_API_KEY=sk-ant-...
3. reinicie o servidor

CUSTO
-----
Cada pergunta custa fracoes de centavo. O modelo usado (Claude Opus 5)
cobra por quantidade de texto processado. Para uso interno de uma equipe
pequena, o gasto mensal e baixo — mas confira os precos atuais no site
da Anthropic, porque eles mudam.
"""

import json
from datetime import date

from sqlalchemy import func

from app import config
from app.database import SessionLocal
from app.models import (
    Claim,
    Commission,
    Delinquency,
    Payment,
    Pendency,
    Policy,
    Proposal,
)

# O modelo de IA usado. Opus 5 e o mais capaz da Anthropic.
MODELO = "claude-opus-5"

# Quantas mensagens antigas da conversa mandamos junto. Mais historia =
# a IA lembra melhor do contexto, mas cada pergunta fica mais cara.
LIMITE_DE_HISTORICO = 12

# Teto de texto na resposta. Respostas de chat sao curtas; este valor
# tambem cobre o "raciocinio" interno do modelo.
MAX_TOKENS = 8000


# ===============================================================
# AS FERRAMENTAS QUE A IA PODE USAR
# ===============================================================
# Cada funcao abaixo consulta o nosso banco e devolve o resultado em
# JSON. A IA le a descricao (o texto entre aspas triplas), decide se
# precisa daquilo, chama, e usa o resultado para responder.
#
# IMPORTANTE: a IA SO conhece os dados que estas funcoes devolvem.
# Ela nao tem acesso direto ao banco e nao consegue apagar nem alterar
# nada — todas as ferramentas apenas LEEM.


def _abrir_banco():
    """Abre uma conexao com o banco. Cada ferramenta fecha a sua."""
    return SessionLocal()


def _json(dados) -> str:
    """Converte para JSON, sem transformar acentos em codigos estranhos."""
    return json.dumps(dados, ensure_ascii=False, default=str)


def resumo_da_carteira() -> str:
    """Números gerais da carteira de seguros: total de apólices por status,
    capital segurado, prêmio mensal, e a contagem de sinistros, propostas,
    inadimplentes e pendências. Use para perguntas panorâmicas.
    """
    db = _abrir_banco()
    try:
        por_status = dict(
            db.query(Policy.status, func.count(Policy.id))
            .group_by(Policy.status)
            .all()
        )
        capital = db.query(func.sum(Policy.capital_total)).filter(
            Policy.status == "Ativa"
        ).scalar() or 0
        premio = db.query(func.sum(Policy.premio_mensal)).filter(
            Policy.status == "Ativa"
        ).scalar() or 0

        return _json({
            "data_de_hoje": date.today().isoformat(),
            "apolices_por_status": por_status,
            "apolices_total": sum(por_status.values()),
            "capital_segurado_ativas_reais": round(capital, 2),
            "premio_mensal_ativas_reais": round(premio, 2),
            "sinistros_em_andamento": db.query(Claim).count(),
            "propostas_na_esteira": db.query(Proposal).count(),
            "participantes_inadimplentes": db.query(Delinquency).count(),
            "pendencias_abertas": db.query(Pendency).filter(
                Pendency.resolvida.is_(False)
            ).count(),
        })
    finally:
        db.close()


def buscar_apolices(
    status: str = "",
    participante: str = "",
    vencendo_em_dias: int = 0,
    capital_minimo: float = 0,
    limite: int = 20,
) -> str:
    """Busca apólices na carteira com filtros.

    Args:
        status: filtra por situação. Valores: Ativa, A renovar, Vencida, Cancelada. Vazio = todas.
        participante: parte do nome do participante. Vazio = todos.
        vencendo_em_dias: só as que vencem nos próximos N dias. 0 = sem filtro.
        capital_minimo: só as com capital segurado igual ou acima deste valor. 0 = sem filtro.
        limite: quantas trazer, no máximo. Padrão 20, máximo 100.
    """
    db = _abrir_banco()
    try:
        consulta = db.query(Policy)

        if status:
            consulta = consulta.filter(Policy.status == status)
        if participante:
            consulta = consulta.filter(Policy.participante.ilike(f"%{participante}%"))
        if capital_minimo > 0:
            consulta = consulta.filter(Policy.capital_total >= capital_minimo)
        if vencendo_em_dias > 0:
            from datetime import timedelta
            limite_data = date.today() + timedelta(days=vencendo_em_dias)
            consulta = consulta.filter(
                Policy.data_vencimento >= date.today(),
                Policy.data_vencimento <= limite_data,
            )

        total = consulta.count()
        limite = max(1, min(limite, 100))
        registros = consulta.order_by(Policy.data_vencimento).limit(limite).all()

        return _json({
            "encontradas": total,
            "mostrando": len(registros),
            "apolices": [
                {
                    "numero": p.numero_apolice,
                    "participante": p.participante,
                    "cobertura": p.cobertura,
                    "capital_segurado": p.capital_total,
                    "premio_mensal": p.premio_mensal,
                    "inicio": p.data_inicio.isoformat(),
                    "vencimento": p.data_vencimento.isoformat(),
                    "dias_para_vencer": p.dias_para_vencer(),
                    "status": p.status,
                }
                for p in registros
            ],
        })
    finally:
        db.close()


def listar_sinistros() -> str:
    """Todos os sinistros em andamento, com protocolo, participante, tipo
    (Morte ou Invalidez), data de abertura, dias em aberto, situação da
    documentação e status do processo.
    """
    db = _abrir_banco()
    try:
        registros = db.query(Claim).order_by(Claim.data_abertura).all()
        return _json({
            "total": len(registros),
            "sinistros": [
                {
                    "protocolo": c.protocolo,
                    "participante": c.participante,
                    "tipo": c.tipo,
                    "aberto_em": c.data_abertura.isoformat(),
                    "dias_em_aberto": c.dias_em_aberto(),
                    "documentacao": c.documentacao,
                    "documentacao_completa": c.documentacao_ok,
                    "status": c.status,
                }
                for c in registros
            ],
        })
    finally:
        db.close()


def listar_inadimplentes() -> str:
    """Participantes em atraso com o pagamento, com valor devido, dias de
    atraso, a faixa da régua de cobrança e se a cobrança já foi enviada.
    """
    db = _abrir_banco()
    try:
        registros = db.query(Delinquency).order_by(
            Delinquency.dias_atraso.desc()
        ).all()
        return _json({
            "total": len(registros),
            "valor_total_em_atraso": round(sum(d.valor for d in registros), 2),
            "inadimplentes": [
                {
                    "participante": d.participante,
                    "apolice": d.numero_apolice,
                    "cobertura": d.cobertura,
                    "valor": d.valor,
                    "dias_atraso": d.dias_atraso,
                    "faixa": d.faixa(),
                    "cobranca_enviada": d.cobranca_enviada,
                }
                for d in registros
            ],
        })
    finally:
        db.close()


def listar_comissoes(competencia: str = "") -> str:
    """Divisão do prêmio arrecadado entre estipulante (10%), corretora (15%)
    e seguradora (75%).

    Args:
        competencia: mês no formato MM/AAAA, por exemplo 07/2026. Vazio = todos os meses.
    """
    db = _abrir_banco()
    try:
        consulta = db.query(Commission)
        if competencia:
            consulta = consulta.filter(Commission.competencia == competencia)
        registros = consulta.order_by(Commission.competencia.desc()).all()

        return _json({
            "total": len(registros),
            "comissoes": [
                {
                    "competencia": c.competencia,
                    "agente": c.papel,
                    "quem_recebe": c.quem,
                    "premio_total_do_mes": c.premio_total,
                    "percentual": c.percentual,
                    "valor": c.valor,
                }
                for c in registros
            ],
        })
    finally:
        db.close()


def listar_pagamentos(competencia: str = "") -> str:
    """Movimentação mensal: os segurados da base, com capital, prêmio e a
    situação do pagamento (Pago, A pagar ou Em atraso).

    Args:
        competencia: mês no formato MM/AAAA. Vazio = a competência mais recente.
    """
    db = _abrir_banco()
    try:
        if not competencia:
            todas = [c[0] for c in db.query(Payment.competencia).distinct().all()]
            if not todas:
                return _json({"total": 0, "pagamentos": []})
            # ordena por ano-mes para achar a mais recente
            competencia = sorted(
                todas, key=lambda c: (c.split("/")[1], c.split("/")[0]), reverse=True
            )[0]

        registros = (
            db.query(Payment)
            .filter(Payment.competencia == competencia)
            .order_by(Payment.matricula)
            .all()
        )

        contagem = {}
        for p in registros:
            contagem[p.status] = contagem.get(p.status, 0) + 1

        return _json({
            "competencia": competencia,
            "total": len(registros),
            "premio_total": round(sum(p.premio for p in registros), 2),
            "por_situacao": contagem,
            "pagamentos": [
                {
                    "matricula": p.matricula,
                    "segurado": p.segurado,
                    "capital_morte": p.capital_morte,
                    "capital_invalidez": p.capital_invalidez,
                    "premio": p.premio,
                    "situacao": p.status,
                }
                for p in registros
            ],
        })
    finally:
        db.close()


def listar_pendencias() -> str:
    """Pendências do sistema: o que falta resolver, com prioridade,
    responsável, prazo e se o documento está faltando.
    """
    db = _abrir_banco()
    try:
        registros = db.query(Pendency).all()
        registros.sort(key=lambda p: (p.resolvida, p.peso_prioridade()))
        return _json({
            "total": len(registros),
            "abertas": sum(1 for p in registros if not p.resolvida),
            "pendencias": [
                {
                    "prioridade": p.prioridade,
                    "titulo": p.titulo,
                    "referente_a": p.referente,
                    "responsavel": p.responsavel,
                    "prazo": p.prazo.isoformat() if p.prazo else None,
                    "documento": p.documento,
                    "documento_ok": p.documento_ok,
                    "resolvida": p.resolvida,
                }
                for p in registros
            ],
        })
    finally:
        db.close()


def listar_propostas() -> str:
    """Propostas na esteira de aceitação, com o número, participante,
    cobertura, capital, em que etapa está (recebida, analise, aceita,
    pendente) e se foi recusada.
    """
    db = _abrir_banco()
    try:
        registros = db.query(Proposal).order_by(Proposal.numero).all()
        return _json({
            "total": len(registros),
            "propostas": [
                {
                    "numero": p.numero,
                    "participante": p.participante,
                    "cobertura": p.cobertura,
                    "capital": p.capital,
                    "etapa": p.etapa,
                    "observacao": p.observacao,
                    "recusada": p.recusada,
                }
                for p in registros
            ],
        })
    finally:
        db.close()


# A lista das ferramentas, na ordem em que a IA as ve.
FERRAMENTAS = [
    resumo_da_carteira,
    buscar_apolices,
    listar_sinistros,
    listar_inadimplentes,
    listar_comissoes,
    listar_pagamentos,
    listar_pendencias,
    listar_propostas,
]


# ===============================================================
# AS INSTRUCOES DA IA (o "system prompt")
# ===============================================================
# E aqui que dizemos a IA quem ela e, o que pode fazer e o que nao deve
# fazer. Este texto e a peca mais importante do arquivo: mudar ele muda
# o comportamento do assistente inteiro.
INSTRUCOES = """\
Você é o assistente da Central Inteligente de Seguros, o sistema que o \
Sebrae Previdência usa para administrar o seguro de risco (morte e \
invalidez) em conjunto com a corretora e a seguradora ICATU.

QUEM É QUEM NA OPERAÇÃO
- Estipulante (Sebrae Previdência): contrata o seguro em nome do grupo e \
representa os participantes. Recebe 10% do prêmio.
- Corretora: intermedeia, envia a movimentação mensal e emite os boletos \
por convênio. Recebe 15%.
- Seguradora (ICATU): assume o risco e paga as indenizações. Fica com 75%.

SEU ESCOPO
Você responde sobre a operação de seguros desta Central: apólices, \
renovações, capital segurado, prêmios, sinistros, inadimplência, \
comissões, pagamentos, propostas, pendências, convênios e os conceitos \
do ramo (o que é apólice, DPS, carência, subscrição, beneficiário...). \
Também explica como o próprio sistema funciona.

Se perguntarem algo claramente fora disso — horário, previsão do tempo, \
receitas, esportes, política, piadas, tradução, orientação médica ou \
jurídica, matemática sem relação com a carteira — recuse com educação em \
uma ou duas frases, diga que você é o assistente da Central e ofereça os \
assuntos que domina. Não invente, não improvise fora do escopo.

COMO USAR OS DADOS
Você tem ferramentas que consultam o banco de dados real da Central. \
SEMPRE use as ferramentas antes de afirmar qualquer número. Nunca invente \
valores, nomes ou datas. Se uma ferramenta devolver lista vazia, diga que \
não há registros — não preencha com exemplos.
Para perguntas conceituais ("o que é prêmio?") responda direto, sem \
ferramenta.

COMO ESCREVER
- Sempre em português do Brasil, tratando a pessoa por você.
- Tom profissional e acolhedor, como um colega experiente do setor.
- Direto ao ponto. Duas a cinco frases na maioria das respostas.
- Valores em reais no padrão brasileiro: R$ 1.234,56. Datas em dd/mm/aaaa.
- Formate em HTML simples, porque a resposta aparece dentro de um balão \
de conversa: use <b> para destacar, <br> para quebrar linha, e <table> \
com <tr>/<th>/<td> quando listar mais de três itens. Não use markdown, \
não use ``` e não use <html>, <head> ou <body>.
- Se a pergunta for ambígua, pergunte o que faltou em vez de adivinhar.
- Cumprimentos e agradecimentos: responda de forma breve e simpática.

Todos os dados desta Central são de uso interno. Não repita CPFs \
completos em respostas a menos que a pessoa peça explicitamente por um \
participante específico.
"""


# ===============================================================
# A CONVERSA
# ===============================================================
def esta_disponivel() -> bool:
    """A IA está configurada e pronta para uso?"""
    return bool(config.ANTHROPIC_API_KEY)


def _cliente():
    """
    Cria o cliente da Anthropic.

    O import fica DENTRO da funcao de proposito: se a biblioteca nao
    estiver instalada, o sistema inteiro nao quebra — so a IA fica
    indisponivel e o assistente por regras assume.
    """
    import anthropic

    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def responder(pergunta: str, historico: list[dict] | None = None) -> tuple[str, str]:
    """
    Envia a pergunta para a IA e devolve a resposta.

    Args:
        pergunta: o que a pessoa digitou.
        historico: as mensagens anteriores da conversa, no formato
                   [{"role": "user"|"assistant", "content": "..."}].

    Devolve DOIS valores:
        - a resposta em HTML
        - o motivo do erro (vazio se deu tudo certo)

    Quando algo falha, quem chama decide o que fazer — no nosso caso,
    o main.py cai para o assistente por regras.
    """
    from anthropic import beta_tool

    cliente = _cliente()

    # Monta a conversa: o historico recente + a pergunta nova.
    mensagens = list(historico or [])[-LIMITE_DE_HISTORICO:]
    mensagens.append({"role": "user", "content": pergunta})

    # O beta_tool transforma cada funcao Python numa ferramenta que a IA
    # entende. Ele le o nome, os parametros e o texto da documentacao.
    ferramentas = [beta_tool(f) for f in FERRAMENTAS]

    try:
        # O tool_runner cuida do vai-e-vem sozinho: a IA pede uma
        # ferramenta, ele executa, devolve o resultado e continua ate a
        # IA ter a resposta final.
        runner = cliente.beta.messages.tool_runner(
            model=MODELO,
            max_tokens=MAX_TOKENS,
            system=INSTRUCOES,
            tools=ferramentas,
            messages=mensagens,
            thinking={"type": "adaptive"},
            output_config={"effort": config.IA_ESFORCO},
        )

        ultima = None
        for mensagem in runner:
            ultima = mensagem

        if ultima is None:
            return "", "a IA nao devolveu resposta"

        # Se a IA recusou por politica de seguranca, avisamos.
        if ultima.stop_reason == "refusal":
            return (
                "Não consigo responder a esta pergunta. Posso ajudar com "
                "assuntos da operação de seguros da Central.",
                "",
            )

        texto = "".join(
            bloco.text for bloco in ultima.content if bloco.type == "text"
        ).strip()

        if not texto:
            return "", "a IA devolveu uma resposta vazia"

        return texto, ""

    except Exception as erro:
        # Qualquer problema (chave invalida, sem internet, limite de uso)
        # vira um motivo em texto. O main.py usa isso para decidir.
        return "", f"{type(erro).__name__}: {erro}"
