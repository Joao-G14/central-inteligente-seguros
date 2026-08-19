"""
ia_treino.py
------------
O material de estudo da nossa IA.

O QUE E ISTO
------------
Uma lista de PERGUNTAS DE EXEMPLO, agrupadas por assunto. O modelo le
tudo isso e aprende a reconhecer o assunto de uma pergunta nova, mesmo
que ela seja escrita de um jeito que nao esta aqui.

E por isso que ele entende "kuantas apolice tem?" mesmo essa frase nunca
tendo sido escrita: ele aprendeu o PADRAO das perguntas de contagem.

COMO ENSINAR UMA COISA NOVA
---------------------------
1. ache o assunto na lista abaixo (ou crie um novo)
2. acrescente 3 ou 4 jeitos diferentes de perguntar aquilo
3. se criou um assunto novo, crie tambem a resposta em app/assistente.py
4. reinicie o servidor — o modelo treina sozinho ao ligar

Quanto mais variados os exemplos, melhor. Vale escrever errado de
proposito, usar giria e abreviacao: e assim que as pessoas digitam.
"""

# ===============================================================
# AS PERGUNTAS DE EXEMPLO, POR ASSUNTO
# ===============================================================
# A chave e o nome do assunto (chamado "intencao" em aprendizado de
# maquina). Cada nome precisa ter uma resposta correspondente no
# arquivo app/assistente.py.

