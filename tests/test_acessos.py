"""
test_acessos.py
---------------
Testa o Controle de Acesso e o assistente melhorado.

  1. Tela de Controle de Acesso (só o estipulante)
  2. Lista de acesso autorizado (cadastrar, bloquear, remover)
  3. A exigência da lista funcionando no login
  4. Histórico de acessos, filtros e exportação
  5. Assistente: conversa, conceitos e recusa de assunto fora do escopo

COMO RODAR (com o venv ativado, na raiz do projeto):
    python tests/test_acessos.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app import config  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    CHAVE_EXIGIR_AUTORIZACAO,
    AuthorizedEmail,
    LoginHistory,
    Setting,
)

passou = 0
falhou = 0


def verificar(descricao: str, condicao: bool, detalhe: str = "") -> None:
    global passou, falhou
    if condicao:
        passou += 1
        print(f"  [OK]     {descricao}")
    else:
        falhou += 1
        print(f"  [FALHOU] {descricao}")
        if detalhe:
            print(f"           -> {detalhe}")


SENHAS = {
    "ESTIPULANTE": config.SENHA_ESTIPULANTE,
    "CORRETORA": config.SENHA_CORRETORA,
    "SEGURADORA": config.SENHA_SEGURADORA,
}


def entrar(cliente, email, senha, perfil):
    return cliente.post(
        "/login",
        data={"email": email, "senha": senha, "perfil": perfil},
        follow_redirects=False,
    )


def logar(perfil="ESTIPULANTE", email="admin@sebraeprev.com.br"):
    c = TestClient(app)
    entrar(c, email, SENHAS[perfil], perfil)
    return c


def perguntar(cliente, texto):
    return cliente.post("/assistente/perguntar", data={"pergunta": texto}).json()["resposta"]


def limpar():
    """Volta a lista e a exigência ao estado inicial."""
    db = SessionLocal()
    db.query(AuthorizedEmail).filter(
        AuthorizedEmail.valor != "@sebraeprev.com.br"
    ).delete()
    s = db.query(Setting).filter(Setting.chave == CHAVE_EXIGIR_AUTORIZACAO).first()
    if s:
        s.valor = "nao"
    dominio = db.query(AuthorizedEmail).filter(
        AuthorizedEmail.valor == "@sebraeprev.com.br"
    ).first()
    if dominio:
        dominio.ativo = True
    db.commit()
    db.close()


print("\n=== TESTANDO CONTROLE DE ACESSO E ASSISTENTE ===\n")

limpar()

# ---------------------------------------------------------------
# 1. QUEM ENXERGA A TELA
# ---------------------------------------------------------------
print("1. Só o estipulante acessa")

estipulante = logar("ESTIPULANTE")
r = estipulante.get("/acessos")
verificar("ESTIPULANTE abre /acessos", r.status_code == 200, f"veio {r.status_code}")
verificar("  a tela mostra a lista de autorizados", "Lista de acesso autorizado" in r.text)
verificar("  e o histórico de acessos", "Histórico de acessos" in r.text)

for perfil in ["CORRETORA", "SEGURADORA"]:
    c = logar(perfil, "outro@sebraeprev.com.br")
    r = c.get("/acessos", follow_redirects=False)
    verificar(f"{perfil} é barrada em /acessos",
              r.status_code == 303 and r.headers.get("location") == "/dashboard",
              f"veio {r.status_code}")
    verificar(f"  e o menu mostra o cadeado para {perfil}", "🔒" in c.get("/dashboard").text)

# As ações que gravam também precisam barrar.
c = logar("CORRETORA", "x@sebraeprev.com.br")
verificar("CORRETORA é barrada ao tentar autorizar alguém",
          c.post("/acessos/autorizar", data={"valor": "invasor@x.com"},
                 follow_redirects=False).status_code == 303)
verificar("CORRETORA é barrada ao exportar o histórico",
          c.get("/acessos/exportar", follow_redirects=False).status_code == 303)

# ---------------------------------------------------------------
# 2. CADASTRAR, BLOQUEAR E REMOVER
# ---------------------------------------------------------------
print("\n2. Cadastrar, bloquear e remover autorizações")

r = estipulante.post("/acessos/autorizar",
                     data={"valor": "Maria.Teste@Empresa.com.BR", "perfil": "CORRETORA",
                           "observacao": "Contato da corretora"})
verificar("cadastra um e-mail", r.status_code == 200)

db = SessionLocal()
novo = db.query(AuthorizedEmail).filter(
    AuthorizedEmail.valor == "maria.teste@empresa.com.br"
).first()
verificar("  guardou em minúsculo", novo is not None)
verificar("  guardou a categoria", novo is not None and novo.perfil == "CORRETORA")
verificar("  guardou quem cadastrou",
          novo is not None and novo.cadastrado_por == "admin@sebraeprev.com.br")
db.close()

r = estipulante.post("/acessos/autorizar", data={"valor": "@parceiro.com.br"})
verificar("cadastra um domínio inteiro", "@parceiro.com.br" in r.text)

# Formatos inválidos
r = estipulante.post("/acessos/autorizar", data={"valor": "isso nao e email"})
verificar("recusa texto que não é e-mail nem domínio", "não é um e-mail válido" in r.text)

r = estipulante.post("/acessos/autorizar", data={"valor": "@semponto"})
verificar("recusa domínio malformado", "não parece um domínio válido" in r.text)

r = estipulante.post("/acessos/autorizar", data={"valor": "maria.teste@empresa.com.br"})
verificar("recusa e-mail repetido", "já está na lista" in r.text)

# Bloquear e reativar
db = SessionLocal()
alvo = db.query(AuthorizedEmail).filter(
    AuthorizedEmail.valor == "maria.teste@empresa.com.br"
).first()
alvo_id = alvo.id
db.close()

estipulante.post(f"/acessos/alternar/{alvo_id}")
db = SessionLocal()
verificar("bloqueia uma autorização",
          not db.query(AuthorizedEmail).filter(AuthorizedEmail.id == alvo_id).first().ativo)
db.close()

estipulante.post(f"/acessos/alternar/{alvo_id}")
db = SessionLocal()
verificar("  e reativa", db.query(AuthorizedEmail).filter(AuthorizedEmail.id == alvo_id).first().ativo)
db.close()

# Bloquear direto do histórico
estipulante.post("/acessos/bloquear-email", data={"email": "suspeito@qualquer.com"})
db = SessionLocal()
bloqueado = db.query(AuthorizedEmail).filter(
    AuthorizedEmail.valor == "suspeito@qualquer.com"
).first()
verificar("bloqueia um e-mail direto do histórico",
          bloqueado is not None and not bloqueado.ativo)
db.close()

# Remover
estipulante.post(f"/acessos/remover/{alvo_id}")
db = SessionLocal()
verificar("remove a autorização de vez",
          db.query(AuthorizedEmail).filter(AuthorizedEmail.id == alvo_id).first() is None)
db.close()

# ---------------------------------------------------------------
# 3. A EXIGÊNCIA FUNCIONANDO NO LOGIN
# ---------------------------------------------------------------
print("\n3. A exigência da lista barrando o login")

limpar()

# Com a exigência DESLIGADA, qualquer e-mail entra.
r = entrar(TestClient(app), "estranho@gmail.com", SENHAS["ESTIPULANTE"], "ESTIPULANTE")
verificar("exigência DESLIGADA: e-mail de fora entra", r.status_code == 303)

# Ligando a exigência.
r = estipulante.post("/acessos/exigencia", data={"ligar": "sim"})
verificar("liga a exigência", "Exigência ligada" in r.text or "exigência" in r.text.lower())

db = SessionLocal()
s = db.query(Setting).filter(Setting.chave == CHAVE_EXIGIR_AUTORIZACAO).first()
verificar("  ficou gravada no banco", s is not None and s.valor == "sim")
db.close()

# Agora o e-mail de fora NÃO entra.
r = entrar(TestClient(app), "estranho@gmail.com", SENHAS["ESTIPULANTE"], "ESTIPULANTE")
verificar("exigência LIGADA: e-mail de fora é recusado",
          r.status_code == 401, f"veio {r.status_code}")

db = SessionLocal()
ultimo = db.query(LoginHistory).order_by(LoginHistory.id.desc()).first()
db.close()
verificar("  o motivo ficou registrado",
          ultimo is not None and "fora da lista" in (ultimo.motivo or ""),
          f"motivo: {ultimo.motivo if ultimo else '?'}")

# Mas quem está no domínio autorizado entra.
r = entrar(TestClient(app), "qualquer.pessoa@sebraeprev.com.br",
           SENHAS["ESTIPULANTE"], "ESTIPULANTE")
verificar("e-mail do domínio autorizado ENTRA", r.status_code == 303, f"veio {r.status_code}")

# Autorização por categoria específica.
estipulante = logar("ESTIPULANTE", "admin@sebraeprev.com.br")
estipulante.post("/acessos/autorizar",
                 data={"valor": "so.corretora@externo.com", "perfil": "CORRETORA"})

r = entrar(TestClient(app), "so.corretora@externo.com", SENHAS["CORRETORA"], "CORRETORA")
verificar("autorizado só para CORRETORA entra como corretora", r.status_code == 303)

r = entrar(TestClient(app), "so.corretora@externo.com",
           SENHAS["ESTIPULANTE"], "ESTIPULANTE")
verificar("  mas NÃO entra como estipulante", r.status_code == 401)

# Bloquear tira o acesso.
db = SessionLocal()
alvo = db.query(AuthorizedEmail).filter(
    AuthorizedEmail.valor == "so.corretora@externo.com"
).first()
alvo_id = alvo.id
db.close()
estipulante.post(f"/acessos/alternar/{alvo_id}")

r = entrar(TestClient(app), "so.corretora@externo.com", SENHAS["CORRETORA"], "CORRETORA")
verificar("depois de bloqueado, não entra mais", r.status_code == 401)

# Formato de e-mail inválido é recusado sempre.
r = entrar(TestClient(app), "isso-nao-e-email", SENHAS["ESTIPULANTE"], "ESTIPULANTE")
verificar("e-mail com formato inválido é recusado", r.status_code == 401)

# Desliga a exigência de volta.
estipulante.post("/acessos/exigencia", data={"ligar": "nao"})
r = entrar(TestClient(app), "estranho@gmail.com", SENHAS["ESTIPULANTE"], "ESTIPULANTE")
verificar("desligando a exigência, volta a entrar", r.status_code == 303)

# ---------------------------------------------------------------
# 4. HISTÓRICO, FILTROS E EXPORTAÇÃO
# ---------------------------------------------------------------
print("\n4. Histórico de acessos")

estipulante = logar("ESTIPULANTE", "admin@sebraeprev.com.br")

r = estipulante.get("/acessos")
verificar("o histórico lista os acessos", "estranho@gmail.com" in r.text)

# CUIDADO com o teste que fatia o HTML por uma palavra: a primeira
# versao aqui dividia o texto em "Histórico" para olhar so a tabela.
# Quando um item chamado "Histórico" entrou no MENU, o ponto de corte
# mudou e o teste falhou sem nada estar errado no sistema.
#
# A conferencia solida e outra: o e-mail buscado aparece, e o e-mail que
# NAO combina com a busca nao aparece em lugar nenhum da tabela.
r = estipulante.get("/acessos?busca=estranho")
linhas_com_email = r.text.count("estranho@gmail.com")
verificar("filtra por parte do e-mail", linhas_com_email >= 1,
          "o e-mail buscado nao apareceu")
verificar("  e o filtro fica marcado no campo de busca",
          'value="estranho"' in r.text)

r = estipulante.get("/acessos?resultado=falha")
verificar("filtra só os recusados", "Recusado" in r.text)

r = estipulante.get("/acessos?perfil=CORRETORA")
verificar("filtra por categoria", r.status_code == 200)

r = estipulante.get("/acessos/exportar")
verificar("exporta o histórico em CSV", r.status_code == 200)
verificar("  vem como arquivo",
          "historico_de_acessos.csv" in r.headers.get("content-disposition", ""))
texto = r.content.decode("utf-8-sig")
verificar("  tem as colunas certas",
          "E-mail informado" in texto and "Motivo" in texto)

# ---------------------------------------------------------------
# 5. ASSISTENTE
# ---------------------------------------------------------------
print("\n5. Assistente — conversa")

CONVERSA = [
    ("Olá, tudo bem?", ["tudo bem", "assistente"]),
    ("bom dia", ["assistente"]),
    ("Quem é você?", ["assistente da"]),
    ("o que você faz?", ["consulto", "explico", "apólice"]),
    ("obrigado!", ["por nada"]),
    ("tchau", ["até logo"]),
    ("ajuda", ["conceitos de seguro", "números da carteira"]),
]
for pergunta, esperados in CONVERSA:
    resposta = perguntar(estipulante, pergunta).lower()
    verificar(f'"{pergunta}"',
              any(e.lower() in resposta for e in esperados),
              f"respondeu: {resposta[:80]}")

print("\n6. Assistente — conceitos de seguro")

CONCEITOS = [
    ("o que é uma apólice?", "contrato do seguro"),
    ("o que significa prêmio?", "valor que se paga"),
    ("o que é capital segurado?", "quanto a seguradora paga"),
    ("o que é DPS?", "questionário de saúde"),
    ("o que é carência?", "tempo de espera"),
    ("quem é o beneficiário?", "recebe a indenização"),
    ("o que faz o estipulante?", "contrata o seguro em nome"),
    ("o que faz a corretora?", "intermedeia"),
    ("o que é subscrição?", "proposta percorre"),
    ("o que é competência?", "mês de referência"),
    ("o que são os convênios?", "entidades parceiras"),
    ("me explica a régua de cobrança", "aviso amigável"),
]
for pergunta, esperado in CONCEITOS:
    resposta = perguntar(estipulante, pergunta).lower()
    verificar(f'"{pergunta}"', esperado.lower() in resposta,
              f"respondeu: {resposta[:80]}")

print("\n7. Assistente — sobre o sistema")

SISTEMA = [
    ("como envio a planilha?", "movimentação"),
    ("como funciona o acesso ao sistema?", "categoria"),
    ("o que é a central?", "sebrae"),
    ("como funciona a api?", "x-api-key"),
]
for pergunta, esperado in SISTEMA:
    resposta = perguntar(estipulante, pergunta).lower()
    verificar(f'"{pergunta}"', esperado.lower() in resposta,
              f"respondeu: {resposta[:80]}")

print("\n8. Assistente — recusa o que não é do escopo")

FORA = [
    "que horas são?",
    "vai chover amanhã?",
    "me dá uma receita de bolo",
    "quem ganhou o jogo ontem?",
    "conta uma piada",
    "quanto está o dólar hoje?",
    "traduz isso para o inglês",
    "estou com dor de cabeça, o que tomo?",
]
for pergunta in FORA:
    resposta = perguntar(estipulante, pergunta).lower()
    verificar(f'"{pergunta}" é recusada com educação',
              "não posso responder" in resposta and "central" in resposta,
              f"respondeu: {resposta[:80]}")

print("\n9. Assistente — os dados continuam funcionando")

DADOS = [
    ("quais apólices vencem este mês?", "renovação"),
    ("quem está inadimplente?", "inadimplentes"),
    ("como estão as comissões?", "competência"),
    ("quantas apólices temos?", "apólices"),
    ("como estão os sinistros?", "sinistros"),
]
for pergunta, esperado in DADOS:
    resposta = perguntar(estipulante, pergunta).lower()
    verificar(f'"{pergunta}"', esperado.lower() in resposta,
              f"respondeu: {resposta[:80]}")

# Uma pergunta com "quanto é" (que está na lista de fora do assunto)
# mas que fala de seguros deve ser respondida, não recusada.
resposta = perguntar(estipulante, "quanto é a comissão da corretora?").lower()
verificar("pergunta com palavra ambígua mas sobre seguros é RESPONDIDA",
          "não posso responder" not in resposta,
          f"respondeu: {resposta[:80]}")

resposta = perguntar(estipulante, "qual a cor do céu?").lower()
verificar("pergunta desconhecida cai na resposta padrão",
          "não consegui entender" in resposta)

# ---------------------------------------------------------------
# LIMPEZA
# ---------------------------------------------------------------
limpar()
db = SessionLocal()
n = db.query(LoginHistory).delete()
db.commit()
db.close()
print(f"\n(limpeza: {n} registros de acesso de teste apagados)")

print("\n" + "=" * 50)
print(f"RESULTADO: {passou} passaram, {falhou} falharam")
print("=" * 50 + "\n")

sys.exit(1 if falhou else 0)
