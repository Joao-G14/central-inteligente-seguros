# Criar um agente no Copilot Studio

Guia para fazer o Microsoft Copilot responder perguntas sobre a Central.

---

## Antes de tudo: entenda o que muda

Nao e a mesma coisa que o assistente do site.

| | Assistente do site | Agente no Copilot Studio |
|---|---|---|
| Onde a pessoa conversa | na tela `/assistente` | no Teams, ou embutido no site |
| Quem responde | Claude, chamado pelo nosso codigo | o Copilot, chamando a nossa API |
| Precisa do sistema publicado | nao | **sim, obrigatorio** |
| Precisa do admin do M365 | nao | **sim** |
| Cobranca | Anthropic ou Azure | licenca/creditos do Copilot Studio |

Os dois podem coexistir. A API que alimenta o agente e a mesma que ja
existe no projeto.

---

## O bloqueio principal

**O Copilot Studio nao alcanca o seu computador.**

Ele roda na nuvem da Microsoft e so consegue chamar enderecos publicos
na internet, com HTTPS. Enquanto a Central estiver em
`http://127.0.0.1:8000`, nao ha como conectar.

Entao a ordem e:

1. publicar a Central num servidor (veja o **DEPLOY.md**)
2. so depois criar o agente

Nao ha atalho para isso.

---

## Passo 1 — Publicar a Central

Siga o `DEPLOY.md`. Ao final voce tera um endereco parecido com:

```
https://central-inteligente-seguros.onrender.com
```

Confira se a API responde. No navegador, abra:

```
https://seu-endereco/docs
```

Deve aparecer a documentacao automatica da API.

---

## Passo 2 — Gerar o arquivo de descricao da API

O Copilot Studio precisa de um arquivo que descreva o que a nossa API
faz. O projeto ja tem um script que gera esse arquivo pronto:

```powershell
python gerar_openapi.py https://seu-endereco-publico
```

Isso cria o **`openapi-central.json`** na pasta do projeto. E esse
arquivo que voce vai enviar a Microsoft.

O script cuida de tres detalhes que dariam problema:

- tira as 32 telas HTML do site, deixando so os 9 enderecos da API
- grava na versao 3.0 do OpenAPI, que e a que a Power Platform aceita
  (o FastAPI gera 3.1 por padrao)
- declara a chave `X-API-Key` como metodo de autenticacao, para o
  Copilot pedir a chave uma vez so, e nao a cada acao

---

## Passo 3 — Criar o conector

No **Power Apps** (make.powerapps.com), na area de conectores
personalizados, crie um novo conector **importando o
`openapi-central.json`**.

Na configuracao de seguranca, escolha **chave de API**:

| Campo | Valor |
|---|---|
| Tipo | API Key |
| Nome do parametro | `X-API-Key` |
| Local | Cabecalho (Header) |

A chave em si e o valor de `API_KEY` que voce cadastrou nas variaveis
de ambiente do servidor.

> Os nomes dos menus da Microsoft mudam com frequencia. Se algum nao
> bater com o que esta escrito aqui, procure pelo termo equivalente —
> a sequencia (importar arquivo, configurar autenticacao, testar) e
> sempre a mesma.

---

## Passo 4 — Criar o agente

No **Copilot Studio** (copilotstudio.microsoft.com):

1. crie um agente novo
2. em conhecimento/acoes, adicione o conector criado no passo 3
3. escreva as instrucoes do agente

Sugestao de instrucoes, adaptando o que ja usamos no assistente do site:

```
Voce e o assistente da Central Inteligente de Seguros, o sistema que o
Sebrae Previdencia usa para administrar o seguro de risco (morte e
invalidez) com a corretora e a seguradora ICATU.

Responda apenas sobre a operacao de seguros: apolices, renovacoes,
capital segurado, premios, sinistros, inadimplencia, comissoes,
pagamentos, propostas e pendencias.

SEMPRE use as acoes disponiveis para buscar os numeros antes de
responder. Nunca invente valores, nomes ou datas. Se uma acao devolver
lista vazia, diga que nao ha registros.

Responda em portugues do Brasil, de forma direta. Valores em reais no
padrao brasileiro (R$ 1.234,56) e datas em dd/mm/aaaa.

Se perguntarem algo fora desse escopo, recuse com educacao e diga quais
assuntos voce cobre.
```

---

## Passo 5 — Publicar o agente

O Copilot Studio permite publicar em varios lugares:

| Canal | O que acontece |
|---|---|
| **Teams / M365 Copilot** | as pessoas perguntam no chat que ja usam |
| **Site** | ele gera um codigo para embutir um chat na pagina |
| Outros | e-mail, WhatsApp e outros, conforme a licenca |

Se publicar no site, da para colocar o chat do Copilot **ao lado** do
assistente que ja existe, ou substituir um pelo outro.

---

## O que perguntar ao TI antes de comecar

1. **Existe licenca de Copilot Studio?** E separada da licenca do
   Microsoft 365 Copilot. Confirme qual vocês tem.
2. **Quem aprova a criacao de conectores personalizados?** Costuma ser
   controlado pelo administrador da Power Platform.
3. **A Seguranca da Informacao autoriza a Central ser chamada de fora?**
   Isso e uma decisao de governanca, nao de programacao.
4. **Onde a Central pode ficar hospedada?** Veja o aviso de LGPD no
   comeco do DEPLOY.md.

---

## Se der problema

### O conector nao importa o arquivo
Confirme que o `openapi-central.json` foi gerado pelo script deste
projeto, e nao baixado direto de `/openapi.json`. O arquivo baixado
direto vem na versao 3.1 e com as telas HTML dentro.

### O agente responde "nao consegui acessar"
Teste a API por fora primeiro. Num terminal:

```powershell
curl.exe -H "X-API-Key: SUA_CHAVE" https://seu-endereco/api/v1/status
```

Se isso nao responder, o problema e no servidor, nao no Copilot.

### O agente inventa numeros
Reforce nas instrucoes que ele deve SEMPRE usar as acoes antes de
responder, e nunca completar com dados proprios.

### O agente pede a chave a cada pergunta
O arquivo foi gerado errado, ou a autenticacao do conector nao ficou
como chave de API no cabecalho. Refaca o passo 3.
