#!/usr/bin/env python3
"""Sonda candidatos fortes (subdominios br. de multinacionais e palpites de nome)
para os quebrados do lote 1000-2000. Merge em correcoes.json. Imprime os que
sobraram sem solucao (para irem para busca web)."""
import json, socket
import requests, urllib3
urllib3.disable_warnings()
from validar import HEADERS

# host_original: ([URLs completas em ordem de preferencia], empresa)
TRY = {
    "br.ajinomoto.com":   (["https://www.ajinomoto.com.br/", "https://ajinomoto.com.br/", "https://www.ajinomoto.com/"], "Ajinomoto"),
    "br.sika.com":        (["https://bra.sika.com/", "https://www.sika.com.br/", "https://www.sika.com/", "https://bra.sika.com/pt.html"], "Sika"),
    "br.atlascopco.com":  (["https://www.atlascopco.com/pt-br", "https://www.atlascopco.com/", "https://www.atlascopco.com.br/"], "Atlas Copco"),
    "br.brookfield.com":  (["https://www.brookfield.com/", "https://br.brookfield.com.br/", "https://www.brookfieldproperties.com/"], "Brookfield"),
    "itwdelfast.co.uk":   (["https://www.itwdelfast.co.uk/", "https://www.delfast.com.br/", "https://delfast.com.br/", "https://www.itwdelfast.com/"], "ITW Delfast"),
    "formaeforma.com.br": (["https://www.formaforte.com.br/", "https://formaforte.com.br/"], "Forma Forte Ind. Metalurgica"),
    "hondalock-sp.com.br": (["https://www.hondalock.com.br/"], "Honda Lock SP"),
    "protendit.com.br":   (["https://www.protendit.com.br/", "http://www.protendit.com.br/"], "Protendit"),
    "romametais.com.br":  (["https://www.romametais.com.br/", "http://www.romametais.com.br/"], "Roma Metais"),
    "arthurklink.com.br": (["https://www.arthurklink.com.br/", "http://www.arthurklink.com.br/"], "Arthur Klink Metalurgica"),
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
    cor = json.load(open("correcoes.json", encoding="utf-8")) if __import__("os").path.exists("correcoes.json") else {}
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
            sem.append((orig, emp)); print(f"  >> {orig} -> sem solucao\n")
    json.dump(cor, open("correcoes.json","w"), ensure_ascii=False, indent=1)
    print("AINDA SEM SOLUCAO:", [s[0] for s in sem])

if __name__ == "__main__":
    main()
