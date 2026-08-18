"""
seed.py
-------
"Seed" quer dizer SEMENTE: este arquivo planta os dados iniciais no banco.

O que ele faz, na ordem:
  1. cria as tabelas (users, login_history, policies)
  2. APAGA os dados que existiam
  3. cria os 3 usuarios ficticios
  4. cria 50 apolices ficticias
  5. gera o arquivo sql/banco.sql para outro dev recriar tudo igual

COMO RODAR (com o venv ativado, na raiz do projeto):
    python -m app.seed

Pode rodar quantas vezes quiser: ele sempre limpa e refaz do zero.
"""

import random
import sqlite3
from datetime import date, datetime, timedelta

from app import config
from app.auth import gerar_hash
from app.database import ARQUIVO_BANCO, PASTA_RAIZ, SessionLocal, criar_tabelas
from app.models import (
    PERFIL_CORRETORA,
    PERFIL_ESTIPULANTE,
    PERFIL_SEGURADORA,
    Agreement,
    Claim,
    Commission,
    Delinquency,
    Invoice,
    LoginHistory,
    Payment,
    Pendency,
    Policy,
    Proposal,
    User,
)

# Onde o script SQL sera gravado.
ARQUIVO_SQL = PASTA_RAIZ / "sql" / "banco.sql"

# Semente do sorteio. Com um numero fixo, o "random" sorteia SEMPRE a mesma
# sequencia. Assim voce e seu colega geram exatamente as mesmas apolices.
sorteio = random.Random(2026)

# Quantas apolices no total.
TOTAL_APOLICES = 50

# Relacao aproximada entre premio mensal e capital, tirada da planilha
# Base_Segurados_Central.xlsx (ex.: R$ 60,70 de premio para R$ 150.000).
FATOR_PREMIO = 0.000405

# A partir de quantos dias antes do vencimento a apolice entra em "A renovar".
# 30 dias = "vence no proximo mes", que e a regra que o prototipo usa quando
# o assistente responde "quais apolices vencem este mes?".
DIAS_PARA_RENOVAR = 30


# ===============================================================
# FUNCOES DE APOIO
# ===============================================================
def calcular_status(vencimento: date, hoje: date) -> str:
    """
    Descobre o status da apolice olhando a data de vencimento.

      ja venceu              -> "Vencida"
      vence em ate 30 dias   -> "A renovar"
      vence depois disso     -> "Ativa"
    """
    dias = (vencimento - hoje).days
    if dias < 0:
        return "Vencida"
    if dias <= DIAS_PARA_RENOVAR:
        return "A renovar"
    return "Ativa"


def separar_capitais(cobertura: str, capital: float) -> tuple[float, float]:
    """
    Distribui o capital entre morte e invalidez conforme a cobertura.

    Na planilha do projeto, quem tem as duas coberturas tem o MESMO valor
    nas duas (nao e metade para cada). Seguimos essa mesma regra.
    """
    if cobertura == "Morte":
        return capital, 0.0
    if cobertura == "Invalidez":
        return 0.0, capital
    return capital, capital  # "Morte + Invalidez"


def calcular_premio(capital: float) -> float:
    """Calcula o premio mensal a partir do capital segurado."""
    return round(capital * FATOR_PREMIO, 2)


def gerar_cpf_ficticio() -> str:
    """
    Monta um CPF no formato 000.000.000-00.

    ATENCAO: e apenas um numero com a APARENCIA de CPF. Nao passa na
    validacao oficial e nao pertence a ninguem. Dados reais nunca entram
    neste projeto.
    """
    n = [sorteio.randint(0, 9) for _ in range(11)]
    return f"{n[0]}{n[1]}{n[2]}.{n[3]}{n[4]}{n[5]}.{n[6]}{n[7]}{n[8]}-{n[9]}{n[10]}"


