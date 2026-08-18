"""
api.py
------
A API da Central de Seguros.

O QUE E UMA API, EM UMA FRASE
-----------------------------
E uma porta de entrada para OUTROS PROGRAMAS. Enquanto as telas HTML
servem para pessoas, a API serve para sistemas: a corretora, a ICATU ou
o Trust Prev poderiam buscar e enviar dados sem ninguem digitar nada.

O QUE ESTA PRONTO E O QUE NAO ESTA
----------------------------------
PRONTO: a metade que depende so de nos — a Central publica os seus dados
e aceita receber movimentacao de fora.

NAO PRONTO: conectar NA ICATU, NA corretora ou NO Trust Prev. Isso nao
depende de programacao: depende de esses sistemas terem uma API, de
alguem autorizar credenciais e da homologacao de seguranca. Enquanto
isso nao existir, nao ha o que programar deste lado.

COMO SE AUTENTICA
-----------------
Todo pedido precisa mandar o cabecalho:

    X-API-Key: <a chave que esta no seu arquivo .env>

Sem a chave certa, a resposta e 401 (nao autorizado).

COMO TESTAR
-----------
Com o servidor ligado, abra no navegador:

    http://127.0.0.1:8000/docs

O FastAPI monta sozinho uma pagina onde da para experimentar cada
endereco, sem instalar nada.
"""

from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.models import Claim, Commission, Delinquency, Payment, Pendency, Policy, Proposal

# O prefixo /api/v1 fica em todos os enderecos deste arquivo.
# O "v1" e a versao: se um dia mudarmos o formato das respostas, criamos
# um /api/v2 e quem ja usava o v1 continua funcionando.
router = APIRouter(prefix="/api/v1", tags=["API de integração"])


# ===============================================================
# AUTENTICACAO DA API
# ===============================================================
def conferir_chave(x_api_key: str = Header(default="")) -> None:
    """
    Confere o cabecalho X-API-Key de cada pedido.

    O nome do parametro (x_api_key) vira o nome do cabecalho (X-API-Key):
    o FastAPI troca o "_" por "-" sozinho.
    """
    if not config.API_KEY:
        raise HTTPException(
            status_code=503,
            detail=(
                "A API está desligada: nenhuma API_KEY foi configurada. "
                "Defina API_KEY no arquivo .env (ou nas variáveis do servidor)."
            ),
        )

    if x_api_key != config.API_KEY:
        raise HTTPException(status_code=401, detail="Chave de API inválida ou ausente.")


# Todo endereco deste arquivo passa por conferir_chave antes de responder.
protegido = [Depends(conferir_chave)]


# ===============================================================
# FORMATOS DE DADOS (o que entra e o que sai)
# ===============================================================
# Estas classes descrevem o formato do JSON. O FastAPI usa elas para
# validar o que chega e para montar a documentacao automatica.


class ApoliceSaida(BaseModel):
    numero_apolice: str
    participante: str
    cpf: str | None = None
    cobertura: str
    capital_total: float
    premio_mensal: float
    data_inicio: date
    data_vencimento: date
    status: str

    # Permite construir o objeto direto a partir da linha do banco.
    model_config = {"from_attributes": True}


class MovimentacaoEntrada(BaseModel):
    """Uma linha de movimentacao enviada por outro sistema."""

    matricula: str = Field(..., max_length=20, description="Matrícula do segurado")
    segurado: str = Field(..., max_length=120)
    cpf: str | None = Field(default=None, max_length=14)
    capital_morte: float = Field(default=0, ge=0)
    capital_invalidez: float = Field(default=0, ge=0)
    premio: float = Field(..., gt=0, description="Prêmio mensal, maior que zero")
    codigo_modulo: str | None = Field(default=None, max_length=10)
    codigo_sub: str | None = Field(default=None, max_length=10)
    competencia: str = Field(..., pattern=r"^\d{2}/\d{4}$", description="No formato MM/AAAA")
    status: str = Field(default="A pagar")


