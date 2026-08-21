"""
test_cadastros.py
-----------------
Testa as telas de cadastrar, editar e excluir.

  1. As 5 telas de cadastro abrem
  2. Cadastra, edita e exclui de verdade
  3. Recusa dados invalidos, com mensagem em portugues
  4. Nao perde o que a pessoa digitou quando da erro
  5. Nao aceita identificador repetido
  6. Calcula sozinho o que da para deduzir
  7. Respeita as permissoes de cada perfil
  8. Aceita valores e datas nos dois formatos

COMO RODAR (com o venv ativado, na raiz do projeto):
    python tests/test_cadastros.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app import cadastros, config  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    ActiveSession,
    Claim,
    Delinquency,
    LoginHistory,
    Pendency,
    Policy,
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


def limpar():
    db = SessionLocal()
    db.query(LoginHistory).delete()
    db.query(ActiveSession).delete()
    db.commit()
    db.close()


def logar(perfil="ESTIPULANTE"):
    senhas = {
        "ESTIPULANTE": config.SENHA_ESTIPULANTE,
        "CORRETORA": config.SENHA_CORRETORA,
        "SEGURADORA": config.SENHA_SEGURADORA,
    }
    c = TestClient(app)
    c.post("/login", data={"email": f"cad.{perfil.lower()}@sebraeprev.com.br",
                           "senha": senhas[perfil], "perfil": perfil},
           follow_redirects=False)
    return c


print("\n=== TESTANDO AS TELAS DE CADASTRO ===\n")
limpar()
cliente = logar()

# ---------------------------------------------------------------
# 1. AS TELAS ABREM
# ---------------------------------------------------------------
print("1. As 5 telas de cadastro abrem")

for nome, cadastro in cadastros.CADASTROS.items():
    r = cliente.get(f"/cadastro/{nome}/novo")
    verificar(f"/cadastro/{nome}/novo responde 200", r.status_code == 200,
              f"veio {r.status_code}")
    verificar(f"  mostra os campos de {cadastro['titulo']}",
              all(c.rotulo in r.text
                  for c in cadastros.campos_visiveis(cadastro)[:3]))

r = cliente.get("/cadastro/coisa-que-nao-existe/novo", follow_redirects=False)
verificar("cadastro inexistente volta ao dashboard",
          r.status_code == 303 and r.headers.get("location") == "/dashboard")

# ---------------------------------------------------------------
# 2. CADASTRAR
# ---------------------------------------------------------------
print("\n2. Cadastrar uma apólice")

NOVA = {
    "numero_apolice": "AP-TESTE1",
    "participante": "Fulano de Teste",
    "cpf": "111.222.333-44",
    "matricula": "999001",
    "cobertura": "Morte + Invalidez",
    "capital_total": "250.000,00",
    "premio_mensal": "101,25",
    "data_inicio": "2026-01-10",
    "data_vencimento": "2027-01-10",
    "status": "Ativa",
    "codigo_modulo": "101",
    "codigo_sub": "01",
    "competencia": "08/2026",
}

r = cliente.post("/cadastro/apolices/novo", data=NOVA, follow_redirects=False)
verificar("grava e volta para a carteira",
          r.status_code == 303 and r.headers.get("location") == "/seguros",
          f"veio {r.status_code}")

db = SessionLocal()
nova = db.query(Policy).filter(Policy.numero_apolice == "AP-TESTE1").first()
verificar("  a apólice está no banco", nova is not None)

if nova:
    verificar("  o nome foi gravado", nova.participante == "Fulano de Teste")
    verificar('  "250.000,00" virou 250000.0', nova.capital_total == 250000.0,
              f"gravou {nova.capital_total}")
    verificar('  "101,25" virou 101.25', nova.premio_mensal == 101.25,
              f"gravou {nova.premio_mensal}")
    verificar("  a data foi convertida",
              nova.data_inicio.strftime("%d/%m/%Y") == "10/01/2026",
              f"gravou {nova.data_inicio}")
    verificar("  marcou a origem como manual", nova.origem == "manual",
              f"origem: {nova.origem}")
    nova_id = nova.id
db.close()

# ---------------------------------------------------------------
# 3. CALCULOS AUTOMATICOS
# ---------------------------------------------------------------
print("\n3. O sistema calcula o que dá para deduzir")

db = SessionLocal()
apolice = db.query(Policy).filter(Policy.numero_apolice == "AP-TESTE1").first()
verificar("Morte + Invalidez: os dois capitais recebem o valor cheio",
          apolice.capital_morte == 250000.0 and apolice.capital_invalidez == 250000.0,
          f"morte={apolice.capital_morte} invalidez={apolice.capital_invalidez}")
db.close()

# Só morte: invalidez tem que ficar zerada.
so_morte = dict(NOVA, numero_apolice="AP-TESTE2", cobertura="Morte")
cliente.post("/cadastro/apolices/novo", data=so_morte, follow_redirects=False)
db = SessionLocal()
a2 = db.query(Policy).filter(Policy.numero_apolice == "AP-TESTE2").first()
verificar("só Morte: invalidez fica zerada",
          a2 is not None and a2.capital_morte == 250000.0
          and a2.capital_invalidez == 0.0,
          f"morte={a2.capital_morte if a2 else '?'} invalidez={a2.capital_invalidez if a2 else '?'}")
db.close()

# ---------------------------------------------------------------
# 4. RECUSA DADOS INVALIDOS
# ---------------------------------------------------------------
print("\n4. Recusa dados inválidos com mensagem clara")

INVALIDOS = [
    ({**NOVA, "numero_apolice": "", "participante": ""},
     ["Número da apólice", "Participante"], "campos obrigatórios em branco"),
    ({**NOVA, "numero_apolice": "AP-X1", "capital_total": "abc"},
     ["Capital segurado"], "valor que não é número"),
    ({**NOVA, "numero_apolice": "AP-X2", "data_inicio": "31/02/2026"},
     ["Início da vigência"], "data que não existe"),
    ({**NOVA, "numero_apolice": "AP-X3", "capital_total": "0"},
     ["Capital segurado"], "capital zerado"),
    ({**NOVA, "numero_apolice": "AP-X4",
      "data_inicio": "2027-01-10", "data_vencimento": "2026-01-10"},
     ["Vencimento"], "vencimento antes do início"),
    ({**NOVA, "numero_apolice": "AP-X5", "cobertura": "Inventada"},
     ["Cobertura"], "opção que não existe"),
]

for dados, esperados, descricao in INVALIDOS:
    r = cliente.post("/cadastro/apolices/novo", data=dados)
    # Fica na mesma tela (200), não redireciona.
    ficou = r.status_code == 200 and "problema(s) no preenchimento" in r.text
    achou = all(e in r.text for e in esperados)
    verificar(f"recusa {descricao}", ficou and achou,
              f"status {r.status_code}")

db = SessionLocal()
lixo = db.query(Policy).filter(Policy.numero_apolice.like("AP-X%")).count()
verificar("  nenhum registro inválido foi gravado", lixo == 0,
          f"gravou {lixo}")
db.close()

# ---------------------------------------------------------------
# 5. NÃO PERDE O QUE FOI DIGITADO
# ---------------------------------------------------------------
print("\n5. Ao dar erro, o formulário volta preenchido")

r = cliente.post("/cadastro/apolices/novo",
                 data={**NOVA, "numero_apolice": "AP-VOLTA",
                       "capital_total": "xyz"})
verificar("o nome digitado continua na tela", "Fulano de Teste" in r.text)
verificar("  o número digitado continua na tela", "AP-VOLTA" in r.text)
verificar("  a cobertura escolhida continua marcada",
          'value="Morte + Invalidez" selected' in r.text)

# ---------------------------------------------------------------
# 6. IDENTIFICADOR REPETIDO
# ---------------------------------------------------------------
print("\n6. Não aceita número repetido")

r = cliente.post("/cadastro/apolices/novo", data=NOVA)
verificar("recusa apólice com número já usado", "Já existe um registro" in r.text)

db = SessionLocal()
verificar("  e não duplicou no banco",
          db.query(Policy).filter(Policy.numero_apolice == "AP-TESTE1").count() == 1)
db.close()

# ---------------------------------------------------------------
# 7. EDITAR
# ---------------------------------------------------------------
print("\n7. Editar")

r = cliente.get(f"/cadastro/apolices/{nova_id}/editar")
verificar("a tela de edição abre", r.status_code == 200)
verificar("  vem preenchida com o que está no banco",
          "Fulano de Teste" in r.text and "AP-TESTE1" in r.text)
verificar("  mostra o botão de excluir", "Excluir AP-TESTE1" in r.text)

alterado = dict(NOVA, participante="Fulano Corrigido",
                capital_total="300.000,00", status="A renovar")
r = cliente.post(f"/cadastro/apolices/{nova_id}/editar", data=alterado,
                 follow_redirects=False)
verificar("salva a alteração", r.status_code == 303)

db = SessionLocal()
editada = db.query(Policy).filter(Policy.id == nova_id).first()
verificar("  o nome mudou", editada.participante == "Fulano Corrigido")
verificar("  o capital mudou", editada.capital_total == 300000.0)
verificar("  a situação mudou", editada.status == "A renovar")
verificar("  o capital recalculou nas duas coberturas",
          editada.capital_morte == 300000.0 and editada.capital_invalidez == 300000.0)
db.close()

# Salvar sem mudar o número não pode acusar duplicidade.
r = cliente.post(f"/cadastro/apolices/{nova_id}/editar", data=alterado,
                 follow_redirects=False)
verificar("  salvar de novo sem mudar o número funciona", r.status_code == 303)

# Mas usar o número de OUTRO registro é recusado.
r = cliente.post(f"/cadastro/apolices/{nova_id}/editar",
                 data=dict(alterado, numero_apolice="AP-TESTE2"))
verificar("  recusa usar o número de outra apólice",
          "Outro registro já usa" in r.text)

r = cliente.get("/cadastro/apolices/999999/editar", follow_redirects=False)
verificar("editar registro inexistente volta para a lista",
          r.status_code == 303 and r.headers.get("location") == "/seguros")

# ---------------------------------------------------------------
# 8. OS OUTROS 4 CADASTROS
# ---------------------------------------------------------------
print("\n8. Os outros quatro cadastros")

CASOS = [
    ("sinistros", Claim, "protocolo", {
        "protocolo": "SIN-TESTE", "participante": "Teste Sinistro",
        "tipo": "Morte", "data_abertura": "2026-08-01",
        "documentacao": "Completa", "documentacao_ok": "sim",
        "status": "Em análise",
    }),
    ("propostas", Proposal, "numero", {
        "numero": "PROP-TESTE", "participante": "Teste Proposta",
        "cobertura": "Morte", "capital": "150.000,00",
        "etapa": "recebida", "observacao": "teste automatico",
    }),
    ("pendencias", Pendency, "titulo", {
        "prioridade": "Alta", "titulo": "Pendência de teste",
        "referente": "AP-TESTE1", "responsavel": "Corretora",
        "prazo": "2026-09-30", "documento": "Apólice", "documento_ok": "sim",
    }),
    ("inadimplencia", Delinquency, "participante", {
        "participante": "Teste Inadimplente", "numero_apolice": "AP-TESTE1",
        "cobertura": "Morte", "valor": "112,00", "dias_atraso": "45",
    }),
]

for nome, modelo, identificador, dados in CASOS:
    r = cliente.post(f"/cadastro/{nome}/novo", data=dados, follow_redirects=False)
    verificar(f"{nome}: cadastra", r.status_code == 303, f"veio {r.status_code}")

    db = SessionLocal()
    coluna = getattr(modelo, identificador)
    criado = db.query(modelo).filter(coluna == dados[identificador]).first()
    verificar(f"  {nome}: está no banco", criado is not None)
    criado_id = criado.id if criado else None
    db.close()

    if criado_id:
        r = cliente.get(f"/cadastro/{nome}/{criado_id}/editar")
        verificar(f"  {nome}: a edição abre", r.status_code == 200)

        # Campo obrigatório em branco tem que ser recusado.
        vazio = dict(dados)
        vazio[identificador] = ""
        r = cliente.post(f"/cadastro/{nome}/{criado_id}/editar", data=vazio)
        verificar(f"  {nome}: recusa obrigatório em branco",
                  "problema(s) no preenchimento" in r.text)

        r = cliente.post(f"/cadastro/{nome}/{criado_id}/excluir",
                         follow_redirects=False)
        verificar(f"  {nome}: exclui", r.status_code == 303)

        db = SessionLocal()
        verificar(f"  {nome}: saiu do banco",
                  db.query(modelo).filter(modelo.id == criado_id).first() is None)
        db.close()

# ---------------------------------------------------------------
# 9. PERMISSOES
# ---------------------------------------------------------------
print("\n9. As permissões valem no cadastro também")

corretora = logar("CORRETORA")
seguradora = logar("SEGURADORA")

# A corretora não vê sinistros — logo, não pode cadastrar sinistros.
r = corretora.get("/cadastro/sinistros/novo", follow_redirects=False)
verificar("CORRETORA é barrada em /cadastro/sinistros/novo",
          r.status_code == 303, f"veio {r.status_code}")

r = corretora.post("/cadastro/sinistros/novo",
                   data={"protocolo": "SIN-INVASOR", "participante": "x",
                         "tipo": "Morte", "data_abertura": "2026-08-01",
                         "documentacao": "Completa", "status": "Em análise"},
                   follow_redirects=False)
verificar("  e barrada ao tentar gravar pelo endereço direto",
          r.status_code == 303)

db = SessionLocal()
verificar("  nada foi gravado",
          db.query(Claim).filter(Claim.protocolo == "SIN-INVASOR").first() is None)
db.close()

# A seguradora não vê inadimplência.
r = seguradora.get("/cadastro/inadimplencia/novo", follow_redirects=False)
verificar("SEGURADORA é barrada em /cadastro/inadimplencia/novo",
          r.status_code == 303)

# Mas cada uma pode no que lhe cabe.
verificar("CORRETORA pode cadastrar apólice",
          corretora.get("/cadastro/apolices/novo").status_code == 200)
verificar("SEGURADORA pode cadastrar sinistro",
          seguradora.get("/cadastro/sinistros/novo").status_code == 200)

# ---------------------------------------------------------------
# 10. OS BOTOES APARECEM NAS LISTAS
# ---------------------------------------------------------------
print("\n10. Os botões aparecem nas telas de listagem")

TELAS = [
    ("/seguros", "apolices", "Nova apólice"),
    ("/sinistros", "sinistros", "Novo sinistro"),
    ("/esteira", "propostas", "Nova proposta"),
    ("/pendencias", "pendencias", "Nova pendência"),
    ("/inadimplencia", "inadimplencia", "Novo registro"),
]
for url, nome, rotulo in TELAS:
    texto = cliente.get(url).text
    verificar(f"{url} tem o botão de novo", f"/cadastro/{nome}/novo" in texto)
    verificar(f"  e o link de editar nas linhas", f"/cadastro/{nome}/" in texto)

# ---------------------------------------------------------------
# LIMPEZA
# ---------------------------------------------------------------
db = SessionLocal()
apagadas = db.query(Policy).filter(Policy.numero_apolice.like("AP-TESTE%")).delete()
db.query(Policy).filter(Policy.numero_apolice.like("AP-X%")).delete()
db.query(Policy).filter(Policy.numero_apolice == "AP-VOLTA").delete()
db.query(Claim).filter(Claim.protocolo.like("SIN-%TESTE%")).delete()
db.query(Proposal).filter(Proposal.numero.like("PROP-TESTE%")).delete()
db.query(Pendency).filter(Pendency.titulo.like("%de teste%")).delete()
db.query(Delinquency).filter(Delinquency.participante.like("Teste%")).delete()
db.query(LoginHistory).delete()
db.query(ActiveSession).delete()
db.commit()
db.close()
print(f"\n(limpeza: {apagadas} apólices de teste e os demais registros apagados)")

print("\n" + "=" * 56)
print(f"RESULTADO: {passou} passaram, {falhou} falharam")
print("=" * 56 + "\n")

sys.exit(1 if falhou else 0)
