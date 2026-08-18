#!/usr/bin/env python3
"""Heuristica de classificacao: dado o caminho e (opcionalmente) o texto de um
PDF, decide se o documento e um certificado de qualidade de material.

Sem dependencias externas. Usado por localizar_certificados.py e testavel
isoladamente via testar_classificador.py."""
import re
import unicodedata

# ---------------------------------------------------------------------------
# Termos. Peso alto = o termo praticamente define o documento.
# Peso de apoio = tipico de certificado de material, mas nao exclusivo.
# Peso negativo = indica outro tipo de documento (NF, cotacao, catalogo...).
# ---------------------------------------------------------------------------

TERMOS_FORTES = [
    (r"certificado\W+de\W+qualidade", 6),
    (r"certificado\W+de\W+materia\W*prima", 6),
    (r"certificado\W+de\W+material", 6),
    (r"certificado\W+de\W+inspecao", 5),
    (r"certificado\W+de\W+ensaio", 5),
    (r"certificado\W+de\W+rastreabilidade", 5),
    (r"certificado\W+de\W+analise", 4),
    (r"certificado\W+de\W+conformidade", 4),
    (r"certificado\W+do\W+fabricante", 4),
    (r"certificado\W+de\W+fabricacao", 4),
    (r"mill\W+test\W+certificate", 6),
    (r"material\W+test\W+report", 6),
    (r"inspection\W+certificate", 5),
    (r"quality\W+certificate", 5),
    (r"material\W+certificate", 5),
    (r"certificate\W+of\W+analysis", 4),
    (r"certificate\W+of\W+conformity", 4),
    (r"\ben\W*10204\b", 6),
    (r"\bnbr\W*15167\b", 3),
    (r"laudo\W+de\W+analise", 3),
    (r"laudo\W+tecnico", 3),
    (r"laudo\W+de\W+ensaio", 4),
    # siglas: so valem como token isolado, para nao casar dentro de palavras
    (r"\bmtc\b", 3),
    (r"\bmtr\b", 3),
    (r"\bcqm\b", 3),
    (r"\bc\W?q\b(?!\w)", 2),
]

TERMOS_APOIO = [
    (r"analise\W+quimica", 4),
    (r"composicao\W+quimica", 4),
    (r"chemical\W+composition", 4),
    (r"\bcomposicao\W+do\W+material\b", 3),
    (r"\bcarbono\W+equivalente\b", 3),
    (r"\bceq\b", 2),
    (r"propriedades\W+mecanicas", 3),
    (r"mechanical\W+propert", 3),
    (r"ensaio\W+de\W+tracao", 3),
    (r"tensile\W+(test|strength)", 3),
    (r"limite\W+de\W+escoamento", 3),
    (r"limite\W+de\W+resistencia", 3),
    (r"resistencia\W+a\W+tracao", 3),
    (r"\byield\W+(point|strength)\b", 2),
    (r"alongamento", 2),
    (r"ensaio\W+de\W+impacto", 2),
    (r"\bcharpy\b", 3),
    (r"dureza\W+(brinell|rockwell|vickers)", 3),
    (r"\b(hardness|brinell|rockwell|vickers)\b", 2),
    (r"numero\W+de\W+corrida", 3),
    (r"\bcorrida\b", 2),
    (r"heat\W+(number|no|n)\b", 3),
    (r"\bheat\W*#", 3),
    (r"rastreabilidade", 2),
    (r"\bastm\W*a?\d", 2),
    (r"\babnt\W+nbr\b", 2),
    (r"\baisi\W*\d", 2),
    (r"\bsae\W*\d", 2),
    (r"\bdin\W*\d", 2),
    (r"\basme\b", 1),
    (r"\bmetalurgic", 1),
    (r"siderurgic", 2),
    (r"\bfundicao\b", 1),
    (r"\blote\b", 1),
    (r"\bbatch\b", 1),
    (r"\bbitola\b", 1),
    (r"\bespessura\b", 1),
    (r"\btratamento\W+termico\b", 2),
    (r"\bnormalizado\b", 1),
    (r"\bzincado|galvaniz", 1),
]

