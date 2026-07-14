"""
Modelos de dados do Otimizador de Composição de Corte de Aço Carbono.

Todos os pesos estão em quilogramas (kg) e todas as dimensoes em milimetros (mm).
A conversao largura/espessura -> peso usa a densidade do aco carbono.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Densidade do aco carbono: 7,85 g/cm3 = 7850 kg/m3.
# Peso por metro linear (kg/m) de uma tira = largura_mm * espessura_mm * 7,85 / 1000.
DENSIDADE_ACO = 7.85


def peso_por_metro(largura_mm: float, espessura_mm: float) -> float:
    """Peso (kg) de 1 metro linear de uma tira de aco carbono."""
    return largura_mm * espessura_mm * DENSIDADE_ACO / 1000.0


@dataclass
class BobinaMae:
    """Uma bobina-mae disponivel no estoque."""
    id: str
    material: str          # especificacao: liga / qualidade (ex.: "SAE1008", "LNE380")
    largura_mm: float
    espessura_mm: float
    peso_kg: float

    def comprimento_m(self) -> float:
        """Comprimento total (m) da bobina, dado o peso e a secao."""
        kg_m = peso_por_metro(self.largura_mm, self.espessura_mm)
        return self.peso_kg / kg_m if kg_m else 0.0


@dataclass
class Pedido:
    """Um item da necessidade (demanda) do PCP, expresso em PESO."""
    material: str
    tipo: str              # "tira" (corte longitudinal) ou "chapa" (corte transversal / CTL)
    largura_mm: float
    peso_kg: float                          # peso necessario
    comprimento_mm: Optional[float] = None  # comprimento da chapa (apenas informativo p/ "chapa")
    peso_estoque_kg: float = 0.0            # peso ja pronto em estoque (abate da necessidade)
    descricao: str = ""

    @property
    def necessidade_liquida_kg(self) -> float:
        """Peso que realmente precisa ser produzido (necessidade - o que ja existe pronto)."""
        return max(0.0, self.peso_kg - self.peso_estoque_kg)


@dataclass
class Parametros:
    """Parametros operacionais da linha de corte."""
    refilo_por_lado_mm: float = 6.0   # refilo (perda) minimo em cada borda da bobina
    num_max_facas: int = 12           # numero maximo de tiras (facas) por composicao
    largura_min_tira_mm: float = 20.0 # menor largura de tira que a slitter aceita
    max_composicoes: int = 4000       # trava de seguranca na geracao de padroes

    @property
    def refilo_total_mm(self) -> float:
        return 2.0 * self.refilo_por_lado_mm


@dataclass
class Plano:
    """Uma composicao de corte escolhida, aplicada a um grupo/bobina."""
    material: str
    largura_bobina_mm: float
    espessura_mm: float
    larguras: tuple                 # larguras da composicao (as tiras lado a lado)
    peso_alocado_kg: float          # quanto peso de bobina roda nesta composicao
    bobina_id: Optional[str] = None # bobina fisica (quando alocado)

    @property
    def soma_larguras_mm(self) -> float:
        return sum(self.larguras)

    @property
    def perda_borda_mm(self) -> float:
        """Sobra de largura nao aproveitada (refilo + eventual folga)."""
        return self.largura_bobina_mm - self.soma_larguras_mm

    @property
    def aproveitamento(self) -> float:
        """Fracao da largura da bobina que vira produto (0..1)."""
        return self.soma_larguras_mm / self.largura_bobina_mm if self.largura_bobina_mm else 0.0

    @property
    def perda_kg(self) -> float:
        return self.peso_alocado_kg * (1.0 - self.aproveitamento)

    def comprimento_m(self) -> float:
        kg_m = peso_por_metro(self.largura_bobina_mm, self.espessura_mm)
        return self.peso_alocado_kg / kg_m if kg_m else 0.0


@dataclass
class ItemResultado:
    """Atendimento de um item da necessidade."""
    material: str
    largura_mm: float
    tipo: str
    necessidade_kg: float
    produzido_kg: float

    @property
    def falta_kg(self) -> float:
        return max(0.0, self.necessidade_kg - self.produzido_kg)

    @property
    def sobra_kg(self) -> float:
        return max(0.0, self.produzido_kg - self.necessidade_kg)

    @property
    def atendimento_pct(self) -> float:
        if self.necessidade_kg <= 0:
            return 100.0
        return min(100.0, 100.0 * self.produzido_kg / self.necessidade_kg)


@dataclass
class Resultado:
    """Resultado completo da otimizacao."""
    planos: list = field(default_factory=list)          # list[Plano] por bobina
    itens: list = field(default_factory=list)           # list[ItemResultado]
    viavel: bool = True
    mensagem: str = ""

    # ---- indicadores agregados ----
    @property
    def peso_necessario_kg(self) -> float:
        return sum(i.necessidade_kg for i in self.itens)

    @property
    def peso_produzido_kg(self) -> float:
        return sum(p.peso_alocado_kg * p.aproveitamento for p in self.planos)

    @property
    def peso_consumido_kg(self) -> float:
        """Peso de bobina-mae consumido (produto util + refilo)."""
        return sum(p.peso_alocado_kg for p in self.planos)

    @property
    def perda_kg(self) -> float:
        return sum(p.perda_kg for p in self.planos)

    @property
    def perda_pct(self) -> float:
        c = self.peso_consumido_kg
        return 100.0 * self.perda_kg / c if c else 0.0

    @property
    def aproveitamento_pct(self) -> float:
        c = self.peso_consumido_kg
        return 100.0 * self.peso_produzido_kg / c if c else 0.0

    @property
    def falta_total_kg(self) -> float:
        return sum(i.falta_kg for i in self.itens)

    @property
    def sobra_total_kg(self) -> float:
        return sum(i.sobra_kg for i in self.itens)
