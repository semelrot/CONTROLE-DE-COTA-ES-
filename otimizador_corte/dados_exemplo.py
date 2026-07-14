"""Dados de exemplo para demonstrar o otimizador (ajuste com seus valores reais)."""
from .modelos import BobinaMae, Pedido, Parametros

BOBINAS_EXEMPLO = [
    BobinaMae(id="BOB-001", material="SAE1008", largura_mm=1200, espessura_mm=2.00, peso_kg=12000),
    BobinaMae(id="BOB-002", material="SAE1008", largura_mm=1200, espessura_mm=2.00, peso_kg=9500),
    BobinaMae(id="BOB-003", material="SAE1008", largura_mm=1000, espessura_mm=2.00, peso_kg=8000),
    BobinaMae(id="BOB-004", material="LNE380",  largura_mm=1250, espessura_mm=3.00, peso_kg=15000),
]

PEDIDOS_EXEMPLO = [
    # material, tipo, largura_mm, peso_kg
    Pedido(material="SAE1008", tipo="tira",  largura_mm=300, peso_kg=6000, descricao="Perfilado A"),
    Pedido(material="SAE1008", tipo="tira",  largura_mm=250, peso_kg=4500, descricao="Perfilado B"),
    Pedido(material="SAE1008", tipo="chapa", largura_mm=200, peso_kg=3000, comprimento_mm=2000, descricao="Chapa 200x2000"),
    Pedido(material="SAE1008", tipo="tira",  largura_mm=180, peso_kg=2000, descricao="Tira estreita"),
    Pedido(material="LNE380",  tipo="chapa", largura_mm=400, peso_kg=8000, comprimento_mm=3000, descricao="Chapa estrutural"),
    Pedido(material="LNE380",  tipo="tira",  largura_mm=420, peso_kg=5000, descricao="Longarina"),
]

PARAMETROS_EXEMPLO = Parametros(
    refilo_por_lado_mm=6.0,
    num_max_facas=12,
    largura_min_tira_mm=20.0,
)
