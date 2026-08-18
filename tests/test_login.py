"""
test_login.py
-------------
Testa o login, a validacao de perfil, o registro de acesso e as permissoes.

COMO RODAR (com o venv ativado, na raiz do projeto):
    python tests/test_login.py

NAO precisa estar com o servidor ligado: o TestClient sobe a aplicacao
por dentro, em memoria, so para o teste.

Cada verificacao mostra [OK] ou [FALHOU].
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app import config  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import LoginHistory  # noqa: E402

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


def contar_acessos() -> int:
    """Quantas linhas existem hoje na tabela login_history."""
    db = SessionLocal()
    try:
        return db.query(LoginHistory).count()
    finally:
        db.close()


def ultimo_acesso() -> LoginHistory | None:
    """O registro de acesso mais recente."""
    db = SessionLocal()
    try:
        return db.query(LoginHistory).order_by(LoginHistory.id.desc()).first()
    finally:
        db.close()


def entrar(cliente: TestClient, email: str, senha: str, perfil: str):
    """Envia o formulario de login. follow_redirects=False para vermos
    o codigo 303 do redirecionamento em vez de ja ir para o dashboard."""
    return cliente.post(
        "/login",
        data={"email": email, "senha": senha, "perfil": perfil},
        follow_redirects=False,
    )


print("\n=== TESTANDO LOGIN, PERFIL E PERMISSOES ===\n")

# ---------------------------------------------------------------
# 1. A tela de login abre?
# ---------------------------------------------------------------
print("1. Tela de login")

cliente = TestClient(app)
resposta = cliente.get("/login")
verificar("GET /login responde 200", resposta.status_code == 200, f"veio {resposta.status_code}")
verificar("  a tela mostra os 3 perfis",
          all(p in resposta.text for p in ["ESTIPULANTE", "CORRETORA", "SEGURADORA"]))
verificar("  a tela tem campo de e-mail e de senha",
          'name="email"' in resposta.text and 'name="senha"' in resposta.text)

# ---------------------------------------------------------------
# 2. Sem login, nao entra
# ---------------------------------------------------------------
print("\n2. Paginas protegidas (sem estar logado)")

for pagina in ["/dashboard", "/seguros", "/sinistros", "/comissoes", "/assistente"]:
    r = TestClient(app).get(pagina, follow_redirects=False)
    verificar(
        f"{pagina} manda de volta para o login",
        r.status_code == 303 and r.headers.get("location") == "/login",
        f"veio {r.status_code} -> {r.headers.get('location')}",
    )

# ---------------------------------------------------------------
# 3. Login com dados certos
# ---------------------------------------------------------------
print("\n3. Login correto")

antes = contar_acessos()
cliente = TestClient(app)
r = entrar(cliente, "estipulante@sebraeprev.com.br", config.SENHA_ESTIPULANTE, "ESTIPULANTE")

verificar("login aceito (303 para /dashboard)",
          r.status_code == 303 and r.headers.get("location") == "/dashboard",
          f"veio {r.status_code} -> {r.headers.get('location')}")
verificar("  o cookie de sessao foi criado", "sessao_central" in r.cookies or
          "sessao_central" in cliente.cookies)

r = cliente.get("/dashboard")
verificar("  o dashboard abre depois do login", r.status_code == 200)
verificar("  o dashboard mostra o nome do usuario", "Luciana Ferraz" in r.text)
verificar("  o dashboard mostra o perfil", "ESTIPULANTE" in r.text)

# ---------------------------------------------------------------
# 4. O acesso foi registrado com data e hora?
# ---------------------------------------------------------------
print("\n4. Registro do acesso (login_history)")

verificar("um novo acesso foi gravado", contar_acessos() == antes + 1,
          f"antes: {antes}, agora: {contar_acessos()}")

registro = ultimo_acesso()
verificar("  marcado como sucesso", registro is not None and registro.sucesso)
verificar("  guardou a data e a hora", registro is not None and registro.data_hora is not None)
verificar("  guardou o e-mail informado",
          registro is not None and registro.email_informado == "estipulante@sebraeprev.com.br")
verificar("  ficou ligado ao usuario", registro is not None and registro.user_id is not None)
if registro:
    print(f"           (registrado em {registro.data_hora.strftime('%d/%m/%Y as %H:%M:%S')})")

# ---------------------------------------------------------------
# 5. Senha errada
# ---------------------------------------------------------------
print("\n5. Senha errada")

antes = contar_acessos()
r = entrar(TestClient(app), "estipulante@sebraeprev.com.br", "senha-errada", "ESTIPULANTE")
verificar("login recusado (401)", r.status_code == 401, f"veio {r.status_code}")
verificar("  a tentativa foi registrada", contar_acessos() == antes + 1)

registro = ultimo_acesso()
verificar("  marcada como falha", registro is not None and not registro.sucesso)
verificar("  o motivo real ficou no banco",
          registro is not None and registro.motivo == "senha incorreta",
          f"motivo: {registro.motivo if registro else '?'}")
verificar("  mas a TELA nao revela qual campo errou",
          "senha incorreta" not in r.text.lower())

# ---------------------------------------------------------------
# 6. E-mail que nao existe
# ---------------------------------------------------------------
print("\n6. E-mail inexistente")

antes = contar_acessos()
r = entrar(TestClient(app), "ninguem@sebraeprev.com.br", "qualquer", "ESTIPULANTE")
verificar("login recusado (401)", r.status_code == 401)
verificar("  a tentativa foi registrada", contar_acessos() == antes + 1)
registro = ultimo_acesso()
verificar("  motivo: e-mail nao encontrado",
          registro is not None and registro.motivo == "e-mail nao encontrado")
verificar("  sem usuario ligado (o e-mail nao existe)",
          registro is not None and registro.user_id is None)

# ---------------------------------------------------------------
# 7. PERFIL ERRADO — o requisito principal do projeto
# ---------------------------------------------------------------
print("\n7. Perfil errado (senha certa, perfil trocado)")

# A corretora tentando entrar como estipulante. Senha certa, perfil errado.
antes = contar_acessos()
r = entrar(TestClient(app), "corretora@sebraeprev.com.br", config.SENHA_CORRETORA, "ESTIPULANTE")
verificar("corretora NAO entra como estipulante", r.status_code == 401, f"veio {r.status_code}")
registro = ultimo_acesso()
verificar("  motivo registrado como perfil incorreto",
          registro is not None and registro.motivo.startswith("perfil nao corresponde"),
          f"motivo: {registro.motivo if registro else '?'}")

# A mesma corretora com o perfil certo tem que entrar normalmente.
c = TestClient(app)
r = entrar(c, "corretora@sebraeprev.com.br", config.SENHA_CORRETORA, "CORRETORA")
verificar("mas entra normalmente como CORRETORA",
          r.status_code == 303 and r.headers.get("location") == "/dashboard")

# Perfil inventado, enviado por fora da tela.
r = entrar(TestClient(app), "estipulante@sebraeprev.com.br", config.SENHA_ESTIPULANTE, "ADMIN")
verificar("perfil inventado ('ADMIN') e recusado", r.status_code == 400, f"veio {r.status_code}")

# ---------------------------------------------------------------
# 8. PERMISSOES POR PERFIL
# ---------------------------------------------------------------
print("\n8. Permissoes de cada perfil")

# Regras do projeto:
#   ESTIPULANTE  pode tudo
#   CORRETORA    nao acessa sinistros
#   SEGURADORA   nao acessa comissoes nem inadimplencia
REGRAS = [
    # (perfil,       email,                            senha,                    modulo,          pode?)
    ("ESTIPULANTE", "estipulante@sebraeprev.com.br", config.SENHA_ESTIPULANTE, "sinistros", True),
    ("ESTIPULANTE", "estipulante@sebraeprev.com.br", config.SENHA_ESTIPULANTE, "comissoes", True),
    ("ESTIPULANTE", "estipulante@sebraeprev.com.br", config.SENHA_ESTIPULANTE, "inadimplencia", True),
    ("CORRETORA", "corretora@sebraeprev.com.br", config.SENHA_CORRETORA, "sinistros", False),
    ("CORRETORA", "corretora@sebraeprev.com.br", config.SENHA_CORRETORA, "comissoes", True),
    ("SEGURADORA", "seguradora@sebraeprev.com.br", config.SENHA_SEGURADORA, "comissoes", False),
    ("SEGURADORA", "seguradora@sebraeprev.com.br", config.SENHA_SEGURADORA, "inadimplencia", False),
    ("SEGURADORA", "seguradora@sebraeprev.com.br", config.SENHA_SEGURADORA, "sinistros", True),
]

for perfil, email, senha, modulo, pode in REGRAS:
    c = TestClient(app)
    entrar(c, email, senha, perfil)

    # Digitando o endereco direto na barra do navegador.
    r = c.get(f"/{modulo}", follow_redirects=False)

    if pode:
        verificar(f"{perfil} PODE abrir /{modulo}",
                  r.status_code == 200, f"veio {r.status_code}")
    else:
        verificar(f"{perfil} e BARRADO em /{modulo}",
                  r.status_code == 303 and r.headers.get("location") == "/dashboard",
                  f"veio {r.status_code} -> {r.headers.get('location')}")

    # O item tambem tem que sumir (com cadeado) do menu lateral.
    if not pode:
        pagina = c.get("/dashboard").text
        verificar(f"  e o menu mostra {modulo} com cadeado", "🔒" in pagina)

# ---------------------------------------------------------------
# 9. Cookie adulterado
# ---------------------------------------------------------------
print("\n9. Cookie adulterado")

c = TestClient(app)
entrar(c, "corretora@sebraeprev.com.br", config.SENHA_CORRETORA, "CORRETORA")
c.cookies.set("sessao_central", "eyJ1c2VyX2lkIjoxfQ.assinatura-falsa")
r = c.get("/dashboard", follow_redirects=False)
verificar("cookie com assinatura falsa e recusado",
          r.status_code == 303 and r.headers.get("location") == "/login",
          f"veio {r.status_code}")

# ---------------------------------------------------------------
# 10. Carteira de apolices e logout
# ---------------------------------------------------------------
print("\n10. Carteira e logout")

c = TestClient(app)
entrar(c, "estipulante@sebraeprev.com.br", config.SENHA_ESTIPULANTE, "ESTIPULANTE")

r = c.get("/seguros")
verificar("a carteira abre", r.status_code == 200)
verificar("  mostra a apolice AP-2041 do prototipo", "AP-2041" in r.text)
verificar("  mostra o participante", "Marcos A. Ribeiro" in r.text)
verificar("  mostra o capital formatado em reais", "R$ 250.000" in r.text)

r = c.post("/logout", follow_redirects=False)
verificar("logout leva de volta ao login",
          r.status_code == 303 and r.headers.get("location") == "/login")

r = c.get("/dashboard", follow_redirects=False)
verificar("  depois do logout o dashboard fecha de novo",
          r.status_code == 303 and r.headers.get("location") == "/login")

# ---------------------------------------------------------------
# LIMPEZA: apaga os acessos criados por este teste
# ---------------------------------------------------------------
db = SessionLocal()
apagados = db.query(LoginHistory).delete()
db.commit()
db.close()
print(f"\n(limpeza: {apagados} registros de teste apagados do login_history)")

# ---------------------------------------------------------------
# RESULTADO
# ---------------------------------------------------------------
print("\n" + "=" * 50)
print(f"RESULTADO: {passou} passaram, {falhou} falharam")
print("=" * 50 + "\n")

sys.exit(1 if falhou else 0)
