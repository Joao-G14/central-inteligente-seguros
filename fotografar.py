"""
fotografar.py
-------------
Tira a foto da carteira: guarda como ela esta neste momento.

QUANDO USAR
-----------
Na pratica, quase nunca — o sistema faz isso sozinho quando liga, se
ainda nao houver foto do mes. Este script serve para tres casos:

  1. conferir os numeros logo depois de carregar uma planilha
  2. rodar por agendamento, num servidor que fica sempre ligado (e que
     portanto nao "liga" todo mes)
  3. registrar um mes que passou sem ninguem abrir o sistema

COMO USAR
---------
    python fotografar.py                 foto do mes corrente
    python fotografar.py --refazer       atualiza a foto do mes corrente
    python fotografar.py --listar        mostra as fotos guardadas
    python fotografar.py --mes 07/2026   registra um mes especifico

POR QUE ISTO IMPORTA
--------------------
O Dashboard mostra a carteira de HOJE. Sem estas fotos, nao ha como
saber como ela estava no mes passado — e essa informacao nao pode ser
reconstruida depois. Um mes que passou sem foto esta perdido.

COMO AGENDAR (Windows)
----------------------
No "Agendador de Tarefas", uma tarefa mensal:

    Programa  : C:\\caminho\\do\\projeto\\venv\\Scripts\\python.exe
    Argumento : fotografar.py
    Iniciar em: C:\\caminho\\do\\projeto

COMO AGENDAR (servidor Linux)
-----------------------------
    0 6 1 * *  cd /app && ./venv/bin/python fotografar.py
"""

import sys

from app import historico
from app.database import SessionLocal, criar_tabelas


def _reais(valor: float) -> str:
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _mostrar(foto, criou: bool) -> None:
    print()
    print("=" * 58)
    print(f"  FOTO DA CARTEIRA — {foto.competencia}")
    print("=" * 58)
    print(f"  {'nova' if criou else 'atualizada'} em "
          f"{foto.data_foto.strftime('%d/%m/%Y as %H:%M:%S')}")
    print()
    print(f"  apolices no total    {foto.apolices_total:>14}")
    print(f"    ativas             {foto.apolices_ativas:>14}")
    print(f"    a renovar          {foto.apolices_a_renovar:>14}")
    print(f"    vencidas           {foto.apolices_vencidas:>14}")
    print(f"    canceladas         {foto.apolices_canceladas:>14}")
    print()
    print(f"  capital segurado     {_reais(foto.capital_segurado):>14}")
    print(f"  premio mensal        {_reais(foto.premio_mensal):>14}")
    print(f"  vidas cobertas       {foto.vidas_cobertas:>14}")
    print()
    print(f"  sinistros abertos    {foto.sinistros_abertos:>14}")
    print(f"  propostas na esteira {foto.propostas_esteira:>14}")
    print(f"  inadimplentes        {foto.inadimplentes:>14}")
    print(f"  valor em atraso      {_reais(foto.valor_inadimplencia):>14}")
    print(f"  pendencias abertas   {foto.pendencias_abertas:>14}")
    print("=" * 58)
    print()


def listar(db) -> None:
    fotos = historico.historico_ordenado(db, quantos=120)

    print()
    if not fotos:
        print("Nenhuma foto ainda. Rode 'python fotografar.py' para tirar a primeira.")
        print()
        return

    print(f"{len(fotos)} foto(s) guardada(s):")
    print()
    print(f"  {'MES':<9} {'APOLICES':>9} {'ATIVAS':>7} {'CAPITAL':>16} {'PREMIO':>12}")
    print("  " + "-" * 56)
    for f in fotos:
        print(f"  {f.competencia:<9} {f.apolices_total:>9} {f.apolices_ativas:>7} "
              f"{_reais(f.capital_segurado):>16} {_reais(f.premio_mensal):>12}")
    print()

    if len(fotos) >= 2:
        primeira, ultima = fotos[0], fotos[-1]
        variacao = ultima.capital_segurado - primeira.capital_segurado
        sinal = "+" if variacao >= 0 else ""
        print(f"  De {primeira.competencia} a {ultima.competencia}: "
              f"{sinal}{_reais(variacao)} de capital")
        print()


def main() -> None:
    argumentos = sys.argv[1:]

    # Garante que as tabelas existem, para o script funcionar mesmo num
    # banco recem-criado.
    criar_tabelas()
    db = SessionLocal()

    try:
        if argumentos and argumentos[0] in ("--listar", "-l"):
            listar(db)
            return

        mes = None
        if "--mes" in argumentos:
            posicao = argumentos.index("--mes")
            if posicao + 1 < len(argumentos):
                mes = argumentos[posicao + 1]
            else:
                print("Falta o mes. Exemplo: python fotografar.py --mes 07/2026")
                return

        refazer = "--refazer" in argumentos or "-r" in argumentos

        foto, criou = historico.fotografar(db, competencia=mes, refazer=refazer)

        if not criou and not refazer:
            print()
            print(f"A foto de {foto.competencia} ja existe, tirada em "
                  f"{foto.data_foto.strftime('%d/%m/%Y as %H:%M')}.")
            print("Ela NAO foi alterada: uma vez tirada, a foto do mes fica como esta.")
            print("Para atualizar de proposito, rode com --refazer.")
            print()
            return

        _mostrar(foto, criou)

    finally:
        db.close()


if __name__ == "__main__":
    main()