TERMOS_NEGATIVOS = [
    (r"\bnota\W+fiscal\b", 3),
    (r"\bdanfe\b", 5),
    (r"\bboleto\b", 5),
    (r"\bcotacao\b", 3),
    (r"\borcamento\b", 3),
    (r"\bproposta\W+comercial\b", 4),
    (r"\bpedido\W+de\W+compra\b", 3),
    (r"\bordem\W+de\W+compra\b", 3),
    (r"\bromaneio\b", 3),
    (r"\bconhecimento\W+de\W+transporte\b", 4),
    (r"\bcte\b", 2),
    (r"\bfispq\b", 4),
    (r"ficha\W+de\W+informacoes\W+de\W+seguranca", 4),
    (r"\biso\W*9001\b", 3),
    (r"\biso\W*14001\b", 3),
    (r"certificado\W+digital", 5),
    (r"certificado\W+de\W+garantia", 3),
    (r"certificado\W+de\W+(participacao|conclusao)", 5),
    (r"\bcurriculo\b", 5),
    (r"manual\W+(de\W+)?(instrucoes|do\W+usuario|operacao)", 4),
    (r"\bcatalogo\b", 3),
    (r"\bfolder\b", 2),
    (r"\bcontrato\W+social\b", 4),
    (r"\bcnd\b", 3),
    (r"certidao\W+negativa", 4),
    (r"\bdesenho\W+tecnico\b", 2),
]

# Termos que caracterizam OUTRO tipo de documento de forma praticamente
# inequivoca. Um veto derruba o resultado para NAO, a menos que haja termo
# exclusivo de material ou evidencia tecnica suficiente (score de apoio).
VETOS = {
    r"\bdanfe\b",
    r"\bnota\W+fiscal\b",
    r"\bboleto\b",
    r"\bfispq\b",
    r"ficha\W+de\W+informacoes\W+de\W+seguranca",
    r"\biso\W*9001\b",
    r"\biso\W*14001\b",
    r"certificado\W+digital",
    r"certificado\W+de\W+(participacao|conclusao)",
    r"\bcurriculo\b",
    r"certidao\W+negativa",
    r"\bcnd\b",
    r"manual\W+(de\W+)?(instrucoes|do\W+usuario|operacao)",
    r"\bcatalogo\b",
    r"\bcontrato\W+social\b",
    r"\bconhecimento\W+de\W+transporte\b",
    r"\bproposta\W+comercial\b",
    r"\bromaneio\b",
    r"\bcotacao\b",
    r"\borcamento\b",
}

# Termos fortes que só aparecem em certificado de material -- imunes ao veto.
EXCLUSIVOS_MATERIAL = {
    r"certificado\W+de\W+qualidade",
    r"certificado\W+de\W+materia\W*prima",
    r"certificado\W+de\W+material",
    r"certificado\W+de\W+rastreabilidade",
    r"certificado\W+de\W+ensaio",
    r"mill\W+test\W+certificate",
    r"material\W+test\W+report",
    r"material\W+certificate",
    r"\ben\W*10204\b",
    r"laudo\W+de\W+ensaio",
    r"\bmtc\b",
    r"\bmtr\b",
    r"\bcqm\b",
}

# Peso extra quando o termo aparece no nome do arquivo ou no caminho da pasta:
# nome de arquivo e muito mais diagnostico que uma mencao perdida no corpo.
MULT_NOME = 2.0
MULT_PASTA = 1.5
MULT_CONTEUDO = 1.0

# Simbolos de elementos tipicos da tabela de composicao quimica de aco.
# A presenca conjunta de varios deles com valores decimais e o sinal mais
# discriminante de um certificado de material -- vale mais que qualquer
# palavra-chave, porque sobrevive a nomes de arquivo genericos.
ELEMENTOS = ["c", "si", "mn", "p", "s", "cr", "ni", "mo", "cu", "al", "nb",
             "v", "ti", "b", "n", "sn", "w", "co", "mg", "ca", "ceq", "ce"]

_CACHE = {}


def _rx(padrao):
    if padrao not in _CACHE:
        _CACHE[padrao] = re.compile(padrao)
    return _CACHE[padrao]


def normalizar(texto):
    """Minusculas, sem acentos, espacos colapsados."""
    if not texto:
        return ""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    # "_" e caractere de palavra para o regex: viraria barreira em \b e \W+
    # ("CQ_barra", "mill_test_certificate"). Tratar como separador.
    t = t.replace("_", " ")
    return re.sub(r"[\s]+", " ", t)


def detectar_tabela_composicao(texto):
    """Procura uma tabela de composicao quimica no texto ja normalizado.

    Exige varios simbolos de elemento como tokens isolados MAIS valores
    decimais no formato tipico de percentual de liga (0,18 / 0.045), para nao
    disparar com letras soltas de um texto qualquer.

    Retorna (peso, elementos_encontrados).
    """
    if not texto:
        return 0.0, []
    achados = [e for e in ELEMENTOS
               if _rx(rf"(?<![a-z0-9]){e}(?![a-z0-9])").search(texto)]
    decimais = len(_rx(r"\b[01][.,]\d{2,4}\b").findall(texto))
    if len(achados) >= 5 and decimais >= 3:
        return 6.0, achados
    if len(achados) >= 4 and decimais >= 2:
        return 4.0, achados
    if len(achados) >= 3 and decimais >= 2:
        return 2.0, achados
    return 0.0, achados


