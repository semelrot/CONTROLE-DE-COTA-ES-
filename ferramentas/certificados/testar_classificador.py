#!/usr/bin/env python3
"""Casos de teste da heuristica. Rode: python3 testar_classificador.py"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classificador import classificar

# (nome, pasta, conteudo, classificacoes aceitas)
CASOS = [
    ("Certificado de Qualidade - Chapa A36.pdf", "Materiais/2024", None,
     {"CERTIFICADO"}),
    ("CQ_barra_redonda_SAE1045.pdf", "Certificados", None,
     {"CERTIFICADO", "PROVAVEL"}),
    ("mill_test_certificate_12345.pdf", "Suprimentos", None, {"CERTIFICADO"}),
    ("doc0001.pdf", "Certificados de Material/Gerdau",
     "CERTIFICADO DE QUALIDADE - Corrida 4471 - Analise quimica C Mn Si - "
     "Limite de escoamento 350 MPa - Alongamento 22% - ASTM A36",
     {"CERTIFICADO"}),
    ("scan_2024_03_11.pdf", "Recebimento",
     "Analise quimica composicao quimica propriedades mecanicas ensaio de tracao "
     "limite de escoamento dureza brinell heat number 8891 ABNT NBR 7480",
     {"CERTIFICADO", "PROVAVEL"}),
    ("Certificado EN 10204 3.1 tubo.pdf", "", None, {"CERTIFICADO"}),
    ("laudo de ensaio - solda.pdf", "Qualidade", None,
     {"CERTIFICADO", "PROVAVEL"}),
    # negativos
    ("Nota Fiscal 88213.pdf", "Financeiro", "DANFE nota fiscal eletronica",
     {"NAO"}),
    ("Cotacao_fornecedor_ACME.pdf", "Compras", "Proposta comercial orcamento",
     {"NAO"}),
    ("Certificado ISO 9001 ACME.pdf", "Fornecedores",
     "Certificado de conformidade do sistema de gestao da qualidade ISO 9001",
     {"NAO", "REVISAR"}),
    ("Certificado de conclusao curso NR12.pdf", "RH", None, {"NAO", "REVISAR"}),
    ("FISPQ tinta epoxi.pdf", "Seguranca",
     "Ficha de informacoes de seguranca de produto quimico", {"NAO"}),
    ("Catalogo tubos 2023.pdf", "Marketing", "Catalogo de produtos", {"NAO"}),
    ("Manual de instrucoes bomba.pdf", "Manuais", None, {"NAO"}),
    # certificado que cita a NF -- nao pode ser derrubado pelo negativo
    ("Certificado de Qualidade chapa.pdf", "Certificados",
     "Certificado de qualidade. Nota fiscal 4471. Pedido de compra 8890. "
     "Analise quimica e propriedades mecanicas conforme ASTM A572",
     {"CERTIFICADO"}),
    # a tabela de composicao quimica sozinha deve bastar, mesmo com nome
    # generico e sem a palavra "certificado" em lugar algum
    ("0001_0042.pdf", "Digitalizacoes/Marco",
     "Corrida 44712  Bitola 12,70 mm  C 0,18  Si 0,25  Mn 1,20  P 0,022  "
     "S 0,015  Cr 0,08  Ni 0,05  Ceq 0,41  Escoamento 372 MPa",
     {"CERTIFICADO", "PROVAVEL"}),
    # FISPQ tambem cita composicao quimica: nao pode virar certificado
    ("FISPQ solvente.pdf", "Seguranca",
     "Ficha de informacoes de seguranca de produto quimico. Secao 3 - "
     "composicao quimica. Xileno 0,45. Tolueno 0,30. Etanol 0,15.",
     {"NAO", "REVISAR"}),
    # digitalizado sem texto -> nunca deve sair como NAO
    ("digitalizado_0042.pdf", "Recebimento de Material", "", {"REVISAR"}),
]


def main():
    falhas = 0
    for nome, pasta, conteudo, esperado in CASOS:
        # conteudo == "" modela PDF digitalizado (sem camada de texto);
        # qualquer texto extraido conta como leitura bem sucedida.
        tem_texto = conteudo != ""
        r = classificar(nome, pasta, conteudo=conteudo, tem_texto=tem_texto)
        ok = r["classificacao"] in esperado
        falhas += not ok
        print(f"[{'ok ' if ok else 'FALHA'}] {r['classificacao']:12s} "
              f"score={r['score']:6.1f} (f={r['score_forte']} a={r['score_apoio']} "
              f"n={r['score_negativo']})  {nome}")
        if not ok:
            print(f"          esperado um de {sorted(esperado)}; "
                  f"termos: {r['termos'][:90]}")
    print(f"\n{len(CASOS) - falhas}/{len(CASOS)} casos ok")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