# ===============================================================
# ETAPA 3: OS 3 USUARIOS FICTICIOS
# ===============================================================
def criar_usuarios(db) -> None:
    """Cria um usuario para cada perfil de acesso."""
    usuarios = [
        User(
            nome="Luciana Ferraz",
            email="estipulante@sebraeprev.com.br",
            senha_hash=gerar_hash(config.SENHA_ESTIPULANTE),
            perfil=PERFIL_ESTIPULANTE,
        ),
        User(
            nome="Corretora Parceira",
            email="corretora@sebraeprev.com.br",
            senha_hash=gerar_hash(config.SENHA_CORRETORA),
            perfil=PERFIL_CORRETORA,
        ),
        User(
            nome="Seguradora ICATU",
            email="seguradora@sebraeprev.com.br",
            senha_hash=gerar_hash(config.SENHA_SEGURADORA),
            perfil=PERFIL_SEGURADORA,
        ),
    ]

    db.add_all(usuarios)
    db.commit()
    print(f"  {len(usuarios)} usuarios criados.")


# ===============================================================
# ETAPA 4: AS 50 APOLICES
# ===============================================================

# --- Grupo 1: as 8 apolices que aparecem na tela do prototipo -----------
# Numero, nome, cobertura e capital foram copiados exatamente do arquivo
# prototipo/Portal_Central_Inteligente_Seguros.html.
#
# POR QUE AS DATAS VIRARAM "DIAS"?
# O prototipo foi desenhado em 21/07/2026. Se copiassemos as datas dele ao
# pe da letra, hoje quase todas apareceriam como "Vencida" e a tela ficaria
# diferente do prototipo — e pior a cada mes que passasse.
#
# Entao guardamos "faltam X dias para vencer", contados a partir do dia em
# que voce roda o seed. Assim a carteira mostra sempre os mesmos status do
# prototipo, hoje e daqui a um ano.
#
# Os X foram tirados do proprio prototipo (ex.: a AP-2041 vencia "em 7 dias")
# e todos receberam o mesmo empurrao de +4 dias, para a AP-2033 ficar acima
# dos 30 dias e continuar "Ativa" como na tela original. O espacamento entre
# as apolices e a ordem de vencimento foram preservados.
APOLICES_DO_PROTOTIPO = [
    # (numero,   participante,       cobertura,          capital, dias_p/_vencer, duracao)  status no prototipo
    ("AP-2041", "Marcos A. Ribeiro", "Morte + Invalidez", 250000, 11, 365),   # A renovar
    ("AP-1899", "Sonia R. Batista", "Invalidez", 100000, 13, 365),            # A renovar
    ("AP-1987", "Fernanda C. Lima", "Morte", 180000, 17, 365),                # A renovar
    ("AP-2115", "Joao P. Andrade", "Invalidez", 120000, 25, 730),             # A renovar
    ("AP-2033", "Claudia M. Souza", "Morte + Invalidez", 300000, 33, 365),    # Ativa
    ("AP-1954", "Roberto Nunes", "Morte", 200000, 203, 365),                  # Ativa
    ("AP-2087", "Patricia Gomes", "Morte + Invalidez", 350000, 248, 365),     # Ativa
    ("AP-2160", "Eduardo Tavares", "Morte", 150000, 332, 365),                # Ativa
]

