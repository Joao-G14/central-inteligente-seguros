# Central Inteligente de Seguros

Aplicacao web que centraliza a operacao de seguros de risco (morte e invalidez),
conectando **Estipulante** (Sebrae Previdencia), **Corretora** e **Seguradora**.

Baseada no prototipo navegavel do Programa Prev IA — 1o Ciclo.

> **Atencao:** todos os dados deste projeto sao **ficticios**, usados apenas para
> desenvolvimento e demonstracao.

---

## Tecnologias

| O que | Para que serve |
|---|---|
| Python 3.12+ | linguagem de programacao |
| FastAPI | cria as paginas e rotas do site |
| Uvicorn | servidor que coloca o site no ar |
| Jinja2 | monta o HTML com dados do banco |
| SQLAlchemy | conversa com o banco de dados |
| SQLite | o banco de dados (um arquivo local) |
| bcrypt | protege as senhas com hash |
| itsdangerous | assina o cookie de sessao do login |
| openpyxl | le a planilha .xlsx enviada pela tela |
| anthropic | o assistente com inteligencia artificial (opcional) |
| HTML / CSS / JavaScript | a interface |

---

## Estrutura de pastas

```
central-inteligente-seguros/
├── app/                  # o codigo Python da aplicacao
│   ├── main.py           # as rotas: cada endereco do site
│   ├── database.py       # conexao com o banco
│   ├── models.py         # as 14 tabelas
│   ├── auth.py           # senha, login, sessao e permissoes
│   ├── config.py         # le o arquivo .env
│   ├── menu.py           # os itens do menu lateral
│   ├── seed.py           # cria e popula o banco
│   ├── planilha.py       # le a planilha .xlsx enviada
│   ├── api.py            # a API para sistemas parceiros
│   ├── assistente.py     # assistente por palavras-chave
│   └── assistente_ia.py  # assistente com IA (Claude)
├── templates/            # as paginas HTML
├── static/
│   ├── css/style.css     # a folha de estilo, com a paleta oficial
│   ├── js/main.js        # avisos de carregamento e busca nas tabelas
│   └── img/              # logo e favicon
├── database/             # o arquivo central.db (nao vai para o GitHub)
├── sql/banco.sql         # script para recriar o banco do zero
├── prototipo/            # o prototipo HTML original, intacto
├── docs/                 # documentacao do projeto
├── tests/                # 6 arquivos de teste
├── venv/                 # ambiente virtual (nao vai para o GitHub)
├── requirements.txt
├── render.yaml           # receita de publicacao no servidor
├── DEPLOY.md             # guia para colocar no ar
├── .env.example          # modelo de configuracao
├── .gitignore
└── README.md
```

---

## Como preparar o ambiente (primeira vez)

Abra o **PowerShell** dentro da pasta do projeto e rode:

```powershell
# 1. criar o ambiente virtual
python -m venv venv

# 2. ativar o ambiente virtual
.\venv\Scripts\Activate.ps1

# 3. instalar as bibliotecas
pip install -r requirements.txt
```

Se o passo 2 der erro de permissao, rode uma vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

> Sempre que abrir o projeto num terminal novo, repita o passo 2 (ativar o venv).
> Voce sabe que funcionou quando aparecer `(venv)` no inicio da linha.

---

## Como criar o banco de dados

O arquivo `database/central.db` **nao vem junto no GitHub**. Cada pessoa cria
o seu, com um comando so:

```powershell
python -m app.seed
```

Isso cria as 14 tabelas e preenche com os dados de demonstracao
(3 categorias de acesso e 100 apolices). Pode rodar quantas vezes
quiser — ele sempre refaz do zero.

> Na pratica voce quase nunca precisa deste comando: o sistema cria o
> banco sozinho ao ligar, se ele nao existir. Use o `seed` quando quiser
> **apagar tudo e comecar do zero**.

Para conferir se deu tudo certo:

```powershell
python tests\test_banco.py
```

Devem aparecer 48 verificacoes com `[OK]`.

> Alternativa: se preferir criar o banco pelo SQL puro, use
> `sqlite3 database/central.db < sql/banco.sql`. O arquivo `sql/banco.sql`
> e gerado automaticamente pelo `app/seed.py` e nao deve ser editado a mao.

---

## Como rodar o site

```powershell
uvicorn app.main:app --reload
```

Depois abra no navegador: http://127.0.0.1:8000

Para parar o servidor, aperte **Ctrl+C** no terminal.

O `--reload` reinicia o servidor sozinho toda vez que voce salva um arquivo.
Serve para desenvolver; em producao nao se usa.

### Rodar todos os testes

