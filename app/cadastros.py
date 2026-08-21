"""
cadastros.py
------------
As telas de cadastrar, editar e excluir.

POR QUE ESTE ARQUIVO EXISTE ASSIM
---------------------------------
Sao 5 coisas cadastraveis (apolices, sinistros, propostas, pendencias e
inadimplencia) e cada uma precisa de 3 acoes: criar, editar e excluir.
Escrevendo uma tela para cada, seriam 5 formularios quase identicos e 25
funcoes parecidas — e qualquer melhoria teria que ser repetida 5 vezes.

Em vez disso, DESCREVEMOS os campos de cada coisa aqui, e um unico
formulario (templates/cadastro.html) sabe desenhar qualquer um deles.

PARA ACRESCENTAR UM CAMPO
-------------------------
Ache o cadastro na lista CADASTROS, no fim do arquivo, e acrescente um
Campo(...). Pronto: ele aparece na tela, e a validacao e a gravacao
passam a considerar ele. Nenhum HTML precisa ser tocado.

PARA CRIAR UM CADASTRO NOVO
---------------------------
Acrescente uma entrada em CADASTROS com o modelo e a lista de campos.
As rotas em app/main.py funcionam para qualquer entrada da lista.
"""

from dataclasses import dataclass, field
from datetime import date, datetime

from app.models import Claim, Delinquency, Pendency, Policy, Proposal


# ===============================================================
# A DESCRICAO DE UM CAMPO
# ===============================================================
@dataclass
class Campo:
    """
    Descreve UM campo do formulario.

    nome        o nome da coluna no banco (ex.: "participante")
    rotulo      o texto que aparece na tela (ex.: "Participante")
    tipo        como desenhar e como validar. Ver TIPOS, abaixo.
    obrigatorio se True, nao deixa gravar vazio
    opcoes      para tipo="selecao": a lista de valores possiveis
    ajuda       um texto pequeno abaixo do campo
    tamanho     limite de caracteres, para tipo="texto"
    minimo      valor minimo, para numero e dinheiro
    largura     "inteira" ocupa a linha toda; "metade" divide com o vizinho
    calculado   se True, o campo NAO aparece na tela: e preenchido pelo
                sistema (ex.: capital_morte, que vem da cobertura)
    """

    nome: str
    rotulo: str
    tipo: str = "texto"
    obrigatorio: bool = False
    opcoes: list[str] = field(default_factory=list)
    ajuda: str = ""
    tamanho: int | None = None
    minimo: float | None = None
    largura: str = "metade"
    calculado: bool = False


# Os tipos que o formulario sabe desenhar:
#
#   texto     uma linha de texto
#   textao    varias linhas
#   numero    numero inteiro
#   dinheiro  valor em reais (aceita 1.234,56 e 1234.56)
#   data      dia/mes/ano
#   selecao   lista de opcoes
#   sim_nao   caixinha de marcar


