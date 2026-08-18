"""
auth.py
-------
Tudo que envolve SENHA, LOGIN e PERMISSAO fica aqui.

O arquivo tem 4 partes:
  1. Senhas       — gerar_hash() e conferir_senha()
  2. Login        — autenticar() e registrar_login()
  3. Sessao       — quem esta logado agora (cookie assinado)
  4. Permissoes   — o que cada perfil pode acessar

POR QUE HASH?
Se guardassemos a senha como "senha123" no banco, qualquer pessoa que
abrisse o arquivo central.db leria a senha de todo mundo. O hash e um
embaralhamento de mao unica: da senha da para chegar no hash, mas do
hash NAO da para voltar para a senha.
"""

import re

import bcrypt
from itsdangerous import BadSignature, URLSafeSerializer

from app import config
from app.models import (
    CHAVE_EXIGIR_AUTORIZACAO,
    AuthorizedEmail,
    LoginHistory,
    Setting,
    User,
)

# ===============================================================
# PARTE 1: SENHAS
# ===============================================================

# O bcrypt so aceita senhas de ate 72 bytes. Senhas maiores dao erro.
LIMITE_BYTES_BCRYPT = 72


def _para_bytes(senha: str) -> bytes:
    """
    O bcrypt trabalha com bytes, nao com texto. Esta funcao converte
    e corta no limite de 72 bytes para nunca dar erro.

    O "_" no inicio do nome e uma convencao Python que significa:
    "esta funcao e de uso interno deste arquivo".
    """
    return senha.encode("utf-8")[:LIMITE_BYTES_BCRYPT]


def gerar_hash(senha: str) -> str:
    """
    Recebe a senha em texto e devolve o hash para guardar no banco.

    Exemplo:
        gerar_hash("senha123")
        -> '$2b$12$CzHJOTXqPGX.akyY01nVne...'

    Rodar duas vezes com a mesma senha da hashes DIFERENTES, porque o
    bcrypt sorteia um "sal" (gensalt) a cada chamada. Isso e proposital
    e deixa o sistema mais seguro.
    """
    hash_em_bytes = bcrypt.hashpw(_para_bytes(senha), bcrypt.gensalt())
    return hash_em_bytes.decode("utf-8")


def conferir_senha(senha_digitada: str, hash_do_banco: str) -> bool:
    """
    Confere se a senha digitada corresponde ao hash guardado.
    Devolve True (bate) ou False (nao bate).

    O try/except existe porque, se o hash estiver corrompido ou vazio,
    o bcrypt levanta um erro. Preferimos responder False a quebrar a tela.
    """
    try:
        return bcrypt.checkpw(
            _para_bytes(senha_digitada),
            hash_do_banco.encode("utf-8"),
        )
    except (ValueError, TypeError, AttributeError):
        return False


# ===============================================================
# PARTE 2: LOGIN
# ===============================================================
def autenticar(db, email: str, senha: str, perfil: str) -> tuple[User | None, str]:
    """
    COMO O LOGIN FUNCIONA NESTE SISTEMA
    -----------------------------------
    Cada CATEGORIA tem a sua propria senha, compartilhada por todas as
    pessoas daquela categoria:

        ESTIPULANTE  -> senha do estipulante
        CORRETORA    -> senha da corretora
        SEGURADORA   -> senha da seguradora

    O e-mail NAO precisa estar cadastrado. Ele serve para identificar
    QUEM entrou, e fica gravado no login_history.

    Ou seja, a conferencia e:
      1. a categoria escolhida existe?
      2. a senha confere com a senha daquela categoria?

    ATENCAO — limitacao conhecida desta escolha:
    como a senha e compartilhada, quem souber a senha da corretora entra
    como corretora. Para tirar o acesso de uma pessoa e preciso trocar a
    senha de todas daquela categoria. E o e-mail digitado nao e conferido,
    entao o registro de quem acessou depende da boa-fe de quem digita.
    Se um dia isso for um problema, a saida e voltar ao login por usuario
    individual — o campo email da tabela users continua preparado para isso.

    Devolve DOIS valores:
      - a conta da categoria (ou None, se falhou)
      - o motivo da falha (ou "" se deu certo), gravado para auditoria
    """
    email = (email or "").strip().lower()

    # 1. o e-mail tem cara de e-mail?
    if not formato_de_email_valido(email):
        return None, "formato de e-mail invalido"

    # 2. a categoria escolhida existe no banco?
    conta = db.query(User).filter(User.perfil == perfil).first()
    if conta is None:
        return None, "categoria inexistente"

    # 3. a senha confere com a senha da categoria?
    if not conferir_senha(senha, conta.senha_hash):
        return None, "senha incorreta para a categoria"

    # 4. a categoria esta ativa?
    if not conta.ativo:
        return None, "categoria inativa"

    # 5. o e-mail esta na lista de acesso autorizado?
    #    (so vale se a exigencia estiver ligada na tela de Controle de Acesso)
    if exigir_autorizacao(db) and not email_autorizado(db, email, perfil):
        return None, "e-mail fora da lista de acesso autorizado"

    return conta, ""


# --- Conferencia do e-mail --------------------------------------

# Regra simples de formato: alguma-coisa @ alguma-coisa . alguma-coisa
# Nao tenta cobrir todos os casos exoticos da internet, so os erros comuns
# (faltou o @, faltou o ponto, tem espaco no meio).
FORMATO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def formato_de_email_valido(email: str) -> bool:
    """
    Confere se o texto TEM CARA de e-mail.

    ATENCAO — o que isto NAO faz:
    nao prova que a caixa de e-mail existe nem que a pessoa e dona dela.
    Isso so um e-mail de confirmacao provaria, e para enviar e-mail seria
    preciso configurar um servidor de envio (SMTP), que o projeto ainda
    nao tem. Por isso o controle de verdade e a lista de acesso
    autorizado, logo abaixo.
    """
    return bool(FORMATO_EMAIL.match((email or "").strip()))