# --- Grupo 2: os 10 segurados da planilha Base_Segurados_Central.xlsx ----
SEGURADOS_DA_PLANILHA = [
    # (nome, matricula, cpf, nascimento, cap_morte, cap_invalidez, premio, sub)
    ("Ana Beatriz Souza", "100001", "384.517.920-41", "15/03/1986", 150000, 150000, 60.70, "01"),
    ("Carlos Henrique Lima", "100002", "617.283.945-08", "22/11/1981", 200000, 200000, 81.10, "01"),
    ("Fernanda Alves Rocha", "100003", "275.619.438-70", "08/07/1990", 120000, 120000, 50.10, "02"),
    ("Gustavo Pereira Martins", "100004", "948.160.372-59", "30/01/1978", 250000, 250000, 102.00, "02"),
    ("Juliana Cristina Moraes", "100005", "503.847.126-91", "19/05/1993", 180000, 180000, 69.60, "01"),
    ("Marcelo Augusto Nunes", "100006", "861.395.704-22", "11/12/1984", 100000, 100000, 42.30, "03"),
    ("Patricia Oliveira Costa", "100007", "429.851.630-17", "03/09/1988", 220000, 220000, 88.70, "01"),
    ("Ricardo Mendes Ferreira", "100008", "796.214.853-64", "27/02/1975", 300000, 300000, 122.00, "02"),
    ("Simone Aparecida Lopes", "100009", "154.762.398-53", "10/10/1992", 160000, 160000, 64.70, "03"),
    ("Thiago Rodrigues Barros", "100010", "682.940.517-85", "05/06/1980", 140000, 140000, 56.90, "01"),
]

# --- Grupo 3: pecas para montar as 32 apolices restantes -----------------
PRIMEIROS_NOMES = [
    "Adriana", "Bruno", "Camila", "Daniel", "Elaine", "Fabio", "Giovana",
    "Heitor", "Isabela", "Jonas", "Karina", "Leandro", "Mariana", "Nelson",
    "Otavio", "Priscila", "Rafael", "Sabrina", "Tiago", "Vanessa",
    "Wagner", "Yasmin", "Alexandre", "Beatriz", "Cristiano", "Debora",
    "Emerson", "Flavia", "Gilberto", "Helena", "Igor", "Juliano",
]

SOBRENOMES = [
    "Almeida", "Barbosa", "Carvalho", "Dias", "Esteves", "Freitas",
    "Guimaraes", "Henriques", "Ismael", "Jardim", "Klein", "Lacerda",
    "Machado", "Neves", "Oliveira", "Pacheco", "Queiroz", "Ramos",
    "Siqueira", "Teixeira",
]

COBERTURAS = ["Morte", "Invalidez", "Morte + Invalidez"]

# Capitais possiveis, na mesma faixa dos dados reais do projeto.
CAPITAIS = [80000, 100000, 120000, 150000, 180000, 200000, 220000, 250000, 300000, 350000, 400000]


def texto_para_data(texto: str) -> date:
    """Converte '28/07/2025' em uma data de verdade que o banco entende."""
    return datetime.strptime(texto, "%d/%m/%Y").date()


