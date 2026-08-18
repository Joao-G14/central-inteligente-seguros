"""
models.py
---------
Aqui descrevemos as TABELAS do banco de dados usando classes Python.

Cada classe = uma tabela.
Cada Column = uma coluna.

O SQLAlchemy le este arquivo e cria as tabelas de verdade no central.db.
"""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.database import Base

# ---------------------------------------------------------------
# OS TRES PERFIS DE ACESSO
# ---------------------------------------------------------------
# Guardamos como texto simples ("ESTIPULANTE") para ficar facil de ler
# direto no banco. Esta lista serve para conferir se o valor e valido.
PERFIL_ESTIPULANTE = "ESTIPULANTE"
PERFIL_CORRETORA = "CORRETORA"
PERFIL_SEGURADORA = "SEGURADORA"

PERFIS_VALIDOS = [PERFIL_ESTIPULANTE, PERFIL_CORRETORA, PERFIL_SEGURADORA]


# ===============================================================
# TABELA 1: users  (quem pode entrar no sistema)
# ===============================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    nome = Column(String(120), nullable=False)

    # unique=True: nao pode existir dois usuarios com o mesmo e-mail.
    # index=True: deixa a busca por e-mail mais rapida (usado no login).
    email = Column(String(120), unique=True, nullable=False, index=True)

    # ATENCAO: guardamos o HASH da senha, nunca a senha em texto puro.
    # O hash e um embaralhamento que NAO pode ser desfeito.
    # Veja app/auth.py para entender como e gerado e conferido.
    senha_hash = Column(String(200), nullable=False)

    # ESTIPULANTE, CORRETORA ou SEGURADORA
    perfil = Column(String(20), nullable=False)

    # Se ativo=False, o usuario existe mas nao consegue entrar.
    ativo = Column(Boolean, nullable=False, default=True)

    criado_em = Column(DateTime, nullable=False, default=datetime.now)

    # Liga este usuario aos seus registros de login.
    # Permite escrever: usuario.logins  -> lista de acessos dele
    logins = relationship("LoginHistory", back_populates="usuario")

    def __repr__(self):
        # Serve so para aparecer bonitinho quando imprimimos no terminal.
        return f"<User {self.email} ({self.perfil})>"


# ===============================================================
# TABELA 2: login_history  (registro de quem entrou e quando)
# ===============================================================
class LoginHistory(Base):
    __tablename__ = "login_history"

    id = Column(Integer, primary_key=True)

    # ForeignKey = "esta coluna aponta para a coluna id da tabela users".
    # Pode ficar vazio (nullable=True) porque tambem registramos TENTATIVAS
    # com e-mail inexistente, e nesse caso nao ha usuario para apontar.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Guardamos o que a pessoa DIGITOU na tela, mesmo se estiver errado.
    # Isso ajuda a entender tentativas de acesso indevido.
    email_informado = Column(String(120), nullable=False)
    perfil_informado = Column(String(20), nullable=False)

    sucesso = Column(Boolean, nullable=False)

    # Se sucesso=False, aqui fica o motivo. Exemplos:
    # "e-mail nao encontrado", "senha incorreta", "perfil nao corresponde"
    motivo = Column(String(200), nullable=True)

    ip = Column(String(45), nullable=True)

    # A data e hora do acesso. Este e o requisito principal desta tabela.
    data_hora = Column(DateTime, nullable=False, default=datetime.now)

    usuario = relationship("User", back_populates="logins")

    def __repr__(self):
        resultado = "OK" if self.sucesso else "FALHOU"
        return f"<Login {self.email_informado} {resultado} {self.data_hora}>"


