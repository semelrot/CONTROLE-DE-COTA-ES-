#!/usr/bin/env python3
"""Reconhecimento: mapeia os padroes de nomenclatura dos PDFs SEM abrir nenhum
arquivo. Use como primeiro passo num drive grande, para ver o que existe e
decidir onde vale investir leitura de conteudo.

    py ferramentas\\certificados\\analisar_padroes.py -r "Y:\\"
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classificador import classificar                      # noqa: E402
from localizar_certificados import (listar_pdfs, gravar,   # noqa: E402
                                    padrao_conclusivo, ORDEM)
from padroes import agrupar                                # noqa: E402

COLUNAS = ["classificacao_pelo_nome", "precisa_abrir", "arquivos", "padrao_nome",
           "padrao_pasta", "exemplo", "termos", "termos_contra"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-r", "--raiz", default="Y:\\")
    ap.add_argument("-s", "--saida", default="padroes_de_nome.csv")
    ap.add_argument("-n", "--mostrar", type=int, default=40,
                    help="quantos padroes exibir na tela (padrao: 40)")
    ap.add_argument("--profundidade", type=int, default=None)
    ap.add_argument("--ignorar", nargs="*",
                    default=["recycle.bin", "$recycle.bin",
                             "system volume information", "temp", "tmp"])
    args = ap.parse_args()

    if not os.path.isdir(args.raiz):
        sys.exit(f"ERRO: caminho nao encontrado ou inacessivel: {args.raiz}")

    print(f"Varrendo {args.raiz} (sem abrir arquivos) ...", file=sys.stderr)
    registros = list(listar_pdfs(args.raiz, args.ignorar, args.profundidade))
    if not registros:
        sys.exit("Nenhum PDF encontrado nesse caminho.")

    grupos = agrupar(registros)
    linhas = []
    for (assin_nome, assin_pasta), itens in grupos.items():
        res = classificar(itens[0][1], itens[0][2], conteudo=None, tem_texto=True)
        linhas.append({
            "classificacao_pelo_nome": res["classificacao"],
            "precisa_abrir": "nao" if padrao_conclusivo(res) else "sim",
            "arquivos": len(itens),
            "padrao_nome": assin_nome,
            "padrao_pasta": assin_pasta,
            "exemplo": itens[0][1],
            "termos": res["termos"],
            "termos_contra": res["termos_contra"],
        })

    linhas.sort(key=lambda l: (ORDEM.get(l["classificacao_pelo_nome"], 9),
                               -l["arquivos"]))
    gravar(args.saida, COLUNAS, linhas)

    print(f"\n{len(registros)} PDFs em {len(grupos)} padroes de nomenclatura\n",
          file=sys.stderr)
    print(f"{'CLASSE':13s} {'ARQ':>6s} {'ABRIR':>6s}  PADRAO", file=sys.stderr)
    for l in linhas[:args.mostrar]:
        print(f"{l['classificacao_pelo_nome']:13s} {l['arquivos']:6d} "
              f"{l['precisa_abrir']:>6s}  {l['padrao_nome'][:52]:52s} "
              f"[{l['padrao_pasta'][:40]}]", file=sys.stderr)
    if len(linhas) > args.mostrar:
        print(f"... e mais {len(linhas) - args.mostrar} padroes (ver o CSV)",
              file=sys.stderr)

    precisa = sum(l["arquivos"] for l in linhas if l["precisa_abrir"] == "sim")
    grupos_abrir = sum(1 for l in linhas if l["precisa_abrir"] == "sim")
    print(f"\n{len(registros) - precisa} arquivos ja decididos pelo nome.",
          file=sys.stderr)
    print(f"{precisa} arquivos em {grupos_abrir} padroes ambiguos -- com "
          f"--por-padrao -a 3, isso custa ~{grupos_abrir * 3} aberturas.",
          file=sys.stderr)
    print(f"\nCSV: {os.path.abspath(args.saida)}", file=sys.stderr)


if __name__ == "__main__":
    main()
