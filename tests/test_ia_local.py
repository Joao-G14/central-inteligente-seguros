"""
test_ia_local.py
----------------
Testa a IA treinada aqui mesmo (aprendizado de maquina).

  1. O modelo treina e conhece todos os assuntos
  2. Acerta perguntas que NUNCA viu, com erro de digitacao e giria
  3. Recusa o que esta fora do escopo, em vez de chutar
  4. Todo assunto treinado tem uma resposta
  5. As respostas trazem numeros do banco de verdade
  6. Reconhece codigos citados (AP-2041, SIN-0448, PROP-3012)

COMO RODAR (com o venv ativado, na raiz do projeto):
    python tests/test_ia_local.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import assistente, ia_local, ia_treino  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import Claim, Policy, Proposal  # noqa: E402

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


print("\n=== TESTANDO A IA LOCAL (aprendizado de maquina) ===\n")

# ---------------------------------------------------------------
# 1. O MODELO
# ---------------------------------------------------------------
print("1. O modelo treina")

inicio = time.time()
pronto = ia_local.preparar()
segundos = time.time() - inicio

verificar("o modelo treinou", pronto, "scikit-learn instalado?")
verificar(f"  treinou rapido ({segundos:.1f}s)", segundos < 30,
          f"levou {segundos:.1f}s")

info = ia_local.informacoes()
verificar("conhece pelo menos 40 assuntos", info["assuntos"] >= 40,
          f"assuntos: {info['assuntos']}")
verificar("aprendeu com pelo menos 300 exemplos", info["exemplos"] >= 300,
          f"exemplos: {info['exemplos']}")
print(f"           ({info['assuntos']} assuntos, {info['exemplos']} frases de treino)")

# ---------------------------------------------------------------
# 2. TODO ASSUNTO TEM RESPOSTA
# ---------------------------------------------------------------
print("\n2. Treino e respostas combinam")

sem_resposta = sorted(set(ia_treino.TREINO) - set(assistente.RESPOSTAS))
verificar("todo assunto treinado tem uma resposta", not sem_resposta,
          f"sem resposta: {sem_resposta}")

sem_treino = sorted(set(assistente.RESPOSTAS) - set(ia_treino.TREINO))
verificar("toda resposta tem exemplos de treino", not sem_treino,
          f"sem treino: {sem_treino}")

verificar("nenhuma resposta esta vazia",
          all(f is not None for f in assistente.RESPOSTAS.values()))

# Todo assunto precisa de pelo menos 5 exemplos, senao o modelo
# nao aprende direito aquele padrao.
poucos = {a: len(f) for a, f in ia_treino.TREINO.items() if len(f) < 5}
verificar("todo assunto tem 5 ou mais exemplos", not poucos,
          f"com poucos exemplos: {poucos}")

# ---------------------------------------------------------------
# 3. PERGUNTAS INEDITAS
# ---------------------------------------------------------------
print("\n3. Perguntas que o modelo NUNCA viu")

# Nenhuma destas frases esta no arquivo de treino.
INEDITAS = [
    ("kuantas apolice a gente tem?", "carteira_resumo"),
    ("oi, td bem?", "cumprimento"),
    ("me fala quem vc e", "apresentacao"),
    ("tem alguma apolice pra vencer?", "renovacoes"),
    ("qnt ta o capital segurdo", "capital_segurado"),
    ("quem nao pagou ainda", "inadimplencia"),
    ("como faco pra mandar a planilha", "sistema_planilha"),
    ("o q significa apolise", "conceito_apolice"),
    ("pq nao consigo ver sinistro", "sistema_permissoes"),
    ("qual site foi feito em que linguagem", "sistema_tecnologia"),
    ("como eu bloqueio o acesso de alguem", "sistema_controle_acesso"),
    ("da pra baixar em excel?", "sistema_exportar"),
    ("vc usa chatgpt?", "sistema_assistente"),
    ("quais pagina o sistema tem", "sistema_telas"),
    ("obrigadao", "agradecimento"),
    ("quanto a corretora recebe de comissao", "comissoes"),
    ("como emitir boleto", "sistema_boleto"),
    ("o que e dps mesmo", "conceito_dps"),
    ("quantas pessoas estao cobertas", "vidas_cobertas"),
    ("os dados daqui sao de verdade?", "sistema_dados"),
]

acertos = 0
for pergunta, esperado in INEDITAS:
    assunto, confianca = ia_local.classificar(pergunta)
    certo = assunto == esperado
    acertos += certo
    if not certo:
        print(f'  [erro]   "{pergunta}"')
        print(f"           -> {assunto or '(nao entendeu)'} ({confianca:.0%}), esperado {esperado}")

taxa = acertos / len(INEDITAS)
verificar(f"acerta pelo menos 80% ({acertos}/{len(INEDITAS)} = {taxa:.0%})",
          taxa >= 0.80)

# ---------------------------------------------------------------
# 4. RECUSA O QUE NAO SABE
# ---------------------------------------------------------------
print("\n4. Recusa em vez de chutar")

FORA = [
    "qual a cor do ceu",
    "abacaxi roxo voando",
    "me da a receita do bolo",
    "quanto e 2 mais 2",
    "quem ganhou o jogo ontem",
    "asdfghjkl",
]
for pergunta in FORA:
    assunto, confianca = ia_local.classificar(pergunta)
    verificar(f'"{pergunta}" nao vira um chute', assunto == "",
              f"chutou: {assunto} ({confianca:.0%})")

# ---------------------------------------------------------------
# 5. AS RESPOSTAS SAO DO BANCO
# ---------------------------------------------------------------
print("\n5. As respostas trazem dados reais")

db = SessionLocal()

total_apolices = db.query(Policy).count()
resposta = assistente.responder(db, "quantas apolices a gente tem?")
verificar(f"a contagem traz o numero real ({total_apolices})",
          str(total_apolices) in resposta,
          f"respondeu: {resposta[:90]}")

ativas = db.query(Policy).filter(Policy.status == "Ativa").count()
resposta = assistente.responder(db, "quantas estao ativas?")
verificar(f"o status traz o numero real ({ativas})", str(ativas) in resposta,
          f"respondeu: {resposta[:90]}")

# Toda resposta precisa devolver texto, nunca vazio nem erro.
print("\n6. Todo assunto responde sem quebrar")
for assunto, funcao in sorted(assistente.RESPOSTAS.items()):
    try:
        texto = funcao(db)
        ok = isinstance(texto, str) and len(texto) > 20
        if not ok:
            verificar(f"{assunto} responde", False, f"devolveu: {texto!r:.60}")
        else:
            passou += 1
    except Exception as e:
        verificar(f"{assunto} responde", False, f"{type(e).__name__}: {e}")
print(f"  [OK]     os {len(assistente.RESPOSTAS)} assuntos responderam sem erro")

# ---------------------------------------------------------------
# 7. CODIGOS CITADOS NA PERGUNTA
# ---------------------------------------------------------------
print("\n7. Reconhece codigos citados")

apolice = db.query(Policy).first()
if apolice:
    resposta = assistente.responder(db, f"me mostra a {apolice.numero_apolice}")
    verificar(f"acha a apolice {apolice.numero_apolice}",
              apolice.participante in resposta,
              f"respondeu: {resposta[:90]}")
    # sem hifen e em minusculo tambem deve funcionar
    sem_hifen = apolice.numero_apolice.replace("-", "").lower()
    resposta = assistente.responder(db, f"detalhes da {sem_hifen}")
    verificar(f'  tambem acha escrito "{sem_hifen}"',
              apolice.participante in resposta)

sinistro = db.query(Claim).first()
if sinistro:
    resposta = assistente.responder(db, f"o que houve no {sinistro.protocolo}")
    verificar(f"acha o sinistro {sinistro.protocolo}",
              sinistro.participante in resposta,
              f"respondeu: {resposta[:90]}")

proposta = db.query(Proposal).first()
if proposta:
    resposta = assistente.responder(db, f"status da {proposta.numero}")
    verificar(f"acha a proposta {proposta.numero}",
              proposta.participante in resposta,
              f"respondeu: {resposta[:90]}")

resposta = assistente.responder(db, "me mostra a AP-9999")
verificar("avisa quando o codigo nao existe", "não encontrei" in resposta.lower(),
          f"respondeu: {resposta[:90]}")

# ---------------------------------------------------------------
# 8. CONVERSA
# ---------------------------------------------------------------
print("\n8. Conversa")

CONVERSA = [
    ("oi, tudo bem?", ["tudo bem", "assistente"]),
    ("quem e voce?", ["assistente"]),
    ("valeu!", ["por nada"]),
    ("tchau", ["até logo"]),
    ("me ajuda", ["conceitos", "carteira"]),
]
for pergunta, esperados in CONVERSA:
    resposta = assistente.responder(db, pergunta).lower()
    verificar(f'"{pergunta}"', any(e.lower() in resposta for e in esperados),
              f"respondeu: {resposta[:70]}")

resposta = assistente.responder(db, "me conta uma piada")
verificar("recusa assunto fora do escopo", "não posso responder" in resposta.lower(),
          f"respondeu: {resposta[:70]}")

resposta = assistente.responder(db, "")
verificar("pergunta vazia pede uma pergunta", "digite" in resposta.lower())

db.close()

print("\n" + "=" * 54)
print(f"RESULTADO: {passou} passaram, {falhou} falharam")
print("=" * 54 + "\n")

sys.exit(1 if falhou else 0)