# ===============================================================
# TABELA 3: policies  (a carteira de apolices)
# ===============================================================
class Policy(Base):
    """
    Uma linha = uma apolice de seguro de risco (morte e/ou invalidez).

    Os campos vieram de duas fontes do projeto:
      - a tabela "Carteira de apolices" do prototipo HTML
      - a planilha Base_Segurados_Central.xlsx

    OBSERVACAO SOBRE DINHEIRO: usamos Float por simplicidade. Em um sistema
    financeiro real o correto e guardar centavos em Integer ou usar Numeric,
    porque Float pode arredondar errado em contas grandes. Para exibir uma
    carteira de demonstracao esta tudo bem.
    """

    __tablename__ = "policies"

    id = Column(Integer, primary_key=True)

    # Ex.: "AP-2041"
    numero_apolice = Column(String(20), unique=True, nullable=False, index=True)

    # --- dados do participante (pessoa segurada) ---
    participante = Column(String(120), nullable=False, index=True)
    cpf = Column(String(14), nullable=True)  # formato 000.000.000-00 (FICTICIO)
    matricula = Column(String(20), nullable=True)
    data_nascimento = Column(Date, nullable=True)

    # --- coberturas ---
    # "Morte", "Invalidez" ou "Morte + Invalidez"
    cobertura = Column(String(30), nullable=False)

    capital_morte = Column(Float, nullable=False, default=0.0)
    capital_invalidez = Column(Float, nullable=False, default=0.0)

    # O valor que aparece na coluna "Capital segurado" da tela do prototipo.
    capital_total = Column(Float, nullable=False, default=0.0)

    premio_mensal = Column(Float, nullable=False, default=0.0)

    # --- vigencia ---
    data_inicio = Column(Date, nullable=False)
    data_vencimento = Column(Date, nullable=False, index=True)

    # "Ativa", "A renovar", "Vencida" ou "Cancelada"
    status = Column(String(20), nullable=False, index=True)

    # --- dados da planilha de pagamento ---
    codigo_modulo = Column(String(10), nullable=True)  # 101 = risco morte/invalidez
    codigo_sub = Column(String(10), nullable=True)  # 01, 02, 03 = subgrupos
    competencia = Column(String(7), nullable=True)  # "07/2026"

    # De onde este registro veio: "prototipo", "planilha" ou "gerado".
    # Ajuda voces a rastrear os dados enquanto estudam o projeto.
    origem = Column(String(20), nullable=True)

    criado_em = Column(DateTime, nullable=False, default=datetime.now)

    def __repr__(self):
        return f"<Policy {self.numero_apolice} {self.participante} {self.status}>"

    # -----------------------------------------------------------
    # Funcoes de apoio (usadas depois nas telas)
    # -----------------------------------------------------------
    def dias_para_vencer(self, hoje: date | None = None) -> int:
        """Quantos dias faltam para vencer. Negativo = ja venceu."""
        if hoje is None:
            hoje = date.today()
        return (self.data_vencimento - hoje).days

    def capital_formatado(self) -> str:
        """Transforma 250000.0 em 'R$ 250.000' para mostrar na tela."""
        return f"R$ {self.capital_total:,.0f}".replace(",", ".")

    def premio_formatado(self) -> str:
        """Transforma 102.0 em 'R$ 102,00'."""
        return f"R$ {self.premio_mensal:,.2f}".replace(",", "X").replace(
            ".", ","
        ).replace("X", ".")


# ===============================================================
# TABELA 4: payments  (movimentacao e pagamento por segurado)
# ===============================================================
class Payment(Base):
    """
    Uma linha = um segurado dentro de uma competencia (mes de referencia).

    Vem da planilha de movimentacao que a corretora envia todo mes.
    Corresponde a tela "Movimentacao & Pagamento" do prototipo.
    """

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)

    competencia = Column(String(7), nullable=False, index=True)  # "07/2026"

    matricula = Column(String(20), nullable=False)
    segurado = Column(String(120), nullable=False)
    cpf = Column(String(14), nullable=True)

    capital_morte = Column(Float, nullable=False, default=0.0)
    capital_invalidez = Column(Float, nullable=False, default=0.0)
    premio = Column(Float, nullable=False, default=0.0)

    codigo_modulo = Column(String(10), nullable=True)
    codigo_sub = Column(String(10), nullable=True)

    # "Pago", "A pagar" ou "Em atraso"
    status = Column(String(20), nullable=False, index=True)

    criado_em = Column(DateTime, nullable=False, default=datetime.now)

    def __repr__(self):
        return f"<Payment {self.matricula} {self.segurado} {self.status}>"


