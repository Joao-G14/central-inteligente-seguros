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
| Python 3.14 | linguagem de programacao |
| FastAPI | cria as paginas e rotas do site |
| Uvicorn | servidor que coloca o site no ar |
| Jinja2 | monta o HTML com dados do banco |
| SQLAlchemy | conversa com o banco de dados |
| SQLite | o banco de dados (um arquivo local) |
| bcrypt | protege as senhas com hash |
| HTML / CSS / JavaScript | a interface (vinda do prototipo) |

---

## Estrutura de pastas

```
central-inteligente-seguros/
├── app/           # o codigo Python da aplicacao
├── templates/     # as paginas HTML
├── static/        # CSS, JavaScript e imagens
├── database/      # o arquivo central.db (nao vai para o GitHub)
├── sql/           # script para recriar o banco do zero
├── prototipo/     # o prototipo HTML original, intacto (referencia visual)
├── docs/          # documentacao do projeto (PRD, planilha, diagrama)
├── tests/         # testes
├── venv/          # ambiente virtual Python (nao vai para o GitHub)
├── requirements.txt
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

Isso cria as 3 tabelas e preenche com os dados ficticios (3 usuarios e
50 apolices). Pode rodar quantas vezes quiser — ele sempre refaz do zero.

Para conferir se deu tudo certo:

```powershell
python tests\test_banco.py
```

Devem aparecer 49 verificacoes com `[OK]`.

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
python tests\test_banco.py     # 49 verificacoes — banco e dados
python tests\test_login.py     # 49 verificacoes — login e permissoes
python tests\test_modulos.py   # 93 verificacoes — as 11 telas
```

Total: **191 verificacoes**. Nao precisa estar com o servidor ligado —
os testes sobem a aplicacao por dentro.

Rode sempre depois de mexer no codigo. Se aparecer `[FALHOU]`, a linha
diz exatamente o que quebrou.

---

## As telas do sistema

Todas as 11 telas do prototipo estao funcionando, lendo dados do banco.

| Endereco | Tela | O que mostra |
|---|---|---|
| `/login` | Entrada | 3 perfis, e-mail e senha |
| `/dashboard` | Dashboard | numeros da carteira + ultimos acessos |
| `/produtos` | Ramos / Produtos | ramo ativo (numeros reais) + roadmap |
| `/integracoes` | Integracoes (API) | como os dados chegam, hoje e no futuro |
| `/seguros` | Gestao de Seguros | 50 apolices, com busca |
| `/esteira` | Esteira de Apolices | quadro de propostas em 4 colunas |
| `/movimentacao` | Movimentacao & Pgto. | 10 segurados, convenios e boletos |
| `/comissoes` | Painel de Comissoes | divisao 10/15/75% + historico |
| `/inadimplencia` | Inadimplencia | regua de cobranca e devedores |
| `/sinistros` | Sinistros | sinistros em andamento |
| `/pendencias` | Pendencias | o que falta resolver |
| `/assistente` | Assistente | perguntas respondidas com o banco |

### Coisas que realmente funcionam (nao sao so telas)

- **Emitir boleto** — muda o status no banco e define o vencimento
- **Cobrar inadimplente** — marca a cobranca como enviada
- **Resolver / reabrir pendencia** — muda a situacao no banco
- **Exportar Excel** — baixa um `.csv` de verdade (movimentacao,
  inadimplencia e pendencias), ja no formato do Excel brasileiro
- **Busca nas tabelas** — filtra sem recarregar a pagina
- **Assistente** — consulta o banco na hora para responder

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

## Usuarios de teste

Todos ficticios, apenas para desenvolvimento:

| E-mail | Senha | Perfil |
|---|---|---|
| `estipulante@sebraeprev.com.br` | `estipulante@sebraeprev` | ESTIPULANTE |
| `corretora@sebraeprev.com.br` | `corretora@sebraeprev` | CORRETORA |
| `seguradora@sebraeprev.com.br` | `seguradora@sebraeprev` | SEGURADORA |

As senhas ficam no arquivo `.env` (que nao vai para o GitHub). Use o
`.env.example` como modelo para criar o seu.

No banco, as senhas sao guardadas como **hash bcrypt** — nunca em texto puro.

---

## As tabelas do banco

| Tabela | O que guarda |
|---|---|
| `users` | quem pode entrar: nome, e-mail, hash da senha, perfil |
| `login_history` | cada tentativa de acesso: quem, quando, de qual IP, deu certo ou nao |
| `policies` | a carteira de apolices (50 registros) |
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
- `gerado` — 32 apolices geradas para dar volume a carteira

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
| **ESTIPULANTE** | tudo |
| **CORRETORA** | tudo, **exceto** Sinistros |
| **SEGURADORA** | tudo, **exceto** Comissoes e Inadimplencia |

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
