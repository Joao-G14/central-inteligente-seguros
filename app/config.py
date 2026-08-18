"""
config.py
---------
Le as configuracoes do arquivo .env (que fica na raiz do projeto e NAO vai
para o GitHub).

Por que isso existe?
Regra basica de seguranca: senhas e chaves nao ficam escritas no codigo,
porque o codigo vai para o GitHub e a chave ficaria publica.

Aqui usamos um leitor de .env caseiro, de umas 10 linhas, para nao precisar
instalar mais nenhuma biblioteca.
"""

import os
from pathlib import Path

PASTA_RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_ENV = PASTA_RAIZ / ".env"


def _carregar_env() -> None:
    """Le o arquivo .env linha por linha e joga tudo nas variaveis de ambiente."""
    if not ARQUIVO_ENV.exists():
        return

    for linha in ARQUIVO_ENV.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()

        # pula linhas vazias, comentarios e linhas sem "="
        if not linha or linha.startswith("#") or "=" not in linha:
            continue

        chave, valor = linha.split("=", 1)
        # setdefault: se a variavel ja existir no sistema, ela tem prioridade
        os.environ.setdefault(chave.strip(), valor.strip())


_carregar_env()


def ler(chave: str, padrao: str = "") -> str:
    """Le uma configuracao. Se nao encontrar, devolve o valor padrao."""
    return os.environ.get(chave, padrao)


# ---------------------------------------------------------------
# CONFIGURACOES DO PROJETO
# ---------------------------------------------------------------
# Chave usada para assinar o cookie de sessao do login (Fase 3).
SECRET_KEY = ler("SECRET_KEY", "chave-insegura-apenas-para-desenvolvimento")

# A senha de cada CATEGORIA de acesso. Quem escolher a categoria na tela
# de login e digitar a senha correspondente entra — o e-mail e livre.
SENHA_ESTIPULANTE = ler("SENHA_ESTIPULANTE", "estipulante@sebraeprev")
SENHA_CORRETORA = ler("SENHA_CORRETORA", "corretora@sebraeprev")
SENHA_SEGURADORA = ler("SENHA_SEGURADORA", "seguradora@sebraeprev")

# Chave que outros sistemas usam para conversar com a nossa API.
# Quem nao mandar esta chave no cabecalho X-API-Key recebe "401 nao autorizado".
API_KEY = ler("API_KEY", "")

# --- Configuracoes que mudam entre o seu PC e o servidor ---
#
# AMBIENTE: "desenvolvimento" no seu computador, "producao" no servidor.
# Em producao o sistema exige HTTPS no cookie e nao mostra detalhes de erro.
AMBIENTE = ler("AMBIENTE", "desenvolvimento").lower()

EM_PRODUCAO = AMBIENTE == "producao"

# O cookie de sessao so deve viajar por HTTPS quando estiver no servidor.
# No seu computador o endereco e http://127.0.0.1, sem S, entao aqui fica
# desligado — senao o login nao funcionaria localmente.
COOKIE_SEGURO = EM_PRODUCAO

# Se True, o sistema cria as tabelas e carrega os dados iniciais sozinho
# ao ligar. E o que permite subir num servidor sem rodar comando nenhum.
CRIAR_BANCO_AO_INICIAR = ler("CRIAR_BANCO_AO_INICIAR", "sim").lower() in (
    "sim", "true", "1", "yes"
)