# ===============================================================
# TABELA 5: agreements + invoices  (convenios e boletos)
# ===============================================================
class Agreement(Base):
    """Um convenio (FENACON, OPBB, CORECON, FenaSebrae)."""

    __tablename__ = "agreements"

    id = Column(Integer, primary_key=True)
    nome = Column(String(60), unique=True, nullable=False)
    descricao = Column(String(200), nullable=True)

    boletos = relationship("Invoice", back_populates="convenio")

    def __repr__(self):
        return f"<Agreement {self.nome}>"


class Invoice(Base):
    """
    Um boleto de um convenio em uma competencia.

    Se status = "A emitir", o boleto ainda nao foi gerado: ele aparece
    nos cartoes de cima da tela, com o botao "Emitir boleto".
    Os demais aparecem na tabela "Boletos emitidos".
    """

    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)

    agreement_id = Column(Integer, ForeignKey("agreements.id"), nullable=False)

    competencia = Column(String(7), nullable=False, index=True)
    vidas = Column(Integer, nullable=False, default=0)
    movimentacoes = Column(Integer, nullable=False, default=0)
    valor = Column(Float, nullable=False, default=0.0)
    data_vencimento = Column(Date, nullable=True)

    # "A emitir", "Em aberto" ou "Pago"
    status = Column(String(20), nullable=False, index=True)

    convenio = relationship("Agreement", back_populates="boletos")

    def __repr__(self):
        return f"<Invoice {self.convenio.nome} {self.competencia} {self.status}>"


# ===============================================================
# TABELA 6: commissions  (divisao do premio entre os 3 agentes)
# ===============================================================
class Commission(Base):
    """
    Uma linha = quanto um agente recebeu em uma competencia.

    Regra do prototipo, sobre o premio arrecadado no mes:
        Estipulante (Sebrae Prev)  10%
        Corretora                  15%
        Seguradora (ICATU)         75%
    """

    __tablename__ = "commissions"

    id = Column(Integer, primary_key=True)

    competencia = Column(String(7), nullable=False, index=True)

    # ESTIPULANTE, CORRETORA ou SEGURADORA — os mesmos nomes dos perfis
    papel = Column(String(20), nullable=False)
    quem = Column(String(80), nullable=False)  # "Sebrae Previdência", "ICATU"...

    premio_total = Column(Float, nullable=False, default=0.0)
    percentual = Column(Float, nullable=False, default=0.0)  # 10, 15 ou 75
    valor = Column(Float, nullable=False, default=0.0)

    descricao = Column(String(120), nullable=True)

    def __repr__(self):
        return f"<Commission {self.competencia} {self.papel} {self.percentual}%>"


# ===============================================================
# TABELA 7: delinquency  (inadimplencia)
# ===============================================================
class Delinquency(Base):
    """
    Um participante em atraso com o pagamento.

    A "regua de cobranca" do prototipo separa por faixa de dias:
        1 a 15   -> Aviso amigavel por e-mail
        16 a 45  -> Notificacao de pendencia
        46 a 90  -> Alerta de suspensao
        +90      -> Risco de cancelamento
    """

    __tablename__ = "delinquency"

    id = Column(Integer, primary_key=True)

    participante = Column(String(120), nullable=False)
    numero_apolice = Column(String(20), nullable=False)
    cobertura = Column(String(30), nullable=False)
    valor = Column(Float, nullable=False, default=0.0)
    dias_atraso = Column(Integer, nullable=False, default=0)

    # Fica True depois que alguem clica em "Cobrar" na tela.
    cobranca_enviada = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<Delinquency {self.participante} {self.dias_atraso}d>"

    def faixa(self) -> str:
        """Em qual degrau da regua de cobranca este atraso se encaixa."""
        if self.dias_atraso > 90:
            return "Cancelamento"
        if self.dias_atraso > 45:
            return "Suspensão"
        if self.dias_atraso > 15:
            return "Notificação"
        return "Aviso"

    def cor_da_faixa(self) -> str:
        """A cor da etiqueta na tela (as classes .pill do CSS)."""
        return {
            "Cancelamento": "late",
            "Suspensão": "warn",
            "Notificação": "warn",
            "Aviso": "blue",
        }[self.faixa()]


