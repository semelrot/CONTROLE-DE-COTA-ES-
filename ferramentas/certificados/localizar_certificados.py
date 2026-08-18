#!/usr/bin/env python3
"""Varre um diretorio (ex.: Y:\\) em busca de PDFs que sejam certificados de
qualidade de material e gera um CSV classificado.

Uso tipico no Windows:
    py ferramentas\\certificados\\localizar_certificados.py -r "Y:\\" -s certificados.csv

Modo padrao (--por-padrao, recomendado em drive de rede): agrupa os PDFs por
padrao de nomenclatura e decide o grupo inteiro de uma vez. Quando o proprio
nome ja e conclusivo, nenhum arquivo daquele padrao e aberto; quando e ambiguo,
abre-se apenas uma amostra e o veredito vale para todo o grupo.

A leitura de conteudo usa pypdf quando disponivel (pip install pypdf). Sem a
biblioteca, a classificacao usa apenas nome de arquivo e caminho de pasta.
"""
import argparse
import csv
import os
import sys
import time
import concurrent.futures as cf
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classificador import classificar          # noqa: E402
from padroes import agrupar, escolher_amostra  # noqa: E402

# Importacao tolerante: uma instalacao parcial do pypdf (ex.: dependencia
# "cryptography" quebrada) levanta erro que nao e ImportError e derrubaria a
# ferramenta. Preferimos degradar para o modo nome/pasta.
PdfReader = None
LEITOR = None
ERRO_LEITOR = ""
for _modulo in ("pypdf", "PyPDF2"):
    try:
        PdfReader = __import__(_modulo, fromlist=["PdfReader"]).PdfReader
        LEITOR = _modulo
        break
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as _exc:  # PanicException (pyo3) nao herda de Exception
        if not isinstance(_exc, ImportError):
            ERRO_LEITOR = f"{_modulo}: {type(_exc).__name__}: {_exc}"[:200]

COLUNAS = ["classificacao", "score", "arquivo", "pasta", "caminho_completo",
           "tamanho_kb", "modificado", "paginas", "origem", "padrao_nome",
           "padrao_pasta", "arquivos_no_padrao", "termos", "termos_contra",
           "score_forte", "score_apoio", "score_negativo", "obs"]

COLUNAS_PADROES = ["classificacao", "arquivos_no_padrao", "padrao_nome",
                   "padrao_pasta", "origem", "abertos", "exemplo", "termos"]

ORDEM = {"CERTIFICADO": 0, "PROVAVEL": 1, "REVISAR": 2, "NAO": 3, "ERRO": 9}

def padrao_conclusivo(res):
    """O nome/pasta ja decide o grupo, dispensando abrir qualquer arquivo?

    Sim para CERTIFICADO (o nome afirma o que o documento e) e para NAO com
    veto (o nome afirma que e OUTRO documento: nota fiscal, manual, catalogo).
    NAO sem veto significa apenas "o nome nao diz nada" -- e ai e obrigatorio
    abrir uma amostra, senao perdemos digitalizacoes de nome generico, que sao
    justamente as que dependem da composicao quimica no conteudo.
    """
    classe = res["classificacao"]
    return classe == "CERTIFICADO" or (classe == "NAO" and res.get("veto"))


# ---------------------------------------------------------------------------
# Varredura e leitura
# ---------------------------------------------------------------------------

def listar_pdfs(raiz, ignorar, profundidade_max):
    """Caminha a arvore devolvendo (caminho, nome, pasta_relativa).

    Pastas sem permissao sao ignoradas em silencio em vez de abortar a varredura.
    """
    raiz = os.path.abspath(raiz)
    base_niveis = raiz.rstrip(os.sep).count(os.sep)
    ignorar_norm = [i.lower() for i in ignorar]
    for pasta, subpastas, arquivos in os.walk(raiz, onerror=lambda e: None):
        if profundidade_max is not None:
            if pasta.rstrip(os.sep).count(os.sep) - base_niveis >= profundidade_max:
                subpastas[:] = []
        subpastas[:] = [s for s in subpastas
                        if s.lower() not in ignorar_norm and not s.startswith("$")]
        try:
            pasta_rel = os.path.relpath(pasta, raiz)
        except ValueError:
            pasta_rel = pasta
        for nome in arquivos:
            if nome.lower().endswith(".pdf"):
                yield os.path.join(pasta, nome), nome, pasta_rel


