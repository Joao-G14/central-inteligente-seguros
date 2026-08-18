"""
database.py
-----------
Este arquivo cuida da CONEXAO com o banco de dados.

Ele responde a 3 perguntas:
  1. Onde fica o arquivo do banco?      -> database/central.db
  2. Como abrir uma conversa com ele?   -> SessionLocal()
  3. Qual a "base" das tabelas?         -> class Base

Voce raramente vai precisar mexer aqui.
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ---------------------------------------------------------------
# 1. ONDE FICA O BANCO
# ---------------------------------------------------------------
# __file__ e este proprio arquivo (app/database.py).
# .parent    -> pasta app/
# .parent    -> pasta central-inteligente-seguros/  (a raiz do projeto)
PASTA_RAIZ = Path(__file__).resolve().parent.parent

PASTA_BANCO = PASTA_RAIZ / "database"
PASTA_BANCO.mkdir(exist_ok=True)  # cria a pasta se ela nao existir

ARQUIVO_BANCO = PASTA_BANCO / "central.db"

# O SQLAlchemy precisa do endereco no formato "sqlite:///caminho/do/arquivo.db"
URL_BANCO = f"sqlite:///{ARQUIVO_BANCO}"


# ---------------------------------------------------------------
# 2. O MOTOR (engine)
# ---------------------------------------------------------------
# O engine e quem realmente abre o arquivo .db.
#
# check_same_thread=False: o SQLite, por padrao, so aceita ser usado pela
# mesma "linha de execucao" que o abriu. O FastAPI atende varios pedidos ao
# mesmo tempo, entao precisamos desligar essa trava. E seguro aqui porque
# cada pedido usa a sua propria sessao (veja get_db abaixo).
engine = create_engine(
    URL_BANCO,
    connect_args={"check_same_thread": False},
    echo=False,  # mude para True se quiser VER no terminal todo SQL executado
)


# ---------------------------------------------------------------
# 3. A SESSAO (a "conversa" com o banco)
# ---------------------------------------------------------------
# Uma sessao e como abrir um caderno de rascunho: voce anota mudancas
# (add, delete) e so no commit() elas sao gravadas de verdade.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# ---------------------------------------------------------------
# 4. A BASE DAS TABELAS
# ---------------------------------------------------------------
# Toda tabela que criarmos em models.py vai herdar desta classe Base.
# E assim que o SQLAlchemy descobre quais tabelas existem no projeto.
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------
# 5. ATALHO PARA O FASTAPI (usaremos na Fase 3)
# ---------------------------------------------------------------
def get_db():
    """
    Abre uma sessao, entrega para quem pediu e SEMPRE fecha no final.

    O FastAPI chama esta funcao sozinho em cada pagina que precisa do banco.
    O "yield" entrega a sessao e pausa; quando a pagina termina, o codigo
    volta aqui e executa o db.close().
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def criar_tabelas():
    """Cria no arquivo .db todas as tabelas definidas em models.py."""
    from app import models  # noqa: F401  (importar registra as tabelas na Base)

    Base.metadata.create_all(bind=engine)
