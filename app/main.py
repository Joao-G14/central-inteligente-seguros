"""
main.py
-------
O coracao da aplicacao. Aqui ficam as ROTAS: cada endereco do site e a
funcao Python que responde por ele.

     GET  /              -> manda para o login ou para o dashboard
     GET  /login         -> mostra a tela de login
     POST /login         -> confere os dados e deixa entrar (ou nao)
     POST /logout        -> sai do sistema
     GET  /dashboard     -> a tela principal
     GET  /seguros       -> a carteira de apolices
     GET  /modulo/{nome} -> pagina "em breve" dos modulos da Fase 4

COMO RODAR (com o venv ativado, na raiz do projeto):
    uvicorn app.main:app --reload

Depois abra no navegador: http://127.0.0.1:8000

O "--reload" faz o servidor reiniciar sozinho toda vez que voce salva
um arquivo. Otimo para desenvolver, mas nao deve ser usado em producao.
"""

from datetime import date, timedelta

import csv
import io

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import assistente, auth
from app.database import PASTA_RAIZ, get_db
from app.menu import MENU, buscar_modulo
from app.models import (
    PERFIS_VALIDOS,
    Agreement,
    Claim,
    Commission,
    Delinquency,
    Invoice,
    LoginHistory,
    Payment,
    Pendency,
    Policy,
    Proposal,
    User,
)

app = FastAPI(title="Central Inteligente de Seguros")

# Diz ao FastAPI onde estao o CSS/JS e as paginas HTML.
app.mount("/static", StaticFiles(directory=PASTA_RAIZ / "static"), name="static")
templates = Jinja2Templates(directory=PASTA_RAIZ / "templates")

# Mensagem unica para qualquer falha de login. Nao dizemos QUAL dos tres
# campos errou, para nao entregar a um invasor que um e-mail existe.
ERRO_LOGIN = "E-mail, senha ou tipo de acesso incorretos."


# ===============================================================
# AJUDANTES
# ===============================================================
def montar_menu(usuario: User) -> list[dict]:
    """
    Monta o menu lateral ja marcando o que este perfil pode acessar.

    Devolve uma copia da lista MENU com um campo novo, "permitido".
    O template base.html usa esse campo para decidir entre link normal
    e item apagado com cadeado.
    """
    itens = []
    for item in MENU:
        copia = dict(item)
        copia["permitido"] = auth.pode_acessar(usuario.perfil, item["chave"])
        itens.append(copia)
    return itens


def pegar_ip(request: Request) -> str | None:
    """Descobre o endereco de quem fez o pedido (para o login_history)."""
    return request.client.host if request.client else None


def exigir_login(request: Request, db: Session = Depends(get_db)):
    """
    Usada em toda pagina de dentro do sistema.

    Se houver alguem logado, devolve o usuario.
    Se nao houver, devolve None — e a rota manda a pessoa para o /login.
    """
    return auth.ler_usuario_do_cookie(db, request)


def formatar_reais(valor: float, casas: int = 0) -> str:
    """
    Transforma 10910000.0 em 'R$ 10.910.000'.

    O Python formata numeros no padrao americano (1,234.56). As trocas
    abaixo invertem para o padrao brasileiro (1.234,56).
    """
    texto = f"{valor:,.{casas}f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_compacto(valor: float) -> str:
    """Encurta valores grandes: 10910000 vira 'R$ 10,9 M'."""
    if valor >= 1_000_000:
        return f"R$ {valor / 1_000_000:.1f} M".replace(".", ",")
    if valor >= 1_000:
        return f"R$ {valor / 1_000:.0f} mil"
    return formatar_reais(valor, 2)


# Deixa as duas funcoes acima disponiveis DENTRO dos templates HTML.
# E por isso que nos arquivos .html podemos escrever {{ reais(1000) }}.
templates.env.globals["reais"] = formatar_reais
templates.env.globals["capital_curto"] = formatar_compacto


