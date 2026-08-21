"""
historico.py
------------
Duas coisas que guardam o passado do sistema:

  1. REGISTRO DE ALTERACOES — quem mudou o que, e quando
  2. FOTOGRAFIA DA CARTEIRA — como a carteira estava em cada mes

As duas existem pelo mesmo motivo: informacao sobre o passado nao pode
ser reconstruida depois. Se ninguem anotou, ninguem sabe.
"""

from sqlalchemy import func

from app import tempo
from app.models import (
    CarteiraSnapshot,
    ChangeLog,
    Claim,
    Delinquency,
    Pendency,
    Policy,
    Proposal,
)

# ===============================================================
# 1. REGISTRO DE ALTERACOES
# ===============================================================
# Campos que NAO entram no registro. Ou porque sao preenchidos pelo
# proprio sistema, ou porque nao dizem nada a quem le depois.
CAMPOS_IGNORADOS = {"id", "criado_em", "atualizado_em", "origem"}


def _mostrar(valor) -> str:
    """
    Deixa um valor legivel para quem for ler o historico daqui a meses.

    Datas em dia/mes/ano, dinheiro no padrao brasileiro, sim/nao em vez
    de True/False. Ninguem quer abrir o historico e ler "2026-08-21" ou
    "250000.0".
    """
    if valor is None or valor == "":
        return "(vazio)"
    if isinstance(valor, bool):
        return "sim" if valor else "nao"
    if hasattr(valor, "strftime"):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, float):
        return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return str(valor)


def comparar(antes: dict, depois: dict) -> str:
    """
    Monta o texto do que mudou entre dois estados.

    Devolve algo assim:

        capital_total: 250.000,00 -> 300.000,00
        status: Ativa -> A renovar

    Devolve texto vazio quando nada mudou — e nesse caso nem gravamos
    registro, para o historico nao encher de linhas inuteis.
    """
    linhas = []
    for campo, valor_novo in depois.items():
        if campo in CAMPOS_IGNORADOS:
            continue
        valor_antigo = antes.get(campo)
        if valor_antigo != valor_novo:
            linhas.append(
                f"{campo}: {_mostrar(valor_antigo)} -> {_mostrar(valor_novo)}"
            )
    return "\n".join(linhas)


def resumir(valores: dict) -> str:
    """
    Monta o texto de um registro novo ou excluido.

    Aqui nao ha "antes e depois": listamos o conteudo, para quem ler
    depois saber o que existia.
    """
    linhas = [
        f"{campo}: {_mostrar(valor)}"
        for campo, valor in valores.items()
        if campo not in CAMPOS_IGNORADOS and valor not in (None, "")
    ]
    return "\n".join(linhas)


def registrar(db, cadastro: str, acao: str, usuario, ip: str | None = None,
              registro_id: int | None = None, identificacao: str = "",
              alteracoes: str = "") -> None:
    """
    Grava uma linha no registro de alteracoes.

    Se "alteracoes" vier vazio numa acao de alterar, nao grava nada: a
    pessoa abriu a tela, clicou em salvar e nao mudou coisa alguma.
    """
    if acao == "alterou" and not alteracoes:
        return

    db.add(ChangeLog(
        cadastro=cadastro,
        registro_id=registro_id,
        identificacao=identificacao or None,
        acao=acao,
        alteracoes=alteracoes or None,
        usuario_email=(getattr(usuario, "email_acesso", None)
                       or getattr(usuario, "nome", None)),
        usuario_perfil=getattr(usuario, "perfil", None),
        ip=ip,
    ))
    db.commit()


def estado_atual(registro, campos: list[str]) -> dict:
    """Le os valores atuais de um registro, para comparar depois."""
    return {c: getattr(registro, c, None) for c in campos}


# ===============================================================
# 2. FOTOGRAFIA DA CARTEIRA
# ===============================================================
def _contar_vidas(db) -> int:
    """
    Quantas coberturas ativas existem.

    Quem tem Morte + Invalidez conta duas vezes, porque sao dois riscos
    cobertos. E a mesma conta usada na tela de Ramos/Produtos.
    """
    com_morte = db.query(func.count(Policy.id)).filter(
        Policy.status == "Ativa", Policy.capital_morte > 0
    ).scalar() or 0
    com_invalidez = db.query(func.count(Policy.id)).filter(
        Policy.status == "Ativa", Policy.capital_invalidez > 0
    ).scalar() or 0
    return com_morte + com_invalidez


