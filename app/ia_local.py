"""
ia_local.py
-----------
A nossa IA, treinada aqui mesmo, rodando no seu computador.

O QUE ELA E — E O QUE NAO E
---------------------------
E um CLASSIFICADOR DE ASSUNTO. Dada uma pergunta, ela responde: "isto
aqui e sobre renovacoes" ou "isto e sobre inadimplencia". Depois o
sistema busca a resposta daquele assunto no banco.

Isso e aprendizado de maquina de verdade: ela aprende sozinha, a partir
dos exemplos em ia_treino.py, e acerta perguntas que nunca viu.

NAO e um modelo de linguagem como o ChatGPT. Ela nao escreve textos
novos nem raciocina em varias etapas. Ela reconhece o assunto e entrega
a resposta certa — que e exatamente o que este sistema precisa.

Vantagens sobre a IA paga:
  - roda offline, sem internet
  - custo zero por pergunta
  - os dados nao saem daqui (importante para a LGPD)
  - treina em menos de 1 segundo

COMO ELA FUNCIONA, EM 3 PASSOS
------------------------------
1. TRANSFORMAR TEXTO EM NUMEROS
   Computador nao entende palavra, so numero. O TF-IDF quebra a frase
   em pedacinhos e conta quais aparecem, dando mais peso aos pedacos
   raros (que distinguem melhor) e menos aos comuns ("de", "o", "que").

   Usamos DOIS jeitos de quebrar ao mesmo tempo:
     - por letras (2 a 5 seguidas): e o que faz "apolise" e "apolice"
       ficarem parecidos, tolerando erro de digitacao
     - por palavras (1 ou 2 seguidas): pega expressoes como
       "capital segurado" como uma coisa so

2. APRENDER
   A Regressao Logistica olha milhares desses numeros e descobre quais
   pedacos indicam cada assunto. Ninguem programa "se tem a palavra X
   entao e Y" — ela deduz isso dos exemplos.

3. RESPONDER COM UM GRAU DE CERTEZA
   Para cada pergunta nova ela devolve o assunto mais provavel E o
   quanto esta confiante. Se a confianca for baixa, preferimos dizer
   "nao entendi" a chutar uma resposta errada.
"""

from app import ia_treino

# A partir de qual confianca aceitamos a resposta do modelo.
# Abaixo disso, e mais honesto dizer que nao entendeu.
#
# Se ele estiver chutando demais, aumente. Se estiver dizendo "nao
# entendi" para perguntas boas, diminua.
CONFIANCA_MINIMA = 0.28

# O modelo treinado. Comeca vazio e e preenchido no primeiro uso.
_modelo = None
_pronto = False
_erro_do_treino = ""


def _treinar():
    """
    Monta e treina o modelo. Roda uma vez so, na primeira pergunta.

    Devolve o modelo pronto, ou None se a biblioteca nao estiver
    instalada — nesse caso o sistema cai para as palavras-chave.
    """
    global _erro_do_treino

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline, FeatureUnion
    except ImportError:
        _erro_do_treino = "biblioteca scikit-learn nao instalada"
        return None

    # --- separa as perguntas (X) dos assuntos (y) ---
    perguntas: list[str] = []
    assuntos: list[str] = []
    for assunto, frases in ia_treino.TREINO.items():
        for frase in frases:
            perguntas.append(_limpar(frase))
            assuntos.append(assunto)

    if not perguntas:
        _erro_do_treino = "nenhum exemplo de treino encontrado"
        return None

    # --- monta o modelo ---
    modelo = Pipeline([
        # Os dois jeitos de quebrar a frase, usados juntos.
        ("texto", FeatureUnion([
            # Por letras: tolera erro de digitacao.
            # char_wb respeita as bordas das palavras, o que funciona
            # melhor do que picar o texto inteiro sem criterio.
            ("letras", TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 5),
                sublinear_tf=True,
                min_df=1,
            )),
            # Por palavras: pega expressoes de duas palavras.
            ("palavras", TfidfVectorizer(
                analyzer="word",
                ngram_range=(1, 2),
                sublinear_tf=True,
                min_df=1,
            )),
        ])),
        # Quem de fato aprende.
        # C alto = confia mais nos exemplos; temos poucos e sao limpos.
        # class_weight balanced evita que assuntos com mais exemplos
        # engulam os que tem menos.
        ("classificador", LogisticRegression(
            C=8.0,
            max_iter=2000,
            class_weight="balanced",
        )),
    ])

    modelo.fit(perguntas, assuntos)
    return modelo


def _limpar(texto: str) -> str:
    """
    Deixa a frase no formato que o modelo aprendeu: minusculo, sem
    acento e sem pontuacao sobrando.

    Assim "Quantas APÓLICES?!" e "quantas apolices" viram a mesma coisa.
    """
    import unicodedata

    texto = (texto or "").strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")

    # troca pontuacao por espaco, mantendo letras, numeros e o hifen
    # (o hifen importa: AP-2041, SIN-0448)
    limpo = []
    for c in texto:
        limpo.append(c if (c.isalnum() or c in " -/") else " ")
    return " ".join("".join(limpo).split())


def preparar() -> bool:
    """
    Treina o modelo, se ainda nao foi treinado.

    Devolve True se a IA esta pronta para uso.
    """
    global _modelo, _pronto

    if _pronto:
        return _modelo is not None

    _modelo = _treinar()
    _pronto = True
    return _modelo is not None


def esta_disponivel() -> bool:
    """A IA local esta pronta para responder?"""
    return preparar()


def classificar(pergunta: str) -> tuple[str, float]:
    """
    Descobre o assunto de uma pergunta.

    Devolve DOIS valores:
      - o nome do assunto (ou "" se nao souber)
      - a confianca, de 0 a 1

    Quando a confianca fica abaixo de CONFIANCA_MINIMA, devolvemos
    assunto vazio: e melhor admitir que nao entendeu do que chutar.
    """
    if not preparar():
        return "", 0.0

    texto = _limpar(pergunta)
    if not texto:
        return "", 0.0

    probabilidades = _modelo.predict_proba([texto])[0]
    classes = _modelo.classes_

    melhor = int(probabilidades.argmax())
    assunto = classes[melhor]
    confianca = float(probabilidades[melhor])

    if confianca < CONFIANCA_MINIMA:
        return "", confianca

    return assunto, confianca


def top_assuntos(pergunta: str, quantos: int = 3) -> list[tuple[str, float]]:
    """
    Os assuntos mais provaveis, do mais para o menos provavel.

    Serve para investigar por que o modelo respondeu o que respondeu —
    util quando voces forem ajustar os exemplos de treino.
    """
    if not preparar():
        return []

    probabilidades = _modelo.predict_proba([_limpar(pergunta)])[0]
    classes = _modelo.classes_

    pares = sorted(zip(classes, probabilidades), key=lambda p: p[1], reverse=True)
    return [(assunto, float(p)) for assunto, p in pares[:quantos]]


def informacoes() -> dict:
    """Um resumo do modelo, para mostrar em diagnostico."""
    preparar()
    return {
        "disponivel": _modelo is not None,
        "erro": _erro_do_treino,
        "assuntos": ia_treino.total_de_assuntos(),
        "exemplos": ia_treino.total_de_exemplos(),
        "confianca_minima": CONFIANCA_MINIMA,
    }
