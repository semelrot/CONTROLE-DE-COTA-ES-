"""
Otimizador de Composicao de Corte de Aco Carbono.

Modulo de PCP que calcula a melhor composicao de corte (slitting / chapa) para
atender uma necessidade em peso a partir do estoque de bobinas, maximizando o
aproveitamento e minimizando a perda.
"""
from .modelos import (
    BobinaMae,
    Pedido,
    Parametros,
    Plano,
    ItemResultado,
    Resultado,
    peso_por_metro,
)
from .engine import otimizar, gerar_composicoes

__all__ = [
    "BobinaMae",
    "Pedido",
    "Parametros",
    "Plano",
    "ItemResultado",
    "Resultado",
    "peso_por_metro",
    "otimizar",
    "gerar_composicoes",
]