# ===============================================================
# TABELA 8: proposals  (esteira de aceitacao)
# ===============================================================
class Proposal(Base):
    """
    Uma proposta de seguro dentro da esteira de subscricao.

    A tela e um quadro (kanban) com 4 colunas, na ordem do fluxo:
        Proposta recebida -> Em analise -> Aceita / Pendente
    """

    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True)

    numero = Column(String(20), unique=True, nullable=False)
    participante = Column(String(120), nullable=False)
    cobertura = Column(String(30), nullable=True)
    capital = Column(Float, nullable=True)

    # "recebida", "analise", "aceita" ou "pendente" — define a coluna
    etapa = Column(String(20), nullable=False, index=True)

    # o texto do segundo campo do cartao, ex.: "Falta DPS assinada"
    observacao = Column(String(120), nullable=True)

    # True quando a proposta foi recusada (aparece em vermelho)
    recusada = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<Proposal {self.numero} {self.etapa}>"


# ===============================================================
# TABELA 9: claims  (sinistros)
# ===============================================================
class Claim(Base):
    """Um sinistro aberto (pedido de pagamento do seguro)."""

    __tablename__ = "claims"

    id = Column(Integer, primary_key=True)

    protocolo = Column(String(20), unique=True, nullable=False)
    participante = Column(String(120), nullable=False)
    tipo = Column(String(20), nullable=False)  # "Morte" ou "Invalidez"
    data_abertura = Column(Date, nullable=False)

    # "Completa", "Falta certidão", "Falta laudo"...
    documentacao = Column(String(60), nullable=False)
    documentacao_ok = Column(Boolean, nullable=False, default=True)

    # "Em análise", "Aguardando doc.", "Em liberação", "Concluído"
    status = Column(String(30), nullable=False, index=True)

    def __repr__(self):
        return f"<Claim {self.protocolo} {self.status}>"

    def dias_em_aberto(self, hoje: date | None = None) -> int:
        """Ha quantos dias este sinistro foi aberto."""
        if hoje is None:
            hoje = date.today()
        return (hoje - self.data_abertura).days


# ===============================================================
# TABELA 10: pendencies  (pendencias)
# ===============================================================
class Pendency(Base):
    """
    Uma pendencia em aberto: algo que falta alguem resolver.

    No prototipo a lista vem "priorizada pela IA". Aqui ordenamos por
    prioridade e depois por prazo, que da o mesmo resultado e e uma
    regra que voces conseguem explicar.
    """

    __tablename__ = "pendencies"

    id = Column(Integer, primary_key=True)

    # "Alta", "Média" ou "Baixa"
    prioridade = Column(String(10), nullable=False, index=True)

    titulo = Column(String(120), nullable=False)
    referente = Column(String(120), nullable=True)
    responsavel = Column(String(60), nullable=True)
    prazo = Column(Date, nullable=True)

    documento = Column(String(60), nullable=True)
    # False = o documento esta faltando (aparece em vermelho na tela)
    documento_ok = Column(Boolean, nullable=False, default=True)

    resolvida = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<Pendency {self.prioridade} {self.titulo}>"

    def peso_prioridade(self) -> int:
        """Numero usado para ordenar: Alta vem primeiro."""
        return {"Alta": 0, "Média": 1, "Baixa": 2}.get(self.prioridade, 9)

    def cor_prioridade(self) -> str:
        return {"Alta": "late", "Média": "warn", "Baixa": "blue"}.get(
            self.prioridade, "cinza"
        )
