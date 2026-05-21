#!/usr/bin/env python3
"""Monta research_queue.json: dominios validados (funciona SIM / corrigido),
em ordem de contatos, com URL efetiva + classificacao existente da base."""
import json
import openpyxl

# base: Tipo/Subtipo/Consome_Aco/Obs por dominio
wb = openpyxl.load_workbook("base_contatos.xlsx", read_only=True, data_only=True)
dom = wb["Dominios (Unificado)"]
base = {}
for r in dom.iter_rows(min_row=2, values_only=True):
    base[r[0]] = {"tipo": r[4], "subtipo": r[5], "consome": r[6], "obs": r[8]}

results = json.load(open("resultados.json", encoding="utf-8"))
correc = json.load(open("correcoes.json", encoding="utf-8"))

queue = []
for i, r in enumerate(results):
    if not r:
        continue
    if r["funciona"] not in ("SIM", "SIM (corrigido)"):
        continue
    host = r["host"]
    eff = r.get("dominio_corrigido") or correc.get(host, {}).get("dominio_corrigido") or host
    b = base.get(r["dominio"], {})
    queue.append({
        "idx": i,
        "lote": i // 100 + 1,
        "dominio_base": r["dominio"],
        "url": f"https://{eff}",
        "dominio_efetivo": eff,
        "empresa": r.get("empresa"),
        "qtd_contatos": r.get("qtd"),
        "tipo_base": b.get("tipo"),
        "subtipo_base": b.get("subtipo"),
        "consome_base": b.get("consome"),
        "obs_base": b.get("obs"),
    })

json.dump(queue, open("research_queue.json", "w"), ensure_ascii=False, indent=1)
print(f"Fila de pesquisa: {len(queue)} dominios validados")
print(f"Primeiro: {queue[0]['dominio_efetivo']} ({queue[0]['empresa']})")
print(f"Bloco 1 = idx 0..99 (lote 1)")