def montar_apolices(hoje: date) -> list[Policy]:
    """Monta a lista completa das 50 apolices, sem gravar nada ainda."""
    apolices: list[Policy] = []

    # -----------------------------------------------------------
    # Grupo 1 — as 8 do prototipo (datas exatamente como na tela)
    # -----------------------------------------------------------
    for numero, nome, cobertura, capital, dias_para_vencer, duracao in APOLICES_DO_PROTOTIPO:
        cap_morte, cap_invalidez = separar_capitais(cobertura, capital)

        # a data de vencimento e sempre calculada a partir de HOJE
        data_venc = hoje + timedelta(days=dias_para_vencer)
        data_inicio = data_venc - timedelta(days=duracao)

        apolices.append(
            Policy(
                numero_apolice=numero,
                participante=nome,
                cpf=gerar_cpf_ficticio(),
                matricula=str(200000 + len(apolices) + 1),
                cobertura=cobertura,
                capital_morte=cap_morte,
                capital_invalidez=cap_invalidez,
                capital_total=float(capital),
                premio_mensal=calcular_premio(capital),
                data_inicio=data_inicio,
                data_vencimento=data_venc,
                status=calcular_status(data_venc, hoje),
                codigo_modulo="101",
                codigo_sub="01",
                competencia="07/2026",
                origem="prototipo",
            )
        )

    # -----------------------------------------------------------
    # Grupo 2 — os 10 segurados da planilha
    # A planilha nao traz datas de vigencia, entao criamos vigencias
    # de 1 ano espalhadas ao redor de hoje.
    # -----------------------------------------------------------
    for i, dados in enumerate(SEGURADOS_DA_PLANILHA):
        nome, matricula, cpf, nascimento, cap_morte, cap_invalidez, premio, sub = dados

        # espalha os inicios entre 11 meses atras e 1 mes atras
        dias_atras = 330 - (i * 30)
        data_inicio = hoje - timedelta(days=dias_atras)
        data_venc = data_inicio + timedelta(days=365)

        apolices.append(
            Policy(
                # matricula 100001 -> AP-3001, matricula 100010 -> AP-3010
                numero_apolice=f"AP-3{int(matricula) - 100000:03d}",
                participante=nome,
                cpf=cpf,
                matricula=matricula,
                data_nascimento=texto_para_data(nascimento),
                cobertura="Morte + Invalidez",
                capital_morte=float(cap_morte),
                capital_invalidez=float(cap_invalidez),
                capital_total=float(cap_morte),
                premio_mensal=premio,
                data_inicio=data_inicio,
                data_vencimento=data_venc,
                status=calcular_status(data_venc, hoje),
                codigo_modulo="101",
                codigo_sub=sub,
                competencia="07/2026",
                origem="planilha",
            )
        )

    # -----------------------------------------------------------
    # Grupo 3 — completa ate 50 com apolices geradas
    # -----------------------------------------------------------
    nomes_usados = {a.participante for a in apolices}
    numero_seq = 4001

    while len(apolices) < TOTAL_APOLICES:
        nome = f"{sorteio.choice(PRIMEIROS_NOMES)} {sorteio.choice(SOBRENOMES)}"
        if nome in nomes_usados:
            continue  # sorteia outro para nao repetir participante
        nomes_usados.add(nome)

        cobertura = sorteio.choice(COBERTURAS)
        capital = float(sorteio.choice(CAPITAIS))
        cap_morte, cap_invalidez = separar_capitais(cobertura, capital)

        # vencimento entre 100 dias atras e 1 ano a frente,
        # garantindo uma mistura de Vencida / A renovar / Ativa
        data_venc = hoje + timedelta(days=sorteio.randint(-100, 365))
        data_inicio = data_venc - timedelta(days=365)

        # nascimento entre 25 e 60 anos atras
        nascimento = hoje - timedelta(days=sorteio.randint(25 * 365, 60 * 365))

        apolices.append(
            Policy(
                numero_apolice=f"AP-{numero_seq}",
                participante=nome,
                cpf=gerar_cpf_ficticio(),
                matricula=str(300000 + numero_seq),
                data_nascimento=nascimento,
                cobertura=cobertura,
                capital_morte=cap_morte,
                capital_invalidez=cap_invalidez,
                capital_total=capital,
                premio_mensal=calcular_premio(capital),
                data_inicio=data_inicio,
                data_vencimento=data_venc,
                status=calcular_status(data_venc, hoje),
                codigo_modulo="101",
                codigo_sub=sorteio.choice(["01", "02", "03"]),
                competencia="07/2026",
                origem="gerado",
            )
        )
        numero_seq += 1

    # -----------------------------------------------------------
    # Algumas apolices canceladas, para a tela nao ficar so com
    # Ativa / A renovar / Vencida.
    # -----------------------------------------------------------
    for apolice in sorteio.sample(
        [a for a in apolices if a.origem == "gerado"], 4
    ):
        apolice.status = "Cancelada"

    return apolices


def criar_apolices(db, hoje: date) -> None:
    """Grava as 50 apolices no banco."""
    apolices = montar_apolices(hoje)
    db.add_all(apolices)
    db.commit()

    # Mostra um resumo para conferencia.
    contagem: dict[str, int] = {}
    for a in apolices:
        contagem[a.status] = contagem.get(a.status, 0) + 1

    resumo = ", ".join(f"{qtd} {status}" for status, qtd in sorted(contagem.items()))
    print(f"  {len(apolices)} apolices criadas ({resumo}).")


