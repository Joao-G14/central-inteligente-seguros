"""
models.py
---------
Aqui descrevemos as TABELAS do banco de dados usando classes Python.

Cada classe = uma tabela.
Cada Column = uma coluna.

O SQLAlchemy le este arquivo e cria as tabelas de verdade no central.db.
"""

from datetime import date, datetime  # noqa: F401  (date e usado nas anotacoes)

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app import tempo
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

    criado_em = Column(DateTime, nullable=False, default=tempo.agora)

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
    data_hora = Column(DateTime, nullable=False, default=tempo.agora)

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

    criado_em = Column(DateTime, nullable=False, default=tempo.agora)

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
# TABELA 2b: active_sessions  (quem esta logado agora)
# ===============================================================
class ActiveSession(Base):
    """
    Uma linha por pessoa logada.

    POR QUE ISTO EXISTE
    -------------------
    Antes, o cookie carregava so o numero da categoria. Ele era assinado,
    entao ninguem conseguia falsifica-lo — mas quem COPIASSE um cookie
    valido (num PC compartilhado, por exemplo) continuaria entrando por
    8 horas, inclusive depois de a pessoa clicar em "Sair". O logout so
    apagava o cookie do navegador dela, nao invalidava o cracha.

    Agora o cookie carrega apenas um CODIGO ALEATORIO, e a sessao de
    verdade mora aqui. O logout APAGA esta linha — e qualquer copia do
    cookie morre na hora.

    Bonus: como cada pessoa tem a sua linha, o logout de uma nao derruba
    as outras. Isso importa porque a senha e compartilhada por categoria:
    varias pessoas usam a mesma conta ao mesmo tempo.
    """

    __tablename__ = "active_sessions"

    id = Column(Integer, primary_key=True)

    # O codigo aleatorio que vai dentro do cookie. E a "chave" da sessao.
    token = Column(String(64), unique=True, nullable=False, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # O e-mail que a pessoa digitou ao entrar.
    email = Column(String(120), nullable=False)
    ip = Column(String(45), nullable=True)

    criado_em = Column(DateTime, nullable=False, default=tempo.agora)

    # Atualizado a cada pagina aberta. Serve para saber quem esta
    # realmente ativo e para expirar sessoes esquecidas.
    ultimo_acesso = Column(DateTime, nullable=False, default=tempo.agora)

    usuario = relationship("User")

    def __repr__(self):
        return f"<ActiveSession {self.email} desde {self.criado_em}>"


# ===============================================================
# TABELA 3b: authorized_emails  (quem pode entrar no sistema)
# ===============================================================
class AuthorizedEmail(Base):
    """
    A lista de acesso autorizado.

    POR QUE ISSO EXISTE
    -------------------
    A senha e compartilhada por categoria. Sozinha, ela deixa QUALQUER
    pessoa que a descubra entrar com QUALQUER e-mail. Esta lista fecha
    essa porta: alem de saber a senha, o e-mail precisa estar liberado.

    DOIS JEITOS DE LIBERAR
    ----------------------
    1. E-mail exato:  joao.sales@sebraeprev.com.br
       Libera so aquela pessoa.

    2. Dominio inteiro: @sebraeprev.com.br
       Libera qualquer e-mail que termine assim. Util para liberar uma
       empresa inteira sem cadastrar pessoa por pessoa.

    Guardamos sempre em minusculo, para "Joao@X.com" e "joao@x.com"
    serem tratados como o mesmo.
    """

    __tablename__ = "authorized_emails"

    id = Column(Integer, primary_key=True)

    # O e-mail completo ou o dominio comecando com @
    valor = Column(String(120), unique=True, nullable=False, index=True)

    # Em qual categoria esta pessoa pode entrar.
    # Se for "TODAS", vale para as tres.
    perfil = Column(String(20), nullable=False, default="TODAS")

    # Anotacao livre: "Analista do financeiro", "Contato da corretora"...
    observacao = Column(String(120), nullable=True)

    # Bloquear em vez de apagar preserva o historico de quem autorizou.
    ativo = Column(Boolean, nullable=False, default=True)

    # Quem cadastrou e quando.
    cadastrado_por = Column(String(120), nullable=True)
    criado_em = Column(DateTime, nullable=False, default=tempo.agora)

    def __repr__(self):
        return f"<AuthorizedEmail {self.valor} ({self.perfil})>"

    def e_dominio(self) -> bool:
        """True se for um domínio (@empresa.com) e não um e-mail completo."""
        return self.valor.startswith("@")

    def vale_para(self, email: str, perfil: str) -> bool:
        """Esta autorizacao libera este e-mail nesta categoria?"""
        if not self.ativo:
            return False

        # A categoria precisa bater (ou a autorizacao vale para todas).
        if self.perfil != "TODAS" and self.perfil != perfil:
            return False

        email = (email or "").strip().lower()

        if self.e_dominio():
            return email.endswith(self.valor)
        return email == self.valor


# ===============================================================
# TABELA 3e: api_keys  (uma chave para cada parceiro)
# ===============================================================
class ApiKey(Base):
    """
    Uma chave de acesso a API, por parceiro.

    POR QUE UMA CHAVE PARA CADA UM
    ------------------------------
    Antes havia uma unica chave no arquivo .env, usada por todos. Isso
    trazia dois problemas:

      1. se a chave da corretora vazasse, era preciso trocar a de todos
         os parceiros ao mesmo tempo
      2. nao havia como saber QUEM fez cada chamada

    Com uma chave por parceiro, da para revogar so a dele e o registro
    de chamadas mostra o nome de quem chamou.

    POR QUE GUARDAMOS O HASH, E NAO A CHAVE
    ---------------------------------------
    Igual as senhas: se o banco cair em maos erradas, ninguem consegue
    usar as chaves. A chave completa aparece UMA VEZ, na tela, no momento
    em que e criada. Depois disso nem nos conseguimos ver — se a pessoa
    perder, e preciso gerar outra.

    Guardamos separado um "inicio" (os 8 primeiros caracteres) apenas
    para dar para identificar qual chave e qual na lista.
    """

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)

    # Quem usa esta chave: "Corretora Parceira", "ICATU", "Copilot"...
    nome = Column(String(80), unique=True, nullable=False)

    # O hash da chave (nunca a chave em si).
    chave_hash = Column(String(200), nullable=False)

    # Os primeiros caracteres, para identificar na lista.
    inicio = Column(String(12), nullable=False)

    observacao = Column(String(200), nullable=True)

    # Bloquear em vez de apagar preserva o historico de chamadas.
    ativo = Column(Boolean, nullable=False, default=True)

    criado_por = Column(String(120), nullable=True)
    criado_em = Column(DateTime, nullable=False, default=tempo.agora)
    ultimo_uso = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<ApiKey {self.nome} ({self.inicio}...)>"