def _medir(db) -> dict:
    """Mede a carteira agora e devolve todos os numeros."""
    por_status = dict(
        db.query(Policy.status, func.count(Policy.id))
        .group_by(Policy.status)
        .all()
    )

    capital = db.query(func.sum(Policy.capital_total)).filter(
        Policy.status == "Ativa"
    ).scalar() or 0
    premio = db.query(func.sum(Policy.premio_mensal)).filter(
        Policy.status == "Ativa"
    ).scalar() or 0
    devido = db.query(func.sum(Delinquency.valor)).scalar() or 0

    return {
        "apolices_total": sum(por_status.values()),
        "apolices_ativas": por_status.get("Ativa", 0),
        "apolices_a_renovar": por_status.get("A renovar", 0),
        "apolices_vencidas": por_status.get("Vencida", 0),
        "apolices_canceladas": por_status.get("Cancelada", 0),
        "capital_segurado": round(capital, 2),
        "premio_mensal": round(premio, 2),
        "vidas_cobertas": _contar_vidas(db),
        "sinistros_abertos": db.query(Claim).count(),
        "propostas_esteira": db.query(Proposal).count(),
        "inadimplentes": db.query(Delinquency).count(),
        "valor_inadimplencia": round(devido, 2),
        "pendencias_abertas": db.query(Pendency).filter(
            Pendency.resolvida.is_(False)
        ).count(),
    }


def competencia_de_hoje() -> str:
    """O mes corrente no formato MM/AAAA."""
    return tempo.hoje().strftime("%m/%Y")


def fotografar(db, competencia: str | None = None, refazer: bool = False):
    """
    Tira a foto da carteira e guarda.

    Args:
        competencia: o mes a registrar. Vazio = o mes corrente.
        refazer: se True, atualiza a foto do mes caso ela ja exista.
                 Se False (o padrao), nao mexe numa foto ja tirada.

    Devolve (foto, criou_agora).

    POR QUE O PADRAO E NAO REFAZER
    Uma vez tirada, a foto de um mes deve ficar como esta. Se ela fosse
    atualizada a cada vez que o sistema liga, no fim do mes ela mostraria
    o ultimo dia, e nao o mes — e o historico perderia o sentido.
    """
    competencia = competencia or competencia_de_hoje()

    existente = db.query(CarteiraSnapshot).filter(
        CarteiraSnapshot.competencia == competencia
    ).first()

    if existente and not refazer:
        return existente, False

    numeros = _medir(db)

    if existente:
        for chave, valor in numeros.items():
            setattr(existente, chave, valor)
        existente.data_foto = tempo.agora()
        db.commit()
        return existente, False

    nova = CarteiraSnapshot(competencia=competencia, **numeros)
    db.add(nova)
    db.commit()
    return nova, True


def garantir_foto_do_mes(db) -> bool:
    """
    Tira a foto do mes se ela ainda nao existir.

    Chamada quando o sistema liga. Assim ninguem precisa lembrar de
    rodar nada, e nenhum mes se perde por esquecimento.

    Devolve True se tirou uma foto nova.
    """
    _, criou = fotografar(db)
    return criou


def historico_ordenado(db, quantos: int = 12) -> list[CarteiraSnapshot]:
    """
    As fotos em ordem de tempo, da mais antiga para a mais recente.

    Ordenamos por ANO-MES e nao pelo texto: ordenar "07/2026" e "12/2025"
    alfabeticamente colocaria julho antes de dezembro, o que esta errado.
    """
    todas = db.query(CarteiraSnapshot).all()
    todas.sort(key=lambda f: (f.competencia[3:], f.competencia[:2]))
    return todas[-quantos:]


def montar_grafico(db, quantos: int = 6) -> list[dict]:
    """
    Prepara as barras do grafico de capital por mes.

    A altura de cada barra e a porcentagem em relacao ao maior mes, para
    a barra mais alta ocupar todo o espaco disponivel.
    """
    fotos = historico_ordenado(db, quantos)
    if not fotos:
        return []

    maior = max(f.capital_segurado for f in fotos) or 1

    return [
        {
            "rotulo": f.mes_curto(),
            "competencia": f.competencia,
            "capital": f.capital_segurado,
            "ativas": f.apolices_ativas,
            "altura": max(4, round(f.capital_segurado * 100 / maior)),
        }
        for f in fotos
    ]
