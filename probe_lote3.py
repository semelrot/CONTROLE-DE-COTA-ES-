#!/usr/bin/env python3
"""Probe inteligente para os 45 quebrados do lote 2000-3000.
Gera candidatos (strip de subdominio, www, troca de TLD), sonda com timeout
maior e overrides manuais p/ rebrands conhecidos. Imprime os que sobram
(para busca web). NAO grava ainda - so reporta."""
import socket, json, re
import concurrent.futures as cf
import requests, urllib3
urllib3.disable_warnings()
from validar import HEADERS

# overrides para rebrands/casos conhecidos (host_original -> candidatos extras no inicio)
OVERRIDE = {
    "colpal.com.br":   ["https://www.colgate.com.br/"],
    "norsa.com.br":    ["https://www.solarbr.com.br/", "https://www.norsa.com.br/"],
    "rexam.com":       ["https://www.ball.com/", "https://www.rexam.com/"],
    "reedexhibitionsbrasil.com.br": ["https://www.rxglobal.com/", "https://www.reedexhibitionsbrasil.com.br/"],
    "detroit.cl":      ["https://www.detroit.com.br/", "https://detroit.cl/"],
    "sipcam-upl.com.br": ["https://www.sipcamnichino.com.br/", "https://www.sipcam-upl.com.br/"],
    "amtektekfor.com": ["https://www.tekfor.com/", "https://www.amtektekfor.com/"],
    "koerber-tissue.com": ["https://www.koerber-tissue.com/", "https://www.koerber.com/"],
}

PREFIX_STRIP = ("lin.", "bra.", "br.", "us.", "global.", "www.")

def gen_candidates(host):
    cands = []
    # strip de subdominio de pais/regiao -> tenta dominio-mae
    for p in PREFIX_STRIP:
        if host.startswith(p) and host.count(".") >= 2:
            base = host[len(p):]
            cands += [f"https://www.{base}/", f"https://{base}/"]
    # host original (timeout maior pode resolver servidor lento) + www
    nowww = host[4:] if host.startswith("www.") else host
    cands += [f"https://www.{nowww}/", f"https://{nowww}/",
              f"http://www.{nowww}/", f"http://{nowww}/"]
    # troca de TLD
    tld = {".com.br": [".com", ".ind.br"], ".com": [".com.br"],
           ".ind.br": [".com.br", ".com"], ".cl": [".com.br"]}
    for suf, alts in tld.items():
        if nowww.endswith(suf):
            stem = nowww[:-len(suf)]
            for a in alts:
                cands += [f"https://www.{stem}{a}/", f"https://{stem}{a}/"]
            break
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c); out.append(c)
    return out

def dns_ok(host):
    try:
        socket.setdefaulttimeout(8); socket.getaddrinfo(host, None); return True
    except Exception:
        return False

def probe(url, timeout=22):
    s = requests.Session(); s.headers.update(HEADERS)
    try:
        r = s.get(url, timeout=timeout, allow_redirects=True, verify=False)
        return r.status_code, r.url
    except Exception as e:
        return type(e).__name__, None

def classify(code):
    if isinstance(code, int):
        if code < 400: return "sim"
        if code in (401,403,429): return "sim (bloqueio bot)"
        if code in (502,503,520,521,522,523,525,530): return "bloqueio/instavel"
        return "erro"
    return "sem resposta"

def solve(host):
    urls = OVERRIDE.get(host, []) + gen_candidates(host)
    for url in urls:
        h = url.split("://")[1].split("/")[0]
        if not dns_ok(h):
            continue
        code, final = probe(url); resp = classify(code)
        if resp in ("sim","sim (bloqueio bot)","bloqueio/instavel"):
            return {"orig": host, "dominio_corrigido": h,
                    "http": code if isinstance(code,int) else None,
                    "responde": resp, "final_url": final}
    return {"orig": host, "dominio_corrigido": None}

def main():
    with open("resultados.json", encoding="utf-8") as f:
        master = json.load(f)
    nao = [r["host"] for r in master[2000:3000] if r and r["funciona"] == "NAO"]
    print(f"{len(nao)} hosts quebrados a resolver\n")
    res = {}
    with cf.ThreadPoolExecutor(max_workers=20) as ex:
        for r in ex.map(solve, nao):
            res[r["orig"]] = r
    ok = {k: v for k, v in res.items() if v["dominio_corrigido"]}
    sem = [k for k, v in res.items() if not v["dominio_corrigido"]]
    print(f"=== RESOLVIDOS POR PROBE ({len(ok)}) ===")
    for k, v in ok.items():
        print(f"  {k:<32} -> {v['dominio_corrigido']:<30} ({v['responde']})")
    print(f"\n=== SOBRAM P/ BUSCA WEB ({len(sem)}) ===")
    for k in sem:
        print(f"  {k}")
    json.dump(res, open("probe_lote3.json", "w"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()