def _pontuar(texto, termos, multiplicador):
    total = 0.0
    achados = []
    for padrao, peso in termos:
        if _rx(padrao).search(texto):
            total += peso * multiplicador
            achados.append(padrao)
    return total, achados


def _rotulo(padrao):
    """Versao legivel do regex, para a coluna de termos encontrados."""
    r = re.sub(r"\\W[*+?]?", " ", padrao)
    r = re.sub(r"\\b|\\d|[()?*+#]|\[[^\]]*\]", "", r)
    r = r.replace("|", "/")
    return re.sub(r"\s+", " ", r).strip()


def classificar(nome_arquivo, caminho_pasta="", conteudo=None, tem_texto=True):
    """Retorna dict com score, classificacao, termos e observacao.

    classificacao:
      CERTIFICADO - alta confianca
      PROVAVEL    - provavelmente sim, conferir
      REVISAR     - sinais fracos/ambiguos
      NAO         - nao parece certificado de material
    """
    n_nome = normalizar(nome_arquivo)
    n_pasta = normalizar(caminho_pasta)
    n_conteudo = normalizar(conteudo) if conteudo else ""

    forte = apoio = negativo = 0.0
    achados_forte, achados_apoio, achados_neg = [], [], []

    for texto, mult in ((n_nome, MULT_NOME), (n_pasta, MULT_PASTA),
                        (n_conteudo, MULT_CONTEUDO)):
        if not texto:
            continue
        p, a = _pontuar(texto, TERMOS_FORTES, mult)
        forte += p
        achados_forte += a
        p, a = _pontuar(texto, TERMOS_APOIO, mult)
        apoio += p
        achados_apoio += a
        p, a = _pontuar(texto, TERMOS_NEGATIVOS, mult)
        negativo += p
        achados_neg += a

    peso_tabela, elementos = detectar_tabela_composicao(n_conteudo)
    forte += peso_tabela

    # Negativos so derrubam quando nao ha indicio forte de certificado:
    # um certificado legitimo costuma citar o numero da NF ou do pedido.
    peso_neg = negativo if forte < 4 else negativo * 0.3
    score = forte + apoio - peso_neg

    if forte >= 8:
        classe = "CERTIFICADO"
    elif forte >= 4 and apoio >= 3:
        classe = "CERTIFICADO"
    elif forte >= 4:
        classe = "PROVAVEL"
    elif forte >= 2 and apoio >= 4:
        classe = "PROVAVEL"
    elif apoio >= 8:
        classe = "PROVAVEL"
    elif forte >= 2 or apoio >= 4:
        classe = "REVISAR"
    else:
        classe = "NAO"

    tem_veto = any(p in VETOS for p in achados_neg)
    exclusivo = (any(p in EXCLUSIVOS_MATERIAL for p in achados_forte)
                 or peso_tabela >= 6)

    if tem_veto and not exclusivo and apoio < 4:
        classe = "NAO"
    elif classe in ("PROVAVEL", "REVISAR") and peso_neg >= 6 and forte < 4:
        classe = "REVISAR" if classe == "PROVAVEL" else "NAO"

    obs = ""
    if not tem_texto:
        obs = ("PDF sem texto extraivel (provavel digitalizacao) - avaliado so "
               "pelo nome/pasta; rode OCR para confirmar")
        # Sem texto, o nome e a unica prova: promover a REVISAR para nao perder
        # certificado digitalizado. Mas se o nome ja denuncia outro documento
        # (nota fiscal, manual, catalogo), NAO continua valendo.
        if classe == "NAO" and not tem_veto:
            classe = "REVISAR"
    elif conteudo is None:
        obs = "Avaliado apenas pelo nome/pasta (leitura de conteudo desativada)"

    termos = sorted({_rotulo(p) for p in achados_forte + achados_apoio})
    if peso_tabela:
        termos.insert(0, "tabela de composicao quimica ("
                      + ",".join(elementos[:10]) + ")")
    contra = sorted({_rotulo(p) for p in achados_neg})

    return {
        "score": round(score, 1),
        "score_forte": round(forte, 1),
        "score_apoio": round(apoio, 1),
        "score_negativo": round(negativo, 1),
        "classificacao": classe,
        # veto=True: o nome/texto identifica outro tipo de documento. Distingue
        # "NAO porque e uma nota fiscal" de "NAO porque o nome nada diz" -- so o
        # primeiro dispensa abrir o arquivo.
        "veto": tem_veto,
        "exclusivo": exclusivo,
        "termos": "; ".join(termos[:12]),
        "termos_contra": "; ".join(contra[:8]),
        "obs": obs,
    }
