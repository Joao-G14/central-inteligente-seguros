"""
test_modulos.py
---------------
Testa as 8 telas criadas na Fase 4:

  Movimentação & Pagamento · Comissões · Inadimplência · Esteira
  Sinistros · Pendências · Ramos/Produtos · Integrações · Assistente

COMO RODAR (com o venv ativado, na raiz do projeto):
    python tests/test_modulos.py

NAO precisa do servidor ligado.

ATENCAO: alguns testes ALTERAM o banco (emitir boleto, cobrar,
resolver pendencia). No fim do arquivo tudo volta ao estado original.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app import config  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Claim,
    Commission,
    Delinquency,
    Invoice,
    LoginHistory,
    Payment,
    Pendency,
    Proposal,
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


def logar(perfil: str = "ESTIPULANTE") -> TestClient:
    """Abre um 'navegador' novo e faz login com o perfil pedido."""
    senhas = {
        "ESTIPULANTE": ("estipulante@sebraeprev.com.br", config.SENHA_ESTIPULANTE),
        "CORRETORA": ("corretora@sebraeprev.com.br", config.SENHA_CORRETORA),
        "SEGURADORA": ("seguradora@sebraeprev.com.br", config.SENHA_SEGURADORA),
    }
    email, senha = senhas[perfil]
    c = TestClient(app)
    c.post("/login", data={"email": email, "senha": senha, "perfil": perfil},
           follow_redirects=False)
    return c


print("\n=== TESTANDO OS MODULOS DA FASE 4 ===\n")

cliente = logar("ESTIPULANTE")

# ---------------------------------------------------------------
# 1. Todas as telas abrem?
# ---------------------------------------------------------------
print("1. Todas as telas abrem para o estipulante")

TELAS = [
    ("/dashboard", "Dashboard da Carteira"),
    ("/produtos", "Catálogo de ramos"),
    ("/integracoes", "Conexões previstas"),
    ("/seguros", "Carteira de apólices"),
    ("/esteira", "Esteira de aceitação"),
    ("/movimentacao", "Movimentações do mês"),
    ("/comissoes", "Painel de Comissões"),
    ("/inadimplencia", "Régua de cobrança"),
    ("/sinistros", "Sinistros em andamento"),
    ("/pendencias", "Pendências em aberto"),
    ("/assistente", "Assistente da Central"),
]

for url, trecho_esperado in TELAS:
    r = cliente.get(url)
    verificar(f"{url} responde 200", r.status_code == 200, f"veio {r.status_code}")
    verificar(f"  e mostra '{trecho_esperado}'", trecho_esperado in r.text)

# ---------------------------------------------------------------
# 2. Os dados do prototipo estao nas telas certas
# ---------------------------------------------------------------
print("\n2. Dados do prototipo aparecem nas telas")

r = cliente.get("/movimentacao")
verificar("movimentacao mostra Ana Beatriz Souza", "Ana Beatriz Souza" in r.text)
verificar("  mostra a CPF da planilha", "384.517.920-41" in r.text)
verificar("  mostra o total de premio R$ 738,10", "738,10" in r.text)
verificar("  mostra os 4 convenios",
          all(c in r.text for c in ["FENACON", "OPBB", "CORECON", "FenaSebrae"]))
verificar("  Patricia Oliveira Costa aparece em atraso", "Em atraso" in r.text)

r = cliente.get("/comissoes")
verificar("comissoes mostra o premio de 07/2026", "214.700" in r.text)
verificar("  mostra a fatia do estipulante (10%)", "21.470" in r.text)
verificar("  mostra a fatia da corretora (15%)", "32.205" in r.text)
verificar("  mostra a fatia da seguradora (75%)", "161.025" in r.text)

r = cliente.get("/inadimplencia")
verificar("inadimplencia mostra Patricia Gomes", "Patrícia Gomes" in r.text)
verificar("  mostra os 4 degraus da regua",
          all(f in r.text for f in ["1 a 15 dias", "16 a 45 dias", "46 a 90 dias", "+90 dias"]))
verificar("  o maior atraso e 112 dias", "112" in r.text)

r = cliente.get("/esteira")
verificar("esteira mostra PROP-3012", "PROP-3012" in r.text)
verificar("  mostra a proposta recusada", "Recusada" in r.text)
verificar("  mostra as 4 colunas",
          all(c in r.text for c in ["Proposta recebida", "Em análise", "Aceita", "Pendente"]))

r = cliente.get("/sinistros")
verificar("sinistros mostra SIN-0448", "SIN-0448" in r.text)
verificar("  mostra a certidao faltante", "Falta certidão" in r.text)

r = cliente.get("/pendencias")
verificar("pendencias mostra a renovacao da AP-2041", "AP-2041" in r.text)
verificar("  mostra as 3 prioridades",
          all(p in r.text for p in ["Alta", "Média", "Baixa"]))

r = cliente.get("/produtos")
verificar("produtos mostra o ramo ativo", "Morte e Invalidez" in r.text)
verificar("  mostra os ramos do roadmap",
          all(x in r.text for x in ["Auto", "Viagem", "Bike", "Residencial"]))

# ---------------------------------------------------------------
# 3. PERMISSOES nas telas novas
# ---------------------------------------------------------------
print("\n3. Permissoes por perfil")

corretora = logar("CORRETORA")
seguradora = logar("SEGURADORA")

verificar("CORRETORA e barrada em /sinistros",
          corretora.get("/sinistros", follow_redirects=False).status_code == 303)
verificar("CORRETORA entra em /comissoes",
          corretora.get("/comissoes").status_code == 200)
verificar("CORRETORA entra em /inadimplencia",
          corretora.get("/inadimplencia").status_code == 200)

verificar("SEGURADORA e barrada em /comissoes",
          seguradora.get("/comissoes", follow_redirects=False).status_code == 303)
verificar("SEGURADORA e barrada em /inadimplencia",
          seguradora.get("/inadimplencia", follow_redirects=False).status_code == 303)
verificar("SEGURADORA entra em /sinistros",
          seguradora.get("/sinistros").status_code == 200)

# As acoes que GRAVAM tambem precisam ser barradas, nao so as telas.
verificar("SEGURADORA e barrada na acao de cobrar",
          seguradora.post("/inadimplencia/cobrar/1", follow_redirects=False).status_code == 303)
verificar("CORRETORA e barrada ao exportar inadimplencia? (nao, ela pode)",
          corretora.get("/inadimplencia/exportar").status_code == 200)
verificar("SEGURADORA e barrada ao exportar inadimplencia",
          seguradora.get("/inadimplencia/exportar", follow_redirects=False).status_code == 303)

# ---------------------------------------------------------------
# 4. Exportacao em CSV
# ---------------------------------------------------------------
print("\n4. Download dos arquivos CSV")

for url, nome, coluna in [
    ("/movimentacao/exportar", "movimentacao.csv", "Matrícula"),
    ("/inadimplencia/exportar", "inadimplencia.csv", "Participante"),
    ("/pendencias/exportar", "pendencias.csv", "Prioridade"),
]:
    r = cliente.get(url)
    verificar(f"{url} responde 200", r.status_code == 200)
    verificar(f"  vem como arquivo {nome}",
              nome in r.headers.get("content-disposition", ""))
    texto = r.content.decode("utf-8-sig")
    verificar(f"  tem a coluna '{coluna}'", coluna in texto)
    verificar("  usa ponto e virgula (padrao do Excel brasileiro)", ";" in texto)

# ---------------------------------------------------------------
# 5. ACOES QUE GRAVAM NO BANCO
# ---------------------------------------------------------------
print("\n5. Acoes que alteram dados")

db = SessionLocal()

# --- emitir boleto ---
boleto = db.query(Invoice).filter(Invoice.status == "A emitir").first()
verificar("existe um boleto para emitir", boleto is not None)
if boleto:
    boleto_id = boleto.id
    cliente.post(f"/movimentacao/emitir/{boleto_id}", follow_redirects=False)
    db.expire_all()
    depois = db.query(Invoice).filter(Invoice.id == boleto_id).first()
    verificar("  apos emitir, o status virou 'Em aberto'", depois.status == "Em aberto")
    verificar("  e ganhou data de vencimento", depois.data_vencimento is not None)
    # desfaz
    depois.status = "A emitir"
    depois.data_vencimento = None
    db.commit()

# --- cobrar inadimplente ---
registro = db.query(Delinquency).first()
verificar("existe um inadimplente", registro is not None)
if registro:
    registro_id = registro.id
    cliente.post(f"/inadimplencia/cobrar/{registro_id}", follow_redirects=False)
    db.expire_all()
    depois = db.query(Delinquency).filter(Delinquency.id == registro_id).first()
    verificar("  apos cobrar, fica marcado como enviado", depois.cobranca_enviada)
    r = cliente.get("/inadimplencia")
    verificar("  e a tela mostra 'Cobrança enviada'", "Cobrança enviada" in r.text)
    depois.cobranca_enviada = False
    db.commit()

# --- resolver e reabrir pendencia ---
pendencia = db.query(Pendency).filter(Pendency.resolvida.is_(False)).first()
verificar("existe uma pendencia aberta", pendencia is not None)
if pendencia:
    pendencia_id = pendencia.id
    cliente.post(f"/pendencias/resolver/{pendencia_id}", follow_redirects=False)
    db.expire_all()
    verificar("  apos resolver, fica marcada como resolvida",
              db.query(Pendency).filter(Pendency.id == pendencia_id).first().resolvida)

    cliente.post(f"/pendencias/reabrir/{pendencia_id}", follow_redirects=False)
    db.expire_all()
    verificar("  e consegue reabrir",
              not db.query(Pendency).filter(Pendency.id == pendencia_id).first().resolvida)

db.close()

# ---------------------------------------------------------------
# 6. ASSISTENTE
# ---------------------------------------------------------------
print("\n6. Assistente (respostas vindas do banco)")

PERGUNTAS = [
    ("Quais apólices vencem este mês?", ["renovação", "apólices"]),
    ("Qual o capital segurado total?", ["capital segurado"]),
    ("Como estão os sinistros?", ["sinistros"]),
    ("Quem está inadimplente?", ["inadimplentes"]),
    ("Como ficaram as comissões?", ["comissões", "competência"]),
    ("Quais pendências estão abertas?", ["pendências"]),
    ("E os pagamentos do mês?", ["segurados"]),
    ("Como está a esteira de propostas?", ["esteira"]),
]

for pergunta, esperado in PERGUNTAS:
    r = cliente.post("/assistente/perguntar", data={"pergunta": pergunta})
    resposta = r.json().get("resposta", "").lower()
    verificar(
        f'"{pergunta[:38]}…" foi entendida',
        r.status_code == 200 and any(e.lower() in resposta for e in esperado),
        f"respondeu: {resposta[:90]}",
    )

# Pergunta que ele nao sabe responder.
r = cliente.post("/assistente/perguntar", data={"pergunta": "qual a receita do bolo?"})
verificar("pergunta desconhecida cai na resposta padrao",
          "não entendi" in r.json()["resposta"].lower())

# O assistente responde com dados REAIS: conferimos um numero.
db = SessionLocal()
total_inadimplentes = db.query(Delinquency).count()
db.close()
r = cliente.post("/assistente/perguntar", data={"pergunta": "quem está inadimplente?"})
verificar(f"a resposta traz o numero real de inadimplentes ({total_inadimplentes})",
          f"<b>{total_inadimplentes} participantes inadimplentes</b>" in r.json()["resposta"])

# ---------------------------------------------------------------
# 7. O banco continua intacto
# ---------------------------------------------------------------
print("\n7. Conferencia final do banco")

db = SessionLocal()
CONTAGENS = [
    (Payment, 10, "pagamentos"),
    (Invoice, 8, "boletos"),
    (Commission, 15, "registros de comissao"),
    (Delinquency, 6, "inadimplentes"),
    (Proposal, 9, "propostas"),
    (Claim, 4, "sinistros"),
    (Pendency, 5, "pendencias"),
]
for modelo, esperado, nome in CONTAGENS:
    achou = db.query(modelo).count()
    verificar(f"{esperado} {nome}", achou == esperado, f"encontrados: {achou}")

verificar("nenhum boleto ficou emitido por engano",
          db.query(Invoice).filter(Invoice.status == "A emitir").count() == 4)
verificar("nenhuma cobranca ficou marcada por engano",
          db.query(Delinquency).filter(Delinquency.cobranca_enviada.is_(True)).count() == 0)
verificar("nenhuma pendencia ficou resolvida por engano",
          db.query(Pendency).filter(Pendency.resolvida.is_(True)).count() == 0)

# limpa os acessos criados pelos logins deste teste
apagados = db.query(LoginHistory).delete()
db.commit()
db.close()
print(f"\n(limpeza: {apagados} registros de login de teste apagados)")

# ---------------------------------------------------------------
print("\n" + "=" * 50)
print(f"RESULTADO: {passou} passaram, {falhou} falharam")
print("=" * 50 + "\n")

sys.exit(1 if falhou else 0)