# ===============================================================
# CONVERSAO E VALIDACAO
# ===============================================================
def _texto_para_data(texto: str) -> date | None:
    """
    Aceita 25/12/2026 e 2026-12-25.

    O navegador manda no formato 2026-12-25 quando usamos type="date",
    mas quem digitar a mao provavelmente usa o formato brasileiro.
    Aceitamos os dois para nao irritar ninguem.
    """
    texto = (texto or "").strip()
    if not texto:
        return None
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def _texto_para_dinheiro(texto: str) -> float | None:
    """
    Aceita "1.234,56", "1234.56", "R$ 1.234,56" e "1234".

    O jeito brasileiro (ponto no milhar, virgula no decimal) e o jeito
    do computador (ponto no decimal) sao diferentes, e as pessoas digitam
    dos dois modos.
    """
    texto = (texto or "").replace("R$", "").strip()
    if not texto:
        return None
    if "," in texto:
        # formato brasileiro: tira os pontos de milhar, virgula vira ponto
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def validar(campos: list[Campo], enviado: dict) -> tuple[dict, list[str]]:
    """
    Confere o que veio do formulario.

    Devolve DOIS valores:
      - os valores ja convertidos (data virou data, dinheiro virou numero)
      - a lista de erros, em portugues, para mostrar na tela

    Se houver qualquer erro, quem chama NAO grava nada. E de proposito:
    e melhor a pessoa corrigir tudo de uma vez do que gravar meio
    registro.
    """
    valores: dict = {}
    erros: list[str] = []

    for campo in campos:
        if campo.calculado:
            continue  # o sistema preenche, nao vem da tela

        cru = (enviado.get(campo.nome) or "").strip()

        # --- vazio ---
        if not cru:
            if campo.obrigatorio:
                erros.append(f"{campo.rotulo}: precisa ser preenchido.")
            else:
                valores[campo.nome] = False if campo.tipo == "sim_nao" else None
            continue

        # --- por tipo ---
        if campo.tipo == "data":
            convertido = _texto_para_data(cru)
            if convertido is None:
                erros.append(f"{campo.rotulo}: data invalida. Use dia/mes/ano.")
                continue
            valores[campo.nome] = convertido

        elif campo.tipo == "dinheiro":
            convertido = _texto_para_dinheiro(cru)
            if convertido is None:
                erros.append(f"{campo.rotulo}: valor invalido. Exemplo: 1.234,56")
                continue
            if campo.minimo is not None and convertido < campo.minimo:
                erros.append(f"{campo.rotulo}: nao pode ser menor que {campo.minimo:g}.")
                continue
            valores[campo.nome] = round(convertido, 2)

        elif campo.tipo == "numero":
            try:
                convertido = int(cru)
            except ValueError:
                erros.append(f"{campo.rotulo}: precisa ser um numero inteiro.")
                continue
            if campo.minimo is not None and convertido < campo.minimo:
                erros.append(f"{campo.rotulo}: nao pode ser menor que {campo.minimo:g}.")
                continue
            valores[campo.nome] = convertido

        elif campo.tipo == "selecao":
            if campo.opcoes and cru not in campo.opcoes:
                erros.append(f"{campo.rotulo}: opcao invalida.")
                continue
            valores[campo.nome] = cru

        elif campo.tipo == "sim_nao":
            valores[campo.nome] = cru in ("sim", "on", "true", "1")

        else:  # texto e textao
            if campo.tamanho and len(cru) > campo.tamanho:
                erros.append(
                    f"{campo.rotulo}: passou de {campo.tamanho} caracteres."
                )
                continue
            valores[campo.nome] = cru

    # As caixinhas de marcar nao vem no envio quando estao desmarcadas,
    # entao precisam ser tratadas por fora do laco acima.
    for campo in campos:
        if campo.tipo == "sim_nao" and campo.nome not in valores:
            valores[campo.nome] = campo.nome in enviado

    return valores, erros


# ===============================================================
# CALCULOS AUTOMATICOS
# ===============================================================
def _calcular_apolice(valores: dict) -> dict:
    """
    Preenche o que da para deduzir de uma apolice.

    O capital de morte e de invalidez saem da cobertura escolhida — nao
    faz sentido pedir tres valores quando dois deles seguem uma regra
    fixa. A regra e a mesma da planilha do projeto: quem tem as duas
    coberturas tem o MESMO valor nas duas, nao metade para cada.
    """
    cobertura = valores.get("cobertura") or ""
    capital = valores.get("capital_total") or 0.0

    if cobertura == "Morte":
        valores["capital_morte"] = capital
        valores["capital_invalidez"] = 0.0
    elif cobertura == "Invalidez":
        valores["capital_morte"] = 0.0
        valores["capital_invalidez"] = capital
    else:  # Morte + Invalidez
        valores["capital_morte"] = capital
        valores["capital_invalidez"] = capital

    return valores


def _validar_apolice(valores: dict) -> list[str]:
    """Confere as regras que dependem de mais de um campo."""
    erros = []

    inicio = valores.get("data_inicio")
    vencimento = valores.get("data_vencimento")
    if inicio and vencimento and vencimento <= inicio:
        erros.append(
            "Vencimento: precisa ser depois do inicio da vigencia."
        )

    return erros