class LoteMovimentacao(BaseModel):
    """O pacote completo que a corretora envia."""

    competencia: str = Field(..., pattern=r"^\d{2}/\d{4}$")
    registros: list[MovimentacaoEntrada] = Field(..., min_length=1, max_length=5000)


# ===============================================================
# ENDERECOS QUE ENTREGAM DADOS (GET)
# ===============================================================
@router.get("/status", dependencies=protegido, summary="A Central está no ar?")
def status(db: Session = Depends(get_db)):
    """Resumo rápido do sistema. Serve para monitoramento."""
    return {
        "situacao": "no ar",
        "data": date.today().isoformat(),
        "totais": {
            "apolices": db.query(Policy).count(),
            "apolices_ativas": db.query(Policy).filter(Policy.status == "Ativa").count(),
            "movimentacoes": db.query(Payment).count(),
            "sinistros": db.query(Claim).count(),
            "propostas": db.query(Proposal).count(),
            "inadimplentes": db.query(Delinquency).count(),
            "pendencias": db.query(Pendency).count(),
        },
    }


@router.get("/apolices", dependencies=protegido, response_model=list[ApoliceSaida],
            summary="Lista as apólices da carteira")
def listar_apolices(
    status: str | None = Query(default=None, description="Ativa, A renovar, Vencida ou Cancelada"),
    vencendo_em: int | None = Query(default=None, ge=0, le=365,
                                    description="Só as que vencem em até N dias"),
    limite: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    consulta = db.query(Policy)

    if status:
        consulta = consulta.filter(Policy.status == status)

    if vencendo_em is not None:
        limite_data = date.today() + __import__("datetime").timedelta(days=vencendo_em)
        consulta = consulta.filter(
            Policy.data_vencimento >= date.today(),
            Policy.data_vencimento <= limite_data,
        )

    return consulta.order_by(Policy.data_vencimento).limit(limite).all()


@router.get("/apolices/{numero}", dependencies=protegido, response_model=ApoliceSaida,
            summary="Busca uma apólice pelo número")
def buscar_apolice(numero: str, db: Session = Depends(get_db)):
    apolice = db.query(Policy).filter(Policy.numero_apolice == numero).first()
    if apolice is None:
        raise HTTPException(status_code=404, detail=f"Apólice {numero} não encontrada.")
    return apolice


@router.get("/movimentacao", dependencies=protegido,
            summary="Movimentação de uma competência")
def listar_movimentacao(
    competencia: str | None = Query(default=None, pattern=r"^\d{2}/\d{4}$"),
    db: Session = Depends(get_db),
):
    consulta = db.query(Payment)
    if competencia:
        consulta = consulta.filter(Payment.competencia == competencia)

    registros = consulta.order_by(Payment.matricula).all()

    return {
        "competencia": competencia or "todas",
        "quantidade": len(registros),
        "premio_total": round(sum(r.premio for r in registros), 2),
        "registros": [
            {
                "matricula": r.matricula,
                "segurado": r.segurado,
                "cpf": r.cpf,
                "capital_morte": r.capital_morte,
                "capital_invalidez": r.capital_invalidez,
                "premio": r.premio,
                "competencia": r.competencia,
                "status": r.status,
            }
            for r in registros
        ],
    }


@router.get("/sinistros", dependencies=protegido, summary="Sinistros em andamento")
def listar_sinistros(db: Session = Depends(get_db)):
    registros = db.query(Claim).order_by(Claim.data_abertura).all()
    return {
        "quantidade": len(registros),
        "registros": [
            {
                "protocolo": c.protocolo,
                "participante": c.participante,
                "tipo": c.tipo,
                "data_abertura": c.data_abertura.isoformat(),
                "dias_em_aberto": c.dias_em_aberto(),
                "documentacao": c.documentacao,
                "documentacao_ok": c.documentacao_ok,
                "status": c.status,
            }
            for c in registros
        ],
    }


@router.get("/comissoes", dependencies=protegido, summary="Comissões por competência")
def listar_comissoes(
    competencia: str | None = Query(default=None, pattern=r"^\d{2}/\d{4}$"),
    db: Session = Depends(get_db),
):
    consulta = db.query(Commission)
    if competencia:
        consulta = consulta.filter(Commission.competencia == competencia)

    registros = consulta.order_by(Commission.competencia.desc()).all()
    return {
        "quantidade": len(registros),
        "registros": [
            {
                "competencia": c.competencia,
                "papel": c.papel,
                "quem": c.quem,
                "premio_total": c.premio_total,
                "percentual": c.percentual,
                "valor": c.valor,
            }
            for c in registros
        ],
    }


@router.get("/inadimplencia", dependencies=protegido, summary="Participantes em atraso")
def listar_inadimplencia(db: Session = Depends(get_db)):
    registros = db.query(Delinquency).order_by(Delinquency.dias_atraso.desc()).all()
    return {
        "quantidade": len(registros),
        "valor_total": round(sum(d.valor for d in registros), 2),
        "registros": [
            {
                "participante": d.participante,
                "apolice": d.numero_apolice,
                "cobertura": d.cobertura,
                "valor": d.valor,
                "dias_atraso": d.dias_atraso,
                "faixa": d.faixa(),
                "cobranca_enviada": d.cobranca_enviada,
            }
            for d in registros
        ],
    }


@router.get("/indicadores", dependencies=protegido,
            summary="Números consolidados da carteira")
def indicadores(db: Session = Depends(get_db)):
    """Os mesmos números do dashboard, para outro sistema consumir."""
    capital = db.query(func.sum(Policy.capital_total)).filter(
        Policy.status == "Ativa"
    ).scalar() or 0
    premio = db.query(func.sum(Policy.premio_mensal)).filter(
        Policy.status == "Ativa"
    ).scalar() or 0

    return {
        "data": date.today().isoformat(),
        "apolices_ativas": db.query(Policy).filter(Policy.status == "Ativa").count(),
        "apolices_a_renovar": db.query(Policy).filter(Policy.status == "A renovar").count(),
        "capital_segurado": round(capital, 2),
        "premio_mensal": round(premio, 2),
        "sinistros_em_andamento": db.query(Claim).count(),
        "inadimplentes": db.query(Delinquency).count(),
        "pendencias_abertas": db.query(Pendency).filter(
            Pendency.resolvida.is_(False)
        ).count(),
    }


# ===============================================================
# ENDERECO QUE RECEBE DADOS (POST)
# ===============================================================
@router.post("/movimentacao", dependencies=protegido, status_code=201,
             summary="Recebe a movimentação de outro sistema")
def receber_movimentacao(lote: LoteMovimentacao, db: Session = Depends(get_db)):
    """
    Substitui a movimentação de uma competência inteira.

    É o mesmo efeito de enviar a planilha pela tela, só que sem arquivo:
    a corretora manda os dados direto em JSON.

    Tudo que existia naquela competência é apagado e entra o conteúdo
    novo. Reenviar o mesmo lote corrigido não duplica nada.
    """
    # Todas as linhas precisam ser da competencia declarada no cabecalho
    # do lote. Isso evita apagar uma competencia sem querer.
    divergentes = [r.matricula for r in lote.registros if r.competencia != lote.competencia]
    if divergentes:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Estas matrículas têm competência diferente de {lote.competencia}: "
                f"{', '.join(divergentes[:10])}"
            ),
        )

    apagados = db.query(Payment).filter(
        Payment.competencia == lote.competencia
    ).delete()

    db.add_all([Payment(**r.model_dump()) for r in lote.registros])
    db.commit()

    return {
        "situacao": "recebido",
        "competencia": lote.competencia,
        "registros_gravados": len(lote.registros),
        "registros_substituidos": apagados,
        "premio_total": round(sum(r.premio for r in lote.registros), 2),
    }
