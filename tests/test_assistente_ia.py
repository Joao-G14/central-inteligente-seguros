"""
test_assistente_ia.py
---------------------
Testa o assistente com IA e a memória da conversa.

  1. As 8 ferramentas que a IA usa para consultar o banco
  2. A memória: a conversa fica guardada e volta ao reabrir a tela
  3. O plano B: sem chave da IA, o modo por palavras-chave assume
  4. Isolamento: cada pessoa vê só a própria conversa

COMO RODAR (com o venv ativado, na raiz do projeto):
    python tests/test_assistente_ia.py

Os testes que precisariam CHAMAR a IA de verdade são pulados quando não
há ANTHROPIC_API_KEY configurada — para não gastar dinheiro sem querer.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app import assistente_ia, config  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import ChatMessage, LoginHistory  # noqa: E402

passou = 0
falhou = 0
pulados = 0


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


def pular(descricao: str, motivo: str) -> None:
    global pulados
    pulados += 1
    print(f"  [PULADO] {descricao}")
    print(f"           -> {motivo}")


def logar(email="assistente.teste@sebraeprev.com.br"):
    c = TestClient(app)
    c.post("/login", data={"email": email, "senha": config.SENHA_ESTIPULANTE,
                           "perfil": "ESTIPULANTE"}, follow_redirects=False)
    return c


def perguntar(cliente, texto):
    return cliente.post("/assistente/perguntar", data={"pergunta": texto}).json()


def limpar_conversas():
    db = SessionLocal()
    db.query(ChatMessage).delete()
    db.commit()
    db.close()


print("\n=== TESTANDO O ASSISTENTE COM IA ===\n")
limpar_conversas()

# ---------------------------------------------------------------
# 1. AS FERRAMENTAS
# ---------------------------------------------------------------
print("1. As ferramentas que consultam o banco")

verificar("existem 8 ferramentas", len(assistente_ia.FERRAMENTAS) == 8,
          f"encontradas: {len(assistente_ia.FERRAMENTAS)}")

verificar("toda ferramenta tem documentacao (a IA lê para saber o que faz)",
          all(f.__doc__ and len(f.__doc__.strip()) > 30
              for f in assistente_ia.FERRAMENTAS),
          "alguma ferramenta está sem docstring")

# Cada ferramenta precisa devolver JSON valido.
for funcao in assistente_ia.FERRAMENTAS:
    try:
        resultado = json.loads(funcao())
        verificar(f"{funcao.__name__}() devolve JSON válido", isinstance(resultado, dict))
    except Exception as e:
        verificar(f"{funcao.__name__}() devolve JSON válido", False,
                  f"{type(e).__name__}: {e}")

# Conteudo real.
resumo = json.loads(assistente_ia.resumo_da_carteira())
verificar("o resumo traz as apólices por status",
          "apolices_por_status" in resumo and resumo["apolices_total"] > 0,
          f"total: {resumo.get('apolices_total')}")
verificar("o resumo traz o capital segurado",
          resumo["capital_segurado_ativas_reais"] > 0)

# Filtros da busca de apólices.
todas = json.loads(assistente_ia.buscar_apolices(limite=100))
ativas = json.loads(assistente_ia.buscar_apolices(status="Ativa", limite=100))
verificar("buscar_apolices filtra por status",
          ativas["encontradas"] < todas["encontradas"] and
          all(a["status"] == "Ativa" for a in ativas["apolices"]))

vencendo = json.loads(assistente_ia.buscar_apolices(vencendo_em_dias=30, limite=100))
verificar("buscar_apolices filtra por vencimento",
          all(0 <= a["dias_para_vencer"] <= 30 for a in vencendo["apolices"]),
          f"encontradas: {vencendo['encontradas']}")

caras = json.loads(assistente_ia.buscar_apolices(capital_minimo=300000, limite=100))
verificar("buscar_apolices filtra por capital mínimo",
          all(a["capital_segurado"] >= 300000 for a in caras["apolices"]))

por_nome = json.loads(assistente_ia.buscar_apolices(participante="Marcos", limite=10))
verificar("buscar_apolices acha pelo nome do participante",
          por_nome["encontradas"] >= 1 and
          any("Marcos" in a["participante"] for a in por_nome["apolices"]),
          f"encontradas: {por_nome['encontradas']}")

verificar("buscar_apolices respeita o limite",
          len(json.loads(assistente_ia.buscar_apolices(limite=5))["apolices"]) == 5)

pagamentos = json.loads(assistente_ia.listar_pagamentos())
verificar("listar_pagamentos pega a competência mais recente sozinho",
          pagamentos.get("competencia") is not None and pagamentos["total"] > 0,
          f"competencia: {pagamentos.get('competencia')}")

# As ferramentas so LEEM: nenhuma pode alterar o banco.
db = SessionLocal()
from app.models import Policy  # noqa: E402
antes = db.query(Policy).count()
db.close()
for funcao in assistente_ia.FERRAMENTAS:
    funcao()
db = SessionLocal()
verificar("as ferramentas não alteram o banco (só leem)",
          db.query(Policy).count() == antes)
db.close()

# ---------------------------------------------------------------
# 2. AS INSTRUCOES DA IA
# ---------------------------------------------------------------
print("\n2. As instruções que definem o comportamento da IA")

INSTR = assistente_ia.INSTRUCOES.lower()
verificar("as instruções dizem que ela é da Central", "central inteligente de seguros" in INSTR)
verificar("  explicam os 3 papéis da operação",
          all(p in INSTR for p in ["estipulante", "corretora", "seguradora"]))
verificar("  mandam recusar assuntos fora do escopo", "recuse" in INSTR)
verificar("  proíbem inventar números", "nunca invente" in INSTR)
verificar("  mandam usar as ferramentas antes de afirmar números",
          "sempre use as ferramentas" in INSTR)
verificar("  pedem resposta em português do Brasil", "português do brasil" in INSTR)
verificar("  pedem formato HTML (a resposta vai num balão)", "html" in INSTR)
verificar("o modelo configurado é o Opus 5", assistente_ia.MODELO == "claude-opus-5",
          f"modelo: {assistente_ia.MODELO}")

# ---------------------------------------------------------------
# 3. MEMORIA DA CONVERSA
# ---------------------------------------------------------------
print("\n3. Memória da conversa")

limpar_conversas()
cliente = logar()

r = cliente.get("/assistente")
verificar("a tela abre", r.status_code == 200)
verificar("  sem conversa, mostra a saudação inicial", "Sou o assistente" in r.text)

perguntar(cliente, "quantas apólices temos?")

db = SessionLocal()
falas = db.query(ChatMessage).all()
db.close()
verificar("a pergunta e a resposta foram guardadas", len(falas) == 2,
          f"guardadas: {len(falas)}")
verificar("  a pergunta ficou marcada como 'user'",
          any(f.papel == "user" and "quantas apólices" in f.conteudo for f in falas))
verificar("  a resposta ficou marcada como 'assistant'",
          any(f.papel == "assistant" for f in falas))
verificar("  a resposta registra qual motor respondeu",
          all(f.origem in ("ia", "regras") for f in falas if f.papel == "assistant"))

# Reabrir a tela precisa trazer a conversa de volta.
r = cliente.get("/assistente")
verificar("ao reabrir, a conversa anterior aparece", "quantas apólices temos?" in r.text)
verificar("  e a saudação inicial some", "Sou o assistente" not in r.text)

# Limpar apaga.
cliente.post("/assistente/limpar", follow_redirects=False)
db = SessionLocal()
verificar("o botão Limpar apaga a conversa", db.query(ChatMessage).count() == 0)
db.close()

# ---------------------------------------------------------------
# 4. CADA PESSOA VE SO A SUA CONVERSA
# ---------------------------------------------------------------
print("\n4. Isolamento entre pessoas")

limpar_conversas()
ana = logar("ana@sebraeprev.com.br")
bruno = logar("bruno@sebraeprev.com.br")

perguntar(ana, "quantos sinistros existem?")
perguntar(bruno, "quem esta inadimplente?")

texto_ana = ana.get("/assistente").text
texto_bruno = bruno.get("/assistente").text

verificar("Ana vê a pergunta dela", "quantos sinistros existem?" in texto_ana)
verificar("  e NÃO vê a do Bruno", "quem esta inadimplente?" not in texto_ana)
verificar("Bruno vê a pergunta dele", "quem esta inadimplente?" in texto_bruno)
verificar("  e NÃO vê a da Ana", "quantos sinistros existem?" not in texto_bruno)

# ---------------------------------------------------------------
# 5. O PLANO B (sem chave da IA)
# ---------------------------------------------------------------
print("\n5. Funcionamento sem a chave da IA")

if assistente_ia.esta_disponivel():
    pular("teste do modo básico", "há uma ANTHROPIC_API_KEY configurada; a IA está ativa")
else:
    verificar("sem chave, a IA fica indisponível", not assistente_ia.esta_disponivel())

    limpar_conversas()
    cliente = logar()
    resposta = perguntar(cliente, "quantas apólices temos?")
    verificar("  mas o assistente responde mesmo assim",
              bool(resposta.get("resposta")))
    verificar("  e informa que respondeu pelo modo básico",
              resposta.get("origem") == "regras",
              f"origem: {resposta.get('origem')}")

    r = cliente.get("/assistente")
    verificar("  a tela avisa que está em modo básico", "Modo básico" in r.text)
    verificar("  e ensina como ativar a IA", "ANTHROPIC_API_KEY" in r.text)

    # O modo básico continua respondendo bem.
    for pergunta_teste, esperado in [
        ("olá, tudo bem?", "assistente"),
        ("o que é capital segurado?", "seguradora paga"),
        ("que horas são?", "não posso responder"),
    ]:
        texto = perguntar(cliente, pergunta_teste)["resposta"].lower()
        verificar(f'  "{pergunta_teste}" ainda funciona', esperado in texto,
                  f"respondeu: {texto[:70]}")

# ---------------------------------------------------------------
# 6. A IA DE VERDADE (só roda se houver chave)
# ---------------------------------------------------------------
print("\n6. A IA de verdade")

if not assistente_ia.esta_disponivel():
    pular("chamada real à IA",
          "sem ANTHROPIC_API_KEY no .env. Configure a chave e rode de novo "
          "para testar a IA (cada pergunta tem um custo).")
else:
    limpar_conversas()
    cliente = logar()

    r = perguntar(cliente, "Quantas apólices ativas nós temos?")
    verificar("a IA respondeu", r.get("origem") == "ia", f"origem: {r.get('origem')}")
    resumo = json.loads(assistente_ia.resumo_da_carteira())
    ativas = resumo["apolices_por_status"].get("Ativa", 0)
    verificar(f"  e trouxe o número certo ({ativas})", str(ativas) in r["resposta"],
              f"respondeu: {r['resposta'][:120]}")

    # Memoria: a segunda pergunta depende da primeira.
    r2 = perguntar(cliente, "E quantas estão vencidas?")
    verificar("  entende a pergunta de continuação", bool(r2.get("resposta")),
              f"respondeu: {r2.get('resposta', '')[:100]}")

    r3 = perguntar(cliente, "me conta uma piada")
    texto = r3["resposta"].lower()
    verificar("  recusa assunto fora do escopo",
              any(p in texto for p in ["não posso", "nao posso", "assistente da central"]),
              f"respondeu: {texto[:100]}")

# ---------------------------------------------------------------
# LIMPEZA
# ---------------------------------------------------------------
limpar_conversas()
db = SessionLocal()
n = db.query(LoginHistory).delete()
db.commit()
db.close()
print(f"\n(limpeza: conversas apagadas e {n} logins de teste removidos)")

print("\n" + "=" * 54)
print(f"RESULTADO: {passou} passaram, {falhou} falharam, {pulados} pulados")
print("=" * 54 + "\n")

sys.exit(1 if falhou else 0)
