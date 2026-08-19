"""
gerar_openapi.py
----------------
Gera o arquivo que voce sobe no Copilot Studio (ou em qualquer outra
ferramenta que consuma a nossa API).

PARA QUE SERVE
--------------
O Copilot Studio nao adivinha o que a nossa API faz. Ele le um arquivo
de especificacao — o padrao se chama OpenAPI — que descreve cada
endereco, cada parametro e cada resposta. A partir dele, o Copilot
monta as "acoes" que o agente pode executar.

O FastAPI ja gera essa especificacao sozinho, em /openapi.json. Mas ela
vem com dois problemas para este uso:

  1. inclui as ~32 telas HTML do site (login, dashboard, etc.), que nao
     interessam a um agente e so atrapalham
  2. usa a versao 3.1 do OpenAPI, e os conectores da Power Platform
     costumam pedir a versao 3.0

Este script resolve os dois: filtra so os enderecos /api/v1 e grava na
versao 3.0.

COMO USAR
---------
    python gerar_openapi.py

Ele cria o arquivo  openapi-central.json  na raiz do projeto.
E esse arquivo que voce envia ao Copilot Studio.

Se o sistema ja estiver publicado num servidor, passe o endereco:

    python gerar_openapi.py https://central.seudominio.com.br
"""

import json
import sys
from pathlib import Path

from app.main import app

# Onde o arquivo sera gravado.
ARQUIVO = Path(__file__).parent / "openapi-central.json"

# Endereco do servidor. O Copilot precisa saber para onde mandar os
# pedidos. Enquanto voces estiverem testando local, fica o 127.0.0.1 —
# mas atencao: o Copilot Studio NAO alcanca o seu computador. Para
# valer, o sistema precisa estar publicado na internet.
ENDERECO_PADRAO = "http://127.0.0.1:8000"


def gerar(endereco: str) -> dict:
    """Monta a especificacao limpa, so com os enderecos da API."""
    completa = app.openapi()

    # --- 1. fica so com /api/v1 ---
    caminhos = {
        rota: definicao
        for rota, definicao in completa["paths"].items()
        if rota.startswith("/api/v1")
    }

    # --- 1b. tira o x-api-key da lista de parametros ---
    # O FastAPI mostra o cabecalho X-API-Key como se fosse um parametro
    # comum, porque no codigo ele e lido com Header(). Mas mais abaixo ja
    # declaramos ele como o metodo de AUTENTICACAO.
    #
    # Se deixassemos os dois, o Copilot Studio pediria a chave em toda
    # acao, uma por uma. Tirando daqui, ele pergunta uma vez so, na hora
    # de criar a conexao — que e como deve ser.
    for definicao in caminhos.values():
        for operacao in definicao.values():
            if "parameters" in operacao:
                operacao["parameters"] = [
                    p for p in operacao["parameters"]
                    if p.get("name", "").lower() != "x-api-key"
                ]
                if not operacao["parameters"]:
                    del operacao["parameters"]

    # --- 2. descobre quais "modelos de dados" essas rotas usam ---
    # A especificacao tem uma secao de componentes com o formato de cada
    # objeto. Trazemos todos: sao poucos e evita referencia quebrada.
    componentes = completa.get("components", {})

    # --- 3. declara como se autentica ---
    # Isto diz ao Copilot Studio: "mande a chave no cabecalho X-API-Key".
    # Sem esta parte, ele tentaria chamar sem chave e levaria 401.
    componentes["securitySchemes"] = {
        "ChaveDaAPI": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "A chave definida em API_KEY, no arquivo .env do servidor.",
        }
    }

    return {
        # Versao 3.0: e a que os conectores da Power Platform aceitam.
        # O FastAPI gera 3.1 por padrao, que e mais nova e pode nao importar.
        "openapi": "3.0.3",
        "info": {
            "title": "Central Inteligente de Seguros",
            "description": (
                "API da Central de Seguros do Sebrae Previdência. "
                "Permite consultar apólices, movimentação, sinistros, comissões "
                "e inadimplência, e receber a movimentação mensal enviada pela "
                "corretora.\n\n"
                "Todo pedido precisa enviar o cabeçalho X-API-Key."
            ),
            "version": "1.0.0",
        },
        "servers": [{"url": endereco, "description": "Central de Seguros"}],
        # Aplica a exigencia da chave em TODOS os enderecos de uma vez.
        "security": [{"ChaveDaAPI": []}],
        "paths": caminhos,
        "components": componentes,
    }


def main() -> None:
    endereco = sys.argv[1] if len(sys.argv) > 1 else ENDERECO_PADRAO
    endereco = endereco.rstrip("/")

    especificacao = gerar(endereco)

    ARQUIVO.write_text(
        json.dumps(especificacao, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("=== ARQUIVO GERADO ===")
    print(f"  {ARQUIVO}")
    print(f"  tamanho: {ARQUIVO.stat().st_size / 1024:.1f} KB")
    print()
    print(f"  endereco do servidor: {endereco}")
    print(f"  enderecos incluidos : {len(especificacao['paths'])}")
    for rota in sorted(especificacao["paths"]):
        metodos = ", ".join(m.upper() for m in especificacao["paths"][rota])
        print(f"    {metodos:<6} {rota}")

    print()
    if endereco.startswith("http://127.0.0.1") or endereco.startswith("http://localhost"):
        print("  ATENCAO: o endereco aponta para o SEU COMPUTADOR.")
        print("  O Copilot Studio nao consegue alcancar esse endereco.")
        print("  Publique o sistema (veja DEPLOY.md) e rode de novo assim:")
        print("      python gerar_openapi.py https://seu-endereco-publico")
    else:
        print("  Pronto para enviar ao Copilot Studio.")
    print()


if __name__ == "__main__":
    main()