# ===============================================================
# MODULOS DA FASE 4
# ===============================================================
# Daqui para baixo estao os dados das outras 8 telas do prototipo.
# Cada bloco tem os dados copiados do arquivo HTML original e uma
# funcao curta que grava tudo no banco.

# A competencia (mes de referencia) usada em todo o sistema. Veio da
# planilha Base_Segurados_Central.xlsx e das telas do prototipo.
COMPETENCIA_ATUAL = "07/2026"


# ---------------------------------------------------------------
# MOVIMENTACAO & PAGAMENTO
# ---------------------------------------------------------------
# Quem pagou, quem falta pagar e quem esta atrasado.
# Copiado da tabela "Movimentacoes do mes" do prototipo.
SITUACAO_PAGAMENTO = {
    "100001": "Pago",
    "100002": "Pago",
    "100003": "Pago",
    "100004": "A pagar",
    "100005": "Pago",
    "100006": "Pago",
    "100007": "Em atraso",
    "100008": "Pago",
    "100009": "A pagar",
    "100010": "Pago",
}


def criar_pagamentos(db) -> None:
    """Cria uma linha de pagamento para cada segurado da planilha."""
    pagamentos = []
    for dados in SEGURADOS_DA_PLANILHA:
        nome, matricula, cpf, _nasc, cap_morte, cap_inval, premio, sub = dados
        pagamentos.append(
            Payment(
                competencia=COMPETENCIA_ATUAL,
                matricula=matricula,
                segurado=nome,
                cpf=cpf,
                capital_morte=float(cap_morte),
                capital_invalidez=float(cap_inval),
                premio=premio,
                codigo_modulo="101",
                codigo_sub=sub,
                status=SITUACAO_PAGAMENTO[matricula],
            )
        )
    db.add_all(pagamentos)
    db.commit()
    print(f"  {len(pagamentos)} pagamentos criados.")


# ---------------------------------------------------------------
# CONVENIOS E BOLETOS
# ---------------------------------------------------------------
CONVENIOS = [
    ("FENACON", "Fed. Nac. das Empresas de Serviços Contábeis"),
    ("OPBB", "Ordem dos Profissionais"),
    ("CORECON", "Conselho Regional de Economia"),
    ("FenaSebrae", "Federação Nacional Sebrae"),
]

# Competencia atual: boletos ainda NAO emitidos (os cartoes com botao).
# (convenio, vidas, movimentacoes, valor)
BOLETOS_A_EMITIR = [
    ("FENACON", 1128, 34, 74320.0),
    ("OPBB", 642, 18, 41870.0),
    ("CORECON", 489, 11, 30510.0),
    ("FenaSebrae", 1651, 42, 68000.0),
]

# Competencia anterior: boletos ja emitidos (a tabela de historico).
# (convenio, competencia, vidas, valor, status)
BOLETOS_EMITIDOS = [
    ("FenaSebrae", "06/2026", 1640, 67200.0, "Pago"),
    ("FENACON", "06/2026", 1115, 73100.0, "Pago"),
    ("OPBB", "06/2026", 638, 41200.0, "Em aberto"),
    ("CORECON", "06/2026", 485, 30100.0, "Pago"),
]


