"""
test_banco.py
-------------
Confere se o banco de dados foi criado corretamente.

COMO RODAR (com o venv ativado, na raiz do projeto):
    python tests/test_banco.py

Cada verificacao mostra [OK] ou [FALHOU].
Se algo falhar, rode  python -m app.seed  e teste de novo.

Nao usamos pytest de proposito: assim voces conseguem ler e entender
o teste inteiro sem aprender uma biblioteca nova agora.
"""

import sys
from pathlib import Path

# Faz o Python enxergar a pasta app/ mesmo rodando de dentro de tests/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.auth import conferir_senha, gerar_hash  # noqa: E402
from app.database import ARQUIVO_BANCO, SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    PERFIS_VALIDOS,
    LoginHistory,
    Policy,
    User,
)

# Contadores do resultado final.
passou = 0
falhou = 0


def verificar(descricao: str, condicao: bool, detalhe: str = "") -> None:
    """Registra o resultado de uma verificacao e imprime na tela."""
    global passou, falhou
    if condicao:
        passou += 1
        print(f"  [OK]     {descricao}")
    else:
        falhou += 1
        print(f"  [FALHOU] {descricao}")
        if detalhe:
            print(f"           -> {detalhe}")


print("\n=== TESTANDO O BANCO DE DADOS ===\n")

# ---------------------------------------------------------------
# 1. O arquivo do banco existe?
# ---------------------------------------------------------------
print("1. Arquivo do banco")
verificar(
    "database/central.db existe",
    ARQUIVO_BANCO.exists(),
    "rode: python -m app.seed",
)

if not ARQUIVO_BANCO.exists():
    print("\nO banco nao existe. Rode 'python -m app.seed' antes de testar.\n")
    sys.exit(1)

db = SessionLocal()

# ---------------------------------------------------------------
# 2. Tabela users
# ---------------------------------------------------------------
print("\n2. Tabela users")

usuarios = db.query(User).all()
verificar("tem exatamente 3 usuarios", len(usuarios) == 3, f"encontrados: {len(usuarios)}")

perfis_encontrados = sorted(u.perfil for u in usuarios)
verificar(
    "existe um usuario de cada perfil",
    perfis_encontrados == sorted(PERFIS_VALIDOS),
    f"encontrados: {perfis_encontrados}",
)

verificar(
    "nenhuma senha esta em texto puro",
    all(u.senha_hash.startswith("$2b$") for u in usuarios),
    "todo hash bcrypt comeca com $2b$",
)

verificar("todos os usuarios estao ativos", all(u.ativo for u in usuarios))

# ---------------------------------------------------------------
# 3. As senhas funcionam?
# ---------------------------------------------------------------
print("\n3. Senhas")

senhas_esperadas = {
    "estipulante@sebraeprev.com.br": config.SENHA_ESTIPULANTE,
    "corretora@sebraeprev.com.br": config.SENHA_CORRETORA,
    "seguradora@sebraeprev.com.br": config.SENHA_SEGURADORA,
}

for email, senha in senhas_esperadas.items():
    usuario = db.query(User).filter(User.email == email).first()
    verificar(f"{email} existe", usuario is not None)
    if usuario:
        verificar(f"  senha correta e aceita ({usuario.perfil})", conferir_senha(senha, usuario.senha_hash))
        verificar("  senha errada e recusada", not conferir_senha("senha-errada", usuario.senha_hash))

verificar(
    "o mesmo texto gera hashes diferentes (sal aleatorio)",
    gerar_hash("teste") != gerar_hash("teste"),
)

# ---------------------------------------------------------------
# 4. Tabela policies
# ---------------------------------------------------------------
print("\n4. Tabela policies (carteira de apolices)")

apolices = db.query(Policy).all()
verificar("tem exatamente 50 apolices", len(apolices) == 50, f"encontradas: {len(apolices)}")

numeros = [a.numero_apolice for a in apolices]
verificar("nenhum numero de apolice repetido", len(numeros) == len(set(numeros)))

verificar(
    "as 8 apolices do prototipo estao no banco",
    db.query(Policy).filter(Policy.origem == "prototipo").count() == 8,
)
verificar(
    "os 10 segurados da planilha estao no banco",
    db.query(Policy).filter(Policy.origem == "planilha").count() == 10,
)

ap2041 = db.query(Policy).filter(Policy.numero_apolice == "AP-2041").first()
verificar("AP-2041 existe (veio do prototipo)", ap2041 is not None)
if ap2041:
    verificar("  participante e Marcos A. Ribeiro", ap2041.participante == "Marcos A. Ribeiro")
    verificar("  capital total e 250.000", ap2041.capital_total == 250000.0)
    verificar("  cobertura e Morte + Invalidez", ap2041.cobertura == "Morte + Invalidez")