def _validar_sinistro(valores: dict) -> list[str]:
    erros = []
    abertura = valores.get("data_abertura")
    if abertura and abertura > date.today():
        erros.append("Aberto em: a data nao pode estar no futuro.")
    return erros


# ===============================================================
# OS 5 CADASTROS
# ===============================================================
STATUS_APOLICE = ["Ativa", "A renovar", "Vencida", "Cancelada"]
COBERTURAS = ["Morte", "Invalidez", "Morte + Invalidez"]

CADASTROS: dict[str, dict] = {

    # -----------------------------------------------------------
    "apolices": {
        "modelo": Policy,
        "titulo": "Apólice",
        "plural": "Apólices",
        "voltar": "/seguros",
        "permissao": "seguros",
        "identificador": "numero_apolice",
        "calcular": _calcular_apolice,
        "validar_extra": _validar_apolice,
        "campos": [
            Campo("numero_apolice", "Número da apólice", obrigatorio=True,
                  tamanho=20, ajuda="Ex.: AP-2041"),
            Campo("participante", "Participante", obrigatorio=True, tamanho=120),
            Campo("cpf", "CPF", tamanho=14, ajuda="Formato 000.000.000-00"),
            Campo("matricula", "Matrícula", tamanho=20),
            Campo("data_nascimento", "Data de nascimento", tipo="data"),
            Campo("cobertura", "Cobertura", tipo="selecao", opcoes=COBERTURAS,
                  obrigatorio=True,
                  ajuda="Define como o capital é dividido entre morte e invalidez"),
            Campo("capital_total", "Capital segurado", tipo="dinheiro",
                  obrigatorio=True, minimo=0.01, ajuda="Ex.: 250.000,00"),
            Campo("premio_mensal", "Prêmio mensal", tipo="dinheiro",
                  obrigatorio=True, minimo=0.01, ajuda="Ex.: 101,25"),
            Campo("data_inicio", "Início da vigência", tipo="data",
                  obrigatorio=True),
            Campo("data_vencimento", "Vencimento", tipo="data", obrigatorio=True),
            Campo("status", "Situação", tipo="selecao", opcoes=STATUS_APOLICE,
                  obrigatorio=True),
            Campo("codigo_modulo", "Código do módulo", tamanho=10,
                  ajuda="101 = risco morte/invalidez"),
            Campo("codigo_sub", "Código sub", tamanho=10, ajuda="01, 02 ou 03"),
            Campo("competencia", "Competência", tamanho=7, ajuda="Formato MM/AAAA"),
            # Estes tres o sistema preenche sozinho:
            Campo("capital_morte", "", calculado=True),
            Campo("capital_invalidez", "", calculado=True),
            Campo("origem", "", calculado=True),
        ],
    },

    # -----------------------------------------------------------
    "sinistros": {
        "modelo": Claim,
        "titulo": "Sinistro",
        "plural": "Sinistros",
        "voltar": "/sinistros",
        "permissao": "sinistros",
        "identificador": "protocolo",
        "validar_extra": _validar_sinistro,
        "campos": [
            Campo("protocolo", "Protocolo", obrigatorio=True, tamanho=20,
                  ajuda="Ex.: SIN-0451"),
            Campo("participante", "Participante", obrigatorio=True, tamanho=120),
            Campo("tipo", "Tipo", tipo="selecao", opcoes=["Morte", "Invalidez"],
                  obrigatorio=True),
            Campo("data_abertura", "Aberto em", tipo="data", obrigatorio=True),
            Campo("documentacao", "Situação da documentação", obrigatorio=True,
                  tamanho=60,
                  ajuda="Ex.: Completa, Falta certidão, Falta laudo"),
            Campo("documentacao_ok", "A documentação está completa",
                  tipo="sim_nao", largura="inteira",
                  ajuda="Desmarcado deixa a linha em vermelho na tela"),
            Campo("status", "Situação do processo", tipo="selecao",
                  opcoes=["Em análise", "Aguardando doc.", "Em liberação",
                          "Concluído"],
                  obrigatorio=True),
        ],
    },

    # -----------------------------------------------------------
    "propostas": {
        "modelo": Proposal,
        "titulo": "Proposta",
        "plural": "Propostas",
        "voltar": "/esteira",
        "permissao": "esteira",
        "identificador": "numero",
        "campos": [
            Campo("numero", "Número da proposta", obrigatorio=True, tamanho=20,
                  ajuda="Ex.: PROP-3012"),
            Campo("participante", "Participante", obrigatorio=True, tamanho=120),
            Campo("cobertura", "Cobertura", tipo="selecao",
                  opcoes=[""] + COBERTURAS,
                  ajuda="Pode ficar em branco enquanto a proposta é analisada"),
            Campo("capital", "Capital pretendido", tipo="dinheiro", minimo=0),
            Campo("etapa", "Etapa na esteira", tipo="selecao",
                  opcoes=["recebida", "analise", "aceita", "pendente"],
                  obrigatorio=True,
                  ajuda="Define em qual coluna do quadro ela aparece"),
            Campo("observacao", "Observação", tamanho=120, largura="inteira",
                  ajuda="Ex.: Falta DPS assinada"),
            Campo("recusada", "Proposta recusada", tipo="sim_nao",
                  largura="inteira",
                  ajuda="Marcado deixa o cartão em vermelho no quadro"),
        ],
    },

    # -----------------------------------------------------------
    "pendencias": {
        "modelo": Pendency,
        "titulo": "Pendência",
        "plural": "Pendências",
        "voltar": "/pendencias",
        "permissao": "pendencias",
        "identificador": "titulo",
        "campos": [
            Campo("prioridade", "Prioridade", tipo="selecao",
                  opcoes=["Alta", "Média", "Baixa"], obrigatorio=True),
            Campo("titulo", "Pendência", obrigatorio=True, tamanho=120,
                  ajuda="Ex.: Certidão de óbito faltante"),
            Campo("referente", "Referente a", tamanho=120,
                  ajuda="Ex.: SIN-0448 · H. Costa"),
            Campo("responsavel", "Responsável", tamanho=60,
                  ajuda="Ex.: Corretora, Seguradora, Beneficiário"),
            Campo("prazo", "Prazo", tipo="data"),
            Campo("documento", "Documento", tamanho=60,
                  ajuda="Ex.: Apólice, Certidão faltante"),
            Campo("documento_ok", "O documento está em ordem", tipo="sim_nao",
                  largura="inteira",
                  ajuda="Desmarcado mostra o documento em vermelho"),
            Campo("resolvida", "Já resolvida", tipo="sim_nao",
                  largura="inteira"),
        ],
    },

    # -----------------------------------------------------------
    "inadimplencia": {
        "modelo": Delinquency,
        "titulo": "Inadimplente",
        "plural": "Inadimplência",
        "voltar": "/inadimplencia",
        "permissao": "inadimplencia",
        "identificador": "participante",
        "campos": [
            Campo("participante", "Participante", obrigatorio=True, tamanho=120),
            Campo("numero_apolice", "Apólice", obrigatorio=True, tamanho=20,
                  ajuda="Ex.: AP-2087"),
            Campo("cobertura", "Cobertura", tipo="selecao", opcoes=COBERTURAS,
                  obrigatorio=True),
            Campo("valor", "Valor em atraso", tipo="dinheiro", obrigatorio=True,
                  minimo=0.01),
            Campo("dias_atraso", "Dias de atraso", tipo="numero",
                  obrigatorio=True, minimo=0,
                  ajuda="A faixa da régua de cobrança é calculada a partir daqui"),
            Campo("cobranca_enviada", "Cobrança já enviada", tipo="sim_nao",
                  largura="inteira"),
        ],
    },
}


def buscar(nome: str) -> dict | None:
    """Acha um cadastro pelo nome. Devolve None se nao existir."""
    return CADASTROS.get(nome)


def campos_visiveis(cadastro: dict) -> list[Campo]:
    """Os campos que aparecem na tela (fora os calculados)."""
    return [c for c in cadastro["campos"] if not c.calculado]
