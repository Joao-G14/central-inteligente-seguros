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
│   ├── models.py         # as 17 tabelas
│   ├── auth.py           # senha, login, sessao, permissoes, forca bruta
│   ├── config.py         # le o .env e confere a seguranca ao ligar
│   ├── tempo.py          # a hora certa (fuso de Brasilia)
│   ├── menu.py           # os itens do menu lateral
│   ├── seed.py           # cria e popula o banco
│   ├── cadastros.py      # a descricao dos campos de cada cadastro
│   ├── planilha.py       # le a planilha .xlsx enviada
│   ├── api.py            # a API para sistemas parceiros
│   ├── assistente.py     # as respostas do assistente
│   ├── ia_treino.py      # as perguntas de exemplo da IA local
│   ├── ia_local.py       # a IA treinada aqui (aprendizado de maquina)
│   └── assistente_ia.py  # a IA na nuvem (Claude), opcional
├── templates/            # as paginas HTML
├── static/
│   ├── css/style.css     # a folha de estilo, com a paleta oficial
│   ├── js/main.js        # avisos de carregamento, busca, conversa
│   └── img/              # logo e favicon
├── database/             # o arquivo central.db (nao vai para o GitHub)
├── backups/              # copias do banco (nao vao para o GitHub)
├── sql/banco.sql         # script para recriar o banco do zero
├── prototipo/            # o prototipo HTML original, intacto
├── docs/                 # documentacao do projeto
├── tests/                # 9 arquivos de teste
├── venv/                 # ambiente virtual (nao vai para o GitHub)
├── requirements.txt
├── backup.py             # faz e restaura copias do banco
├── gerar_openapi.py      # gera o arquivo para o Copilot Studio
├── render.yaml           # receita de publicacao no servidor
├── DEPLOY.md             # guia para colocar no ar
├── COPILOT-STUDIO.md     # guia do agente no Copilot
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