# As 8 apolices do prototipo devem mostrar na tela exatamente o mesmo status
# que aparece no arquivo Portal_Central_Inteligente_Seguros.html.
# Como as datas sao calculadas a partir de hoje, isso vale em qualquer dia.
STATUS_DO_PROTOTIPO = {
    "AP-2041": "A renovar",
    "AP-1899": "A renovar",
    "AP-1987": "A renovar",
    "AP-2115": "A renovar",
    "AP-2033": "Ativa",
    "AP-1954": "Ativa",
    "AP-2087": "Ativa",
    "AP-2160": "Ativa",
}

for numero, status_esperado in STATUS_DO_PROTOTIPO.items():
    apolice = db.query(Policy).filter(Policy.numero_apolice == numero).first()
    verificar(
        f"  {numero} esta como '{status_esperado}' (igual ao prototipo)",
        apolice is not None and apolice.status == status_esperado,
        f"encontrado: {apolice.status if apolice else 'apolice nao existe'}",
    )

verificar(
    "nenhuma apolice do prototipo aparece como Vencida",
    db.query(Policy)
    .filter(Policy.origem == "prototipo", Policy.status == "Vencida")
    .count()
    == 0,
)

ana = db.query(Policy).filter(Policy.matricula == "100001").first()
verificar("segurada da planilha (matricula 100001) existe", ana is not None)
if ana:
    verificar("  nome e Ana Beatriz Souza", ana.participante == "Ana Beatriz Souza")
    verificar("  premio mensal e 60,70", abs(ana.premio_mensal - 60.70) < 0.01)

verificar(
    "toda apolice tem vencimento depois do inicio",
    all(a.data_vencimento > a.data_inicio for a in apolices),
)

status_validos = {"Ativa", "A renovar", "Vencida", "Cancelada"}
verificar(
    "todos os status sao validos",
    all(a.status in status_validos for a in apolices),
    f"status encontrados: {sorted({a.status for a in apolices})}",
)

verificar(
    "toda apolice tem algum capital maior que zero",
    all(a.capital_total > 0 for a in apolices),
)

# ---------------------------------------------------------------
# 5. Tabela login_history
# ---------------------------------------------------------------
print("\n5. Tabela login_history")

# A tabela deve existir e comecar vazia: ela so enche quando alguem
# realmente fizer login (isso e a Fase 3).
total_logins = db.query(LoginHistory).count()
verificar("a tabela existe e pode ser consultada", total_logins >= 0)
verificar("comeca vazia (ninguem logou ainda)", total_logins == 0, f"encontrados: {total_logins}")

# Testa gravar e apagar um registro, para provar que a tabela funciona.
registro = LoginHistory(
    email_informado="teste@teste.com",
    perfil_informado="ESTIPULANTE",
    sucesso=False,
    motivo="teste automatico",
    ip="127.0.0.1",
)
db.add(registro)
db.commit()

gravado = db.query(LoginHistory).filter(LoginHistory.motivo == "teste automatico").first()
verificar("consegue gravar um acesso", gravado is not None)
if gravado:
    verificar("  a data e hora foram preenchidas sozinhas", gravado.data_hora is not None)
    db.delete(gravado)
    db.commit()
    verificar(
        "  consegue apagar o registro de teste",
        db.query(LoginHistory).filter(LoginHistory.motivo == "teste automatico").count() == 0,
    )

# ---------------------------------------------------------------
# 6. Arquivo sql/banco.sql
# ---------------------------------------------------------------
print("\n6. Script SQL")

arquivo_sql = Path(__file__).resolve().parent.parent / "sql" / "banco.sql"
verificar("sql/banco.sql existe", arquivo_sql.exists())
if arquivo_sql.exists():
    conteudo = arquivo_sql.read_text(encoding="utf-8")
    verificar("  contem a tabela users", "CREATE TABLE users" in conteudo)
    verificar("  contem a tabela login_history", "CREATE TABLE login_history" in conteudo)
    verificar("  contem a tabela policies", "CREATE TABLE policies" in conteudo)
    # O SQLite escreve os nomes de tabela entre aspas: INSERT INTO "policies"
    total_inserts = conteudo.count('INSERT INTO "policies"')
    verificar(
        "  contem os dados das 50 apolices",
        total_inserts == 50,
        f"encontrados: {total_inserts} INSERT",
    )
    verificar(
        "  contem os dados dos 3 usuarios",
        conteudo.count('INSERT INTO "users"') == 3,
    )

db.close()

# ---------------------------------------------------------------
# RESULTADO
# ---------------------------------------------------------------
print("\n" + "=" * 50)
print(f"RESULTADO: {passou} passaram, {falhou} falharam")
print("=" * 50 + "\n")

sys.exit(1 if falhou else 0)
