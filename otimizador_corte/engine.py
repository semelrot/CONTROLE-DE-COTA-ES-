"""
Motor de otimizacao da composicao de corte (slitting 1.5D com demanda em PESO).

Ideia central
-------------
Dentro de uma bobina-mae de largura Wc, o peso se distribui proporcionalmente a
largura. Uma tira de largura w cortada ao longo de toda a bobina rende, em peso,
`peso_bobina * w / Wc`. Isso vale independentemente da espessura/comprimento.

Logo, "chapa" e "tira" sao equivalentes no nivel de PESO: ambas sao uma largura
que consome peso da bobina proporcionalmente. A diferenca (corte transversal em
chapas) e um passo seguinte, que nao muda o aproveitamento da largura.

O problema entao vira:
  1) GERAR COMPOSICOES  -> conjuntos de larguras (tiras) que cabem na largura da
     bobina, respeitando refilo minimo e numero maximo de facas.
  2) SELECIONAR         -> quanto peso de cada grupo de bobina roda em cada
     composicao para atender o peso pedido de cada largura, com a MENOR perda
     (menor consumo de material) possivel. Resolvido de forma exata com PuLP/CBC.

A folga (slack) de cada item revela o "peso da necessidade que o estoque NAO
cobre" -> exatamente o comparativo necessidade x disponivel pedido pelo PCP.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import pulp

from .modelos import (
    BobinaMae,
    Pedido,
    Parametros,
    Plano,
    ItemResultado,
    Resultado,
    peso_por_metro,
)


# --------------------------------------------------------------------------- #
# 1) Geracao de composicoes (padroes de corte)                                #
# --------------------------------------------------------------------------- #
def gerar_composicoes(
    larguras: Iterable[float],
    largura_util_mm: float,
    num_max_facas: int,
    max_composicoes: int = 4000,
) -> list[tuple]:
    """
    Gera todas as composicoes MAXIMAIS de larguras que cabem em `largura_util_mm`.

    Maximal = nao e possivel adicionar mais nenhuma tira (nem a mais estreita)
    sem estourar a largura util ou o numero maximo de facas. Isso mantem apenas
    os padroes "bem preenchidos", evitando explosao combinatoria.

    Retorna uma lista de tuplas (larguras ordenadas desc), sem repetidos.
    """
    larguras = sorted({float(w) for w in larguras if w > 0}, reverse=True)
    if not larguras:
        return []
    menor = larguras[-1]
    resultados: set[tuple] = set()

    def rec(inicio: int, atual: list, soma: float):
        if len(resultados) >= max_composicoes:
            return
        estendeu = False
        for i in range(inicio, len(larguras)):
            w = larguras[i]
            if len(atual) < num_max_facas and soma + w <= largura_util_mm + 1e-6:
                atual.append(w)
                rec(i, atual, soma + w)
                atual.pop()
                estendeu = True
        # E' folha (maximal) quando nao coube mais nada ou atingiu o limite de facas.
        if (not estendeu or len(atual) >= num_max_facas) and atual:
            resultados.add(tuple(atual))

    rec(0, [], 0.0)
    return list(resultados)


def _conta(composicao: tuple, largura: float) -> int:
    return sum(1 for w in composicao if abs(w - largura) < 1e-6)


# --------------------------------------------------------------------------- #
# 2) Otimizacao (selecao das composicoes por peso)                            #
# --------------------------------------------------------------------------- #
def otimizar(
    bobinas: list[BobinaMae],
    pedidos: list[Pedido],
    parametros: Parametros | None = None,
) -> Resultado:
    """
    Resolve a melhor composicao de corte para atender os `pedidos` (em peso)
    usando as `bobinas` de estoque, minimizando o material consumido (perda).
    """
    par = parametros or Parametros()

    # --- necessidade liquida agregada por (material, largura) ---
    # tira e chapa da mesma largura/material sao equivalentes na composicao.
    demanda: dict[tuple, float] = defaultdict(float)
    tipos: dict[tuple, set] = defaultdict(set)
    for p in pedidos:
        chave = (p.material, round(p.largura_mm, 3))
        demanda[chave] += p.necessidade_liquida_kg
        tipos[chave].add(p.tipo)

    # --- grupos de bobina por (material, largura, espessura) ---
    grupos: dict[tuple, dict] = {}
    for b in bobinas:
        chave = (b.material, round(b.largura_mm, 3), round(b.espessura_mm, 3))
        g = grupos.setdefault(
            chave,
            {"material": b.material, "largura": b.largura_mm,
             "espessura": b.espessura_mm, "peso": 0.0, "bobinas": []},
        )
        g["peso"] += b.peso_kg
        g["bobinas"].append(b)

    larguras_por_material: dict[str, set] = defaultdict(set)
    for (mat, larg) in demanda:
        larguras_por_material[mat].add(larg)

    # --- composicoes por grupo de bobina ---
    composicoes_por_grupo: dict[tuple, list[tuple]] = {}
    for chave, g in grupos.items():
        util = g["largura"] - par.refilo_total_mm
        comps = gerar_composicoes(
            larguras_por_material.get(g["material"], set()),
            util,
            par.num_max_facas,
            par.max_composicoes,
        )
        composicoes_por_grupo[chave] = comps

    # --- modelo PuLP ---
    prob = pulp.LpProblem("composicao_corte", pulp.LpMinimize)

    # x[g, k] = peso (kg) do grupo g rodando na composicao k  (>= 0)
    x: dict[tuple, pulp.LpVariable] = {}
    for chave, comps in composicoes_por_grupo.items():
        for k, _comp in enumerate(comps):
            x[(chave, k)] = pulp.LpVariable(f"x_{abs(hash((chave, k)))}", lowBound=0)

    # folga (falta) por item de demanda -> peso nao coberto pelo estoque
    falta = {
        chave: pulp.LpVariable(f"falta_{abs(hash(chave))}", lowBound=0)
        for chave in demanda
    }

    # Objetivo: minimizar material consumido + penalidade forte por falta.
    M = 1_000_000.0
    prob += (
        pulp.lpSum(x.values())
        + M * pulp.lpSum(falta.values())
    )

    # Restricao de capacidade: nao usar mais peso do que o grupo tem em estoque.
    for chave, g in grupos.items():
        vars_g = [x[(chave, k)] for k in range(len(composicoes_por_grupo[chave]))]
        if vars_g:
            prob += pulp.lpSum(vars_g) <= g["peso"], f"cap_{abs(hash(chave))}"

    # Restricao de atendimento: producao (em peso) de cada largura >= necessidade.
    for chave_dem, necessidade in demanda.items():
        mat, larg = chave_dem
        termos = []
        for chave_g, g in grupos.items():
            if g["material"] != mat:
                continue
            Wc = g["largura"]
            for k, comp in enumerate(composicoes_por_grupo[chave_g]):
                n = _conta(comp, larg)
                if n:
                    # peso produzido dessa largura = x * (n * larg / Wc)
                    termos.append(x[(chave_g, k)] * (n * larg / Wc))
        prob += (
            pulp.lpSum(termos) + falta[chave_dem] >= necessidade,
            f"dem_{abs(hash(chave_dem))}",
        )

    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    status = pulp.LpStatus[prob.status]
    viavel = status in ("Optimal", "Not Solved", "Feasible")

    # --- montar planos por grupo, depois alocar em bobinas fisicas ---
    planos: list[Plano] = []
    for chave_g, comps in composicoes_por_grupo.items():
        g = grupos[chave_g]
        alocacoes = []  # (composicao, peso)
        for k, comp in enumerate(comps):
            peso = x[(chave_g, k)].value() or 0.0
            if peso > 1e-6:
                alocacoes.append((comp, peso))
        alocacoes.sort(key=lambda ac: -sum(ac[0]))  # maior aproveitamento primeiro
        planos.extend(_alocar_em_bobinas(g, alocacoes))

    # --- atendimento por item ---
    produzido_por_chave: dict[tuple, float] = defaultdict(float)
    for pl in planos:
        for larg in set(pl.larguras):
            n = _conta(pl.larguras, larg)
            produzido_por_chave[(pl.material, round(larg, 3))] += (
                pl.peso_alocado_kg * n * larg / pl.largura_bobina_mm
            )

    itens: list[ItemResultado] = []
    for chave_dem, necessidade in demanda.items():
        mat, larg = chave_dem
        tipo = "+".join(sorted(tipos[chave_dem]))
        itens.append(
            ItemResultado(
                material=mat,
                largura_mm=larg,
                tipo=tipo,
                necessidade_kg=necessidade,
                produzido_kg=produzido_por_chave.get(chave_dem, 0.0),
            )
        )
    itens.sort(key=lambda i: (i.material, -i.largura_mm))

    res = Resultado(planos=planos, itens=itens, viavel=viavel, mensagem=status)
    return res


def _alocar_em_bobinas(grupo: dict, alocacoes: list) -> list[Plano]:
    """
    Distribui as composicoes escolhidas (com seus pesos) nas bobinas fisicas do
    grupo, preenchendo bobina a bobina. Quando uma composicao nao cabe inteira em
    uma bobina, ela e dividida -> e' o "aliviar a bobina" e rodar composicoes
    diferentes em partes diferentes da mesma bobina.
    """
    planos: list[Plano] = []
    bobinas = sorted(grupo["bobinas"], key=lambda b: -b.peso_kg)
    restante_bobina = {b.id: b.peso_kg for b in bobinas}
    idx = 0

    for comp, peso in alocacoes:
        peso_rest = peso
        while peso_rest > 1e-6 and idx < len(bobinas):
            b = bobinas[idx]
            disp = restante_bobina[b.id]
            if disp <= 1e-6:
                idx += 1
                continue
            usar = min(peso_rest, disp)
            planos.append(
                Plano(
                    material=grupo["material"],
                    largura_bobina_mm=grupo["largura"],
                    espessura_mm=grupo["espessura"],
                    larguras=tuple(sorted(comp, reverse=True)),
                    peso_alocado_kg=usar,
                    bobina_id=b.id,
                )
            )
            restante_bobina[b.id] -= usar
            peso_rest -= usar
            if restante_bobina[b.id] <= 1e-6:
                idx += 1

    return planos