Isso cria as 17 tabelas e preenche com os dados de demonstracao
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
python tests\test_acessos.py        # 77 — controle de acesso
python tests\test_assistente_ia.py  # 48 — a IA na nuvem e a conversa
python tests\test_ia_local.py       # 79 — a IA treinada aqui
python tests\test_seguranca.py      # 50 — as correcoes de seguranca
python tests\test_cadastros.py      # 83 — cadastrar, editar, excluir
```

Total: **589 verificacoes**. Nao precisa estar com o servidor ligado —
os testes sobem a aplicacao por dentro.

Rode sempre depois de mexer no codigo. Se aparecer `[FALHOU]`, a linha
diz exatamente o que quebrou.

> O `test_seguranca.py` merece atencao: cada verificacao dele
> corresponde a um problema que EXISTIU e foi corrigido (XSS, forca
> bruta, logout que nao invalidava a sessao...). Se algum voltar, aquele
> arquivo acusa.

---

## Copias de seguranca

O banco e um unico arquivo e nao vai para o GitHub. Se ele corromper,
os dados enviados por planilha se perdem. Por isso:

```powershell
python backup.py                 # faz uma copia agora
python backup.py --listar        # mostra as copias existentes
python backup.py --restaurar 3   # volta para a copia numero 3
```

As copias ficam em `backups/`, que tambem nao vai para o GitHub. As 30
mais recentes sao guardadas; as antigas saem sozinhas.

Vale automatizar: no Windows, pelo Agendador de Tarefas; num servidor
Linux, por cron. O passo a passo esta comentado no `backup.py`.

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
| `/api-chaves` | Chaves da API | uma chave por parceiro + quem chamou |
| `/senha` | Trocar senha | troca a senha de uma categoria |
| `/docs` | Documentacao da API | pagina automatica, da para testar por ali |

As tres ultimas sao de administracao e **so o estipulante** enxerga.

### Cadastrar, editar e excluir

Cinco telas tem botao de **+ Novo** e link de **Editar** em cada linha:
apolices, sinistros, propostas, pendencias e inadimplencia.

O que muda entre elas esta descrito em **`app/cadastros.py`** — um unico
formulario (`templates/cadastro.html`) desenha todas. Para acrescentar
um campo, e **uma linha** naquele arquivo: nenhum HTML precisa ser
tocado.

O formulario aceita valor nos dois formatos (`1.234,56` e `1234.56`) e
data nos dois (`25/12/2026` e `2026-12-25`), mostra todos os erros de uma
vez e volta preenchido quando algo esta errado. Nada e gravado se houver
qualquer problema.

A permissao do cadastro e a **mesma** da listagem, e vale tambem no
endereco direto: quem nao ve sinistros nao cadastra sinistros nem
chamando a rota na mao.

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

### Seguranca

O sistema passou por uma auditoria e os 12 pontos encontrados foram
corrigidos. O que esta em vigor hoje:

| Protecao | Como funciona |
|---|---|
| Senhas | guardadas com hash bcrypt, nunca em texto |
| Sessao | o cookie carrega so um codigo aleatorio; a sessao mora no banco |
| Logout | apaga a sessao do banco, entao um cookie copiado morre na hora |
| Forca bruta | 8 falhas do mesmo IP em 10 min bloqueiam por 15 min |
| Permissoes | travadas no servidor, nao so no menu |
| Lista de acesso | opcional: so entra quem estiver autorizado |
| Chaves de API | uma por parceiro, guardadas com hash |
| Registro | todo login e toda chamada de API ficam gravados |
| Conferencia ao ligar | em producao, o sistema **se recusa a subir** com a SECRET_KEY padrao, com senha do exemplo ou com chave curta |

**Duas coisas para nao esquecer antes de colocar no ar:**

1. Gere uma `SECRET_KEY` propria e troque as tres senhas. O sistema nao
   sobe em producao sem isso — e proposital.
2. Ligue a **exigencia da lista de acesso**, na tela de Controle de
   Acesso. Sem ela, qualquer e-mail entra sabendo a senha da categoria.

**Limitacao conhecida:** a senha e da CATEGORIA, nao da pessoa. Para
tirar o acesso de uma pessoa e preciso trocar a senha de todas as
daquela categoria, e o e-mail registrado no historico e o que a pessoa
digitou — o sistema nao confere se e dela. Se um dia o registro precisar
valer como prova formal, o caminho e migrar para senha individual.

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

Ele tem **tres motores** e escolhe sozinho, nesta ordem:

| # | Motor | Arquivo | Quando roda |
|---|---|---|---|
| 1 | **IA na nuvem** (Claude) | `app/assistente_ia.py` | se houver `ANTHROPIC_API_KEY` no `.env` |
| 2 | **IA local** (nossa) | `app/ia_local.py` | sempre que o scikit-learn estiver instalado |
| 3 | Palavras-chave | `app/assistente.py` | se os dois acima falharem |

Ninguem fica sem resposta: se um motor falha, o seguinte assume.

#### A IA local — treinada aqui mesmo

E um **modelo de aprendizado de maquina** treinado no proprio servidor,
sem internet, sem custo por pergunta e sem os dados sairem daqui — o que
importa para a LGPD.

**Como funciona, em 3 passos:**

1. **TF-IDF** transforma a frase em numeros, quebrando de dois jeitos ao
   mesmo tempo: por letras (2 a 5 seguidas), o que tolera erro de
   digitacao, e por palavras (1 ou 2), o que pega expressoes como
   "capital segurado" como uma coisa so.
2. Uma **Regressao Logistica** aprende, a partir dos exemplos, quais
   pedacos indicam cada assunto. Ninguem escreve "se tem a palavra X
   entao e Y" — ela deduz sozinha.
3. Ela responde o assunto **e o quanto esta confiante**. Abaixo de 28%
   de confianca, prefere dizer que nao entendeu a chutar.

Por isso ela entende `"kuantas apolice a gente tem?"` sem que essa frase
exista em lugar nenhum do codigo.

**O que ela cobre:** 50 assuntos — os dados da carteira, os conceitos do
seguro (apolice, premio, DPS, carencia, subscricao...) e **como usar cada
tela do sistema** (login, permissoes, envio de planilha, exportacao,
emissao de boleto, busca, API).

Ela tambem reconhece codigos citados no meio da pergunta: escreva
`AP-2041`, `SIN-0448` ou `PROP-3012` e ela traz aquele registro.

**Ensinar algo novo** — leva 2 minutos:

1. abra `app/ia_treino.py`
2. ache o assunto (ou crie um novo)
3. acrescente 3 ou 4 jeitos diferentes de perguntar aquilo
4. se criou um assunto novo, crie a resposta em `app/assistente.py`
5. reinicie o servidor — ele treina sozinho ao ligar, em ~2 segundos

Vale escrever errado de proposito e usar giria: e assim que as pessoas
digitam.

> **O que ela NAO e:** um modelo de linguagem como o ChatGPT. Ela nao
> escreve textos novos nem raciocina em varias etapas. Ela reconhece o
> assunto e busca a resposta no banco — que e o que este sistema precisa.

#### A IA na nuvem (opcional)

Com uma `ANTHROPIC_API_KEY` no `.env`, o assistente passa a usar o
**Claude Opus 5**. Ele conversa de verdade, compara numeros e lembra do
contexto. Nao tem acesso direto ao banco: usa **8 ferramentas** que
apenas LEEM.

```
ANTHROPIC_API_KEY=sk-ant-...
```

Crie a chave em https://console.anthropic.com. Cada pergunta custa
fracoes de centavo.

O selo no topo da conversa mostra qual motor esta ativo: **IA na nuvem**,
**IA local** ou **Modo basico**.

A conversa fica guardada por pessoa (tabela `chat_messages`) e ha um
botao **Limpar** para recomecar.

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

São **17 tabelas**:

| Tabela | O que guarda |
|---|---|
| `users` | as 3 categorias de acesso e a senha de cada uma |
| `active_sessions` | quem esta logado agora (uma linha por pessoa) |
| `authorized_emails` | quem pode entrar (e-mails e dominios liberados) |
| `api_keys` | uma chave de API por parceiro, guardada com hash |
| `api_calls` | quem chamou a API, quando, o que e o resultado |
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
- [x] **Fase 2** — banco de dados
- [x] **Fase 3** — login, autenticacao, permissoes e dashboard
- [x] **Fase 4** — todas as telas do prototipo funcionando
- [x] **Fase 5** — planilha, API, controle de acesso, identidade visual
- [x] **Fase 6** — assistente com aprendizado de maquina
- [x] **Fase 7** — auditoria de seguranca e correcao dos 12 pontos
- [x] **Fase 8** — telas de cadastrar, editar e excluir

**589 verificacoes automatizadas**, em 9 arquivos de teste.

### O que ficou de fora, e por que

Nada disso e falta de codigo: sao coisas que dependem de decisao de
negocio, de credenciais de terceiros ou de infraestrutura.

| O que falta | Do que depende |
|---|---|
| **Publicar num servidor** | decisao de onde hospedar (veja o aviso de LGPD no DEPLOY.md) |
| **Integracao com ICATU e corretora** | esses sistemas terem API, liberarem credenciais e passarem pela homologacao de seguranca. A **nossa** metade esta pronta: a Central publica e recebe |
| **Area do Participante** | autoatendimento; previsto para depois |
| **Envio real de e-mail** | o botao "Cobrar" marca no banco, mas nao dispara e-mail. Exige um servidor de envio (SMTP) configurado |
| **Login individual por pessoa** | hoje a senha e por categoria. Trocar e uma decisao de operacao, nao tecnica |
| **Cadastro de usuarios pela tela** | so faz sentido junto com o login individual |
| **Grafico de capital por mes** | nao temos dados historicos de capital, so de comissao |
| **Receber apolices e sinistros por API** | so a movimentacao tem endereco de recebimento hoje. Os outros 8 serao feitos quando o formato do parceiro for conhecido — construir antes seria adivinhar os nomes dos campos |

---

## Prototipo original

O arquivo `prototipo/Portal_Central_Inteligente_Seguros.html` e o prototipo
navegavel original, com 11 telas. Ele **nao deve ser alterado** — serve como
referencia visual enquanto convertemos cada tela.

Para ve-lo, basta abrir o arquivo com um duplo clique.
