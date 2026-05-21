#!/usr/bin/env python3
"""Valida dominios da aba 'Dominios (Unificado)': checa se funcionam para
acessar o site da empresa e, quando quebrados, tenta heuristicas de correcao.
Saida: resultados.json (consumido depois pelo passo de busca web + escrita xlsx)."""
import socket, json, time, sys, re
import concurrent.futures as cf
import requests
import urllib3
urllib3.disable_warnings()

XLSX = "base_contatos.xlsx"
SRC_SHEET = "Dominios (Unificado)"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
              "image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

def dns_ok(host):
    try:
        socket.setdefaulttimeout(6)
        socket.getaddrinfo(host, None)
        return True
    except Exception:
        return False

def http_probe(host):
    """Retorna (status, responde, final_url). status pode ser int ou nome de erro."""
    s = requests.Session()
    s.headers.update(HEADERS)
    last = (None, "sem resposta", None)
    for scheme in ("https", "http"):
        url = f"{scheme}://{host}"
        try:
            r = s.get(url, timeout=12, allow_redirects=True, verify=False)
            code = r.status_code
            if code < 400:
                responde = "sim"
            elif code in (401, 403, 429):
                responde = "sim (bloqueio bot)"
            elif code in (502, 503, 520, 521, 522, 523, 525, 530):
                responde = "bloqueio/instavel"
            else:
                responde = "erro"
            return (code, responde, r.url)
        except requests.exceptions.SSLError:
            last = ("SSLError", "sem resposta", None)
            continue
        except Exception as e:
            last = (type(e).__name__, "sem resposta", None)
            continue
    return last

def norm_host(domain):
    d = (domain or "").strip().lower()
    d = re.sub(r"^https?://", "", d).split("/")[0].strip()
    return d

def works(responde):
    return responde in ("sim", "sim (bloqueio bot)", "bloqueio/instavel")

def candidates(host):
    """Gera variacoes heuristicas plausiveis para um host quebrado."""
    cands = []
    base = host[4:] if host.startswith("www.") else host
    # toggle www
    cands.append("www." + base)
    cands.append(base)
    # troca de TLD comum no Brasil
    tld_variants = {
        ".com.br": [".com", ".ind.br", ".net.br"],
        ".com": [".com.br", ".ind.br"],
        ".ind.br": [".com.br", ".com"],
        ".net.br": [".com.br", ".com"],
        ".net": [".com.br", ".com"],
    }
    for suf, alts in tld_variants.items():
        if base.endswith(suf):
            stem = base[: -len(suf)]
            for a in alts:
                cands.append(stem + a)
                cands.append("www." + stem + a)
            break
    # dedup preservando ordem
    seen, out = set(), []
    for c in cands:
        if c and c != host and c not in seen:
            seen.add(c); out.append(c)
    return out

def correct(host):
    """Tenta achar dominio que funcione via heuristica. Retorna dict ou None."""
    for cand in candidates(host):
        ch = norm_host(cand)
        if not dns_ok(ch):
            continue
        code, responde, final = http_probe(ch)
        if works(responde):
            return {"dominio_corrigido": ch, "http": code, "responde": responde,
                    "final_url": final, "metodo": "heuristica"}
    return None

def check(rec):
    domain, qtd, empresa = rec
    host = norm_host(domain)
    out = {"dominio": domain, "qtd": qtd, "empresa": empresa, "host": host,
           "dns": "nao", "http": None, "responde": "sem resposta",
           "final_url": None, "funciona": "NAO", "dominio_corrigido": None,
           "metodo_correcao": None, "obs": None}
    if not host:
        out["obs"] = "dominio vazio"
        return out
    if dns_ok(host):
        out["dns"] = "sim"
        code, responde, final = http_probe(host)
        out["http"], out["responde"], out["final_url"] = code, responde, final
        if works(responde):
            out["funciona"] = "SIM"
            return out
    # quebrado (sem DNS ou sem resposta/erro): tenta corrigir por heuristica
    fix = correct(host)
    if fix:
        out["funciona"] = "SIM (corrigido)"
        out["dominio_corrigido"] = fix["dominio_corrigido"]
        out["http"] = fix["http"]
        out["responde"] = fix["responde"]
        out["final_url"] = fix["final_url"]
        out["metodo_correcao"] = fix["metodo"]
        if out["dns"] == "nao":
            out["dns"] = "nao (orig)"
        out["obs"] = f"original '{host}' nao funcionou; corrigido por heuristica"
    else:
        out["funciona"] = "NAO"
        out["obs"] = ("DNS nao resolve" if out["dns"] == "nao"
                      else f"DNS ok mas site nao responde ({out['responde']})")
    return out

def main():
    import openpyxl
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    ws = wb[SRC_SHEET]
    recs = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        recs.append((r[0], r[1], r[2]))  # Dominio, Qtd_Contatos, Empresa
    recs = recs[:n]
    print(f"Validando {len(recs)} dominios...", flush=True)
    results = [None] * len(recs)
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=40) as ex:
        futs = {ex.submit(check, rec): i for i, rec in enumerate(recs)}
        done = 0
        for f in cf.as_completed(futs):
            i = futs[f]
            results[i] = f.result()
            done += 1
            if done % 100 == 0:
                print(f"  {done}/{len(recs)}  ({time.time()-t0:.0f}s)", flush=True)
    with open("resultados.json", "w") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)
    from collections import Counter
    print(f"\nConcluido em {time.time()-t0:.0f}s")
    print("funciona:", Counter(r["funciona"] for r in results))
    print("dns:", Counter(r["dns"] for r in results))
    nao = [r for r in results if r["funciona"] == "NAO"]
    print(f"\n--- {len(nao)} ainda QUEBRADOS (precisam busca web) ---")
    for r in nao:
        print(f"  [{r['host']}] empresa='{r['empresa']}' dns={r['dns']} resp={r['responde']}")

if __name__ == "__main__":
    main()