TREINO: dict[str, list[str]] = {

    # -----------------------------------------------------------
    # CONVERSA
    # -----------------------------------------------------------
    "cumprimento": [
        "ola", "oi", "oi tudo bem", "ola tudo bem?", "e ai", "eai",
        "bom dia", "boa tarde", "boa noite", "opa", "salve",
        "oi, tudo bem com voce?", "ola, como vai?", "tudo bem?",
        "tudo bom?", "hey", "hello", "oi bom dia", "boa tarde tudo bem",
        "como voce esta", "beleza?",
    ],
    "apresentacao": [
        "quem e voce", "quem es tu", "o que voce e", "voce e um robo?",
        "voce e uma inteligencia artificial?", "se apresente",
        "qual o seu nome", "voce e humano?", "com quem estou falando",
        "o que voce faz", "para que voce serve", "qual sua funcao",
        "me fala de voce", "voce e a IA?", "voce é um bot",
    ],
    "agradecimento": [
        "obrigado", "obrigada", "valeu", "vlw", "muito obrigado",
        "agradeço", "show", "perfeito obrigado", "otimo, valeu",
        "muito bom", "excelente", "top", "ajudou muito", "brigado",
    ],
    "despedida": [
        "tchau", "ate logo", "ate mais", "adeus", "falou", "flw",
        "ate a proxima", "vou sair", "encerrar", "por hoje e so",
    ],
    "ajuda": [
        "ajuda", "me ajuda", "o que voce sabe fazer",
        "o que posso te perguntar", "quais sao as opcoes",
        "me da exemplos de perguntas", "nao sei o que perguntar",
        "socorro", "como usar", "o que voce pode responder",
        "lista o que voce faz", "menu", "comandos",
    ],

    # -----------------------------------------------------------
    # DADOS DA CARTEIRA
    # -----------------------------------------------------------
    "carteira_resumo": [
        "quantas apolices temos", "total de apolices", "quantas apolices",
        "me da um resumo da carteira", "como esta a carteira",
        "panorama geral", "visao geral", "resumo geral", "resuma tudo",
        "situacao da carteira", "quantas apolice tem", "numero de apolices",
        "quantos contratos temos", "tamanho da carteira",
        "me mostra os numeros", "quais os indicadores",
        "como estao as coisas", "status geral",
        # variacoes de "quantidade" que o modelo errou nos testes
        "quantas apolices a gente tem", "a gente tem quantas apolices",
        "temos quantas apolices", "qual a quantidade de apolices",
        "quantas apolices existem", "conta as apolices",
        "quantas apolices estao cadastradas", "quantas apolices no total",
        "tem quantas apolices", "quantidade de apolices na carteira",
    ],
    "apolices_por_status": [
        "quantas apolices ativas", "quantas estao ativas",
        "quantas apolices vencidas", "quantas venceram",
        "quantas canceladas", "apolices por situacao",
        "quantas estao a renovar", "divisao por status",
        "quantas apolices cada status", "apolices ativas e vencidas",
        "me mostra as vencidas", "lista as canceladas",
    ],
    "renovacoes": [
        "quais apolices vencem este mes", "o que vence agora",
        "renovacoes", "quais renovam", "proximas renovacoes",
        "o que precisa renovar", "apolices vencendo",
        "quais vencem nos proximos 30 dias", "vencimentos proximos",
        "tem alguma vencendo?", "o que ta pra vencer",
        "renovacao vencendo", "quais apolices preciso renovar",
        "vence essa semana?", "quantas renovacoes em 30 dias",
    ],
    "capital_segurado": [
        "qual o capital segurado", "capital segurado total",
        "quanto vale a carteira", "soma do capital",
        "capital total segurado", "quanto esta segurado",
        "valor total das apolices", "qual o capital",
        "quanto de capital temos", "montante segurado",
    ],
    "premio_total": [
        "qual o premio total", "quanto arrecadamos por mes",
        "premio mensal", "quanto entra por mes", "receita mensal",
        "soma dos premios", "arrecadacao", "faturamento mensal",
        "quanto os segurados pagam",
    ],
    "buscar_apolice": [
        "me mostra a apolice AP-2041", "procura a apolice do Marcos",
        "busca a apolice", "detalhes da AP-1987",
        "quero ver a apolice de Fernanda", "acha a apolice do participante",
        "informacoes da apolice AP-2115", "consulta apolice",
        "dados do segurado Marcos Ribeiro", "pesquisa por nome",
        "quero saber da apolice de Claudia", "ver apolice especifica",
    ],
    "vidas_cobertas": [
        "quantas vidas cobertas", "quantas pessoas seguradas",
        "quantos participantes", "numero de vidas",
        "quantas pessoas estao no seguro", "total de segurados",
        "quantas vidas temos",
    ],
    "sinistros": [
        "como estao os sinistros", "quantos sinistros",
        "sinistros em andamento", "tem sinistro aberto?",
        "situacao dos sinistros", "sinistros pendentes",
        "quais sinistros estao abertos", "casos de morte",
        "sinistros de invalidez", "protocolo SIN-0448",
        "quanto tempo de analise dos sinistros",
        "sinistro com documentacao faltando", "falta documento em algum sinistro",
    ],
    "inadimplencia": [
        "quem esta inadimplente", "quem esta devendo",
        "inadimplencia", "quem esta em atraso", "valor em atraso",
        "quantos inadimplentes", "quem nao pagou",
        "participantes atrasados", "quem ta devendo",
        "risco de cancelamento", "quem esta com mais atraso",
        "total devido", "cobrancas pendentes", "atrasos",
    ],
    "comissoes": [
        "como estao as comissoes", "divisao das comissoes",
        "quanto cada um recebe", "comissao da corretora",
        "quanto o estipulante recebe", "repasse do mes",
        "comissoes de julho", "quanto e a comissao",
        "percentual de comissao", "quanto a seguradora fica",
        "historico de comissoes", "comissao por competencia",
    ],
    "pagamentos": [
        "como estao os pagamentos", "quem pagou",
        "movimentacao do mes", "quantos pagaram",
        "quem esta a pagar", "situacao dos pagamentos",
        "base de segurados do mes", "movimentacao",
        "quantos segurados na competencia", "pagamentos de julho",
        "quem esta em atraso no pagamento", "planilha do mes",
    ],
    "propostas": [
        "como esta a esteira", "quantas propostas",
        "propostas em analise", "quais propostas foram aceitas",
        "propostas recusadas", "esteira de aceitacao",
        "o que esta na esteira", "propostas pendentes",
        "quantas propostas recebemos", "subscricao",
        "alguma proposta recusada?", "status das propostas",
    ],
    "pendencias": [
        "quais pendencias estao abertas", "o que falta resolver",
        "pendencias", "tem pendencia?", "quantas pendencias",
        "pendencias criticas", "o que e prioridade alta",
        "o que esta atrasado", "documentos faltando",
        "pendencias urgentes", "o que preciso fazer",
        "lista de pendencias",
    ],
    "convenios": [
        "quais sao os convenios", "convenios parceiros",
        "boletos por convenio", "quantos boletos",
        "boletos emitidos", "boletos em aberto",
        "quanto cada convenio arrecada", "FENACON",
        "quantas vidas por convenio", "boletos a emitir",
    ],

    # -----------------------------------------------------------
    # CONCEITOS DO SEGURO
    # -----------------------------------------------------------
    "conceito_apolice": [
        "o que e uma apolice", "o que significa apolice",
        "me explica o que e apolice", "defina apolice",
        "para que serve a apolice", "conceito de apolice",
        "apolice e o que", "o que quer dizer apolice",
        # grafias erradas comuns e outras formas de perguntar
        "o que significa apolise", "o que e apolise",
        "significado de apolice", "apolice significa o que",
        "explica apolice", "o que vem a ser uma apolice",
        "nunca entendi o que e apolice", "apolice quer dizer o que",
        "me explica o conceito de apolice",
    ],
    "conceito_premio": [
        "o que e premio", "o que significa premio",
        "premio e o que", "me explica premio",
        "por que se chama premio", "premio de seguro o que e",
        "qual a diferenca entre premio e indenizacao",
    ],
    "conceito_capital": [
        "o que e capital segurado", "o que significa capital segurado",
        "me explica capital segurado", "capital segurado e o que",
        "o que e indenizacao", "quanto a seguradora paga",
    ],
    "conceito_sinistro": [
        "o que e sinistro", "o que significa sinistro",
        "me explica sinistro", "sinistro quer dizer o que",
        "quando abre um sinistro", "como funciona o sinistro",
    ],
    "conceito_dps": [
        "o que e DPS", "o que significa DPS",
        "declaracao pessoal de saude", "para que serve a DPS",
        "me explica a DPS", "por que precisa de DPS",
    ],
    "conceito_carencia": [
        "o que e carencia", "o que significa carencia",
        "como funciona a carencia", "me explica carencia",
        "tem carencia no seguro?",
    ],
    "conceito_beneficiario": [
        "o que e beneficiario", "quem e o beneficiario",
        "quem recebe a indenizacao", "como se define o beneficiario",
        "beneficiario significa o que",
    ],
    "conceito_estipulante": [
        "o que e estipulante", "quem e o estipulante",
        "o que faz o estipulante", "qual o papel do estipulante",
        "estipulante significa o que", "quem representa os participantes",
    ],
    "conceito_corretora": [
        "o que faz a corretora", "qual o papel da corretora",
        "para que serve a corretora", "corretora faz o que",
        "quanto a corretora ganha",
    ],
    "conceito_seguradora": [
        "o que faz a seguradora", "qual o papel da seguradora",
        "quem e a seguradora", "o que e a ICATU",
        "quem paga a indenizacao",
    ],
    "conceito_subscricao": [
        "o que e subscricao", "como funciona a esteira",
        "o que e aceitacao de proposta", "explica o fluxo da proposta",
        "como uma proposta vira apolice", "o que e risco agravado",
    ],
    "conceito_competencia": [
        "o que e competencia", "o que significa competencia",
        "competencia e o que", "que mes e a competencia",
        "como funciona a competencia",
    ],
    "conceito_cobertura": [
        "o que e cobertura de morte", "o que e invalidez",
        "quais sao as coberturas", "tipos de cobertura",
        "o que o seguro cobre", "cobertura morte e invalidez",
        "qual a diferenca entre morte e invalidez",
    ],
    "conceito_convenio": [
        "o que e um convenio", "o que significa convenio",
        "me explica o que e convenio", "convenio quer dizer o que",
        "por que existem convenios", "para que serve o convenio",
        "o que e uma entidade parceira",
    ],
    "conceito_regua": [
        "o que e regua de cobranca", "como funciona a cobranca",
        "quais as faixas de atraso", "o que acontece se atrasar",
        "quando cancela por inadimplencia", "explica a regua",
    ],
    "conceito_ramo": [
        "o que e ramo", "quais ramos a central opera",
        "o que e modulo 101", "quais produtos existem",
        "vao ter outros seguros?", "o que e codigo sub",
    ],

    # -----------------------------------------------------------
    # SOBRE O PROPRIO SITE
    # -----------------------------------------------------------
    "sistema_o_que_e": [
        "o que e a central", "para que serve este sistema",
        "o que este site faz", "qual o objetivo do sistema",
        "me explica a central", "sobre o sistema",
        "o que e a central inteligente de seguros",
        "por que este sistema existe", "qual o proposito",
    ],
    "sistema_telas": [
        "quais telas existem", "o que tem no menu",
        "quais paginas tem no site", "o que da pra fazer aqui",
        "quais modulos existem", "me mostra o menu",
        "onde encontro cada coisa", "como navegar",
        "quais funcionalidades", "o que tem no sistema",
    ],
    "sistema_login": [
        "como entrar no sistema", "como faco login",
        "esqueci a senha", "como trocar a senha",
        "por que nao consigo entrar", "qual a senha",
        "como funciona o acesso", "quem pode entrar",
        "meu login nao funciona", "erro ao entrar",
    ],
    "sistema_permissoes": [
        "o que cada perfil ve", "quais as permissoes",
        "por que nao vejo sinistros", "por que tem cadeado no menu",
        "o que a corretora pode acessar",
        "o que a seguradora nao ve", "diferenca entre os perfis",
        "por que nao tenho acesso", "meu perfil ve o que",
        # formas de reclamar que algo esta bloqueado
        "por que nao consigo ver sinistro", "nao consigo abrir sinistros",
        "nao consigo acessar comissoes", "nao aparece inadimplencia pra mim",
        "esta bloqueado pra mim", "por que aparece o cadeado",
        "nao tenho permissao", "fui barrado", "acesso negado",
        "por que sumiu do menu", "nao consigo entrar nessa tela",
        "por que voltei pro dashboard",
    ],
    "sistema_controle_acesso": [
        "como controlo quem entra", "como autorizo alguem",
        "como bloqueio um email", "lista de acesso",
        "como vejo quem acessou", "historico de acessos",
        "quem entrou no sistema", "como restrinjo o acesso",
        "controle de acesso",
    ],
    "sistema_planilha": [
        "como envio a planilha", "como subo a base",
        "como importo os segurados", "upload de planilha",
        "onde mando o arquivo", "que colunas a planilha precisa",
        "como atualizo a movimentacao", "erro ao enviar planilha",
        "posso reenviar a planilha?", "formato da planilha",
    ],
    "sistema_exportar": [
        "como exporto para o excel", "da pra baixar os dados",
        "quero exportar", "como salvo em planilha",
        "gerar relatorio", "baixar csv", "download dos dados",
        "posso exportar a inadimplencia?",
    ],
    "sistema_boleto": [
        "como emito um boleto", "onde emito os boletos",
        "boleto por convenio", "como gero cobranca",
        "o que acontece ao emitir o boleto",
    ],
    "sistema_cobrar": [
        "como cobro um inadimplente", "botao cobrar",
        "como envio a cobranca", "o que faz o botao cobrar",
        "como aviso quem esta devendo",
    ],
    "sistema_pendencia_resolver": [
        "como marco uma pendencia como resolvida",
        "como resolvo pendencia", "como reabro uma pendencia",
        "o que faz o botao marcar resolvida",
        "como dou baixa numa pendencia", "onde fecho a pendencia",
        "resolvi errado, como desfaco", "como tiro da lista de pendencias",
        "marquei sem querer, e agora",
    ],
    "sistema_busca": [
        "como busco na tabela", "tem filtro?",
        "como procuro um participante", "como filtro os dados",
        "onde pesquiso", "da pra buscar por nome",
    ],
    "sistema_api": [
        "como funciona a api", "o que e a integracao",
        "como outro sistema acessa", "tem api?",
        "como conecto com a icatu", "integracao por api",
        "onde vejo a documentacao da api", "chave da api",
    ],
    "sistema_dados": [
        "de onde vem os dados", "os dados sao reais?",
        "onde ficam guardados os dados", "qual o banco de dados",
        "os dados sao ficticios?", "como os dados chegam aqui",
        "quem alimenta o sistema", "e seguro guardar isso aqui",
    ],
    "sistema_tecnologia": [
        "com que foi feito o site", "qual tecnologia usa",
        "que linguagem", "foi feito em que", "usa python?",
        "como o site foi construido", "qual framework",
    ],
    "sistema_assistente": [
        "como voce funciona", "voce usa inteligencia artificial?",
        "voce e chatgpt?", "como voce responde",
        "voce aprende?", "de onde vem suas respostas",
        "voce inventa resposta?", "voce tem acesso ao banco?",
    ],
}


def total_de_exemplos() -> int:
    """Quantas frases de treino existem no total."""
    return sum(len(frases) for frases in TREINO.values())


def total_de_assuntos() -> int:
    """Quantos assuntos diferentes o modelo conhece."""
    return len(TREINO)