```powershell
python tests\test_banco.py          # 48 — banco e dados
python tests\test_login.py          # 49 — login e permissoes
python tests\test_modulos.py        # 94 — as telas dos modulos
python tests\test_novidades.py      # 61 — planilha e API
python tests\test_acessos.py        # 77 — controle de acesso e assistente
python tests\test_assistente_ia.py  # 48 — a IA e a memoria da conversa
```

Total: **377 verificacoes**. Nao precisa estar com o servidor ligado —
os testes sobem a aplicacao por dentro.

Rode sempre depois de mexer no codigo. Se aparecer `[FALHOU]`, a linha
diz exatamente o que quebrou.

---

## As telas do sistema

As 12 telas funcionam, lendo dados do banco.

| Endereco | Tela | O que mostra |
|---|---|---|
| `/login` | Entrada | 3 categorias, e-mail e senha |
| `/dashboard` | Dashboard | numeros da carteira + ultimos acessos |
| `/produtos` | Ramos / Produtos | ramo ativo (numeros reais) + roadmap |
| `/integracoes` | Integracoes (API) | os enderecos da API e o roadmap |
| `/seguros` | Gestao de Seguros | 100 apolices, com busca |
| `/esteira` | Esteira de Apolices | quadro de propostas em 4 colunas |
| `/movimentacao` | Movimentacao & Pgto. | envio de planilha, convenios e boletos |
| `/comissoes` | Painel de Comissoes | divisao 10/15/75% + historico |
| `/inadimplencia` | Inadimplencia | regua de cobranca e devedores |
| `/sinistros` | Sinistros | sinistros em andamento |
| `/pendencias` | Pendencias | o que falta resolver |
| `/assistente` | Assistente | perguntas respondidas com o banco |
| `/acessos` | Controle de Acesso | quem pode entrar e quem ja entrou |
| `/docs` | Documentacao da API | pagina automatica, da para testar por ali |

### Coisas que realmente funcionam (nao sao so telas)

- **Enviar planilha `.xlsx`** — le, valida linha por linha e grava. A
  planilha substitui a competencia inteira, entao reenviar uma versao
  corrigida nao duplica nada. Se houver erro, o banco nem e tocado.
- **Emitir boleto** — muda o status no banco e define o vencimento
- **Cobrar inadimplente** — marca a cobranca como enviada
- **Resolver / reabrir pendencia** — muda a situacao no banco
- **Autorizar e bloquear acesso** — pela tela de Controle de Acesso
- **Exportar Excel** — baixa um `.csv` de verdade (movimentacao,
  inadimplencia, pendencias e historico de acessos), ja no formato do
  Excel brasileiro
- **Busca nas tabelas** — filtra sem recarregar a pagina
- **Assistente** — consulta o banco na hora para responder
- **API de integracao** — 9 enderecos para sistemas parceiros

### A API de integracao

Serve para outros sistemas (corretora, seguradora) buscarem e enviarem
dados sem ninguem digitar. A documentacao automatica fica em **`/docs`**,
e da para testar cada endereco por ali mesmo.

| Metodo | Endereco | O que faz |
|---|---|---|
| GET | `/api/v1/status` | confere se a Central esta no ar |
| GET | `/api/v1/indicadores` | numeros consolidados da carteira |
| GET | `/api/v1/apolices` | lista apolices (filtra por status e vencimento) |
| GET | `/api/v1/apolices/{numero}` | busca uma apolice |
| GET | `/api/v1/movimentacao` | movimentacao de uma competencia |
| GET | `/api/v1/sinistros` | sinistros em andamento |
| GET | `/api/v1/comissoes` | comissoes por competencia |
| GET | `/api/v1/inadimplencia` | participantes em atraso |
| POST | `/api/v1/movimentacao` | **recebe** a base da corretora |

Todo pedido precisa enviar o cabecalho `X-API-Key` com a chave definida
no `.env`. Sem ela, a resposta e 401.

> A conexao **com** ICATU, corretora e Trust Prev nao depende de
> programacao nossa: depende de esses sistemas publicarem uma API,
> liberarem credenciais e passarem pela homologacao de seguranca.

#### Conectar ao Microsoft Copilot

Da para criar um agente no Copilot Studio que responde sobre a Central
usando esta API — as pessoas perguntariam no Teams. O passo a passo esta
em **[COPILOT-STUDIO.md](COPILOT-STUDIO.md)**.

O arquivo que a Microsoft precisa e gerado por:

```powershell
python gerar_openapi.py https://seu-endereco-publico
```

> Exige o sistema **publicado na internet**: o Copilot Studio nao
> alcanca `127.0.0.1`.