def exigir_autorizacao(db) -> bool:
    """
    A exigencia da lista de acesso esta ligada?

    Fica guardado no banco (tabela settings) e nao no arquivo .env,
    para o estipulante conseguir ligar e desligar pela propria tela.
    """
    config_banco = (
        db.query(Setting).filter(Setting.chave == CHAVE_EXIGIR_AUTORIZACAO).first()
    )
    return config_banco is not None and config_banco.valor == "sim"


def email_autorizado(db, email: str, perfil: str) -> bool:
    """
    Percorre a lista de acesso e responde se este e-mail pode entrar
    nesta categoria.

    Basta UMA autorizacao servir (por e-mail exato ou por dominio).
    """
    for autorizacao in db.query(AuthorizedEmail).filter(
        AuthorizedEmail.ativo.is_(True)
    ):
        if autorizacao.vale_para(email, perfil):
            return True
    return False


def registrar_login(
    db,
    email: str,
    perfil: str,
    sucesso: bool,
    motivo: str = "",
    usuario: User | None = None,
    ip: str | None = None,
) -> None:
    """
    Grava a tentativa de acesso na tabela login_history.

    Registramos TODAS as tentativas, inclusive as que falharam. Isso
    atende o requisito de "registrar data e hora do login" e ainda
    permite perceber tentativas de acesso indevido.

    A data e hora sao preenchidas sozinhas pelo banco (veja models.py).
    """
    db.add(
        LoginHistory(
            user_id=usuario.id if usuario else None,
            email_informado=(email or "").strip().lower(),
            perfil_informado=perfil or "",
            sucesso=sucesso,
            motivo=motivo or None,
            ip=ip,
        )
    )
    db.commit()


# ===============================================================
# PARTE 3: SESSAO (lembrar quem esta logado)
# ===============================================================
# COMO FUNCIONA, EM UMA FRASE:
# depois do login, mandamos para o navegador um "cracha" (cookie) com o
# numero do usuario. Esse cracha vai ASSINADO com a SECRET_KEY, entao se
# alguem tentar editar o numero na marra, a assinatura quebra e o cracha
# e recusado.

NOME_DO_COOKIE = "sessao_central"

_assinador = URLSafeSerializer(config.SECRET_KEY, salt="sessao-central-seguros")


def criar_cookie_sessao(resposta, usuario: User, email: str = "") -> None:
    """
    Coloca o cracha assinado na resposta que vai para o navegador.

    Guardamos duas coisas: a categoria (user_id) e o e-mail que a pessoa
    digitou. O e-mail aparece no canto da tela, para quem estiver usando
    saber com qual identificacao entrou.
    """
    valor = _assinador.dumps({"user_id": usuario.id, "email": email})
    resposta.set_cookie(
        key=NOME_DO_COOKIE,
        value=valor,
        httponly=True,   # o JavaScript da pagina nao consegue ler o cookie
        samesite="lax",  # o cookie nao e enviado a partir de outros sites
        secure=config.COOKIE_SEGURO,  # em HTTPS, so trafega criptografado
        max_age=60 * 60 * 8,  # vale por 8 horas
    )


def apagar_cookie_sessao(resposta) -> None:
    """Tira o cracha do navegador (usado no logout)."""
    resposta.delete_cookie(NOME_DO_COOKIE)


def _abrir_cookie(request) -> dict | None:
    """Le e confere a assinatura do cracha. Devolve o conteudo ou None."""
    valor = request.cookies.get(NOME_DO_COOKIE)
    if not valor:
        return None
    try:
        return _assinador.loads(valor)
    except BadSignature:
        return None  # cookie adulterado ou assinado com outra chave


def ler_usuario_do_cookie(db, request) -> User | None:
    """
    Le o cracha e devolve a categoria de acesso correspondente.

    Devolve None se: nao ha cookie, a assinatura nao confere,
    a categoria sumiu do banco ou esta inativa.
    """
    dados = _abrir_cookie(request)
    if dados is None:
        return None

    usuario = db.query(User).filter(User.id == dados.get("user_id")).first()
    if usuario is None or not usuario.ativo:
        return None

    return usuario


def ler_email_do_cookie(request) -> str:
    """Devolve o e-mail que a pessoa digitou ao entrar (ou vazio)."""
    dados = _abrir_cookie(request)
    return (dados or {}).get("email", "")


# ===============================================================
# PARTE 4: PERMISSOES
# ===============================================================
# Regra simples: cada perfil tem uma LISTA do que NAO pode acessar.
# Lista vazia = pode tudo.
#
# As regras vieram do enunciado do projeto:
#   CORRETORA   nao acessa sinistros
#   SEGURADORA  nao acessa comissoes nem inadimplencia
MODULOS_BLOQUEADOS = {
    # O estipulante e quem administra o sistema, entao ve tudo,
    # inclusive o Controle de Acesso.
    "ESTIPULANTE": [],
    "CORRETORA": ["sinistros", "acessos"],
    "SEGURADORA": ["comissoes", "inadimplencia", "acessos"],
}


def pode_acessar(perfil: str, modulo: str) -> bool:
    """Responde True ou False para 'este perfil pode abrir este modulo?'."""
    return modulo not in MODULOS_BLOQUEADOS.get(perfil, [])
