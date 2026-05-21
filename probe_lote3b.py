#!/usr/bin/env python3
"""Verificacao final dos candidatos da busca web (lote 2000-3000) e merge em
correcoes.json. Lixo de dados marcado direto como NAO."""
import json, socket, os
import requests, urllib3
urllib3.disable_warnings()
from validar import HEADERS

# host_original: ([URLs candidatas], empresa)
TRY = {
    "usimabe.com.br":           (["https://www.usimabe.com.br/", "http://usimabe.com.br/site/"], "Usimabe Usinagem"),
    "smorenometalurgica.com.br": (["https://www.smorenometalurgica.com.br/", "http://www.smorenometalurgica.com.br/"], "S. Moreno Metalurgica"),
    "positivaindustrial.com.br": (["https://www.positivaindustrial.com.br/", "http://www.positivaindustrial.com.br/"], "Positiva Industrial"),
    "mediacom.com":             (["https://www.essencemediacom.com/", "https://www.mediacom.com/"], "MediaCom -> EssenceMediacom"),
    "sugoiincorporadora.com.br": (["https://sugoisa.com.br/", "https://www.sugoisa.com.br/"], "Sugoi Incorporadora"),
    "csdvarejo.com.br":         (["https://www.grupoamigao.com/", "https://csd.com.br/", "https://csdvarejo.com.br/"], "CSD -> Grupo Amigao"),
    "airplusengenharia.com.br": (["https://www.airplusengenharia.com.br/", "https://www.airplus.engineering/"], "Air Plus Engenharia"),
    "metalurgicamagalhaes.com.br": (["https://www.metalurgicamagalhaes.com.br/"], "Metalurgica Magalhaes"),
    "ttxequipamentos.com.br":   (["https://www.ttxequipamentos.com.br/", "https://grupottx.com.br/"], "TTX Equipamentos"),
    "carueme.com.br":           (["https://www.grupocarueme.com.br/", "https://www.carueme.com.br/"], "Grupo Carueme"),
    "kfestamparia.com.br":      (["https://www.kfestamparia.com.br/", "http://www.kfestamparia.com.br/"], "KF Estamparia"),
    "metalurgicaclara.com.br":  (["https://metalurgicaclara.com.br/empresa/", "https://www.metalurgicaclara.com.br/"], "Metalurgica Clara"),
    "cassioecassio.com.br":     (["https://cassioecassio.com.br/site/", "https://www.cassioecassio.com.br/", "https://cassioecassio.com.br/"], "Cassio & Cassio (aco)"),
    "tiberina.com.br":          (["https://www.tiberina.com/", "https://tiberina.com/", "https://www.tiberina.it/"], "Tiberina (autopecas IT)"),
    # palpites fracos (provavel NAO)
    "decioindmet.com.br":       (["https://www.decioindmet.com.br/"], "Decio Ind. Metalurgica"),
    "ferramentariadamp.com.br": (["https://www.ferramentariadamp.com.br/", "https://damp.pt/"], "Ferramentaria DAMP"),
    "vectoreq.com.br":          (["https://www.vectoreq.com.br/"], "Vector Equipamentos"),
}
# lixo de dados / sem empresa real -> NAO direto, com motivo
GARBAGE = {
    "3x.png":                 "valor invalido na base (nome de arquivo de imagem, nao e dominio)",
    "idealsboardmail.com":    "nao e empresa da base (parece produto de software); sem site valido",
    "proficientnowresearch.com": "dominio generico/sem empresa identificavel; sem site valido",
    "varinhadigital.com.br":  "registro sem empresa real (campo dizia 'em busca de oportunidades'); dominio nao resolve",
    "prototype3d.com.br":     "dominio nao resolve (NXDOMAIN); nenhum site de 'Prototype 3D' confirmado",
    "ab-rodofort.com.br":     "empresa baixada/incorporada; sem site ativo",
}

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

def main():
    cor = json.load(open("correcoes.json", encoding="utf-8")) if os.path.exists("correcoes.json") else {}
    for host, motivo in GARBAGE.items():
        cor[host] = {"dominio_corrigido": None, "funciona": "NAO", "metodo": "busca web", "obs": motivo}
        print(f"  [{host}] -> NAO (lixo/sem empresa)")
    for orig, (urls, emp) in TRY.items():
        achou = None
        for url in urls:
            h = url.split("://")[1].split("/")[0]
            if not dns_ok(h):
                print(f"  [{orig}] {url}: DNS nao"); continue
            code, final = probe(url); resp = classify(code)
            print(f"  [{orig}] {url}: http={code} resp={resp}")
            if resp in ("sim","sim (bloqueio bot)","bloqueio/instavel"):
                achou = {"dominio_corrigido": h, "http": code if isinstance(code,int) else None,
                         "responde": resp, "final_url": final, "funciona": "SIM (corrigido)",
                         "metodo": "busca web", "obs": f"original nao funcionou; corrigido via busca web ({emp})"}
                break
        if achou:
            cor[orig] = achou; print(f"  >> {orig} -> {achou['dominio_corrigido']} OK\n")
        else:
            cor[orig] = {"dominio_corrigido": None, "funciona": "NAO", "metodo": "busca web",
                         "obs": f"sem site ativo localizado via busca web ({emp})"}
            print(f"  >> {orig} -> NAO\n")
    json.dump(cor, open("correcoes.json","w"), ensure_ascii=False, indent=1)
    ach = sum(1 for v in cor.values() if v.get("dominio_corrigido"))
    print(f"\nTotal correcoes.json: {ach} corrigidos, {len(cor)-ach} sem site")

if __name__ == "__main__":
    main()
