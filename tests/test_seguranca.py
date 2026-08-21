"""
test_seguranca.py
-----------------
Trava as correcoes de seguranca encontradas na auditoria.

Cada teste aqui corresponde a um defeito que EXISTIU e foi corrigido.
Se algum voltar, este arquivo acusa.

  1. XSS: dado do banco nao pode virar HTML executavel
  2. Forca bruta: excesso de tentativas e bloqueado
  3. SECRET_KEY padrao e recusada em producao
  4. Logout invalida a sessao no servidor
  5. Fuso horario de Brasilia
  6. Chaves de API por parceiro, guardadas com hash
  7. Toda chamada da API e registrada
  8. Paginas de erro proprias
  9. Paginacao da carteira

COMO RODAR (com o venv ativado, na raiz do projeto):
    python tests/test_seguranca.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app import assistente, auth, config, tempo  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    ActiveSession,
    ApiCall,
    ApiKey,
    LoginHistory,
    Policy,
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


def logar(email="seguranca@sebraeprev.com.br"):
    c = TestClient(app)
    c.post("/login", data={"email": email, "senha": config.SENHA_ESTIPULANTE,
                           "perfil": "ESTIPULANTE"}, follow_redirects=False)
    return c


def limpar_tentativas():
    """Apaga o historico para o bloqueio por forca bruta nao interferir."""
    db = SessionLocal()
    db.query(LoginHistory).delete()
    db.commit()
    db.close()


def limpar_sessoes():
    """
    Apaga as sessoes abertas.

    IMPORTANTE: outros arquivos de teste tambem fazem login, e as sessoes
    deles podem ficar na tabela. Sem esta limpeza, um teste que conta
    sessoes por e-mail acusaria falha por causa de resto de outro teste.
    Foi exatamente o que aconteceu aqui na primeira versao.
    """
    db = SessionLocal()
    db.query(ActiveSession).delete()
    db.commit()
    db.close()


print("\n=== TESTANDO AS CORRECOES DE SEGURANCA ===\n")
limpar_tentativas()
limpar_sessoes()

# ---------------------------------------------------------------
# 1. XSS
# ---------------------------------------------------------------
print("1. Dado do banco nao pode virar HTML executavel")

# Cada uma destas tentativas e um jeito diferente de injetar codigo.
ATAQUES = [
    '<img src=x onerror="alert(1)">',
    "<script>alert(1)</script>",
    '"><svg onload=alert(1)>',
    "<iframe src=javascript:alert(1)>",
]

db = SessionLocal()
alvo = db.query(Policy).first()
original = alvo.participante

for ataque in ATAQUES:
    alvo.participante = ataque
    db.commit()

    # Pergunta que faz o assistente montar o detalhe daquela apolice.
    resposta = assistente.responder(db, f"me mostra a {alvo.numero_apolice}")

    # A conferencia certa: o texto do ataque NAO pode aparecer igual ao
    # que foi gravado. Se estiver escapado, o "<" virou "&lt;" e a
    # comparacao falha — que e o que queremos.
    #
    # Cuidado com o teste ingenuo: procurar por "onerror=" da falso
    # positivo, porque essa parte aparece intacta dentro do texto
    # escapado (&lt;img src=x onerror=&quot;...) e ali ela e inofensiva,
    # ja que nenhuma tag foi aberta.
    verificar(f'"{ataque[:28]}…" sai escapado', ataque not in resposta,
              f"vazou cru em: {resposta[:110]}")

    # E, por garantia, nenhuma tag nova pode ter sido criada.
    verificar("  nenhuma tag foi aberta",
              not re.search(r"<(script|img|svg|iframe|object|embed)\b",
                            resposta, re.IGNORECASE))

# Tambem nas respostas de LISTA, nao so no detalhe.
alvo.participante = '<script>alert("lista")</script>'
alvo.status = "A renovar"
db.commit()
resposta = assistente.responder(db, "quais apolices vencem este mes?")
verificar("  tambem escapa nas listagens", "<script" not in resposta,
          f"vazou em: {resposta[:110]}")

alvo.participante = original
alvo.status = "Ativa"
db.commit()
db.close()

# ---------------------------------------------------------------
# 2. FORCA BRUTA
# ---------------------------------------------------------------
print("\n2. Excesso de tentativas de senha e bloqueado")

limpar_tentativas()
cliente = TestClient(app)
bloqueou_em = None

for i in range(1, 30):
    r = cliente.post("/login", data={"email": f"chute{i}@x.com",
                                     "senha": f"errada{i}",
                                     "perfil": "ESTIPULANTE"},
                     follow_redirects=False)
    if r.status_code == 429:
        bloqueou_em = i
        break

verificar("bloqueia depois de varias tentativas erradas", bloqueou_em is not None,
          "fiz 29 tentativas e nenhuma foi bloqueada")
if bloqueou_em:
    print(f"           (bloqueou na tentativa {bloqueou_em})")
    verificar(f"  bloqueia em no maximo 12 tentativas", bloqueou_em <= 12,
              f"levou {bloqueou_em}")

    # Bloqueado mesmo com a senha CERTA — e isso que trava o ataque.
    r = cliente.post("/login", data={"email": "certo@sebraeprev.com.br",
                                     "senha": config.SENHA_ESTIPULANTE,
                                     "perfil": "ESTIPULANTE"},
                     follow_redirects=False)
    verificar("  bloqueia mesmo com a senha correta", r.status_code == 429,
              f"veio {r.status_code}")
    verificar("  avisa quanto tempo falta", "minuto" in r.text.lower())

    db = SessionLocal()
    ultimo = db.query(LoginHistory).order_by(LoginHistory.id.desc()).first()
    db.close()
    verificar("  o bloqueio fica registrado",
              ultimo is not None and "bloqueado" in (ultimo.motivo or ""))

limpar_tentativas()

# ---------------------------------------------------------------
# 3. SECRET_KEY
# ---------------------------------------------------------------
print("\n3. SECRET_KEY insegura e recusada")

verificar("existe a conferencia de seguranca", hasattr(config, "conferir_seguranca"))
verificar("  a SECRET_KEY atual nao e a padrao",
          config.SECRET_KEY != config.SECRET_KEY_INSEGURA)
verificar("  a SECRET_KEY tem tamanho suficiente", len(config.SECRET_KEY) >= 32,
          f"tem {len(config.SECRET_KEY)}")

# Simula o cenario perigoso: chave padrao + producao.
guardado = (config.SECRET_KEY, config.EM_PRODUCAO)
config.SECRET_KEY = config.SECRET_KEY_INSEGURA
problemas = config.conferir_seguranca()
verificar("  com a chave padrao, acusa problema", len(problemas) > 0)
verificar("  e explica como resolver",
          any("secrets.token_hex" in p for p in problemas))
config.SECRET_KEY = guardado[0]

# ---------------------------------------------------------------
# 4. LOGOUT
# ---------------------------------------------------------------
print("\n4. Logout invalida a sessao no servidor")

limpar_sessoes()

c = logar("logout@sebraeprev.com.br")
cookie = c.cookies.get("sessao_central")
verificar("o cookie foi criado", bool(cookie))

r = c.get("/dashboard")
verificar("  entra normalmente", r.status_code == 200)

c.post("/logout", follow_redirects=False)

# Reusa o cookie COPIADO num navegador novo.
copia = TestClient(app)
copia.cookies.set("sessao_central", cookie)
r = copia.get("/dashboard", follow_redirects=False)
verificar("  o cookie copiado NAO funciona depois do logout",
          r.status_code == 303 and r.headers.get("location") == "/login",
          f"veio {r.status_code} — o cookie copiado ainda entra!")

# Duas pessoas na mesma categoria: o logout de uma nao derruba a outra.
ana = logar("ana@sebraeprev.com.br")
bruno = logar("bruno@sebraeprev.com.br")
ana.post("/logout", follow_redirects=False)
verificar("  o logout de uma pessoa nao derruba a outra",
          bruno.get("/dashboard").status_code == 200,
          "o Bruno caiu quando a Ana saiu")

db = SessionLocal()
verificar("  a sessao sai da tabela ao fazer logout",
          db.query(ActiveSession).filter(
              ActiveSession.email == "ana@sebraeprev.com.br").count() == 0)
db.close()

# ---------------------------------------------------------------
# 5. FUSO HORARIO
# ---------------------------------------------------------------
print("\n5. Fuso horario de Brasilia")

import datetime as _dt  # noqa: E402

utc = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
brasilia = tempo.agora()
diferenca = round((utc - brasilia).total_seconds() / 3600)

verificar("agora() devolve o horario de Brasilia (UTC-3)", diferenca == 3,
          f"diferenca para UTC: {diferenca}h")
verificar("  hoje() acompanha", tempo.hoje() == brasilia.date())

# O registro de acesso precisa usar esse fuso.
limpar_tentativas()
logar("fuso@sebraeprev.com.br")
db = SessionLocal()
registro = db.query(LoginHistory).order_by(LoginHistory.id.desc()).first()
db.close()
if registro:
    minutos = abs((registro.data_hora - tempo.agora()).total_seconds() / 60)
    verificar("  o historico de acesso grava na hora de Brasilia", minutos < 5,
              f"gravou {minutos:.0f} minutos fora")

# ---------------------------------------------------------------
# 6. CHAVES DE API
# ---------------------------------------------------------------
print("\n6. Chaves de API por parceiro")

admin = logar("admin@sebraeprev.com.br")
r = admin.post("/api-chaves/criar",
               data={"nome": "Parceiro Teste", "observacao": "teste automatico"})
achado = re.search(r'<code id="chaveNova">([^<]+)</code>', r.text)
chave = achado.group(1) if achado else None

verificar("cria uma chave e mostra uma vez", bool(chave))

if chave:
    db = SessionLocal()
    registro = db.query(ApiKey).filter(ApiKey.nome == "Parceiro Teste").first()
    verificar("  guarda o HASH, nao a chave",
              registro is not None and registro.chave_hash.startswith("$2b$"))
    verificar("  a chave em texto nao esta no banco",
              registro is not None and chave not in registro.chave_hash)
    verificar("  guarda o inicio para identificar",
              registro is not None and chave.startswith(registro.inicio))
    chave_id = registro.id
    db.close()

    api = TestClient(app)
    verificar("  a chave nova funciona",
              api.get("/api/v1/status",
                      headers={"X-API-Key": chave}).status_code == 200)
    verificar("  chave errada e recusada",
              api.get("/api/v1/status",
                      headers={"X-API-Key": "cis_errada"}).status_code == 401)
    verificar("  sem chave e recusado",
              api.get("/api/v1/status").status_code == 401)

    # Bloquear tira o acesso na hora.
    admin.post(f"/api-chaves/alternar/{chave_id}")
    verificar("  bloquear a chave tira o acesso",
              api.get("/api/v1/status",
                      headers={"X-API-Key": chave}).status_code == 401)

    admin.post(f"/api-chaves/remover/{chave_id}")
    db = SessionLocal()
    verificar("  remover apaga a chave",
              db.query(ApiKey).filter(ApiKey.nome == "Parceiro Teste").first() is None)
    db.close()

# ---------------------------------------------------------------
# 7. REGISTRO DE CHAMADAS
# ---------------------------------------------------------------
print("\n7. Toda chamada da API e registrada")

db = SessionLocal()
antes = db.query(ApiCall).count()
db.close()

api = TestClient(app)
api.get("/api/v1/status", headers={"X-API-Key": config.API_KEY})
api.get("/api/v1/status", headers={"X-API-Key": "invalida"})
api.get("/api/v1/status")

db = SessionLocal()
depois = db.query(ApiCall).count()
verificar("as 3 chamadas foram registradas", depois == antes + 3,
          f"registrou {depois - antes}")

recusadas = db.query(ApiCall).filter(ApiCall.status == 401).count()
verificar("  as recusadas tambem entram no registro", recusadas >= 2)

ultima = db.query(ApiCall).order_by(ApiCall.id.desc()).first()
verificar("  guarda metodo, caminho e resultado",
          ultima is not None and ultima.metodo == "GET"
          and ultima.caminho.startswith("/api/") and ultima.status > 0)
db.close()

r = admin.get("/api-chaves/exportar")
verificar("  da para exportar o registro", r.status_code == 200)

# ---------------------------------------------------------------
# 8. PAGINAS DE ERRO
# ---------------------------------------------------------------
print("\n8. Paginas de erro proprias")

c = logar()
r = c.get("/endereco-que-nao-existe")
verificar("404 mostra a nossa pagina", r.status_code == 404
          and "Página não encontrada" in r.text)
verificar("  com o logo do sistema", "sebraeprev.webp" in r.text)

r = c.get("/api/v1/nao-existe")
verificar("na API, o 404 responde JSON e nao HTML",
          "application/json" in r.headers.get("content-type", ""))

# ---------------------------------------------------------------
# 9. PAGINACAO
# ---------------------------------------------------------------
print("\n9. Paginacao da carteira")

db = SessionLocal()
total = db.query(Policy).count()
db.close()

r = c.get("/seguros")
linhas = r.text.count("<tr>") - 1
verificar(f"a primeira pagina nao mostra tudo de uma vez ({total} apolices)",
          linhas <= 51, f"desenhou {linhas} linhas")
verificar("  informa o total", str(total) in r.text)

if total > 50:
    verificar("  mostra a navegacao entre paginas", "paginacao" in r.text)
    r2 = c.get("/seguros?pagina=2")
    verificar("  a pagina 2 abre", r2.status_code == 200)
    verificar("  e mostra registros diferentes", r.text != r2.text)

r = c.get("/seguros?pagina=9999")
verificar("  pagina alta demais cai na ultima", r.status_code == 200)

r = c.get("/seguros?status=Vencida")
verificar("  filtro por situacao funciona", r.status_code == 200)

# ---------------------------------------------------------------
# LIMPEZA
# ---------------------------------------------------------------
db = SessionLocal()
db.query(LoginHistory).delete()
db.query(ActiveSession).delete()
db.query(ApiCall).delete()
db.commit()
db.close()

print("\n" + "=" * 56)
print(f"RESULTADO: {passou} passaram, {falhou} falharam")
print("=" * 56 + "\n")

sys.exit(1 if falhou else 0)
