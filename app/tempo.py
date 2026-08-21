"""
tempo.py
--------
A hora certa do sistema.

O PROBLEMA QUE ISTO RESOLVE
---------------------------
O Python, quando voce pede datetime.now(), devolve a hora do RELOGIO DA
MAQUINA. No seu computador isso e o horario de Brasilia, e tudo parece
certo. Mas servidores na nuvem quase sempre rodam em UTC, que esta
3 horas a frente.

Ou seja: um login feito as 16h apareceria no historico como 19h. Num
registro de acesso, que serve justamente para auditoria, isso e grave —
alguem poderia ser acusado de ter entrado num horario em que nao estava
trabalhando.

A SOLUCAO
---------
Nunca usar datetime.now() direto. Usar agora(), definida aqui, que
sempre devolve a hora de Brasilia, independente do fuso do servidor.
"""

from datetime import date, datetime, timedelta, timezone

# ---------------------------------------------------------------
# O FUSO DE BRASILIA
# ---------------------------------------------------------------
# Tentamos usar o fuso oficial pelo nome ("America/Sao_Paulo"). Ele vem
# da base de fusos do sistema e ja cuida de horario de verao, caso o
# Brasil volte a adotar.
#
# O Windows NAO traz essa base instalada. Se ela nao existir, usamos
# UTC-3 fixo, que e o horario de Brasilia desde 2019, quando o horario
# de verao foi extinto. Funciona igual — so nao se ajustaria sozinho se
# a regra mudasse.
try:
    from zoneinfo import ZoneInfo

    FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")
    FUSO_PELO_NOME = True
except Exception:
    FUSO_BRASILIA = timezone(timedelta(hours=-3), name="America/Sao_Paulo")
    FUSO_PELO_NOME = False


def agora() -> datetime:
    """
    A data e hora atuais em Brasilia.

    Devolvemos SEM o fuso colado no objeto (naive), porque:
      - o SQLite guarda datas como texto simples
      - as comparacoes e a formatacao ficam mais simples
      - todo o sistema usa o mesmo fuso, entao nao ha ambiguidade

    O importante e que o VALOR e sempre o horario de Brasilia.
    """
    return datetime.now(FUSO_BRASILIA).replace(tzinfo=None)


def hoje() -> date:
    """A data de hoje em Brasilia."""
    return agora().date()
