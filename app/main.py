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

from datetime import date, datetime, timedelta

import csv
import secrets
import io

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import api, assistente, assistente_ia, auth, config, ia_local, planilha, seed, tempo
from app.database import PASTA_RAIZ, get_db
from app.menu import MENU, buscar_modulo
from app.models import (
    CHAVE_EXIGIR_AUTORIZACAO,
    PERFIS_VALIDOS,
    ActiveSession,
    Agreement,
    ApiCall,
    ApiKey,
    AuthorizedEmail,
    ChatMessage,
    Claim,
    Commission,
    Delinquency,
    Invoice,
    LoginHistory,
    Payment,
    Pendency,
    Policy,
    Proposal,
    Setting,
    User,
)

@asynccontextmanager
async def ao_ligar_e_desligar(app: FastAPI):
    """
    Roda UMA VEZ quando o sistema liga.

    Prepara o banco sozinho: cria as tabelas que faltarem e, se o banco
    estiver vazio, carrega os dados iniciais.

    É isto que permite subir o sistema num servidor sem abrir terminal
    nenhum. No seu computador o efeito é o mesmo: se você apagar o
    central.db por engano, ele volta ao ligar.
    """
    # --- CONFERENCIA DE SEGURANCA ---
    # Feita ANTES de qualquer outra coisa. Se houver problema grave e o
    # sistema estiver em producao, ele nao sobe: um site no ar sem tranca
    # e pior do que um site fora do ar.
    problemas = config.conferir_seguranca()
    if problemas:
        print()
        print("=" * 66)
        print("  PROBLEMAS DE SEGURANCA NA CONFIGURACAO")
        print("=" * 66)
        for i, p in enumerate(problemas, 1):
            print(f"  {i}. {p}")
        print("=" * 66)

        if config.EM_PRODUCAO:
            print("  AMBIENTE=producao: o sistema NAO vai subir assim.")
            print("  Corrija os itens acima e tente de novo.")
            print("=" * 66)
            print()
            raise RuntimeError(
                "Configuracao insegura para producao. Veja a lista acima."
            )

        print("  AMBIENTE=desenvolvimento: seguindo, mas CORRIJA antes de")
        print("  colocar no ar.")
        print("=" * 66)
        print()

    if config.CRIAR_BANCO_AO_INICIAR:
        try:
            if seed.garantir_banco():
                print(">> Banco vazio: dados iniciais carregados.")
            else:
                print(">> Banco já tinha dados: nada foi alterado.")
        except Exception as erro:
            # Nao derrubamos o servidor por causa disso: avisamos alto e
            # deixamos o site subir, senao fica impossivel diagnosticar.
            print(f">> ERRO ao preparar o banco: {erro}")

    # Treina a IA agora, enquanto o servidor esta subindo. Se deixassemos
    # para depois, a PRIMEIRA pergunta de alguem demoraria uns 2 segundos
    # a mais. Aqui esse tempo entra na inicializacao, que ninguem espera.
    try:
        if ia_local.preparar():
            info = ia_local.informacoes()
            print(f">> IA local pronta: {info['assuntos']} assuntos, "
                  f"{info['exemplos']} exemplos de treino.")
        else:
            print(f">> IA local indisponivel ({ia_local.informacoes()['erro']}). "
                  f"O assistente vai usar palavras-chave.")
    except Exception as erro:
        print(f">> ERRO ao treinar a IA local: {erro}")

    yield  # daqui em diante o site esta no ar


app = FastAPI(
    title="Central Inteligente de Seguros",
    description="Sistema de gestão de seguros de risco (morte e invalidez).",
    version="1.0.0",
    lifespan=ao_ligar_e_desligar,
)

# Liga a API de integração (todos os endereços começam com /api/v1).
app.include_router(api.router)


# ===============================================================
# PAGINAS DE ERRO
# ===============================================================
# Sem estas duas funcoes, um endereco errado mostraria um JSON cru em
# ingles e um defeito no codigo mostraria uma tela branca. Aqui trocamos
# as duas coisas por uma pagina em portugues, com a cara do sistema.
#
# A API (/api/v1) fica de FORA: quem chama a API e outro programa, e
# programa entende JSON melhor do que HTML.


def _pagina_de_erro(request: Request, codigo: int, icone: str,
                    titulo: str, mensagem: str):
    return templates.TemplateResponse(
        request,
        "erro.html",
        {"codigo": codigo, "icone": icone, "titulo": titulo, "mensagem": mensagem},
        status_code=codigo,
    )


@app.exception_handler(404)
def pagina_nao_encontrada(request: Request, exc):
    """Endereco que nao existe."""
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Endereço não encontrado."}, status_code=404)

    return _pagina_de_erro(
        request, 404, "🧭",
        "Página não encontrada",
        "O endereço que você tentou abrir não existe. Talvez o link esteja "
        "errado ou a página tenha mudado de lugar.",
    )


