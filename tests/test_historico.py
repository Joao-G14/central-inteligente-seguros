"""
test_historico.py
-----------------
Testa as duas coisas que guardam o passado do sistema:

  1. REGISTRO DE ALTERACOES — quem criou, editou ou excluiu, e o que mudou
  2. FOTOGRAFIA DA CARTEIRA — como a carteira estava em cada mes

COMO RODAR (com o venv ativado, na raiz do projeto):
    python tests/test_historico.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app import config, historico, tempo  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    ActiveSession,
    CarteiraSnapshot,
    ChangeLog,
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


def logar(perfil="ESTIPULANTE", email=None):
    senhas = {
        "ESTIPULANTE": config.SENHA_ESTIPULANTE,
        "CORRETORA": config.SENHA_CORRETORA,
        "SEGURADORA": config.SENHA_SEGURADORA,
    }
    c = TestClient(app)
    c.post("/login", data={"email": email or f"hist.{perfil.lower()}@sebraeprev.com.br",
                           "senha": senhas[perfil], "perfil": perfil},
           follow_redirects=False)
    return c


def limpar():
    db = SessionLocal()
    db.query(LoginHistory).delete()
    db.query(ActiveSession).delete()
    db.commit()
    db.close()


print("\n=== TESTANDO O HISTORICO ===\n")
limpar()

APOLICE = {
    "numero_apolice": "AP-HIST1",
    "participante": "Teste Historico",
    "cobertura": "Morte",
    "capital_total": "200.000,00",
    "premio_mensal": "81,00",
    "data_inicio": "2026-01-01",
    "data_vencimento": "2027-01-01",
    "status": "Ativa",
}

# ---------------------------------------------------------------
# 1. REGISTRA A CRIACAO
# ---------------------------------------------------------------
print("1. Registra quem criou")

db = SessionLocal()
antes_de_tudo = db.query(ChangeLog).count()
db.close()

cliente = logar(email="joao.teste@sebraeprev.com.br")
cliente.post("/cadastro/apolices/novo", data=APOLICE, follow_redirects=False)

db = SessionLocal()
registro = db.query(ChangeLog).order_by(ChangeLog.id.desc()).first()
nova = db.query(Policy).filter(Policy.numero_apolice == "AP-HIST1").first()
nova_id = nova.id if nova else None

verificar("gravou uma linha no histórico",
          db.query(ChangeLog).count() == antes_de_tudo + 1)
verificar("  a ação é 'criou'", registro is not None and registro.acao == "criou")
verificar("  guardou qual cadastro", registro.cadastro == "apolices")
verificar("  guardou a identificação legível",
          registro.identificacao == "AP-HIST1",
          f"guardou: {registro.identificacao}")
verificar("  guardou QUEM fez",
          registro.usuario_email == "joao.teste@sebraeprev.com.br",
          f"guardou: {registro.usuario_email}")
verificar("  guardou a categoria", registro.usuario_perfil == "ESTIPULANTE")
verificar("  guardou o conteúdo do registro",
          "Teste Historico" in (registro.alteracoes or ""))
verificar("  a hora está no fuso de Brasília",
          abs((registro.data_hora - tempo.agora()).total_seconds()) < 300)
db.close()

# ---------------------------------------------------------------
# 2. REGISTRA A ALTERACAO, COM ANTES E DEPOIS
# ---------------------------------------------------------------
print("\n2. Registra o que mudou, com antes e depois")

alterado = dict(APOLICE, capital_total="350.000,00", status="A renovar")
cliente.post(f"/cadastro/apolices/{nova_id}/editar", data=alterado,
             follow_redirects=False)

db = SessionLocal()
registro = db.query(ChangeLog).order_by(ChangeLog.id.desc()).first()
verificar("a ação é 'alterou'", registro.acao == "alterou")

texto = registro.alteracoes or ""
verificar("  mostra o valor ANTIGO do capital", "200.000,00" in texto,
          f"gravou: {texto}")
verificar("  mostra o valor NOVO do capital", "350.000,00" in texto)
verificar("  mostra a seta entre os dois", "->" in texto)
verificar("  registra também a troca de status",
          "Ativa" in texto and "A renovar" in texto)
verificar("  o capital calculado também entra",
          "capital_morte" in texto)
print(f"           (gravou: {texto.replace(chr(10), ' | ')})")
db.close()

# Salvar sem mudar nada NAO deve gerar linha.
db = SessionLocal()
antes = db.query(ChangeLog).count()
db.close()

cliente.post(f"/cadastro/apolices/{nova_id}/editar", data=alterado,
             follow_redirects=False)

db = SessionLocal()
verificar("salvar sem mudar nada NÃO gera linha no histórico",
          db.query(ChangeLog).count() == antes,
          "gerou linha para uma alteração vazia")
db.close()

# ---------------------------------------------------------------
# 3. REGISTRA A EXCLUSAO — o caso mais importante
# ---------------------------------------------------------------
print("\n3. Registra a exclusão (o caso que mais importa)")

cliente.post(f"/cadastro/apolices/{nova_id}/excluir", follow_redirects=False)

db = SessionLocal()
verificar("a apólice saiu do banco",
          db.query(Policy).filter(Policy.id == nova_id).first() is None)

registro = db.query(ChangeLog).order_by(ChangeLog.id.desc()).first()
verificar("  mas o histórico guardou a exclusão", registro.acao == "excluiu")
verificar("  com a identificação, mesmo o registro não existindo mais",
          registro.identificacao == "AP-HIST1")
verificar("  e com o conteúdo que ela tinha",
          "Teste Historico" in (registro.alteracoes or "")
          and "350.000,00" in (registro.alteracoes or ""),
          f"gravou: {(registro.alteracoes or '')[:120]}")
db.close()

# ---------------------------------------------------------------
# 4. A TELA DE HISTORICO
# ---------------------------------------------------------------
print("\n4. A tela de histórico")

r = cliente.get("/historico")
verificar("a tela abre", r.status_code == 200)
verificar("  mostra a apólice de teste", "AP-HIST1" in r.text)
verificar("  mostra quem alterou", "joao.teste@sebraeprev.com.br" in r.text)
verificar("  tem a seção de evolução da carteira", "Evolução da carteira" in r.text)

r = cliente.get("/historico?acao=excluiu")
verificar("filtra por ação", "AP-HIST1" in r.text)

r = cliente.get("/historico?cadastro=apolices")
verificar("filtra por cadastro", r.status_code == 200)

r = cliente.get("/historico?busca=AP-HIST1")
verificar("busca por identificação", "AP-HIST1" in r.text)

r = cliente.get("/historico?busca=zzznaoexiste")
verificar("busca sem resultado mostra aviso",
          "Nenhuma alteração encontrada" in r.text)

r = cliente.get("/historico/exportar")
verificar("exporta em CSV", r.status_code == 200)
texto_csv = r.content.decode("utf-8-sig")
verificar("  o CSV tem as colunas certas",
          "O que mudou" in texto_csv and "Quem" in texto_csv)
verificar("  as quebras de linha viraram ' | ' para não estragar o CSV",
          "|" in texto_csv)

# Só o estipulante enxerga.
for perfil in ("CORRETORA", "SEGURADORA"):
    c = logar(perfil)
    r = c.get("/historico", follow_redirects=False)
    verificar(f"{perfil} é barrada em /historico", r.status_code == 303,
              f"veio {r.status_code}")

# ---------------------------------------------------------------
# 5. A FOTOGRAFIA DA CARTEIRA
# ---------------------------------------------------------------
print("\n5. A fotografia da carteira")

db = SessionLocal()
competencia = historico.competencia_de_hoje()
foto = db.query(CarteiraSnapshot).filter(
    CarteiraSnapshot.competencia == competencia
).first()
verificar(f"existe a foto do mês corrente ({competencia})", foto is not None)

# Tiramos uma foto NOVA antes de comparar.
#
# POR QUE: a foto guardada pode ter sido tirada horas atras, ou por outro
# teste que rodou antes e mexeu nos dados. Comparar uma foto antiga com o
# banco de agora testaria "nada mudou desde a foto", que nao e a nossa
# regra — a foto e justamente um retrato de um momento passado.
#
# O que interessa conferir e: a MEDICAO esta certa? Ou seja, quando a
# foto e tirada, ela reflete o banco naquele instante.
historico.fotografar(db, refazer=True)
db.expire_all()

foto = db.query(CarteiraSnapshot).filter(
    CarteiraSnapshot.competencia == competencia
).first()

if foto:
    ativas = db.query(Policy).filter(Policy.status == "Ativa").count()
    total = db.query(Policy).count()
    renovar = db.query(Policy).filter(Policy.status == "A renovar").count()

    verificar("  o número de ativas bate com o banco",
              foto.apolices_ativas == ativas,
              f"foto: {foto.apolices_ativas}, banco: {ativas}")
    verificar("  o total bate com o banco",
              foto.apolices_total == total,
              f"foto: {foto.apolices_total}, banco: {total}")
    verificar("  as a renovar batem com o banco",
              foto.apolices_a_renovar == renovar,
              f"foto: {foto.apolices_a_renovar}, banco: {renovar}")
    verificar("  guardou o capital segurado", foto.capital_segurado > 0)
    verificar("  guardou as vidas cobertas", foto.vidas_cobertas > 0)
    verificar("  '08/2026' virou 'Ago'", len(foto.mes_curto()) == 3,
              f"deu: {foto.mes_curto()}")
db.close()

# Tirar de novo NAO pode duplicar nem sobrescrever sem pedir.
db = SessionLocal()
quantas_antes = db.query(CarteiraSnapshot).count()
tirada_em = db.query(CarteiraSnapshot).filter(
    CarteiraSnapshot.competencia == competencia
).first().data_foto

_, criou = historico.fotografar(db)
verificar("tirar a foto de novo não cria outra", not criou)
verificar("  e não altera a foto existente",
          db.query(CarteiraSnapshot).filter(
              CarteiraSnapshot.competencia == competencia
          ).first().data_foto == tirada_em,
          "a foto do mês foi sobrescrita sem pedir")
verificar("  a quantidade de fotos não mudou",
          db.query(CarteiraSnapshot).count() == quantas_antes)
db.close()

# Com refazer=True, aí sim atualiza.
db = SessionLocal()
historico.fotografar(db, refazer=True)
nova_data = db.query(CarteiraSnapshot).filter(
    CarteiraSnapshot.competencia == competencia
).first().data_foto
verificar("com --refazer, a foto do mês é atualizada", nova_data >= tirada_em)
db.close()

# ---------------------------------------------------------------
# 6. A ORDEM DAS FOTOS
# ---------------------------------------------------------------
print("\n6. A ordem das fotos (o erro clássico de data em texto)")

db = SessionLocal()
# Duas competências onde a ordem alfabética estaria ERRADA:
# "03/2027" vem antes de "12/2026" no alfabeto, mas depois no tempo.
for c in ("12/2026", "03/2027"):
    if not db.query(CarteiraSnapshot).filter(
        CarteiraSnapshot.competencia == c
    ).first():
        db.add(CarteiraSnapshot(competencia=c, apolices_ativas=1,
                                capital_segurado=1000.0))
db.commit()

ordenadas = [f.competencia for f in historico.historico_ordenado(db, quantos=50)]
pos_dez = ordenadas.index("12/2026")
pos_mar = ordenadas.index("03/2027")
verificar("dezembro/2026 vem ANTES de março/2027", pos_dez < pos_mar,
          f"ordem: {ordenadas}")

db.query(CarteiraSnapshot).filter(
    CarteiraSnapshot.competencia.in_(["12/2026", "03/2027"])
).delete()
db.commit()
db.close()

# ---------------------------------------------------------------
# 7. O GRAFICO NO DASHBOARD
# ---------------------------------------------------------------
print("\n7. O gráfico no dashboard")

db = SessionLocal()
barras = historico.montar_grafico(db, quantos=6)
verificar("o gráfico tem barras", len(barras) > 0)
if barras:
    verificar("  a barra mais alta tem 100%",
              max(b["altura"] for b in barras) == 100)
    verificar("  nenhuma barra fica invisível",
              all(b["altura"] >= 4 for b in barras))
    verificar("  cada barra tem rótulo curto do mês",
              all(len(b["rotulo"]) <= 4 for b in barras))
db.close()

cliente = logar(email="joao.teste@sebraeprev.com.br")
r = cliente.get("/dashboard")
verificar("o dashboard mostra o gráfico", "Capital segurado por mês" in r.text)

# ---------------------------------------------------------------
# 8. AS OUTRAS ACOES TAMBEM SAO REGISTRADAS?
# ---------------------------------------------------------------
print("\n8. Cobertura do registro nos 5 cadastros")

CASOS = [
    ("sinistros", {"protocolo": "SIN-HIST", "participante": "Teste",
                   "tipo": "Morte", "data_abertura": "2026-08-01",
                   "documentacao": "Completa", "status": "Em análise"}),
    ("propostas", {"numero": "PROP-HIST", "participante": "Teste",
                   "etapa": "recebida"}),
    ("pendencias", {"prioridade": "Alta", "titulo": "Pendência histórico"}),
    ("inadimplencia", {"participante": "Teste Hist", "numero_apolice": "AP-1",
                       "cobertura": "Morte", "valor": "50,00",
                       "dias_atraso": "10"}),
]

for nome, dados in CASOS:
    db = SessionLocal()
    antes = db.query(ChangeLog).filter(ChangeLog.cadastro == nome).count()
    db.close()

    cliente.post(f"/cadastro/{nome}/novo", data=dados, follow_redirects=False)

    db = SessionLocal()
    depois = db.query(ChangeLog).filter(ChangeLog.cadastro == nome).count()
    verificar(f"{nome}: a criação foi registrada", depois == antes + 1)
    db.close()

# ---------------------------------------------------------------
# LIMPEZA
# ---------------------------------------------------------------
db = SessionLocal()
from app.models import Claim, Delinquency, Pendency, Proposal  # noqa: E402

db.query(Policy).filter(Policy.numero_apolice.like("AP-HIST%")).delete()
db.query(Claim).filter(Claim.protocolo.like("SIN-HIST%")).delete()
db.query(Proposal).filter(Proposal.numero.like("PROP-HIST%")).delete()
db.query(Pendency).filter(Pendency.titulo.like("%histórico%")).delete()
db.query(Delinquency).filter(Delinquency.participante.like("Teste Hist%")).delete()
n = db.query(ChangeLog).delete()
db.query(LoginHistory).delete()
db.query(ActiveSession).delete()
db.commit()
db.close()
print(f"\n(limpeza: {n} linhas de histórico de teste apagadas)")

print("\n" + "=" * 56)
print(f"RESULTADO: {passou} passaram, {falhou} falharam")
print("=" * 56 + "\n")

sys.exit(1 if falhou else 0)