### Identidade visual

O site usa a **paleta oficial do Sebrae Previdencia**. As 9 cores estao
no topo do `static/css/style.css` com o nome oficial de cada uma —
trocar ali muda o site inteiro.

Tres cores (Green Leaf, Gray Steel e Sky Cloud) tem contraste abaixo do
minimo legivel quando usadas como texto sobre branco. Elas continuam
sendo usadas como **preenchimento** (barras, bordas, bolinhas), e o
arquivo define versoes escurecidas so para texto. O motivo esta
comentado no proprio CSS.

### Sobre o Assistente

Ele tem **dois motores**, e escolhe sozinho qual usar:

| Motor | Arquivo | Quando roda |
|---|---|---|
| **IA de verdade** (Claude Opus 5) | `app/assistente_ia.py` | quando ha uma `ANTHROPIC_API_KEY` no `.env` |
| **Palavras-chave** | `app/assistente.py` | sem chave, ou se a IA falhar |

Com a IA ligada, ele entende qualquer jeito de perguntar, conversa,
compara numeros e lembra do que foi dito antes. A IA nao tem acesso
direto ao banco: ela usa **8 ferramentas** que apenas LEEM
(apolices, sinistros, inadimplencia, comissoes, pagamentos, pendencias,
propostas e o resumo da carteira). Ela nao consegue alterar nem apagar nada.

Sem a chave, o modo por palavras-chave assume e ninguem fica sem resposta.

A conversa fica guardada por pessoa (tabela `chat_messages`) e ha um
botao **Limpar** para recomecar.

#### Como ligar a IA