def criar_convenios_e_boletos(db, hoje: date) -> None:
    """Cria os 4 convenios e os boletos de cada um."""
    convenios = {}
    for nome, descricao in CONVENIOS:
        convenio = Agreement(nome=nome, descricao=descricao)
        db.add(convenio)
        convenios[nome] = convenio
    db.commit()  # precisa gravar antes, para os convenios ganharem id

    boletos = []

    for nome, vidas, movimentacoes, valor in BOLETOS_A_EMITIR:
        boletos.append(
            Invoice(
                agreement_id=convenios[nome].id,
                competencia=COMPETENCIA_ATUAL,
                vidas=vidas,
                movimentacoes=movimentacoes,
                valor=valor,
                data_vencimento=None,  # ainda nao tem, o boleto nao existe
                status="A emitir",
            )
        )

    # O prototipo mostra vencimento 10/07/2026, cerca de 11 dias antes da
    # data em que ele foi desenhado. Mantemos essa distancia em relacao a hoje.
    vencimento_anterior = hoje - timedelta(days=11)

    for nome, competencia, vidas, valor, status in BOLETOS_EMITIDOS:
        boletos.append(
            Invoice(
                agreement_id=convenios[nome].id,
                competencia=competencia,
                vidas=vidas,
                movimentacoes=0,
                valor=valor,
                data_vencimento=vencimento_anterior,
                status=status,
            )
        )

    db.add_all(boletos)
    db.commit()
    print(f"  {len(convenios)} convenios e {len(boletos)} boletos criados.")


# ---------------------------------------------------------------
# COMISSOES
# ---------------------------------------------------------------
# A divisao do premio entre os 3 agentes, conforme o prototipo.
# (papel, quem, percentual, descricao)
DIVISAO_COMISSAO = [
    (PERFIL_ESTIPULANTE, "Sebrae Previdência", 10, "repasse à Entidade"),
    (PERFIL_CORRETORA, "Corretora parceira", 15, "intermediação"),
    (PERFIL_SEGURADORA, "ICATU", 75, "risco e operação"),
]

# O premio arrecadado em cada mes. Julho (R$ 214.700) veio do prototipo;
# os meses anteriores seguem a mesma proporcao do grafico de barras dele.
PREMIO_POR_COMPETENCIA = [
    ("03/2026", 143100.0),
    ("04/2026", 157400.0),
    ("05/2026", 171800.0),
    ("06/2026", 186100.0),
    ("07/2026", 214700.0),
]


def criar_comissoes(db) -> None:
    """Cria as 3 fatias de comissao para cada um dos 5 meses."""
    comissoes = []
    for competencia, premio in PREMIO_POR_COMPETENCIA:
        for papel, quem, percentual, descricao in DIVISAO_COMISSAO:
            comissoes.append(
                Commission(
                    competencia=competencia,
                    papel=papel,
                    quem=quem,
                    premio_total=premio,
                    percentual=percentual,
                    valor=round(premio * percentual / 100, 2),
                    descricao=f"{percentual}% do prêmio · {descricao}",
                )
            )
    db.add_all(comissoes)
    db.commit()
    print(f"  {len(comissoes)} registros de comissao criados.")


# ---------------------------------------------------------------
# INADIMPLENCIA
# ---------------------------------------------------------------
# (participante, apolice, cobertura, valor, dias de atraso)
INADIMPLENTES = [
    ("Patrícia Gomes", "AP-2087", "Morte + Invalidez", 112.00, 112),
    ("Alexandre Pinto", "AP-1902", "Morte", 178.00, 98),
    ("Rita Fonseca", "AP-2044", "Invalidez", 90.00, 91),
    ("Gustavo Nery", "AP-2110", "Morte + Invalidez", 145.00, 62),
    ("Helena Braga", "AP-1975", "Morte", 88.00, 34),
    ("Diego Martins", "AP-2120", "Invalidez", 60.00, 9),
]


def criar_inadimplencia(db) -> None:
    db.add_all(
        [
            Delinquency(
                participante=nome,
                numero_apolice=apolice,
                cobertura=cobertura,
                valor=valor,
                dias_atraso=dias,
            )
            for nome, apolice, cobertura, valor, dias in INADIMPLENTES
        ]
    )
    db.commit()
    print(f"  {len(INADIMPLENTES)} inadimplentes criados.")


