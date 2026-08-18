# Como colocar a Central no ar

Guia passo a passo para publicar o sistema em um servidor.

---

## ⚠️ Leia isto antes de tudo

A documentacao do projeto fala em **LGPD** e em **ambiente Microsoft
homologado**. Isso muda a decisao:

| Se o objetivo e... | Entao... |
|---|---|
| **Demonstrar** o sistema (banca, diretoria, colegas) | Pode usar um servico gratuito da internet. Os dados sao ficticios. |
| **Usar de verdade**, com dados de participantes reais | **Nao pode** ser um servico gratuito qualquer. Precisa ir para a infraestrutura homologada do Sebrae Previdencia, com aval da Seguranca da Informacao. |

**Converse com seu gestor antes de subir dados reais em qualquer lugar.**
Este guia cobre o caminho de **demonstracao**.

---

## O que voce vai precisar

- A conta do GitHub (ja tem)
- Uma conta no Render (gratuita, criada com o proprio GitHub)
- 15 minutos

---

## Passo 1 — Criar a conta no Render

1. Abra https://render.com
2. Clique em **Get Started** e depois em **GitHub**
3. Autorize o Render a ver os seus repositorios

---

## Passo 2 — Publicar

O projeto ja tem o arquivo `render.yaml`, que ensina o Render a montar
tudo sozinho.

1. No painel do Render, clique em **New +** → **Blueprint**
2. Escolha o repositorio **central-inteligente-seguros**
3. O Render le o `render.yaml` e mostra o que vai criar
4. Ele vai **pedir 3 senhas**. Preencha:

| Campo | O que colocar |
|---|---|
| `SENHA_ESTIPULANTE` | uma senha nova, sua |
| `SENHA_CORRETORA` | outra senha |
| `SENHA_SEGURADORA` | outra senha |

> ⚠️ **Nao repita as senhas de desenvolvimento** (`estipulante@sebraeprev`
> etc.). Elas estao no `.env.example`, que e publico dentro do repositorio.
> Escolha senhas novas, so suas.

5. Clique em **Apply**

Em 3 a 5 minutos o site fica no ar, num endereco como:

```
https://central-inteligente-seguros.onrender.com
```

O `SECRET_KEY` e o `API_KEY` sao sorteados pelo proprio Render — voce
nao precisa inventar.

---

## Passo 3 — Primeiro acesso

Abra o endereco e entre com:

- **Categoria:** Estipulante
- **E-mail:** o seu e-mail
- **Senha:** a `SENHA_ESTIPULANTE` que voce definiu

Va em **Controle de Acesso** e **ligue a exigencia da lista**. O dominio
`@sebraeprev.com.br` ja vem cadastrado, entao voce continua entrando.

---

## ⚠️ Passo 4 — O ponto mais importante deste guia

**No plano gratuito, o disco e apagado a cada reinicio.**

O Render desliga o servico depois de 15 minutos sem acesso. Quando ele
volta, o arquivo `database/central.db` **nao existe mais** — o sistema
recria do zero.

Na pratica isso significa que **some**:

- a planilha que voce enviou
- os e-mails que voce autorizou
- os boletos que voce emitiu
- as pendencias que voce resolveu
- o historico de acessos

Para **demonstrar**, isso nao atrapalha: o sistema volta sempre bonito,
com a carteira de exemplo.

Para **usar de verdade**, nao serve. As saidas sao:

| Saida | O que envolve |
|---|---|
| **Disco persistente** | Planos pagos do Render oferecem um disco que sobrevive aos reinicios. Confira os planos atuais no site deles. |
| **Banco PostgreSQL** | Trocar o SQLite por um banco de verdade, que fica fora do servidor. Exige mudar 1 linha em `app/database.py` e instalar um driver. |
| **Servidor do Sebrae** | O caminho correto para dados reais, conforme a governanca. |

Quando chegar a hora, me chame que eu ajudo na migracao.

---

## Passo 5 — Quando for usar com dados reais

Enquanto for demonstracao, deixe como esta. Quando for comecar a usar de
verdade, mude **uma** configuracao no painel do Render:

**Environment** → `CARREGAR_DADOS_DEMO` → troque `sim` por **`nao`**

Com isso, o sistema sobe **vazio**: so as 3 categorias de acesso, sem
nenhuma apolice inventada. A carteira entra pela planilha ou pela API.

> Isso so vale para um banco novo. Se ja houver dados, nada e apagado.

---

## As configuracoes explicadas

Ficam no painel do Render, em **Environment**:

| Configuracao | Para que serve |
|---|---|
| `AMBIENTE` | `producao` liga a exigencia de HTTPS no cookie de sessao |
| `SECRET_KEY` | assina o cookie de login. Se trocar, todo mundo e deslogado |
| `API_KEY` | a chave que sistemas parceiros usam na API |
| `SENHA_ESTIPULANTE` | senha da categoria Estipulante |
| `SENHA_CORRETORA` | senha da categoria Corretora |
| `SENHA_SEGURADORA` | senha da categoria Seguradora |
| `CARREGAR_DADOS_DEMO` | `sim` sobe com a carteira de exemplo; `nao` sobe vazio |
| `CRIAR_BANCO_AO_INICIAR` | deixe `sim`: cria as tabelas sozinho |

Mudou alguma? O Render reinicia o servico sozinho.

---

## Como enviar uma atualizacao depois

Toda vez que voce enviar codigo novo para o GitHub, o Render publica
sozinho:

```powershell
git add -A
git commit -m "descreva o que mudou"
git push
```

Em poucos minutos a versao nova esta no ar. Acompanhe em **Logs**, no
painel do Render.

---

## Se der problema

### O site demora 50 segundos para abrir
Normal no plano gratuito: o servico estava dormindo. Se for demonstrar
para alguem, **abra o site 1 minuto antes**.

### O build falhou por causa da versao do Python
O arquivo `.python-version` pede a versao `3.12.11`. Se o Render reclamar
que ela nao existe, abra o arquivo e troque por outra versao 3.12 ou 3.13
disponivel.

### O login nao funciona no servidor, mas funciona no seu PC
Confira se `AMBIENTE` esta como `producao` e se o endereco comeca com
`https://`. O cookie de sessao so trafega por HTTPS em producao.

### "Internal Server Error" em alguma tela
Abra **Logs** no painel do Render e procure a palavra `Error`. A ultima
linha costuma dizer exatamente o que faltou.

### Esqueci as senhas que cadastrei
Va em **Environment** no painel do Render, troque o valor e salve. O
servico reinicia com a senha nova.

---

## Rodando localmente (relembrando)

```powershell
cd central-inteligente-seguros
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

http://127.0.0.1:8000