def contexto(usuario: User, modulo: str, **extras) -> dict:
    """
    Monta os dados que TODA pagina de dentro do sistema precisa
    (usuario logado, menu e qual item do menu esta ativo), mais o que
    for especifico daquela pagina.

    Evita repetir as mesmas 3 linhas em cada rota.
    """
    dados = {
        "usuario": usuario,
        "menu": montar_menu(usuario),
        "modulo_atual": modulo,
        "hoje": date.today(),
    }
    dados.update(extras)
    return dados


def barrar(usuario: User | None, modulo: str) -> RedirectResponse | None:
    """
    Confere se a pessoa pode abrir esta pagina.

    Devolve um redirecionamento se NAO puder, ou None se puder.
    Toda rota de dentro do sistema comeca chamando esta funcao.

    Sao duas travas:
      1. nao esta logado          -> vai para o login
      2. perfil sem permissao     -> volta para o dashboard
    """
    if usuario is None:
        return RedirectResponse("/login", status_code=303)
    if not auth.pode_acessar(usuario.perfil, modulo):
        return RedirectResponse("/dashboard", status_code=303)
    return None


def gerar_csv(nome_arquivo: str, cabecalho: list[str], linhas: list[list]) -> Response:
    """
    Monta um arquivo .csv para download, que abre direto no Excel.

    Dois detalhes importantes para o Excel brasileiro:
      - separador ponto e virgula (;) em vez de virgula
      - utf-8-sig, que inclui uma marca no inicio do arquivo para o
        Excel entender os acentos (sem isso, "Apólice" vira "ApÃ³lice")
    """
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";")
    escritor.writerow(cabecalho)
    escritor.writerows(linhas)

    return Response(
        content=buffer.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


# ===============================================================
# ROTAS DE LOGIN
# ===============================================================
@app.get("/")
def raiz(request: Request, db: Session = Depends(get_db)):
    """A pagina inicial so encaminha para o lugar certo."""
    usuario = auth.ler_usuario_do_cookie(db, request)
    destino = "/dashboard" if usuario else "/login"
    return RedirectResponse(destino, status_code=303)


@app.get("/login", response_class=HTMLResponse)
def mostrar_login(request: Request, db: Session = Depends(get_db)):
    """Mostra a tela de login (quem ja esta logado vai direto ao dashboard)."""
    if auth.ler_usuario_do_cookie(db, request):
        return RedirectResponse("/dashboard", status_code=303)

    return templates.TemplateResponse(request, "login.html", {})


@app.post("/login", response_class=HTMLResponse)
def processar_login(
    request: Request,
    # Form(...) significa: este valor vem de um campo do formulario HTML.
    # O nome tem que ser igual ao name="..." do input no login.html.
    perfil: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Recebe o formulario e faz o login, na ordem pedida no projeto:

      1. validar e-mail
      2. validar senha
      3. validar perfil
      4. registrar o login
      5. criar a sessao
      6. redirecionar para o dashboard
    """
    ip = pegar_ip(request)

    # Antes de tudo: o perfil enviado e um dos tres validos?
    # Protege contra alguem enviar um perfil inventado por fora da tela.
    if perfil not in PERFIS_VALIDOS:
        auth.registrar_login(db, email, perfil, False, "perfil invalido", ip=ip)
        return templates.TemplateResponse(
            request,
            "login.html",
            {"erro": ERRO_LOGIN, "email_digitado": email},
            status_code=400,
        )

    # Passos 1, 2 e 3 acontecem dentro de autenticar().
    usuario, motivo = auth.autenticar(db, email, senha, perfil)

    # Passo 4: registrar SEMPRE, tenha dado certo ou nao.
    auth.registrar_login(
        db,
        email=email,
        perfil=perfil,
        sucesso=usuario is not None,
        motivo=motivo,
        usuario=usuario,
        ip=ip,
    )

    if usuario is None:
        # Deu errado: volta para a tela com a mensagem generica.
        # O motivo detalhado fica so no banco, para auditoria.
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "erro": ERRO_LOGIN,
                "email_digitado": email,
                "perfil_marcado": perfil,
            },
            status_code=401,
        )

    # Passos 5 e 6: cria o cracha e manda para o dashboard.
    resposta = RedirectResponse("/dashboard", status_code=303)
    auth.criar_cookie_sessao(resposta, usuario)
    return resposta


@app.post("/logout")
def logout():
    """Sai do sistema: apaga o cracha e volta para o login."""
    resposta = RedirectResponse("/login", status_code=303)
    auth.apagar_cookie_sessao(resposta)
    return resposta


# ===============================================================
# ROTAS DE DENTRO DO SISTEMA
# ===============================================================
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """A tela principal, com os numeros calculados do banco."""
    if usuario is None:
        return RedirectResponse("/login", status_code=303)

    hoje = date.today()

    # --- os 4 numeros do topo ---
    total = db.query(Policy).count()
    ativas = db.query(Policy).filter(Policy.status == "Ativa").count()
    a_renovar = db.query(Policy).filter(Policy.status == "A renovar").count()

    # func.sum soma uma coluna inteira direto no banco (mais rapido do que
    # trazer as 50 linhas para o Python e somar aqui).
    # O "or 0" cobre o caso de nao existir nenhuma apolice ativa: sem ele,
    # a soma viria como None e a conta quebraria.
    capital = db.query(func.sum(Policy.capital_total)).filter(
        Policy.status == "Ativa"
    ).scalar() or 0
    premio = db.query(func.sum(Policy.premio_mensal)).filter(
        Policy.status == "Ativa"
    ).scalar() or 0

    kpis = {
        "total": total,
        "ativas": ativas,
        "a_renovar": a_renovar,
        "capital": formatar_compacto(capital),
        "premio": formatar_reais(premio, 2),
    }

    # --- proximas renovacoes (as 6 mais proximas) ---
    renovacoes = (
        db.query(Policy)
        .filter(Policy.status == "A renovar")
        .order_by(Policy.data_vencimento)
        .limit(6)
        .all()
    )

    # --- distribuicao por cobertura (o grafico de rosca) ---
    cobertura = montar_grafico_cobertura(db)

    # --- ultimos 8 acessos ao sistema ---
    acessos = (
        db.query(LoginHistory)
        .order_by(LoginHistory.data_hora.desc())
        .limit(8)
        .all()
    )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "usuario": usuario,
            "menu": montar_menu(usuario),
            "modulo_atual": "dashboard",
            "hoje": hoje,
            "kpis": kpis,
            "renovacoes": renovacoes,
            "cobertura": cobertura,
            "acessos": acessos,
        },
    )


def montar_grafico_cobertura(db: Session) -> list[dict]:
    """
    Calcula as fatias do grafico de rosca: quantas apolices tem cada
    tipo de cobertura, em porcentagem.

    O "offset" e onde cada fatia comeca a ser desenhada no circulo.
    Comeca em 25 para a primeira fatia nascer no topo, e cada fatia
    seguinte comeca de onde a anterior parou.
    """
    cores = {
        "Morte": "#1F3B8C",
        "Invalidez": "#3B8FD4",
        "Morte + Invalidez": "#2E75B6",
    }

    contagem = (
        db.query(Policy.cobertura, func.count(Policy.id))
        .group_by(Policy.cobertura)
        .all()
    )

    total = sum(qtd for _, qtd in contagem)
    if total == 0:
        return []

    fatias = []
    offset = 25
    for nome, qtd in contagem:
        pct = round(qtd * 100 / total)
        fatias.append(
            {
                "nome": nome,
                "pct": pct,
                "cor": cores.get(nome, "#6B7691"),
                "offset": offset,
            }
        )
        offset -= pct

    return fatias


@app.get("/seguros", response_class=HTMLResponse)
def seguros(
    request: Request,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """A carteira de apolices completa."""
    if usuario is None:
        return RedirectResponse("/login", status_code=303)

    apolices = db.query(Policy).order_by(Policy.data_vencimento).all()

    return templates.TemplateResponse(
        request,
        "seguros.html",
        {
            "usuario": usuario,
            "menu": montar_menu(usuario),
            "modulo_atual": "seguros",
            "apolices": apolices,
        },
    )


@app.get("/modulo/{chave}", response_class=HTMLResponse)
def modulo_em_breve(
    chave: str,
    request: Request,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """
    Pagina provisoria dos modulos que ainda nao foram convertidos.

    Aqui esta a parte importante da SEGURANCA das permissoes: nao basta
    esconder o item no menu. Se a pessoa digitar o endereco na barra do
    navegador, precisamos barrar de verdade. E o que o segundo "if" faz.
    """
    if usuario is None:
        return RedirectResponse("/login", status_code=303)

    modulo = buscar_modulo(chave)
    if modulo is None:
        return RedirectResponse("/dashboard", status_code=303)

    # A trava de verdade: perfil sem permissao volta para o dashboard.
    if not auth.pode_acessar(usuario.perfil, chave):
        return RedirectResponse("/dashboard", status_code=303)

    return templates.TemplateResponse(
        request,
        "em_breve.html",
        contexto(usuario, chave, modulo=modulo),
    )


# ===============================================================
# MODULO: MOVIMENTACAO & PAGAMENTO
# ===============================================================
@app.get("/movimentacao", response_class=HTMLResponse)
def movimentacao(
    request: Request,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    fora = barrar(usuario, "movimentacao")
    if fora:
        return fora

    pagamentos = db.query(Payment).order_by(Payment.matricula).all()
    competencia = pagamentos[0].competencia if pagamentos else "—"

    totais = {
        "morte": sum(p.capital_morte for p in pagamentos),
        "invalidez": sum(p.capital_invalidez for p in pagamentos),
        "premio": sum(p.premio for p in pagamentos),
    }

    # joinedload nao e necessario aqui porque sao poucos registros;
    # o SQLAlchemy busca o convenio de cada boleto quando o template pede.
    a_emitir = (
        db.query(Invoice)
        .filter(Invoice.status == "A emitir")
        .join(Agreement)
        .order_by(Agreement.nome)
        .all()
    )
    emitidos = (
        db.query(Invoice)
        .filter(Invoice.status != "A emitir")
        .order_by(Invoice.competencia.desc(), Invoice.valor.desc())
        .all()
    )

    return templates.TemplateResponse(
        request,
        "movimentacao.html",
        contexto(
            usuario,
            "movimentacao",
            pagamentos=pagamentos,
            competencia=competencia,
            totais=totais,
            a_emitir=a_emitir,
            emitidos=emitidos,
        ),
    )


@app.post("/movimentacao/emitir/{boleto_id}")
def emitir_boleto(
    boleto_id: int,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """Emite um boleto: muda o status de 'A emitir' para 'Em aberto'."""
    fora = barrar(usuario, "movimentacao")
    if fora:
        return fora

    boleto = db.query(Invoice).filter(Invoice.id == boleto_id).first()
    if boleto and boleto.status == "A emitir":
        boleto.status = "Em aberto"
        # o boleto vence 10 dias depois de emitido
        boleto.data_vencimento = date.today() + timedelta(days=10)
        db.commit()

    return RedirectResponse("/movimentacao", status_code=303)


@app.get("/movimentacao/exportar")
def exportar_movimentacao(
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """Baixa as movimentacoes em .csv (abre no Excel)."""
    fora = barrar(usuario, "movimentacao")
    if fora:
        return fora

    pagamentos = db.query(Payment).order_by(Payment.matricula).all()
    linhas = [
        [
            p.matricula,
            p.segurado,
            p.cpf,
            f"{p.capital_morte:.2f}".replace(".", ","),
            f"{p.capital_invalidez:.2f}".replace(".", ","),
            f"{p.premio:.2f}".replace(".", ","),
            p.codigo_modulo,
            p.codigo_sub,
            p.competencia,
            p.status,
        ]
        for p in pagamentos
    ]
    return gerar_csv(
        "movimentacao.csv",
        ["Matrícula", "Segurado", "CPF", "Capital Morte", "Capital Invalidez",
         "Prêmio", "Módulo", "Sub", "Competência", "Pagamento"],
        linhas,
    )


# ===============================================================
# MODULO: COMISSOES  (a seguradora nao acessa)
# ===============================================================
@app.get("/comissoes", response_class=HTMLResponse)
def comissoes(
    request: Request,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    fora = barrar(usuario, "comissoes")
    if fora:
        return fora

    todas = (
        db.query(Commission)
        .order_by(Commission.competencia.desc(), Commission.percentual)
        .all()
    )

    if not todas:
        return templates.TemplateResponse(
            request,
            "comissoes.html",
            contexto(usuario, "comissoes", competencia="—", premio_total=0,
                     comissoes=[], historico=[], todas=[]),
        )

    # A competencia mais recente e a que aparece nos 3 cartoes de cima.
    competencia = todas[0].competencia
    do_mes = [c for c in todas if c.competencia == competencia]
    premio_total = do_mes[0].premio_total

    historico = montar_historico_comissoes(db)

    return templates.TemplateResponse(
        request,
        "comissoes.html",
        contexto(
            usuario,
            "comissoes",
            competencia=competencia,
            premio_total=premio_total,
            comissoes=do_mes,
            historico=historico,
            todas=todas,
        ),
    )


def montar_historico_comissoes(db: Session) -> list[dict]:
    """
    Monta as barras do grafico: quanto o estipulante recebeu por mes.

    A altura de cada barra e a porcentagem em relacao ao maior mes,
    para a barra mais alta ocupar 100% do espaco.
    """
    registros = (
        db.query(Commission)
        .filter(Commission.papel == "ESTIPULANTE")
        .order_by(Commission.competencia)
        .all()
    )
    if not registros:
        return []

    maior = max(c.valor for c in registros)
    meses = {
        "01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr",
        "05": "Mai", "06": "Jun", "07": "Jul", "08": "Ago",
        "09": "Set", "10": "Out", "11": "Nov", "12": "Dez",
    }

    return [
        {
            "rotulo": meses.get(c.competencia[:2], c.competencia),
            "valor": c.valor,
            "altura": round(c.valor * 100 / maior) if maior else 0,
        }
        for c in registros
    ]


# ===============================================================
# MODULO: INADIMPLENCIA  (a seguradora nao acessa)
# ===============================================================
# Os degraus da regua de cobranca: (limite de dias, nome, acao)
# O ultimo tem limite None, que significa "daqui para cima".
REGUA_COBRANCA = [
    (15, "1 a 15 dias", "Aviso amigável por e-mail"),
    (45, "16 a 45 dias", "Notificação de pendência"),
    (90, "46 a 90 dias", "Alerta de suspensão"),
    (None, "+90 dias", "Risco de cancelamento"),
]


@app.get("/inadimplencia", response_class=HTMLResponse)
def inadimplencia(
    request: Request,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    fora = barrar(usuario, "inadimplencia")
    if fora:
        return fora

    registros = (
        db.query(Delinquency).order_by(Delinquency.dias_atraso.desc()).all()
    )

    kpis = {
        "total": sum(d.valor for d in registros),
        "quantidade": len(registros),
        "em_risco": sum(1 for d in registros if d.dias_atraso > 90),
        "maior_atraso": max((d.dias_atraso for d in registros), default=0),
        "maior_nome": registros[0].participante if registros else "—",
    }

    # Conta quantos caem em cada degrau da regua.
    regua = []
    anterior = 0
    for limite, faixa, acao in REGUA_COBRANCA:
        if limite is None:
            quantidade = sum(1 for d in registros if d.dias_atraso > anterior)
        else:
            quantidade = sum(
                1 for d in registros if anterior < d.dias_atraso <= limite
            )
            anterior = limite
        regua.append({"faixa": faixa, "acao": acao, "quantidade": quantidade})

    return templates.TemplateResponse(
        request,
        "inadimplencia.html",
        contexto(usuario, "inadimplencia", inadimplentes=registros,
                 kpis=kpis, regua=regua),
    )


@app.post("/inadimplencia/cobrar/{registro_id}")
def cobrar(
    registro_id: int,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """Marca que a cobranca foi enviada para aquele participante."""
    fora = barrar(usuario, "inadimplencia")
    if fora:
        return fora

    registro = db.query(Delinquency).filter(Delinquency.id == registro_id).first()
    if registro:
        registro.cobranca_enviada = True
        db.commit()

    return RedirectResponse("/inadimplencia", status_code=303)


@app.get("/inadimplencia/exportar")
def exportar_inadimplencia(
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    fora = barrar(usuario, "inadimplencia")
    if fora:
        return fora

    registros = db.query(Delinquency).order_by(Delinquency.dias_atraso.desc()).all()
    linhas = [
        [
            d.participante,
            d.numero_apolice,
            d.cobertura,
            f"{d.valor:.2f}".replace(".", ","),
            d.dias_atraso,
            d.faixa(),
            "Sim" if d.cobranca_enviada else "Não",
        ]
        for d in registros
    ]
    return gerar_csv(
        "inadimplencia.csv",
        ["Participante", "Apólice", "Cobertura", "Valor", "Dias em atraso",
         "Faixa", "Cobrança enviada"],
        linhas,
    )


# ===============================================================
# MODULO: ESTEIRA DE APOLICES
# ===============================================================
# As 4 colunas do quadro, na ordem do fluxo.
# (chave da etapa, titulo na tela, classe de cor do cartao)
COLUNAS_ESTEIRA = [
    ("recebida", "Proposta recebida", ""),
    ("analise", "Em análise (subscrição)", ""),
    ("aceita", "Aceita ✅", "ok"),
    ("pendente", "Pendente ⚠️", "pend"),
]


@app.get("/esteira", response_class=HTMLResponse)
def esteira(
    request: Request,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    fora = barrar(usuario, "esteira")
    if fora:
        return fora

    propostas = db.query(Proposal).order_by(Proposal.numero).all()

    colunas = [
        {
            "titulo": titulo,
            "cor": cor,
            "propostas": [p for p in propostas if p.etapa == etapa],
        }
        for etapa, titulo, cor in COLUNAS_ESTEIRA
    ]

    return templates.TemplateResponse(
        request,
        "esteira.html",
        contexto(usuario, "esteira", colunas=colunas,
                 propostas=propostas, total=len(propostas)),
    )


# ===============================================================
# MODULO: SINISTROS  (a corretora nao acessa)
# ===============================================================
@app.get("/sinistros", response_class=HTMLResponse)
def sinistros(
    request: Request,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    fora = barrar(usuario, "sinistros")
    if fora:
        return fora

    hoje = date.today()
    registros = db.query(Claim).order_by(Claim.data_abertura).all()

    dias = [c.dias_em_aberto(hoje) for c in registros]
    kpis = {
        "em_andamento": len(registros),
        "com_pendencia": sum(1 for c in registros if not c.documentacao_ok),
        "doc_ok": sum(1 for c in registros if c.documentacao_ok),
        "tempo_medio": (
            str(round(sum(dias) / len(dias), 1)).replace(".", ",") if dias else "0"
        ),
    }

    return templates.TemplateResponse(
        request,
        "sinistros.html",
        contexto(usuario, "sinistros", sinistros=registros, kpis=kpis),
    )


# ===============================================================
# MODULO: PENDENCIAS
# ===============================================================
@app.get("/pendencias", response_class=HTMLResponse)
def pendencias(
    request: Request,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    fora = barrar(usuario, "pendencias")
    if fora:
        return fora

    hoje = date.today()
    todas = db.query(Pendency).all()

    abertas = [p for p in todas if not p.resolvida]
    resolvidas = [p for p in todas if p.resolvida]

    # Ordena por prioridade (Alta primeiro) e, dentro dela, pelo prazo.
    abertas.sort(key=lambda p: (p.peso_prioridade(), p.prazo or date.max))

    kpis = {
        "total": len(todas),
        "abertas": len(abertas),
        "altas": sum(1 for p in abertas if p.prioridade == "Alta"),
        "sem_documento": sum(1 for p in abertas if not p.documento_ok),
        "urgentes": sum(
            1 for p in abertas if p.prazo and 0 <= (p.prazo - hoje).days <= 7
        ),
    }

    return templates.TemplateResponse(
        request,
        "pendencias.html",
        contexto(usuario, "pendencias", pendencias=abertas,
                 resolvidas=resolvidas, kpis=kpis),
    )


@app.post("/pendencias/resolver/{pendencia_id}")
def resolver_pendencia(
    pendencia_id: int,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    fora = barrar(usuario, "pendencias")
    if fora:
        return fora

    return _mudar_pendencia(db, pendencia_id, resolvida=True)


@app.post("/pendencias/reabrir/{pendencia_id}")
def reabrir_pendencia(
    pendencia_id: int,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    fora = barrar(usuario, "pendencias")
    if fora:
        return fora

    return _mudar_pendencia(db, pendencia_id, resolvida=False)


def _mudar_pendencia(db: Session, pendencia_id: int, resolvida: bool):
    """Marca a pendencia como resolvida ou reabre. Usada pelas duas rotas."""
    pendencia = db.query(Pendency).filter(Pendency.id == pendencia_id).first()
    if pendencia:
        pendencia.resolvida = resolvida
        db.commit()
    return RedirectResponse("/pendencias", status_code=303)


@app.get("/pendencias/exportar")
def exportar_pendencias(
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    fora = barrar(usuario, "pendencias")
    if fora:
        return fora

    todas = db.query(Pendency).all()
    todas.sort(key=lambda p: (p.resolvida, p.peso_prioridade(), p.prazo or date.max))

    linhas = [
        [
            p.prioridade,
            p.titulo,
            p.referente,
            p.responsavel,
            p.prazo.strftime("%d/%m/%Y") if p.prazo else "",
            p.documento,
            "Sim" if p.documento_ok else "Não",
            "Resolvida" if p.resolvida else "Aberta",
        ]
        for p in todas
    ]
    return gerar_csv(
        "pendencias.csv",
        ["Prioridade", "Pendência", "Referente a", "Responsável", "Prazo",
         "Documento", "Documento OK", "Situação"],
        linhas,
    )


# ===============================================================
# MODULO: RAMOS / PRODUTOS
# ===============================================================
# Os ramos previstos no roadmap. Nao tem tabela no banco porque nao
# ha dado operacional nenhum: e informacao de planejamento.
RAMOS_DO_ROADMAP = [
    {"nome": "Auto", "icone": "🚗", "fase": "Fase 2",
     "descricao": "Seguro de veículos — casco, terceiros e assistência 24h. Mesmo motor de esteira e cobrança."},
    {"nome": "Viagem", "icone": "✈️", "fase": "Fase 2",
     "descricao": "Assistência e seguro viagem nacional e internacional, com emissão rápida de bilhete."},
    {"nome": "Bike", "icone": "🚲", "fase": "Fase 3",
     "descricao": "Seguro para bicicletas — roubo, furto, danos e responsabilidade civil."},
    {"nome": "Residencial", "icone": "🏠", "fase": "Fase 3",
     "descricao": "Seguro residencial — incêndio, danos elétricos, roubo e assistência ao lar."},
]


@app.get("/produtos", response_class=HTMLResponse)
def produtos(
    request: Request,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    fora = barrar(usuario, "produtos")
    if fora:
        return fora

    ativas = db.query(Policy).filter(Policy.status == "Ativa").count()
    capital = db.query(func.sum(Policy.capital_total)).filter(
        Policy.status == "Ativa"
    ).scalar() or 0

    # "Vidas cobertas" = quantas coberturas existem somadas. Quem tem
    # morte + invalidez conta como 2 vidas cobertas.
    vidas = (
        db.query(func.count(Policy.id))
        .filter(Policy.status == "Ativa", Policy.capital_morte > 0)
        .scalar()
        or 0
    ) + (
        db.query(func.count(Policy.id))
        .filter(Policy.status == "Ativa", Policy.capital_invalidez > 0)
        .scalar()
        or 0
    )

    numeros = {
        "apolices": ativas,
        "vidas": vidas,
        "capital": formatar_compacto(capital),
    }

    return templates.TemplateResponse(
        request,
        "produtos.html",
        contexto(usuario, "produtos", numeros=numeros, roadmap=RAMOS_DO_ROADMAP),
    )


# ===============================================================
# MODULO: INTEGRACOES (API)
# ===============================================================
CONEXOES_PREVISTAS = [
    {"icone": "📥", "nome": "Envio de planilha (atual)", "cor": "on", "situacao": "● Ativo",
     "descricao": "Base recebida da corretora e carregada pelo comando do projeto — funciona hoje, sem integração"},
    {"icone": "🛡️", "nome": "API ICATU (seguradora)", "cor": "plan", "situacao": "Fase 3",
     "descricao": "Apólices, coberturas e sinistros sincronizados automaticamente"},
    {"icone": "🤝", "nome": "API Corretora", "cor": "plan", "situacao": "Fase 3",
     "descricao": "Movimentações, propostas e comissões em tempo real"},
    {"icone": "🗄️", "nome": "Trust Prev", "cor": "plan", "situacao": "Fase 3",
     "descricao": "Dados cadastrais e de plano dos participantes"},
    {"icone": "👤", "nome": "Área do Participante", "cor": "dev", "situacao": "Fase 4",
     "descricao": "Autoatendimento e consulta pelo próprio participante"},
]

PRE_REQUISITOS = [
    ("Credenciais de acesso", "Chaves/API keys autorizadas por cada sistema (ICATU, corretora, Trust Prev)"),
    ("Homologação de segurança", "Validação da Segurança da Informação e aderência à LGPD"),
    ("Mapeamento de dados", "De/para entre os campos de cada sistema e a Central"),
    ("Ambiente homologado", "Tráfego e armazenamento apenas no ambiente corporativo aprovado"),
    ("Validação da área", "Manifestação favorável da área responsável pelo processo"),
]


@app.get("/integracoes", response_class=HTMLResponse)
def integracoes(
    request: Request,
    usuario: User | None = Depends(exigir_login),
):
    fora = barrar(usuario, "integracoes")
    if fora:
        return fora

    return templates.TemplateResponse(
        request,
        "integracoes.html",
        contexto(usuario, "integracoes", conexoes=CONEXOES_PREVISTAS,
                 prerequisitos=PRE_REQUISITOS),
    )


# ===============================================================
# MODULO: ASSISTENTE
# ===============================================================
@app.get("/assistente", response_class=HTMLResponse)
def tela_assistente(
    request: Request,
    usuario: User | None = Depends(exigir_login),
):
    fora = barrar(usuario, "assist")
    if fora:
        return fora

    return templates.TemplateResponse(
        request,
        "assistente.html",
        contexto(usuario, "assist", sugestoes=assistente.SUGESTOES),
    )


@app.post("/assistente/perguntar")
def perguntar_ao_assistente(
    pergunta: str = Form(...),
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """
    Recebe a pergunta digitada e devolve a resposta em JSON.

    O JavaScript da tela chama esta rota e escreve a resposta na
    conversa, sem recarregar a pagina.
    """
    if usuario is None:
        return {"resposta": "Sua sessão expirou. Entre novamente."}

    return {"resposta": assistente.responder(db, pergunta)}
