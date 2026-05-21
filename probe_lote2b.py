#!/usr/bin/env python3
"""Verifica via HTTP os candidatos da busca web (segundo grupo do lote 1000-2000).
Merge em correcoes.json."""
import json, socket, os
import requests, urllib3
urllib3.disable_warnings()
from validar import HEADERS

TRY = {
    "eurolaf.com.br":          (["https://www.eurolaf.com.br/", "http://www.eurolaf.com.br/"], "Eurolaf Veiculos Especiais"),
    "brc-brasil.com":          (["http://brc-brasil.com/home", "https://www.brc-brasil.com/", "https://brc-brasil.com/"], "BRC Brasil"),
    "mptrafos.com.br":         (["https://www.mptrafos.com.br/", "http://www.mptrafos.com.br/"], "MP Trafos Engenharia"),
    "ldatanques.com.br":       (["https://ldaequipamentos.com.br/", "http://www.ldatanques.com.br/", "https://www.ldaequipamentos.com.br/"], "LDA Equipamentos"),
    "mafiza.com.br":           (["https://mafiza.com.br/site/", "https://www.mafiza.com.br/site/", "http://mafiza.com.br/site/"], "Mafiza Engenharia"),
    "chrilu.com.br":           (["https://www.chrilu.com.br/", "http://www.chrilu.com.br/"], "Chrilu Equipamentos"),
    "redrasfer.com.br":        (["https://redrasfer.com.br/", "https://www.redrasfer.com.br/"], "Redrasfer (inapta)"),
    "arthurklink.com.br":      (["https://www.arthurklink.com.br/", "https://arthurklink.com.br/", "https://www.arthur-klink.de/en/"], "Arthur Klink Metalurgica"),
    "kallasnet.com.br":        (["https://www.kallasnet.com.br/", "http://www.kallasnet.com.br/"], "Kallas (ambiguo)"),
    "fsdusinagem.com.br":      (["http://fsdusinagem.com.br/", "https://www.fsdusinagem.com.br/", "https://fsdusinagem.com.br/"], "FSD Usinagem"),
    "vmaxsuprimentos.ind.br":  (["https://www.vmaxsuprimentos.ind.br/", "http://www.vmaxsuprimentos.ind.br/"], "Vmax Suprimentos"),
    "vsiderurgia.com.br":      (["http://www.vsiderurgia.com.br/", "https://www.vsiderurgia.com.br/"], "V Siderurgia"),
    "tononbioenergia.com.br":  (["https://www.tononbioenergia.com.br/", "http://www.tononbioenergia.com.br/"], "Tonon Bioenergia (falida)"),
    "romametais.com.br":       (["https://romametais.com.br/", "http://www.romametais.com.br/"], "Roma Metais (ambiguo)"),
    "stampspumas.com.br":      (["https://stampspumas.com.br/", "https://www.stampspumas.com.br/"], "Stamp Spumas"),
}

def probe(url, timeout=25):
    s = requests.Session(); s.headers.update(HEADERS)
    try:
        r = s.get(url, timeout=timeout, allow_redirects=True, verify=False)
        return r.status_code, r.url
    except Exception as e:
        return type(e).__name__, None

def classify(code):
    if isinstance(code, int):
        if code < 400: return "sim"
        if code in (401, 403, 429): return "sim (bloqueio bot)"
        if code in (502, 503, 520, 521, 522, 523, 525, 530): return "bloqueio/instavel"
        return "erro"
    return "sem resposta"

def dns_ok(host):
    try:
        socket.setdefaulttimeout(8); socket.getaddrinfo(host, None); return True
    except Exception:
        return False

def main():
    cor = json.load(open("correcoes.json", encoding="utf-8")) if os.path.exists("correcoes.json") else {}
    sem = []
    for orig, (urls, emp) in TRY.items():
        achou = None
        for url in urls:
            host = url.split("://")[1].split("/")[0]
            if not dns_ok(host):
                print(f"  [{orig}] {url}: DNS nao"); continue
            code, final = probe(url); resp = classify(code)
            print(f"  [{orig}] {url}: http={code} resp={resp}")
            if resp in ("sim", "sim (bloqueio bot)", "bloqueio/instavel"):
                achou = {"dominio_corrigido": host, "http": code if isinstance(code,int) else None,
                         "responde": resp, "final_url": final, "funciona": "SIM (corrigido)",
                         "metodo": "busca web", "obs": f"original nao funcionou; corrigido via busca web ({emp})"}
                break
        if achou:
            cor[orig] = achou; print(f"  >> {orig} -> {achou['dominio_corrigido']} OK\n")
        else:
            cor[orig] = {"dominio_corrigido": None, "funciona": "NAO", "metodo": "busca web",
                         "obs": f"sem site ativo localizado via busca web ({emp})"}
            sem.append(orig); print(f"  >> {orig} -> NAO\n")
    json.dump(cor, open("correcoes.json","w"), ensure_ascii=False, indent=1)
    print("SEM SITE:", sem)

if __name__ == "__main__":
    main()