1. crie uma conta em https://console.anthropic.com
2. gere uma chave de API
3. coloque no arquivo `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

4. reinicie o servidor

O selo no topo da conversa mostra qual motor esta ativo: **IA ativa** ou
**Modo basico**.

> Cada pergunta a IA tem um custo (fracoes de centavo). Confira os precos
> atuais no site da Anthropic.

---

## Como funciona o acesso

O login e por **CATEGORIA**, nao por usuario individual. Cada categoria
tem a sua senha, compartilhada por todas as pessoas daquela categoria:

| Categoria | Senha (definida no `.env`) |
|---|---|
| ESTIPULANTE | `SENHA_ESTIPULANTE` |
| CORRETORA | `SENHA_CORRETORA` |
| SEGURADORA | `SENHA_SEGURADORA` |

O **e-mail e livre**: serve para identificar quem entrou e fica gravado
no historico com data, hora e IP.

As senhas ficam no arquivo `.env` (que nao vai para o GitHub). Use o
`.env.example` como modelo. No banco elas sao guardadas como
**hash bcrypt** — nunca em texto puro.

### Controle de Acesso (so o estipulante)

A tela `/acessos` tem duas partes:

**Lista de acesso autorizado** — cadastre e-mails especificos
(`joao@empresa.com.br`) ou dominios inteiros (`@empresa.com.br`, libera
a empresa toda). Da para bloquear, reativar e remover.

Um interruptor liga a **exigencia da lista**. Com ela ligada, entrar
exige duas coisas: estar cadastrado **e** saber a senha da categoria.
Ela comeca desligada, com o dominio `@sebraeprev.com.br` ja cadastrado,
para ligar a exigencia nao travar o acesso de ninguem.

**Historico de acessos** — toda tentativa, com filtros por e-mail,
categoria e resultado, e exportacao em CSV.

> **Limitacao conhecida:** como a senha e compartilhada e o e-mail nao e
> conferido, o registro de quem acessou depende da boa-fe de quem digita.
> Se um dia for preciso auditoria a prova de contestacao, o caminho e
> voltar ao login individual por pessoa — o campo `email` da tabela
> `users` ja esta preparado para isso.

---

## As tabelas do banco

São **14 tabelas**:

| Tabela | O que guarda |
|---|---|
| `users` | as 3 categorias de acesso e a senha de cada uma |
| `authorized_emails` | quem pode entrar (e-mails e dominios liberados) |
| `settings` | configuracoes que o estipulante liga pela tela |
| `login_history` | cada tentativa de acesso: quem, quando, de qual IP |
| `chat_messages` | a conversa de cada pessoa com o assistente |
| `policies` | a carteira de apolices (100 registros) |
| `payments` | movimentacao mensal por segurado (10 registros) |
| `agreements` | os 4 convenios (FENACON, OPBB, CORECON, FenaSebrae) |
| `invoices` | boletos por convenio e competencia (8 registros) |
| `commissions` | divisao do premio entre os 3 agentes (15 registros) |
| `delinquency` | participantes em atraso (6 registros) |
| `proposals` | propostas na esteira de aceitacao (9 registros) |
| `claims` | sinistros abertos (4 registros) |
| `pendencies` | pendencias a resolver (5 registros) |

Os dados das apolices vieram de 3 origens, marcadas na coluna `origem`:

- `prototipo` — as 8 apolices que aparecem na tela do prototipo HTML
- `planilha` — os 10 segurados da `Base_Segurados_Central.xlsx`
- `gerado` — 82 apolices geradas para dar volume a carteira

Para mudar a quantidade, altere `TOTAL_APOLICES` no `app/seed.py`.
Os testes leem essa constante, entao nada quebra.

### Subir o sistema VAZIO (para uso real)

No `.env`, troque `CARREGAR_DADOS_DEMO=sim` por **`nao`** e apague o
`database/central.db`. O sistema sobe so com as categorias de acesso,
sem nenhuma apolice inventada — a carteira entra pela planilha ou pela
API. Isso so vale para um banco novo; dados existentes nunca sao apagados.

### Como o status da apolice e calculado

| Situacao | Status |
|---|---|
| a data de vencimento ja passou | `Vencida` |
| vence em ate 30 dias | `A renovar` |
| vence depois disso | `Ativa` |
| (marcada a mao no seed) | `Cancelada` |

As datas nao sao fixas no codigo: elas sao calculadas **a partir do dia em
que voce roda `python -m app.seed`**. Guardamos "faltam X dias para vencer"
em vez de "vence em 28/07/2026".

Foi feito assim porque o prototipo foi desenhado em 21/07/2026. Com datas
fixas, a carteira iria envelhecendo e daqui a alguns meses tudo apareceria
como `Vencida`. Com dias, as 8 apolices do prototipo mostram sempre os
mesmos status da tela original — hoje e daqui a anos.

---

## Perfis de acesso

| Perfil | O que pode ver |
|---|---|
| **ESTIPULANTE** | tudo, inclusive o Controle de Acesso |
| **CORRETORA** | tudo, **exceto** Sinistros e Controle de Acesso |
| **SEGURADORA** | tudo, **exceto** Comissoes, Inadimplencia e Controle de Acesso |

As regras ficam em `MODULOS_BLOQUEADOS`, no `app/auth.py` — uma lista
por perfil do que ele **nao** pode acessar.

A trava e no **servidor**, nao so no menu: digitar o endereco na barra
do navegador tambem e barrado. Esconder o item do menu sozinho nao
protege nada.

---

## Colocar no ar

O passo a passo completo esta em **[DEPLOY.md](DEPLOY.md)**.

Resumo: o projeto ja traz o `render.yaml`, entao no Render basta
**New + → Blueprint → escolher o repositorio**. Ele pergunta as 3 senhas
e publica sozinho.

⚠️ **Antes de subir dados reais**, leia o aviso sobre LGPD no comeco do
DEPLOY.md. Para dados de participantes reais, o sistema precisa ir para a
infraestrutura homologada do Sebrae Previdencia.

---

## Status do desenvolvimento

- [x] **Fase 1** — analise do prototipo e preparacao do ambiente
- [x] **Fase 2** — banco de dados (`users`, `login_history`, `policies`)
- [x] **Fase 3** — tela de login, autenticacao, permissoes e dashboard
- [x] **Fase 4** — todas as 11 telas do prototipo funcionando

### O que ficou de fora (proximos passos)

Coisas que o prototipo sugeria mas que **nao** foram implementadas,
porque exigem decisoes de negocio ou integracoes externas:

- **Envio de planilha pela tela** — hoje a base entra pelo `app/seed.py`.
  Ler um `.xlsx` enviado pelo navegador e o proximo passo natural.
- **Integracoes por API** (ICATU, corretora, Trust Prev) — dependem de
  credenciais e homologacao de seguranca; a tela `/integracoes` explica.
- **Area do Participante** — autoatendimento, previsto para depois.
- **Cadastro de usuarios pela tela** — hoje os 3 usuarios sao criados
  pelo seed. Nao ha tela de "novo usuario" nem troca de senha.
- **Envio real de e-mail de cobranca** — o botao "Cobrar" marca no
  banco, mas nao dispara e-mail.
- **Grafico de capital por mes** no dashboard — nao temos dados
  historicos de capital, so de comissao.

---

## Prototipo original

O arquivo `prototipo/Portal_Central_Inteligente_Seguros.html` e o prototipo
navegavel original, com 11 telas. Ele **nao deve ser alterado** — serve como
referencia visual enquanto convertemos cada tela.

Para ve-lo, basta abrir o arquivo com um duplo clique.
