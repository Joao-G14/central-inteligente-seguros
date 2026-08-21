"""
backup.py
---------
Faz uma copia de seguranca do banco de dados.

POR QUE ISTO EXISTE
-------------------
Todo o sistema vive num unico arquivo: database/central.db. Ele NAO vai
para o GitHub (tem dados pessoais). Se esse arquivo corromper, o disco
falhar ou alguem apagar por engano, perde-se tudo o que foi enviado por
planilha e toda a configuracao de acesso.

Backup nao e luxo: e a diferenca entre um susto e um desastre.

COMO USAR
---------
    python backup.py                 faz uma copia agora
    python backup.py --listar        mostra as copias existentes
    python backup.py --restaurar 3   volta para a copia numero 3

As copias ficam em backups/ e NAO vao para o GitHub.

COMO AUTOMATIZAR (Windows)
--------------------------
Abra o "Agendador de Tarefas" e crie uma tarefa que rode, todo dia:

    Programa : C:\\caminho\\do\\projeto\\venv\\Scripts\\python.exe
    Argumento: backup.py
    Iniciar em: C:\\caminho\\do\\projeto

COMO AUTOMATIZAR (servidor Linux)
---------------------------------
    0 3 * * *  cd /app && ./venv/bin/python backup.py
"""

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
BANCO = RAIZ / "database" / "central.db"
PASTA_BACKUPS = RAIZ / "backups"

# Quantas copias guardar. As mais antigas sao apagadas para a pasta nao
# crescer sem parar.
QUANTAS_GUARDAR = 30


def _copias_existentes() -> list[Path]:
    """As copias, da mais nova para a mais antiga."""
    if not PASTA_BACKUPS.exists():
        return []
    return sorted(PASTA_BACKUPS.glob("central-*.db"), reverse=True)


def _tamanho(arquivo: Path) -> str:
    kb = arquivo.stat().st_size / 1024
    return f"{kb / 1024:.1f} MB" if kb > 1024 else f"{kb:.0f} KB"


def fazer_copia() -> Path | None:
    """
    Copia o banco para a pasta backups/, com data e hora no nome.

    Usamos o comando de backup do proprio SQLite, e nao um simples copiar
    e colar. A diferenca importa: se alguem estiver usando o sistema no
    momento da copia, um copiar comum poderia pegar o arquivo no meio de
    uma gravacao e gerar uma copia corrompida. O backup do SQLite espera
    o momento seguro.
    """
    if not BANCO.exists():
        print(f"ERRO: o banco nao existe em {BANCO}")
        print("      Rode o sistema uma vez, ou 'python -m app.seed'.")
        return None

    PASTA_BACKUPS.mkdir(exist_ok=True)

    quando = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    destino = PASTA_BACKUPS / f"central-{quando}.db"

    # Se ja existir uma copia com este nome (duas execucoes no mesmo
    # segundo), acrescentamos um numero. Sem isso, a segunda copia
    # sobrescreveria a primeira em silencio — e backup que apaga backup
    # e pior do que nao ter backup.
    contador = 2
    while destino.exists():
        destino = PASTA_BACKUPS / f"central-{quando}_{contador}.db"
        contador += 1

    origem = sqlite3.connect(BANCO)
    copia = sqlite3.connect(destino)
    with copia:
        origem.backup(copia)
    copia.close()
    origem.close()

    print(f"Copia criada: {destino.name}  ({_tamanho(destino)})")

    # Apaga as mais antigas.
    copias = _copias_existentes()
    if len(copias) > QUANTAS_GUARDAR:
        for velha in copias[QUANTAS_GUARDAR:]:
            velha.unlink()
            print(f"  copia antiga removida: {velha.name}")

    return destino


def listar() -> None:
    """Mostra as copias existentes."""
    copias = _copias_existentes()

    print()
    if not copias:
        print("Nenhuma copia ainda. Rode 'python backup.py' para criar a primeira.")
        print()
        return

    print(f"{len(copias)} copia(s) em backups/ (da mais nova para a mais antiga):")
    print()
    for i, arquivo in enumerate(copias, 1):
        quando = datetime.fromtimestamp(arquivo.stat().st_mtime)
        print(f"  {i:>3}. {arquivo.name}   {_tamanho(arquivo):>9}   "
              f"{quando.strftime('%d/%m/%Y as %H:%M')}")
    print()
    print("Para voltar para uma delas:  python backup.py --restaurar NUMERO")
    print()


def restaurar(numero: int) -> None:
    """
    Substitui o banco atual por uma copia.

    Antes de sobrescrever, guardamos o banco atual como
    'antes-de-restaurar'. Assim, se a restauracao foi um engano, ainda
    da para voltar.
    """
    copias = _copias_existentes()

    if not copias:
        print("Nenhuma copia disponivel.")
        return

    if not 1 <= numero <= len(copias):
        print(f"Numero invalido. Escolha de 1 a {len(copias)}.")
        print("Use 'python backup.py --listar' para ver a lista.")
        return

    escolhida = copias[numero - 1]

    print()
    print("ATENCAO: isto vai SUBSTITUIR o banco atual.")
    print(f"  copia escolhida: {escolhida.name}")
    print(f"  banco atual    : {BANCO.name}")
    print()
    print("Pare o servidor antes de continuar, senao o arquivo estara em uso.")
    resposta = input('Digite "confirmo" para prosseguir: ').strip().lower()

    if resposta != "confirmo":
        print("Cancelado. Nada foi alterado.")
        return

    if BANCO.exists():
        segredo = PASTA_BACKUPS / "antes-de-restaurar.db"
        shutil.copy2(BANCO, segredo)
        print(f"  banco atual guardado como {segredo.name}")

    shutil.copy2(escolhida, BANCO)
    print(f"  restaurado a partir de {escolhida.name}")
    print()
    print("Pronto. Ligue o servidor de novo.")
    print()


def main() -> None:
    argumentos = sys.argv[1:]

    if not argumentos:
        fazer_copia()
        return

    if argumentos[0] in ("--listar", "-l"):
        listar()
        return

    if argumentos[0] in ("--restaurar", "-r"):
        if len(argumentos) < 2 or not argumentos[1].isdigit():
            print("Falta o numero da copia. Exemplo: python backup.py --restaurar 3")
            print("Use 'python backup.py --listar' para ver os numeros.")
            return
        restaurar(int(argumentos[1]))
        return

    print(__doc__)


if __name__ == "__main__":
    main()