# ===============================================================
# TABELA 3f: api_calls  (registro de quem chamou a API)
# ===============================================================
class ApiCall(Base):
    """
    Uma linha por chamada recebida na API.

    POR QUE ISTO EXISTE
    -------------------
    O login guardava tudo, mas a API nao guardava nada. Se a corretora
    dissesse "enviei a base ontem", nao havia como conferir. Agora da
    para responder: quem chamou, quando, de onde, o que pediu e se deu
    certo.

    Isto tambem serve para perceber uso indevido: muitas chamadas
    recusadas seguidas costumam ser alguem tentando adivinhar a chave.
    """

    __tablename__ = "api_calls"

    id = Column(Integer, primary_key=True)

    # Qual parceiro chamou. Fica vazio quando a chave era invalida —
    # e justamente esse caso que interessa investigar.
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)
    parceiro = Column(String(80), nullable=True)

    metodo = Column(String(10), nullable=False)   # GET, POST...
    caminho = Column(String(200), nullable=False)  # /api/v1/apolices
    status = Column(Integer, nullable=False)       # 200, 401, 422...

    ip = Column(String(45), nullable=True)

    # Quanto tempo a Central levou para responder, em milissegundos.
    duracao_ms = Column(Integer, nullable=True)

    # Um resumo curto do que aconteceu. Ex.: "10 registros gravados".
    # NAO guardamos o conteudo enviado: a base tem CPF e nome, e guardar
    # duas vezes o mesmo dado pessoal aumenta o risco sem necessidade.
    resumo = Column(String(200), nullable=True)

    data_hora = Column(DateTime, nullable=False, default=tempo.agora, index=True)

    chave = relationship("ApiKey")

    def __repr__(self):
        return f"<ApiCall {self.metodo} {self.caminho} -> {self.status}>"


# ===============================================================
# TABELA 3c: settings  (configuracoes que mudam pela tela)
# ===============================================================
class Setting(Base):
    """
    Guarda configuracoes que o estipulante liga e desliga pela tela,
    sem precisar mexer em arquivo nenhum.

    Cada linha e um par: uma chave e um valor, os dois em texto.
    Hoje so usamos uma chave, "exigir_email_autorizado", mas o formato
    aceita quantas precisarmos no futuro.
    """

    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    chave = Column(String(60), unique=True, nullable=False, index=True)
    valor = Column(String(200), nullable=False, default="")
    atualizado_em = Column(DateTime, nullable=False, default=tempo.agora)

    def __repr__(self):
        return f"<Setting {self.chave}={self.valor}>"


# A chave que liga/desliga a exigencia da lista de acesso.
CHAVE_EXIGIR_AUTORIZACAO = "exigir_email_autorizado"


# ===============================================================
# TABELA 3d: chat_messages  (a memoria do assistente)
# ===============================================================
class ChatMessage(Base):
    """
    Cada linha e uma fala da conversa com o assistente.

    POR QUE GUARDAR
    Sem memoria, cada pergunta comeca do zero e nao da para perguntar
    "e no mes passado?" logo depois de "quanto foi a comissao de julho?".
    Guardando o historico, o assistente entende o que "e no mes passado"
    quer dizer.

    A conversa e separada por E-MAIL: cada pessoa tem a sua, e ninguem
    ve a conversa de outra.
    """

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True)

    # De quem e esta conversa (o e-mail informado no login).
    usuario_email = Column(String(120), nullable=False, index=True)

    # "user" = a pessoa · "assistant" = o assistente
    papel = Column(String(12), nullable=False)

    conteudo = Column(Text, nullable=False)

    # "ia" (respondeu o Claude) ou "regras" (respondeu o assistente.py).
    # Fica so nas respostas; nas perguntas da pessoa e None.
    origem = Column(String(10), nullable=True)

    criado_em = Column(DateTime, nullable=False, default=tempo.agora, index=True)

    def __repr__(self):
        return f"<ChatMessage {self.papel}: {self.conteudo[:40]}>"


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

    criado_em = Column(DateTime, nullable=False, default=tempo.agora)

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