def ler_texto(caminho, paginas, limite_chars):
    """Extrai texto das primeiras paginas. Retorna (texto, n_paginas, erro).

    texto None significa que o PDF nao pode ser aberto.
    """
    if PdfReader is None:
        return None, "", ""
    try:
        leitor = PdfReader(caminho, strict=False)
        total = len(leitor.pages)
        partes = []
        for pag in leitor.pages[:paginas]:
            try:
                partes.append(pag.extract_text() or "")
            except Exception:
                continue
            if sum(len(p) for p in partes) >= limite_chars:
                break
        return " ".join(partes)[:limite_chars], str(total), ""
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as exc:
        return None, "", f"falha ao ler PDF: {type(exc).__name__}"


def metadados(caminho):
    try:
        st = os.stat(caminho)
        return (round(st.st_size / 1024, 1),
                datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"))
    except OSError:
        return "", ""


# ---------------------------------------------------------------------------
# Classificacao de um arquivo
# ---------------------------------------------------------------------------

def avaliar(caminho, nome, pasta_rel, paginas, limite_chars, abrir):
    """Classifica um PDF. Com abrir=False, usa apenas nome e pasta."""
    if not abrir:
        res = classificar(nome, pasta_rel, conteudo=None, tem_texto=True)
        return res, ""

    texto, n_paginas, erro = ler_texto(caminho, paginas, limite_chars)
    conteudo, tem_texto = texto, True
    if texto is None:                     # nao abriu
        conteudo, tem_texto = None, False
    elif len(texto.strip()) < 60:         # digitalizado, sem camada de texto
        tem_texto = False

    res = classificar(nome, pasta_rel, conteudo=conteudo, tem_texto=tem_texto)
    if erro:
        res["obs"] = (res["obs"] + " | " + erro).strip(" |")
    return res, n_paginas


def montar_linha(caminho, nome, pasta_rel, res, n_paginas, origem, chave, tamanho_grupo):
    tamanho_kb, modificado = metadados(caminho)
    return {
        "classificacao": res["classificacao"],
        "score": res["score"],
        "arquivo": nome,
        "pasta": pasta_rel,
        "caminho_completo": caminho,
        "tamanho_kb": tamanho_kb,
        "modificado": modificado,
        "paginas": n_paginas,
        "origem": origem,
        "padrao_nome": chave[0],
        "padrao_pasta": chave[1],
        "arquivos_no_padrao": tamanho_grupo,
        "termos": res["termos"],
        "termos_contra": res["termos_contra"],
        "score_forte": res["score_forte"],
        "score_apoio": res["score_apoio"],
        "score_negativo": res["score_negativo"],
        "obs": res["obs"],
    }


def veredito_grupo(classificacoes):
    """Voto da amostra: classe mais frequente; empate vai para a mais
    certificado-like (nunca descarta um grupo por empate)."""
    contagem = Counter(classificacoes)
    maior = max(contagem.values())
    empatadas = [c for c, n in contagem.items() if n == maior]
    return min(empatadas, key=lambda c: ORDEM.get(c, 9))


# ---------------------------------------------------------------------------
# Estrategias
# ---------------------------------------------------------------------------

def rodar_por_arquivo(registros, args, executor):
    """Abre (ou nao) cada PDF individualmente."""
    linhas = []
    futuros = {
        executor.submit(avaliar, c, n, p, args.paginas, args.limite_chars,
                        not args.so_nome): (c, n, p)
        for c, n, p in registros
    }
    for i, fut in enumerate(cf.as_completed(futuros), 1):
        c, n, p = futuros[fut]
        try:
            res, n_pag = fut.result()
            linhas.append(montar_linha(c, n, p, res, n_pag,
                                       "nome" if args.so_nome else "arquivo",
                                       ("", ""), 1))
        except Exception as exc:
            linhas.append(linha_erro(c, n, p, exc))
        if i % 200 == 0 or i == len(futuros):
            print(f"  {i}/{len(futuros)}", file=sys.stderr)
    return linhas, []


def rodar_por_padrao(registros, args, executor):
    """Decide por padrao de nomenclatura, abrindo apenas amostras.

    Grupo com nome conclusivo (CERTIFICADO ou NAO) nao abre nenhum arquivo.
    Grupo ambiguo abre no maximo --amostra arquivos e propaga o veredito.
    """
    grupos = agrupar(registros)
    print(f"{len(grupos)} padroes de nomenclatura identificados.", file=sys.stderr)

    conclusivos, ambiguos = {}, {}
    for chave, itens in grupos.items():
        nome_ex, pasta_ex = itens[0][1], itens[0][2]
        res = classificar(nome_ex, pasta_ex, conteudo=None, tem_texto=True)
        # Sem leitura de conteudo, amostrar nao acrescenta informacao: a amostra
        # seria classificada pelo mesmo nome do grupo. Todo grupo vira decidido
        # pelo nome, e o relatorio nao afirma aberturas que nao aconteceram.
        conclusivo = padrao_conclusivo(res) or args.so_nome
        (conclusivos if conclusivo else ambiguos)[chave] = (itens, res)

    abertos_previstos = sum(min(args.amostra, len(i)) for i, _ in ambiguos.values())
    poupados = len(registros) - abertos_previstos
    print(f"  {len(conclusivos)} padroes decididos pelo nome "
          f"(nenhum arquivo aberto)", file=sys.stderr)
    if ambiguos:
        print(f"  {len(ambiguos)} padroes ambiguos -> abrir ate "
              f"{abertos_previstos} arquivos de amostra", file=sys.stderr)
        print(f"  {poupados} de {len(registros)} PDFs nao serao abertos "
              f"({100 * poupados // max(1, len(registros))}%)", file=sys.stderr)

    linhas, resumo_padroes = [], []

    # Grupos conclusivos: veredito do padrao vale para todos.
    for chave, (itens, res) in conclusivos.items():
        for caminho, nome, pasta_rel in itens:
            r = dict(res)
            if len(itens) > 1:
                r["obs"] = (r["obs"] + f" | decidido pelo padrao de nome "
                            f"({len(itens)} arquivos, nenhum aberto)").strip(" |")
            linhas.append(montar_linha(caminho, nome, pasta_rel, r, "",
                                       "padrao-nome", chave, len(itens)))
        resumo_padroes.append({
            "classificacao": res["classificacao"],
            "arquivos_no_padrao": len(itens), "padrao_nome": chave[0],
            "padrao_pasta": chave[1], "origem": "padrao-nome", "abertos": 0,
            "exemplo": itens[0][1], "termos": res["termos"],
        })

    if not ambiguos:
        return linhas, resumo_padroes

    # Grupos ambiguos: abrir a amostra.
    amostras = {}
    for chave, (itens, _) in ambiguos.items():
        for caminho, nome, pasta_rel in escolher_amostra(itens, args.amostra):
            fut = executor.submit(avaliar, caminho, nome, pasta_rel, args.paginas,
                                  args.limite_chars, not args.so_nome)
            amostras.setdefault(chave, []).append((fut, caminho, nome, pasta_rel))

    total_amostras = sum(len(v) for v in amostras.values())
    print(f"Lendo {total_amostras} arquivos de amostra...", file=sys.stderr)

    for chave, tarefas in amostras.items():
        itens, res_nome = ambiguos[chave]
        vistos, resultados = [], {}
        for fut, caminho, nome, pasta_rel in tarefas:
            try:
                res, n_pag = fut.result()
            except Exception as exc:
                linhas.append(linha_erro(caminho, nome, pasta_rel, exc, chave,
                                         len(itens)))
                continue
            vistos.append(res["classificacao"])
            resultados[caminho] = (res, n_pag, nome, pasta_rel)

        classe = veredito_grupo(vistos) if vistos else res_nome["classificacao"]
        # Melhor resultado da amostra: serve de justificativa do grupo.
        melhor = min((r for r, _, _, _ in resultados.values()),
                     key=lambda r: (ORDEM.get(r["classificacao"], 9), -r["score"]),
                     default=res_nome)

        for caminho, nome, pasta_rel in itens:
            if caminho in resultados:
                res, n_pag, _, _ = resultados[caminho]
                linhas.append(montar_linha(caminho, nome, pasta_rel, res, n_pag,
                                           "amostra-lida", chave, len(itens)))
            else:
                r = dict(melhor)
                r["classificacao"] = classe
                r["obs"] = (f"inferido do padrao de nome: {len(vistos)} de "
                            f"{len(itens)} arquivos lidos como amostra; "
                            f"este nao foi aberto")
                linhas.append(montar_linha(caminho, nome, pasta_rel, r, "",
                                           "padrao-amostra", chave, len(itens)))

        resumo_padroes.append({
            "classificacao": classe, "arquivos_no_padrao": len(itens),
            "padrao_nome": chave[0], "padrao_pasta": chave[1],
            "origem": "amostra", "abertos": len(vistos),
            "exemplo": itens[0][1], "termos": melhor["termos"],
        })

    return linhas, resumo_padroes


def linha_erro(caminho, nome, pasta_rel, exc, chave=("", ""), tamanho=1):
    return {**{k: "" for k in COLUNAS}, "classificacao": "ERRO",
            "arquivo": nome, "pasta": pasta_rel, "caminho_completo": caminho,
            "padrao_nome": chave[0], "padrao_pasta": chave[1],
            "arquivos_no_padrao": tamanho, "origem": "erro",
            "obs": f"{type(exc).__name__}: {exc}"}


# ---------------------------------------------------------------------------

def gravar(caminho_csv, colunas, linhas):
    with open(caminho_csv, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=colunas, delimiter=";",
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(linhas)


def main():
    ap = argparse.ArgumentParser(
        description="Localiza PDFs que sao certificados de qualidade de material.")
    ap.add_argument("-r", "--raiz", default="Y:\\",
                    help="diretorio inicial da varredura (padrao: Y:\\)")
    ap.add_argument("-s", "--saida", default="certificados_encontrados.csv",
                    help="CSV de saida, uma linha por PDF")
    ap.add_argument("--saida-padroes", default=None,
                    help="CSV opcional com o resumo por padrao de nomenclatura")
    ap.add_argument("--por-padrao", action="store_true",
                    help="agrupar por padrao de nome e abrir so amostras "
                         "(recomendado em drive de rede)")
    ap.add_argument("-a", "--amostra", type=int, default=3,
                    help="arquivos abertos por padrao ambiguo (padrao: 3)")
    ap.add_argument("-p", "--paginas", type=int, default=2,
                    help="paginas lidas por PDF (padrao: 2)")
    ap.add_argument("--limite-chars", type=int, default=6000,
                    help="maximo de caracteres extraidos por PDF")
    ap.add_argument("-t", "--threads", type=int, default=8,
                    help="leituras simultaneas (padrao: 8)")
    ap.add_argument("--so-nome", action="store_true",
                    help="nunca abrir os PDFs; classificar so por nome/pasta")
    ap.add_argument("--profundidade", type=int, default=None,
                    help="limitar niveis de subpasta")
    ap.add_argument("--ignorar", nargs="*",
                    default=["recycle.bin", "$recycle.bin",
                             "system volume information", "temp", "tmp"],
                    help="nomes de pasta a pular")
    ap.add_argument("--minimo", default="REVISAR",
                    choices=["CERTIFICADO", "PROVAVEL", "REVISAR", "NAO"],
                    help="classificacao minima gravada no CSV (padrao: REVISAR)")
    args = ap.parse_args()

    if not os.path.isdir(args.raiz):
        sys.exit(f"ERRO: caminho nao encontrado ou inacessivel: {args.raiz}\n"
                 "Verifique se o drive esta mapeado e se voce tem permissao.")

    if LEITOR is None:
        # Sem biblioteca de leitura, todo PDF cairia em "sem texto extraivel" e
        # o CSV inteiro viraria REVISAR. Modo nome/pasta e o comportamento certo.
        args.so_nome = True
        print("AVISO: sem biblioteca de leitura de PDF -- classificando apenas "
              "pelo nome do arquivo e da pasta.\n       Para maior precisao: "
              "pip install pypdf\n", file=sys.stderr)
        if ERRO_LEITOR:
            print(f"       (a importacao falhou: {ERRO_LEITOR})\n", file=sys.stderr)
    elif args.so_nome:
        print("Modo --so-nome: os PDFs nao serao abertos.", file=sys.stderr)
    else:
        print(f"Lendo conteudo dos PDFs com {LEITOR}.", file=sys.stderr)

    print(f"Varrendo {args.raiz} ...", file=sys.stderr)
    t0 = time.time()
    registros = list(listar_pdfs(args.raiz, args.ignorar, args.profundidade))
    print(f"{len(registros)} PDFs encontrados em {time.time() - t0:.1f}s.",
          file=sys.stderr)
    if not registros:
        sys.exit("Nenhum PDF encontrado nesse caminho.")

    estrategia = rodar_por_padrao if args.por_padrao else rodar_por_arquivo
    with cf.ThreadPoolExecutor(max_workers=max(1, args.threads)) as executor:
        linhas, resumo_padroes = estrategia(registros, args, executor)

    linhas.sort(key=lambda l: (ORDEM.get(l["classificacao"], 9),
                               -float(l["score"] or 0), l["arquivo"].lower()))
    corte = ORDEM[args.minimo]
    filtradas = [l for l in linhas
                 if ORDEM.get(l["classificacao"], 9) <= corte
                 or l["classificacao"] == "ERRO"]
    gravar(args.saida, COLUNAS, filtradas)

    if args.saida_padroes and resumo_padroes:
        resumo_padroes.sort(key=lambda p: (ORDEM.get(p["classificacao"], 9),
                                           -p["arquivos_no_padrao"]))
        gravar(args.saida_padroes, COLUNAS_PADROES, resumo_padroes)

    resumo = Counter(l["classificacao"] for l in linhas)
    print("\nResumo:", file=sys.stderr)
    for classe in ["CERTIFICADO", "PROVAVEL", "REVISAR", "NAO", "ERRO"]:
        if resumo.get(classe):
            print(f"  {classe:12s} {resumo[classe]}", file=sys.stderr)
    if args.por_padrao:
        abertos = sum(1 for l in linhas if l["origem"] == "amostra-lida")
        print(f"\nPDFs abertos: {abertos} de {len(registros)}", file=sys.stderr)
    elif args.so_nome:
        print("\nPDFs abertos: 0 (modo nome/pasta)", file=sys.stderr)
    print(f"{len(filtradas)} linhas gravadas em {os.path.abspath(args.saida)} "
          f"({time.time() - t0:.1f}s no total)", file=sys.stderr)
    if args.saida_padroes and resumo_padroes:
        print(f"{len(resumo_padroes)} padroes gravados em "
              f"{os.path.abspath(args.saida_padroes)}", file=sys.stderr)


if __name__ == "__main__":
    main()