# ---------------------------------------------------------------
# ESTEIRA DE APOLICES (propostas)
# ---------------------------------------------------------------
# (numero, participante, cobertura, capital, etapa, observacao, recusada)
PROPOSTAS = [
    ("PROP-3012", "Ricardo Alves", "Morte + Invalidez", 220000, "recebida", None, False),
    ("PROP-3015", "Juliana Reis", "Morte", 150000, "recebida", None, False),
    ("PROP-3018", "Carlos Menezes", "Invalidez", 120000, "recebida", None, False),
    ("PROP-3008", "Amanda Prado", "Invalidez", None, "analise", "DPS em avaliação", False),
    ("PROP-3010", "Bruno Carvalho", "Morte + Invalidez", None, "analise", "Aguardando análise", False),
    ("PROP-2998", "Teresa Lopes", "Morte", None, "aceita", "Emitir apólice", False),
    ("PROP-3001", "Felipe Duarte", "Morte + Invalidez", None, "aceita", "Emitir apólice", False),
    ("PROP-3005", "Sandra Vieira", None, None, "pendente", "Falta DPS assinada", False),
    ("PROP-2995", "Otávio Ramos", None, None, "pendente", "Recusada — risco agravado", True),
]


def criar_propostas(db) -> None:
    db.add_all(
        [
            Proposal(
                numero=numero,
                participante=nome,
                cobertura=cobertura,
                capital=float(capital) if capital else None,
                etapa=etapa,
                observacao=obs,
                recusada=recusada,
            )
            for numero, nome, cobertura, capital, etapa, obs, recusada in PROPOSTAS
        ]
    )
    db.commit()
    print(f"  {len(PROPOSTAS)} propostas criadas.")


# ---------------------------------------------------------------
# SINISTROS
# ---------------------------------------------------------------
# Os "dias atras" foram calculados a partir da data em que o prototipo
# foi desenhado (21/07/2026), pelo mesmo motivo das apolices: assim os
# sinistros continuam parecendo recentes em qualquer dia do ano.
# (protocolo, participante, tipo, dias_atras, documentacao, doc_ok, status)
SINISTROS = [
    ("SIN-0451", "Antônio Ferreira", "Morte", 19, "Completa", True, "Em liberação"),
    ("SIN-0448", "Beneficiário — H. Costa", "Morte", 23, "Falta certidão", False, "Aguardando doc."),
    ("SIN-0455", "Luís G. Pereira", "Invalidez", 13, "Falta laudo", False, "Em análise"),
    ("SIN-0459", "Maria E. Dias", "Invalidez", 9, "Completa", True, "Em análise"),
]


def criar_sinistros(db, hoje: date) -> None:
    db.add_all(
        [
            Claim(
                protocolo=protocolo,
                participante=nome,
                tipo=tipo,
                data_abertura=hoje - timedelta(days=dias_atras),
                documentacao=doc,
                documentacao_ok=doc_ok,
                status=status,
            )
            for protocolo, nome, tipo, dias_atras, doc, doc_ok, status in SINISTROS
        ]
    )
    db.commit()
    print(f"  {len(SINISTROS)} sinistros criados.")


# ---------------------------------------------------------------
# PENDENCIAS
# ---------------------------------------------------------------
# Os prazos tambem sao contados a partir de hoje.
# O prazo da primeira (renovacao da AP-2041) e 11 dias, o mesmo
# vencimento que demos aquela apolice, para as duas telas combinarem.
# (prioridade, titulo, referente, responsavel, dias_ate_o_prazo, documento, doc_ok)
PENDENCIAS = [
    ("Alta", "Renovação vencendo", "AP-2041 · Marcos Ribeiro", "Corretora", 11, "Apólice", True),
    ("Alta", "Certidão de óbito faltante", "SIN-0448 · H. Costa", "Beneficiário", 4, "Certidão faltante", False),
    ("Média", "Laudo médico pendente", "SIN-0455 · L. Pereira", "Seguradora", 9, "Laudo faltante", False),
    ("Média", "Confirmação de comissão", "AP-1987 · F. Lima", "Financeiro", 15, "Extrato", True),
    ("Baixa", "Atualização de cadastro", "AP-2115 · J. Andrade", "Estipulante", 21, "Cadastro", True),
]


