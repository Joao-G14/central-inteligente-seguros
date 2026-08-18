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

# Senhas dos 3 usuarios ficticios de desenvolvimento.
# Os valores reais ficam no .env; o que esta aqui e so um plano B.
SENHA_ESTIPULANTE = ler("SENHA_ESTIPULANTE", "estipulante@sebraeprev")
SENHA_CORRETORA = ler("SENHA_CORRETORA", "corretora@sebraeprev")
SENHA_SEGURADORA = ler("SENHA_SEGURADORA", "seguradora@sebraeprev")
