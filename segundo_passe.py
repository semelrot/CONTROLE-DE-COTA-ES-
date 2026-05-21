#!/usr/bin/env python3
"""Segundo passe para os 11 que falharam: timeout maior + teste de caminhos
reais (sites com 404 na raiz mas que existem em subpaginas). Atualiza correcoes.json."""
import json, socket
import requests, urllib3
urllib3.disable_warnings()
from validar import HEADERS, dns_ok

# host_original: (lista de URLs completas a testar, empresa)
TRY = {
    "plascargroup.com":       (["https://plascar.com.br/en/", "https://plascar.com.br/pt/", "https://www.plascar.com.br/en/"], "Plascar"),
    "integrada.coop.br":      (["https://www.integrada.coop.br/", "http://www.integrada.coop.br/"], "Integrada Cooperativa"),
    "buritirama.com":         (["https://www.buritirama.com/", "http://www.buritirama.com/"], "Buritirama Mineracao"),
    "jaraguaequipamentos.com": (["https://jaraguaequipamentos.com.br/", "http://www.jaraguaequipamentos.com/br/Institucional.aspx"], "Jaragua Equipamentos"),
    "hondalock.com.br":       (["https://www.hondalock.com.br/", "http://www.hondalock.com.br/"], "Honda Lock do Brasil"),
    "grupotoniello.com.br":   (["https://grupotoniello.com.br/", "https://senior.grupotoniello.com.br/novocurriculoweb/"], "Grupo Toniello"),
    "ramahtecnologia.com.br": (["https://www.ramahtecnologia.com.br/en", "https://www.ramahtecnologia.com.br/pt", "https://ramahtecnologia.com.br/"], "Ramah Tecnologia"),
    "flsmidth.com":           (["https://www.flsmidth.com/en-gb", "https://flsmidth.com/en-gb", "https://www.flsmidth.com/pt-br"], "FLSmidth"),
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

def main():
    with open("correcoes.json", encoding="utf-8") as f:
        cor = json.load(f)
    socket.setdefaulttimeout(10)
    for orig, (urls, empresa) in TRY.items():
        achou = None
        for url in urls:
            host = url.split("://")[1].split("/")[0]
            if not dns_ok(host):
                print(f"  [{orig}] {url}: DNS nao"); continue
            code, final = probe(url)
            resp = classify(code)
            print(f"  [{orig}] {url}: http={code} resp={resp}")
            if resp in ("sim", "sim (bloqueio bot)", "bloqueio/instavel"):
                achou = {"dominio_corrigido": host, "http": code if isinstance(code, int) else None,
                         "responde": resp, "final_url": final, "funciona": "SIM (corrigido)",
                         "metodo": "busca web", "obs": f"original nao funcionou; corrigido via busca web ({empresa})"}
                break
        if achou:
            cor[orig] = achou
            print(f"  >> {orig} -> {achou['dominio_corrigido']} OK ({achou['responde']})\n")
        else:
            cor[orig] = {"dominio_corrigido": None, "funciona": "NAO", "metodo": "busca web",
                         "obs": f"dominio nao responde mesmo apos busca web ({empresa})"}
            print(f"  >> {orig} -> ainda sem resposta\n")

    with open("correcoes.json", "w") as f:
        json.dump(cor, f, ensure_ascii=False, indent=1)
    achados = sum(1 for v in cor.values() if v.get("dominio_corrigido"))
    print(f"Total corrigidos via busca web: {achados}/{len(cor)}")
    print("Sem site:", [k for k, v in cor.items() if not v.get("dominio_corrigido")])

if __name__ == "__main__":
    main()
