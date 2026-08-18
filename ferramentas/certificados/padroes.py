#!/usr/bin/env python3
"""Agrupamento de PDFs por padrao de nomenclatura.

Ideia: num drive de rede, abrir cada PDF e o gargalo. Mas arquivos gerados pelo
mesmo processo compartilham o mesmo molde de nome ("CQ 4471.pdf", "CQ 4472.pdf",
"CQ 4473.pdf"). Reduzindo cada nome a uma ASSINATURA -- numeros e datas viram
marcadores -- os arquivos caem em poucos grupos. Basta decidir o grupo: quando o
proprio padrao ja e conclusivo, ninguem e aberto; quando e ambiguo, abre-se uma
AMOSTRA e o veredito vale para todo o grupo."""
import os
import re

from classificador import normalizar

MARC_DATA = "<data>"
MARC_NUM = "<n>"


def assinatura_nome(nome):
    """Reduz o nome do arquivo ao seu molde.

    'CQ_4471-2024.pdf' e 'CQ_4472-2024.pdf' -> 'cq <n>.pdf'
    """
    base, ext = os.path.splitext(nome)
    t = normalizar(base)
    # datas primeiro, senao viram uma sequencia de <n>
    t = re.sub(r"\b\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}\b", MARC_DATA, t)
    t = re.sub(r"\b(19|20)\d{2}\b", MARC_DATA, t)
    t = re.sub(r"\d+", MARC_NUM, t)
    # separadores e pontuacao viram espaco; letras e marcadores permanecem
    t = re.sub(r"[^a-z<>\s]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    # sequencias de marcadores repetidos colapsam num so
    t = re.sub(r"(?:<n>\s*)+", "<n> ", t)
    t = re.sub(r"(?:<data>\s*)+", "<data> ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return (t or "<so numeros>") + ext.lower()


def assinatura_pasta(pasta_rel):
    """Reduz o caminho da pasta ao seu molde, preservando os nomes textuais."""
    if not pasta_rel or pasta_rel == ".":
        return "<raiz>"
    partes = []
    for parte in re.split(r"[\\/]+", pasta_rel):
        if not parte:
            continue
        p = normalizar(parte)
        if re.fullmatch(r"(19|20)\d{2}", p):
            partes.append(MARC_DATA)
        elif re.fullmatch(r"[\d\s.-]+", p):
            partes.append(MARC_NUM)
        else:
            partes.append(re.sub(r"\d+", MARC_NUM, p).strip())
    return "/".join(partes) or "<raiz>"


def agrupar(registros):
    """registros: iteravel de (caminho, nome, pasta_rel).

    Retorna dict {(assin_nome, assin_pasta): [registros...]} com os grupos
    ordenados do maior para o menor.
    """
    grupos = {}
    for caminho, nome, pasta_rel in registros:
        chave = (assinatura_nome(nome), assinatura_pasta(pasta_rel))
        grupos.setdefault(chave, []).append((caminho, nome, pasta_rel))
    return dict(sorted(grupos.items(), key=lambda kv: -len(kv[1])))


def escolher_amostra(itens, quantidade):
    """Amostra espalhada pelo grupo (inicio, meio, fim), nao os N primeiros --
    pastas costumam estar ordenadas por data e os primeiros arquivos podem ser
    de uma fase antiga do processo."""
    n = len(itens)
    if quantidade >= n:
        return list(itens)
    if quantidade == 1:
        return [itens[n // 2]]
    passo = (n - 1) / (quantidade - 1)
    indices = sorted({int(round(i * passo)) for i in range(quantidade)})
    return [itens[i] for i in indices]