@app.exception_handler(500)
@app.exception_handler(Exception)
def erro_interno(request: Request, exc):
    """
    Defeito no proprio sistema.

    O detalhe tecnico do erro vai para o TERMINAL, para quem cuida do
    sistema investigar. Na tela mostramos so uma mensagem generica: se
    mostrassemos o erro tecnico, poderiamos revelar caminhos de arquivo,
    nomes de tabela e outras informacoes uteis para um invasor.
    """
    import traceback

    print()
    print("=" * 66)
    print(f"  ERRO NAO TRATADO em {request.method} {request.url.path}")
    print("=" * 66)
    traceback.print_exception(type(exc), exc, exc.__traceback__)
    print("=" * 66)
    print()

    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Erro interno do servidor."}, status_code=500)

    return _pagina_de_erro(
        request, 500, "⚠️",
        "Algo deu errado",
        "O sistema encontrou um problema ao montar esta página. Não foi "
        "culpa sua. O detalhe técnico foi registrado no servidor.",
    )

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

    Se houver alguem logado, devolve a categoria de acesso.
    Se nao houver, devolve None — e a rota manda a pessoa para o /login.

    Aproveitamos para pendurar o e-mail digitado no objeto, com o nome
    email_acesso. E so um campo extra na memoria (nao vai para o banco)
    e permite que a barra de cima mostre quem esta usando o sistema.
    """
    usuario = auth.ler_usuario_do_cookie(db, request)
    if usuario is not None:
        usuario.email_acesso = auth.ler_email_do_cookie(db, request)
    return usuario


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
        "hoje": tempo.hoje(),
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

    # --- PROTECAO CONTRA FORCA BRUTA ---
    # Antes de conferir qualquer senha: este endereco ja errou demais?
    # Se sim, recusamos sem nem olhar a senha. Isso torna inviavel testar
    # senhas em sequencia.
    bloqueado, faltam = auth.esta_bloqueado(db, ip)
    if bloqueado:
        auth.registrar_login(db, email, perfil, False,
                             f"bloqueado por excesso de tentativas ({ip})", ip=ip)
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "erro": f"Muitas tentativas incorretas. Aguarde {faltam} minuto(s) "
                        f"antes de tentar novamente.",
                "email_digitado": email,
                "perfil_marcado": perfil,
            },
            status_code=429,  # 429 = "too many requests"
        )

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

    # Passos 5 e 6: abre a sessao no banco, entrega o cracha e manda
    # para o dashboard.
    token = auth.abrir_sessao(db, usuario, email.strip().lower(), ip)
    resposta = RedirectResponse("/dashboard", status_code=303)
    auth.criar_cookie_sessao(resposta, token)
    return resposta


@app.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    """
    Sai do sistema.

    Faz DUAS coisas, e as duas importam:
      1. apaga a sessao do banco — assim qualquer copia do cookie morre
      2. apaga o cookie do navegador
    """
    auth.fechar_sessao(db, request)
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

    hoje = tempo.hoje()

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
    # Cores da paleta oficial Sebrae Previdencia.
    # Blue Prev, Sky Cloud e Navy Sea — as mesmas do arquivo style.css.
    cores = {
        "Morte": "#1517B3",              # Blue Prev
        "Invalidez": "#1A98DA",          # Sky Cloud
        "Morte + Invalidez": "#071F59",  # Navy Sea
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


# Quantas apolices por pagina.
#
# POR QUE PAGINAR: a tela desenha uma linha de tabela para cada apolice.
# Com 100 fica tranquilo, mas com 5.000 o navegador engasga e a pagina
# demora para abrir. Mostrando de 50 em 50, o tempo nao cresce junto com
# a carteira.
APOLICES_POR_PAGINA = 50


@app.get("/seguros", response_class=HTMLResponse)
def seguros(
    request: Request,
    pagina: int = 1,
    status: str = "",
    busca: str = "",
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """A carteira de apolices, com filtros e paginacao."""
    if usuario is None:
        return RedirectResponse("/login", status_code=303)

    consulta = db.query(Policy)

    if status:
        consulta = consulta.filter(Policy.status == status)
    if busca:
        # ilike = nao diferencia maiuscula de minuscula.
        # O | e "ou": procura no nome OU no numero da apolice.
        alvo = f"%{busca}%"
        consulta = consulta.filter(
            (Policy.participante.ilike(alvo))
            | (Policy.numero_apolice.ilike(alvo))
            | (Policy.cpf.ilike(alvo))
        )

    total = consulta.count()

    # Quantas paginas cabem. O -(-a // b) e um truque para arredondar
    # para CIMA: 101 apolices em paginas de 50 dao 3 paginas, nao 2.
    paginas = max(1, -(-total // APOLICES_POR_PAGINA))
    pagina = max(1, min(pagina, paginas))

    apolices = (
        consulta.order_by(Policy.data_vencimento)
        .offset((pagina - 1) * APOLICES_POR_PAGINA)
        .limit(APOLICES_POR_PAGINA)
        .all()
    )

    # Os status que existem de fato no banco, para montar o filtro.
    status_existentes = [
        s[0] for s in db.query(Policy.status).distinct().order_by(Policy.status).all()
    ]

    return templates.TemplateResponse(
        request,
        "seguros.html",
        contexto(
            usuario,
            "seguros",
            apolices=apolices,
            total=total,
            pagina=pagina,
            paginas=paginas,
            por_pagina=APOLICES_POR_PAGINA,
            primeiro=(pagina - 1) * APOLICES_POR_PAGINA + 1 if total else 0,
            ultimo=min(pagina * APOLICES_POR_PAGINA, total),
            filtros={"status": status, "busca": busca},
            status_existentes=status_existentes,
        ),
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
def ordem_da_competencia(competencia: str) -> str:
    """
    Transforma "07/2026" em "2026-07", que ordena corretamente como texto.

    Sem isso, ordenar "07/2026" e "12/2025" alfabeticamente colocaria
    julho antes de dezembro, o que esta errado.
    """
    if "/" in competencia:
        mes, ano = competencia.split("/", 1)
        return f"{ano}-{mes}"
    return competencia


def _tela_movimentacao(
    request: Request,
    db: Session,
    usuario: User,
    competencia: str | None = None,
    resumo: dict | None = None,
    erros: list[str] | None = None,
):
    """
    Monta a tela de movimentacao.

    Fica numa funcao separada porque TRES rotas precisam dela: abrir a
    tela, enviar a planilha e trocar a competencia. Assim a montagem
    existe em um lugar so.
    """
    # Quais competencias existem no banco, da mais nova para a mais antiga.
    todas = [c[0] for c in db.query(Payment.competencia).distinct().all()]
    todas.sort(key=ordem_da_competencia, reverse=True)

    # Qual mostrar: a pedida, ou a mais recente.
    if competencia not in todas:
        competencia = todas[0] if todas else None

    pagamentos = (
        db.query(Payment)
        .filter(Payment.competencia == competencia)
        .order_by(Payment.matricula)
        .all()
        if competencia
        else []
    )

    totais = {
        "morte": sum(p.capital_morte for p in pagamentos),
        "invalidez": sum(p.capital_invalidez for p in pagamentos),
        "premio": sum(p.premio for p in pagamentos),
    }

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
            competencia=competencia or "—",
            competencias=todas,
            totais=totais,
            a_emitir=a_emitir,
            emitidos=emitidos,
            resumo=resumo,
            erros=erros or [],
        ),
    )


@app.get("/movimentacao", response_class=HTMLResponse)
def movimentacao(
    request: Request,
    competencia: str | None = None,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    fora = barrar(usuario, "movimentacao")
    if fora:
        return fora

    return _tela_movimentacao(request, db, usuario, competencia=competencia)


# Tamanho maximo do arquivo enviado, para nao derrubar o servidor.
LIMITE_ARQUIVO_MB = 5


@app.post("/movimentacao/enviar", response_class=HTMLResponse)
async def enviar_planilha(
    request: Request,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """
    Recebe a planilha .xlsx enviada pela tela e grava no banco.

    O caminho e sempre o mesmo:
      1. confere se e um .xlsx e se nao e grande demais
      2. LE o arquivo (nada e gravado ainda)
      3. se a leitura achou linhas validas, GRAVA
      4. volta para a tela mostrando o que aconteceu

    Ler e gravar sao separados de proposito: se a planilha tiver
    problema, o banco nem chega a ser tocado.
    """
    fora = barrar(usuario, "movimentacao")
    if fora:
        return fora

    nome = (arquivo.filename or "").lower()
    if not nome.endswith(".xlsx"):
        return _tela_movimentacao(
            request, db, usuario,
            erros=[f'"{arquivo.filename}" não é um arquivo .xlsx do Excel. '
                   f"Se a sua planilha for .xls ou .csv, abra no Excel e "
                   f'salve como "Pasta de Trabalho do Excel (*.xlsx)".'],
        )

    conteudo = await arquivo.read()

    if len(conteudo) > LIMITE_ARQUIVO_MB * 1024 * 1024:
        return _tela_movimentacao(
            request, db, usuario,
            erros=[f"O arquivo tem mais de {LIMITE_ARQUIVO_MB} MB. "
                   f"Envie uma planilha menor."],
        )

    registros, erros = planilha.ler_planilha(conteudo)

    if not registros:
        return _tela_movimentacao(request, db, usuario, erros=erros)

    resumo = planilha.gravar(db, registros)
    resumo["arquivo"] = arquivo.filename

    return _tela_movimentacao(request, db, usuario, resumo=resumo, erros=erros)


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
        boleto.data_vencimento = tempo.hoje() + timedelta(days=10)
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

    hoje = tempo.hoje()
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

    hoje = tempo.hoje()
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
# Os enderecos da API que ja funcionam. Ficam aqui so para a tela
# /integracoes conseguir listar; quem manda de verdade e o app/api.py.
ENDPOINTS_DA_API = [
    ("GET", "/api/v1/status", "Confere se a Central está no ar e traz os totais"),
    ("GET", "/api/v1/indicadores", "Números consolidados da carteira"),
    ("GET", "/api/v1/apolices", "Lista as apólices (filtra por status e vencimento)"),
    ("GET", "/api/v1/apolices/{numero}", "Busca uma apólice pelo número"),
    ("GET", "/api/v1/movimentacao", "Movimentação de uma competência"),
    ("GET", "/api/v1/sinistros", "Sinistros em andamento"),
    ("GET", "/api/v1/comissoes", "Comissões por competência"),
    ("GET", "/api/v1/inadimplencia", "Participantes em atraso"),
    ("POST", "/api/v1/movimentacao", "Recebe a movimentação enviada pela corretora"),
]

CONEXOES_PREVISTAS = [
    {"icone": "🔌", "nome": "API da Central", "cor": "on", "situacao": "● Ativo",
     "descricao": "Publica os dados da carteira e recebe movimentação de sistemas parceiros"},
    {"icone": "📥", "nome": "Envio de planilha", "cor": "on", "situacao": "● Ativo",
     "descricao": "Base da corretora enviada em .xlsx pela tela de Movimentação & Pagamento"},
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
                 prerequisitos=PRE_REQUISITOS, endpoints=ENDPOINTS_DA_API),
    )


# ===============================================================
# MODULO: CONTROLE DE ACESSO  (só o estipulante)
# ===============================================================
# Quantos acessos mostrar na tela de uma vez.
LIMITE_HISTORICO = 200


@app.get("/acessos", response_class=HTMLResponse)
def acessos(
    request: Request,
    busca: str = "",
    perfil: str = "",
    resultado: str = "",
    aviso: str = "",
    erro: str = "",
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """Mostra quem pode entrar e quem já entrou."""
    fora = barrar(usuario, "acessos")
    if fora:
        return fora

    return _tela_acessos(request, db, usuario, busca, perfil, resultado, aviso, erro)


def _tela_acessos(request, db, usuario, busca="", perfil="", resultado="",
                  aviso="", erro=""):
    """Monta a tela. Fica separado porque várias rotas voltam para ela."""
    # --- histórico, com os filtros aplicados ---
    consulta = db.query(LoginHistory)

    if busca:
        # ilike = busca sem diferenciar maiúscula de minúscula.
        # O % antes e depois significa "contém em qualquer posição".
        consulta = consulta.filter(LoginHistory.email_informado.ilike(f"%{busca}%"))
    if perfil:
        consulta = consulta.filter(LoginHistory.perfil_informado == perfil)
    if resultado == "sucesso":
        consulta = consulta.filter(LoginHistory.sucesso.is_(True))
    elif resultado == "falha":
        consulta = consulta.filter(LoginHistory.sucesso.is_(False))

    total_filtrado = consulta.count()
    registros = (
        consulta.order_by(LoginHistory.data_hora.desc()).limit(LIMITE_HISTORICO).all()
    )

    # --- números do topo (sempre do total, não do filtro) ---
    total = db.query(LoginHistory).count()
    sucessos = db.query(LoginHistory).filter(LoginHistory.sucesso.is_(True)).count()
    emails_unicos = db.query(
        func.count(func.distinct(LoginHistory.email_informado))
    ).scalar() or 0

    autorizados = (
        db.query(AuthorizedEmail)
        .order_by(AuthorizedEmail.ativo.desc(), AuthorizedEmail.valor)
        .all()
    )

    kpis = {
        "total": total,
        "sucessos": sucessos,
        "falhas": total - sucessos,
        "emails_unicos": emails_unicos,
        "autorizacoes": sum(1 for a in autorizados if a.ativo),
    }

    return templates.TemplateResponse(
        request,
        "acessos.html",
        contexto(
            usuario,
            "acessos",
            acessos=registros,
            total_filtrado=total_filtrado,
            limite=LIMITE_HISTORICO,
            autorizados=autorizados,
            # para o botão "Bloquear" não aparecer em quem já está na lista
            emails_ja_listados={a.valor for a in autorizados},
            exigir=auth.exigir_autorizacao(db),
            kpis=kpis,
            filtros={"busca": busca, "perfil": perfil, "resultado": resultado},
            aviso=aviso,
            erro=erro,
        ),
    )


def _voltar_para_acessos(aviso: str = "", erro: str = ""):
    """Volta para a tela mostrando uma mensagem."""
    from urllib.parse import urlencode

    parametros = {k: v for k, v in {"aviso": aviso, "erro": erro}.items() if v}
    destino = "/acessos"
    if parametros:
        destino += "?" + urlencode(parametros)
    return RedirectResponse(destino, status_code=303)


@app.post("/acessos/autorizar")
def autorizar_email(
    valor: str = Form(...),
    perfil: str = Form("TODAS"),
    observacao: str = Form(""),
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """Cadastra um e-mail ou domínio na lista de acesso."""
    fora = barrar(usuario, "acessos")
    if fora:
        return fora

    valor = (valor or "").strip().lower()

    # Confere o formato: ou é um domínio (@algo.com) ou um e-mail inteiro.
    if valor.startswith("@"):
        if "." not in valor[1:] or len(valor) < 5:
            return _voltar_para_acessos(
                erro=f'"{valor}" não parece um domínio válido. Exemplo: @empresa.com.br'
            )
    elif not auth.formato_de_email_valido(valor):
        return _voltar_para_acessos(
            erro=f'"{valor}" não é um e-mail válido nem um domínio. '
                 f"Para liberar uma empresa inteira, comece com @."
        )

    if perfil not in ["TODAS"] + PERFIS_VALIDOS:
        perfil = "TODAS"

    if db.query(AuthorizedEmail).filter(AuthorizedEmail.valor == valor).first():
        return _voltar_para_acessos(erro=f"{valor} já está na lista.")

    db.add(
        AuthorizedEmail(
            valor=valor,
            perfil=perfil,
            observacao=(observacao or "").strip() or None,
            ativo=True,
            cadastrado_por=usuario.email_acesso or usuario.nome,
        )
    )
    db.commit()

    return _voltar_para_acessos(aviso=f"{valor} foi autorizado.")


@app.post("/acessos/bloquear-email")
def bloquear_email(
    email: str = Form(...),
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """
    Atalho do histórico: cadastra o e-mail já como BLOQUEADO.

    Serve para quando você vê no histórico um e-mail que não deveria
    estar acessando e quer barrá-lo na hora.
    """
    fora = barrar(usuario, "acessos")
    if fora:
        return fora

    email = (email or "").strip().lower()
    if not email:
        return _voltar_para_acessos(erro="E-mail vazio.")

    existente = db.query(AuthorizedEmail).filter(AuthorizedEmail.valor == email).first()
    if existente:
        existente.ativo = False
    else:
        db.add(
            AuthorizedEmail(
                valor=email,
                perfil="TODAS",
                observacao="Bloqueado pelo histórico de acessos",
                ativo=False,
                cadastrado_por=usuario.email_acesso or usuario.nome,
            )
        )
    db.commit()

    return _voltar_para_acessos(
        aviso=f"{email} foi bloqueado. Lembre-se: o bloqueio só faz efeito "
              f"com a exigência da lista ligada."
    )


@app.post("/acessos/alternar/{registro_id}")
def alternar_autorizacao(
    registro_id: int,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """Bloqueia quem está ativo, reativa quem está bloqueado."""
    fora = barrar(usuario, "acessos")
    if fora:
        return fora

    registro = db.query(AuthorizedEmail).filter(AuthorizedEmail.id == registro_id).first()
    if registro is None:
        return _voltar_para_acessos(erro="Registro não encontrado.")

    registro.ativo = not registro.ativo
    db.commit()

    situacao = "reativado" if registro.ativo else "bloqueado"
    return _voltar_para_acessos(aviso=f"{registro.valor} foi {situacao}.")


@app.post("/acessos/remover/{registro_id}")
def remover_autorizacao(
    registro_id: int,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """Apaga a autorização de vez."""
    fora = barrar(usuario, "acessos")
    if fora:
        return fora

    registro = db.query(AuthorizedEmail).filter(AuthorizedEmail.id == registro_id).first()
    if registro is None:
        return _voltar_para_acessos(erro="Registro não encontrado.")

    valor = registro.valor
    db.delete(registro)
    db.commit()

    return _voltar_para_acessos(aviso=f"{valor} foi removido da lista.")


@app.post("/acessos/exigencia")
def alternar_exigencia(
    ligar: str = Form(...),
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """
    Liga ou desliga a exigência da lista de acesso.

    Com ela LIGADA, entrar exige duas coisas: estar na lista e saber a
    senha da categoria. Com ela DESLIGADA, basta a senha.
    """
    fora = barrar(usuario, "acessos")
    if fora:
        return fora

    novo_valor = "sim" if ligar == "sim" else "nao"

    registro = (
        db.query(Setting).filter(Setting.chave == CHAVE_EXIGIR_AUTORIZACAO).first()
    )
    if registro is None:
        registro = Setting(chave=CHAVE_EXIGIR_AUTORIZACAO)
        db.add(registro)

    registro.valor = novo_valor
    registro.atualizado_em = tempo.agora()
    db.commit()

    if novo_valor == "sim":
        ativas = db.query(AuthorizedEmail).filter(AuthorizedEmail.ativo.is_(True)).count()
        if ativas == 0:
            return _voltar_para_acessos(
                erro="Exigência LIGADA, mas a lista está vazia — ninguém consegue "
                     "entrar. Cadastre pelo menos um e-mail ou domínio agora."
            )
        return _voltar_para_acessos(
            aviso=f"Exigência ligada. Agora só entram os {ativas} cadastros ativos."
        )

    return _voltar_para_acessos(
        aviso="Exigência desligada. Qualquer e-mail entra com a senha da categoria."
    )


@app.get("/acessos/exportar")
def exportar_acessos(
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """Baixa o histórico completo de acessos em .csv."""
    fora = barrar(usuario, "acessos")
    if fora:
        return fora

    registros = db.query(LoginHistory).order_by(LoginHistory.data_hora.desc()).all()
    linhas = [
        [
            r.data_hora.strftime("%d/%m/%Y %H:%M:%S"),
            r.email_informado,
            r.perfil_informado,
            r.ip or "",
            "Entrou" if r.sucesso else "Recusado",
            r.motivo or "",
        ]
        for r in registros
    ]
    return gerar_csv(
        "historico_de_acessos.csv",
        ["Data e hora", "E-mail informado", "Categoria", "IP", "Resultado", "Motivo"],
        linhas,
    )


# ===============================================================
# CHAVES DA API E REGISTRO DE CHAMADAS  (só o estipulante)
# ===============================================================
LIMITE_CHAMADAS = 100


@app.get("/api-chaves", response_class=HTMLResponse)
def api_chaves(
    request: Request,
    aviso: str = "",
    erro: str = "",
    chave_nova: str = "",
    nome_novo: str = "",
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """Gerencia as chaves de API e mostra quem chamou."""
    fora = barrar(usuario, "acessos")
    if fora:
        return fora

    chaves = db.query(ApiKey).order_by(ApiKey.ativo.desc(), ApiKey.nome).all()
    chamadas = (
        db.query(ApiCall)
        .order_by(ApiCall.data_hora.desc())
        .limit(LIMITE_CHAMADAS)
        .all()
    )

    total = db.query(ApiCall).count()
    recusadas = db.query(ApiCall).filter(ApiCall.status == 401).count()

    return templates.TemplateResponse(
        request,
        "api_chaves.html",
        contexto(
            usuario, "acessos",
            chaves=chaves,
            chamadas=chamadas,
            limite=LIMITE_CHAMADAS,
            kpis={
                "total": total,
                "recusadas": recusadas,
                "ativas": sum(1 for c in chaves if c.ativo),
                "tem_env": bool(config.API_KEY),
            },
            aviso=aviso, erro=erro,
            chave_nova=chave_nova, nome_novo=nome_novo,
        ),
    )


def _voltar_para_chaves(**parametros):
    from urllib.parse import urlencode

    limpos = {k: v for k, v in parametros.items() if v}
    destino = "/api-chaves"
    if limpos:
        destino += "?" + urlencode(limpos)
    return RedirectResponse(destino, status_code=303)


@app.post("/api-chaves/criar")
def criar_chave_api(
    nome: str = Form(...),
    observacao: str = Form(""),
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """
    Cria uma chave para um parceiro.

    A chave completa e mostrada UMA VEZ, na volta para a tela. Depois
    disso nem nos conseguimos ver: guardamos so o hash, igual as senhas.
    Se o parceiro perder, gera-se outra.
    """
    fora = barrar(usuario, "acessos")
    if fora:
        return fora

    nome = (nome or "").strip()
    if len(nome) < 3:
        return _voltar_para_chaves(erro="Dê um nome ao parceiro (ao menos 3 letras).")

    if db.query(ApiKey).filter(ApiKey.nome == nome).first():
        return _voltar_para_chaves(erro=f'Já existe uma chave chamada "{nome}".')

    # token_urlsafe(32) gera algo impossivel de adivinhar. O prefixo
    # "cis_" ajuda quem receber a saber de onde a chave veio.
    chave = "cis_" + secrets.token_urlsafe(32)

    db.add(ApiKey(
        nome=nome,
        chave_hash=auth.gerar_hash(chave),
        inicio=chave[:12],
        observacao=(observacao or "").strip() or None,
        ativo=True,
        criado_por=usuario.email_acesso or usuario.nome,
    ))
    db.commit()

    return _voltar_para_chaves(chave_nova=chave, nome_novo=nome)


@app.post("/api-chaves/alternar/{chave_id}")
def alternar_chave_api(
    chave_id: int,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """Bloqueia ou reativa uma chave."""
    fora = barrar(usuario, "acessos")
    if fora:
        return fora

    registro = db.query(ApiKey).filter(ApiKey.id == chave_id).first()
    if registro is None:
        return _voltar_para_chaves(erro="Chave não encontrada.")

    registro.ativo = not registro.ativo
    db.commit()
    situacao = "reativada" if registro.ativo else "bloqueada"
    return _voltar_para_chaves(aviso=f'A chave "{registro.nome}" foi {situacao}.')


@app.post("/api-chaves/remover/{chave_id}")
def remover_chave_api(
    chave_id: int,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """
    Apaga a chave de vez.

    O historico de chamadas dela e preservado: apenas perde o vinculo,
    mas o nome do parceiro continua gravado em cada linha.
    """
    fora = barrar(usuario, "acessos")
    if fora:
        return fora

    registro = db.query(ApiKey).filter(ApiKey.id == chave_id).first()
    if registro is None:
        return _voltar_para_chaves(erro="Chave não encontrada.")

    nome = registro.nome
    db.query(ApiCall).filter(ApiCall.api_key_id == chave_id).update(
        {ApiCall.api_key_id: None}
    )
    db.delete(registro)
    db.commit()

    return _voltar_para_chaves(aviso=f'A chave "{nome}" foi removida.')


@app.get("/api-chaves/exportar")
def exportar_chamadas_api(
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """Baixa o registro de chamadas da API em .csv."""
    fora = barrar(usuario, "acessos")
    if fora:
        return fora

    registros = db.query(ApiCall).order_by(ApiCall.data_hora.desc()).all()
    linhas = [
        [
            c.data_hora.strftime("%d/%m/%Y %H:%M:%S"),
            c.parceiro or "(não identificado)",
            c.metodo,
            c.caminho,
            c.status,
            c.ip or "",
            c.resumo or "",
        ]
        for c in registros
    ]
    return gerar_csv(
        "chamadas_da_api.csv",
        ["Data e hora", "Parceiro", "Método", "Endereço", "Status", "IP", "Resumo"],
        linhas,
    )


# ===============================================================
# TROCAR A SENHA DE UMA CATEGORIA  (só o estipulante)
# ===============================================================
@app.get("/senha", response_class=HTMLResponse)
def tela_senha(
    request: Request,
    aviso: str = "",
    erro: str = "",
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """Tela para trocar a senha de uma das três categorias."""
    fora = barrar(usuario, "acessos")
    if fora:
        return fora

    contas = db.query(User).order_by(User.perfil).all()
    sessoes = {}
    for c in contas:
        sessoes[c.perfil] = db.query(ActiveSession).filter(
            ActiveSession.user_id == c.id
        ).count()

    return templates.TemplateResponse(
        request,
        "senha.html",
        contexto(usuario, "acessos", contas=contas, sessoes=sessoes,
                 aviso=aviso, erro=erro),
    )


@app.post("/senha/trocar")
def trocar_senha(
    perfil: str = Form(...),
    senha_atual: str = Form(...),
    nova: str = Form(...),
    repetir: str = Form(...),
    derrubar: str = Form(""),
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """
    Troca a senha de uma categoria.

    Exige a senha ATUAL daquela categoria. Assim, mesmo que alguem
    esqueca a tela aberta, nao consegue trocar senhas sem saber a antiga.
    """
    from urllib.parse import urlencode

    def voltar(**p):
        limpos = {k: v for k, v in p.items() if v}
        destino = "/senha"
        if limpos:
            destino += "?" + urlencode(limpos)
        return RedirectResponse(destino, status_code=303)

    fora = barrar(usuario, "acessos")
    if fora:
        return fora

    if perfil not in PERFIS_VALIDOS:
        return voltar(erro="Categoria inválida.")

    conta = db.query(User).filter(User.perfil == perfil).first()
    if conta is None:
        return voltar(erro="Categoria não encontrada.")

    if not auth.conferir_senha(senha_atual, conta.senha_hash):
        return voltar(erro=f"A senha atual de {perfil} está incorreta.")

    if len(nova) < 10:
        return voltar(erro="A senha nova precisa ter ao menos 10 caracteres.")

    if nova != repetir:
        return voltar(erro="A senha nova e a repetição não são iguais.")

    if auth.conferir_senha(nova, conta.senha_hash):
        return voltar(erro="A senha nova é igual à atual.")

    conta.senha_hash = auth.gerar_hash(nova)
    db.commit()

    mensagem = f"Senha de {perfil} trocada."

    # Derrubar as sessoes obriga todo mundo daquela categoria a entrar de
    # novo com a senha nova. E o certo quando a troca foi por vazamento.
    if derrubar == "sim":
        quantas = auth.encerrar_todas_as_sessoes(db, perfil)
        mensagem += f" {quantas} sessão(ões) encerrada(s)."

    # A senha nova FICA GRAVADA e sobrevive a reinicios: ao ligar, o
    # sistema so popula o banco se ele estiver vazio, entao nao sobrescreve
    # nada. O .env vale apenas na PRIMEIRA criacao do banco.
    #
    # A unica coisa que desfaz a troca e rodar "python -m app.seed" de
    # proposito, que apaga tudo e recria do zero.
    mensagem += (
        " A senha nova já está valendo e continua após reiniciar o servidor."
        " Vale atualizar o .env também, para o caso de o banco ser recriado"
        " algum dia."
    )

    return voltar(aviso=mensagem)


# ===============================================================
# MODULO: ASSISTENTE
# ===============================================================
# Quantas falas da conversa mostramos ao abrir a tela.
LIMITE_CONVERSA = 40


def _conversa_de(db: Session, email: str) -> list[ChatMessage]:
    """As falas anteriores desta pessoa, da mais antiga para a mais nova."""
    recentes = (
        db.query(ChatMessage)
        .filter(ChatMessage.usuario_email == email)
        .order_by(ChatMessage.id.desc())
        .limit(LIMITE_CONVERSA)
        .all()
    )
    return list(reversed(recentes))


@app.get("/assistente", response_class=HTMLResponse)
def tela_assistente(
    request: Request,
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    fora = barrar(usuario, "assist")
    if fora:
        return fora

    email = usuario.email_acesso or usuario.email

    return templates.TemplateResponse(
        request,
        "assistente.html",
        contexto(
            usuario,
            "assist",
            sugestoes=assistente.SUGESTOES,
            conversa=_conversa_de(db, email),
            # o selo no topo mostra qual motor esta respondendo
            usando_ia=assistente_ia.esta_disponivel(),
            ia_local=ia_local.informacoes(),
        ),
    )


@app.post("/assistente/perguntar")
def perguntar_ao_assistente(
    pergunta: str = Form(...),
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """
    Recebe a pergunta e devolve a resposta em JSON.

    A ordem de tentativa:
      1. se houver chave da Anthropic, pergunta para a IA
      2. se a IA falhar (sem internet, chave invalida, limite atingido),
         cai para o assistente por palavras-chave
      3. o assistente por palavras-chave sempre responde alguma coisa

    Assim ninguem nunca fica sem resposta, nem quando a IA esta fora.
    """
    if usuario is None:
        return {"resposta": "Sua sessão expirou. Entre novamente.", "origem": "erro"}

    pergunta = (pergunta or "").strip()
    if not pergunta:
        return {"resposta": "Digite uma pergunta para eu poder ajudar. 🙂",
                "origem": "regras"}

    email = usuario.email_acesso or usuario.email
    aviso = ""

    # --- 1. tenta a IA ---
    resposta = ""
    origem = "regras"

    if assistente_ia.esta_disponivel():
        historico = [
            {"role": m.papel, "content": m.conteudo}
            for m in _conversa_de(db, email)
        ]
        resposta, erro = assistente_ia.responder(pergunta, historico)
        if resposta:
            origem = "ia"
        else:
            # A IA falhou. Registramos no terminal para voces verem o
            # motivo, e seguimos para o plano B.
            print(f">> IA indisponivel ({erro}). Usando o assistente por regras.")
            aviso = (
                '<br><br><span style="font-size:11.5px;opacity:.7">'
                "⚠️ A IA está indisponível no momento; respondi pelo modo básico."
                "</span>"
            )

    # --- 2. plano B: palavras-chave ---
    if not resposta:
        resposta = assistente.responder(db, pergunta) + aviso

    # --- 3. guarda a conversa ---
    db.add(ChatMessage(usuario_email=email, papel="user", conteudo=pergunta))
    db.add(ChatMessage(usuario_email=email, papel="assistant",
                       conteudo=resposta, origem=origem))
    db.commit()

    return {"resposta": resposta, "origem": origem}


@app.post("/assistente/limpar")
def limpar_conversa(
    db: Session = Depends(get_db),
    usuario: User | None = Depends(exigir_login),
):
    """Apaga a conversa desta pessoa e começa do zero."""
    fora = barrar(usuario, "assist")
    if fora:
        return fora

    email = usuario.email_acesso or usuario.email
    db.query(ChatMessage).filter(ChatMessage.usuario_email == email).delete()
    db.commit()

    return RedirectResponse("/assistente", status_code=303)
