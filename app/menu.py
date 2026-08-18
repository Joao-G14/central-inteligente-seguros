"""
menu.py
-------
A lista de modulos que aparece no menu lateral.

Isto aqui e so uma LISTA DE DADOS, sem nenhuma logica. Ficou em arquivo
separado para o main.py nao ficar gigante e porque, a cada modulo que
voces converterem na Fase 4, so precisam mexer neste arquivo:
trocar "pronto": False por "pronto": True.

Os modulos e os icones foram copiados do menu do prototipo, na mesma ordem.

Significado de cada campo:
  chave  -> nome curto usado no codigo e nas permissoes (veja auth.py)
  titulo -> o texto que aparece na tela
  url    -> para onde o link leva
  icone  -> o desenho SVG do prototipo
  pronto -> True se o modulo ja funciona; False mostra a pagina "em breve"
"""

MENU = [
    {
        "chave": "dashboard",
        "titulo": "Dashboard",
        "url": "/dashboard",
        "icone": '<rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/>',
        "pronto": True,
    },
    {
        "chave": "produtos",
        "titulo": "Ramos / Produtos",
        "url": "/produtos",
        "icone": '<path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-14L4 7m8 4v10M4 7v10l8 4"/>',
        "pronto": True,
    },
    {
        "chave": "integracoes",
        "titulo": "Integrações (API)",
        "url": "/integracoes",
        "icone": '<path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/>',
        "pronto": True,
    },
    {
        "chave": "seguros",
        "titulo": "Gestão de Seguros",
        "url": "/seguros",
        "icone": '<path d="M12 3l7 3v6c0 4-3 7-7 9-4-2-7-5-7-9V6z"/>',
        "pronto": True,
    },
    {
        "chave": "esteira",
        "titulo": "Esteira de Apólices",
        "url": "/esteira",
        "icone": '<rect x="3" y="4" width="4" height="16"/><rect x="10" y="4" width="4" height="10"/><rect x="17" y="4" width="4" height="13"/>',
        "pronto": True,
    },
    {
        "chave": "movimentacao",
        "titulo": "Movimentação & Pgto.",
        "url": "/movimentacao",
        "icone": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
        "pronto": True,
    },
    {
        "chave": "comissoes",
        "titulo": "Painel de Comissões",
        "url": "/comissoes",
        "icone": '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
        "pronto": True,
    },
    {
        "chave": "inadimplencia",
        "titulo": "Inadimplência",
        "url": "/inadimplencia",
        "icone": '<path d="M1 4h22v16H1z"/><line x1="1" y1="10" x2="23" y2="10"/><line x1="5" y1="15" x2="9" y2="15"/>',
        "pronto": True,
    },
    {
        "chave": "sinistros",
        "titulo": "Sinistros",
        "url": "/sinistros",
        "icone": '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12" y2="17"/>',
        "pronto": True,
    },
    {
        "chave": "pendencias",
        "titulo": "Pendências",
        "url": "/pendencias",
        "icone": '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/>',
        "pronto": True,
    },
    {
        "chave": "assist",
        # O prototipo chamava de "Assistente IA". Trocamos para so
        # "Assistente" porque o nosso responde por palavras-chave, nao
        # por inteligencia artificial — chamar de IA seria enganoso.
        "titulo": "Assistente ★",
        "url": "/assistente",
        "icone": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
        "pronto": True,
    },
]


def buscar_modulo(chave: str) -> dict | None:
    """Acha um modulo do menu pela chave. Devolve None se nao existir."""
    for item in MENU:
        if item["chave"] == chave:
            return item
    return None
