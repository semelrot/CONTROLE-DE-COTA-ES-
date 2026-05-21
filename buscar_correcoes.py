#!/usr/bin/env python3
"""Verifica via HTTP os candidatos vindos da busca web para os 18 dominios
quebrados e grava correcoes.json (host_original -> correcao)."""
import json
from validar import dns_ok, http_probe, norm_host, works

# host_original: (lista de candidatos em ordem de preferencia, fonte/empresa)
CAND = {
    "plascargroup.com":      (["plascar.com.br", "www.plascar.com.br"], "Plascar"),
    "castrolanda.coop.br":   (["www.castrolanda.coop.br", "castrolanda.com", "www.castrolanda.com"], "Castrolanda"),
    "integrada.coop.br":     (["www.integrada.coop.br"], "Integrada Cooperativa"),
    "produquimica.com.br":   (["www.produquimica.com.br", "compassminerals.com.br", "www.compassminerals.com.br", "www.compassminerals.com"], "Compass Minerals (ex-Produquimica)"),
    "plasticomnium.com":     (["opmobility.com", "www.opmobility.com"], "Plastic Omnium / OPmobility"),
    "grupoantolin.com":      (["antolin.com", "www.antolin.com"], "Grupo Antolin"),
    "servatis.com.br":       (["www.servatis.com.br"], "Servatis (faliu 2018)"),
    "buritirama.com":        (["www.buritirama.com", "buritirama.com.br", "www.buritirama.com.br"], "Buritirama Mineracao"),
    "jaraguaequipamentos.com": (["jaraguaequipamentos.com.br", "www.jaraguaequipamentos.com.br", "www.jaraguaequipamentos.com"], "Jaragua Equipamentos"),
    "hondalock.com.br":      (["www.hondalock.com.br"], "Honda Lock do Brasil"),
    "barga-brasil.com.br":   (["www.barga-brasil.com.br", "bgabrasil.com", "www.bgabrasil.com"], "Barga Brasil"),
    "bservicos.com.br":      (["www.bservicos.com.br"], "bservicos (nao identificado)"),
    "colpal.com":            (["colgate.com.br", "www.colgate.com.br", "colgatepalmolive.com", "www.colgatepalmolive.com"], "Colgate-Palmolive"),
    "ferrolene.com.br":      (["www.ferrolene.com.br"], "Ferrolene"),
    "br.gestamp.com":        (["gestamp.com", "www.gestamp.com"], "Gestamp"),
    "grupotoniello.com.br":  (["www.grupotoniello.com.br"], "Grupo Toniello"),
    "ramahtecnologia.com.br": (["www.ramahtecnologia.com.br"], "Ramah Tecnologia"),
    "flsmidth.com":          (["www.flsmidth.com", "flsmidth.com"], "FLSmidth"),
}

def main():
    out = {}
    for orig, (cands, empresa) in CAND.items():
        achou = None
        for c in cands:
            h = norm_host(c)
            if not dns_ok(h):
                print(f"  [{orig}] cand {h}: DNS nao")
                continue
            code, responde, final = http_probe(h)
            print(f"  [{orig}] cand {h}: http={code} resp={responde}")
            if works(responde):
                achou = {"dominio_corrigido": h, "http": code, "responde": responde,
                         "final_url": final, "funciona": "SIM (corrigido)",
                         "metodo": "busca web",
                         "obs": f"original nao funcionou; corrigido via busca web ({empresa})"}
                break
        if achou:
            out[orig] = achou
            print(f"  >> {orig} -> {achou['dominio_corrigido']} OK\n")
        else:
            out[orig] = {"dominio_corrigido": None, "funciona": "NAO",
                         "metodo": "busca web",
                         "obs": f"sem site ativo localizado via busca web ({empresa})"}
            print(f"  >> {orig} -> NENHUM candidato funcionou\n")

    with open("correcoes.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    achados = sum(1 for v in out.values() if v.get("dominio_corrigido"))
    print(f"\nCorrigidos via busca web: {achados}/{len(out)}")
    print("Ainda sem site:", [k for k, v in out.items() if not v.get("dominio_corrigido")])

if __name__ == "__main__":
    main()