def criar_pendencias(db, hoje: date) -> None:
    db.add_all(
        [
            Pendency(
                prioridade=prioridade,
                titulo=titulo,
                referente=referente,
                responsavel=responsavel,
                prazo=hoje + timedelta(days=dias),
                documento=documento,
                documento_ok=doc_ok,
            )
            for prioridade, titulo, referente, responsavel, dias, documento, doc_ok in PENDENCIAS
        ]
    )
    db.commit()
    print(f"  {len(PENDENCIAS)} pendencias criadas.")


# ===============================================================
# ETAPA 5: EXPORTAR PARA sql/banco.sql
# ===============================================================
def exportar_para_sql() -> None:
    """
    Le o banco pronto e escreve um arquivo .sql com todos os comandos
    necessarios para recriar o banco identico em outro computador.

    Assim o arquivo central.db nao precisa ir para o GitHub.
    """
    ARQUIVO_SQL.parent.mkdir(exist_ok=True)

    conexao = sqlite3.connect(ARQUIVO_BANCO)

    linhas = [
        "-- ==================================================================",
        "-- Central Inteligente de Seguros - banco de dados completo",
        "-- ==================================================================",
        "-- Arquivo GERADO AUTOMATICAMENTE por app/seed.py. Nao edite a mao:",
        "-- suas alteracoes serao perdidas na proxima vez que o seed rodar.",
        "--",
        "-- Para recriar o banco a partir daqui:",
        "--     sqlite3 database/central.db < sql/banco.sql",
        "--",
        "-- Ou, mais simples, rode:  python -m app.seed",
        "--",
        "-- TODOS OS DADOS SAO FICTICIOS.",
        "-- ==================================================================",
        "",
    ]
    linhas.extend(conexao.iterdump())
    conexao.close()

    ARQUIVO_SQL.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"  sql/banco.sql gerado ({len(linhas)} linhas).")


# ===============================================================
# PROGRAMA PRINCIPAL
# ===============================================================
def executar() -> None:
    hoje = date.today()

    print("\n=== POPULANDO O BANCO DE DADOS ===\n")
    print(f"Arquivo: {ARQUIVO_BANCO}")
    print(f"Data de referencia: {hoje.strftime('%d/%m/%Y')}\n")

    # 1. cria as tabelas se ainda nao existirem
    criar_tabelas()
    print("  Tabelas criadas/verificadas.")

    db = SessionLocal()
    try:
        # 2. limpa os dados antigos.
        # A ordem importa: quem depende de outra tabela e apagado primeiro.
        # Invoice depende de Agreement, e LoginHistory depende de User.
        for tabela in (
            LoginHistory,
            Invoice,
            Agreement,
            Payment,
            Commission,
            Delinquency,
            Proposal,
            Claim,
            Pendency,
            Policy,
            User,
        ):
            db.query(tabela).delete()
        db.commit()
        print("  Dados antigos apagados.")

        # 3 e 4: usuarios e carteira de apolices
        criar_usuarios(db)
        criar_apolices(db, hoje)

        # 5: os dados das outras telas (Fase 4)
        criar_pagamentos(db)
        criar_convenios_e_boletos(db, hoje)
        criar_comissoes(db)
        criar_inadimplencia(db)
        criar_propostas(db)
        criar_sinistros(db, hoje)
        criar_pendencias(db, hoje)
    finally:
        db.close()

    # 5
    exportar_para_sql()

    print("\n=== PRONTO ===")
    print("\nUsuarios para teste:")
    print("  estipulante@sebraeprev.com.br  /  estipulante@sebraeprev")
    print("  corretora@sebraeprev.com.br    /  corretora@sebraeprev")
    print("  seguradora@sebraeprev.com.br   /  seguradora@sebraeprev")
    print()


# Esta linha significa: "so execute se o arquivo for chamado direto,
# nao quando ele for importado por outro arquivo".
if __name__ == "__main__":
    executar()
