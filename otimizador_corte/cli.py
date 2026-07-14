"""
Relatorio em texto do otimizador (roda sem interface grafica).

Uso:
    python -m otimizador_corte.cli
"""
from __future__ import annotations

from .dados_exemplo import BOBINAS_EXEMPLO, PEDIDOS_EXEMPLO, PARAMETROS_EXEMPLO
from .engine import otimizar
from .modelos import Resultado


def _kg(v: float) -> str:
    return f"{v:,.0f} kg".replace(",", ".")


def imprimir_relatorio(res: Resultado) -> None:
    print("=" * 68)
    print("  OTIMIZADOR DE COMPOSICAO DE CORTE - RELATORIO")
    print("=" * 68)

    print("\n>> RESUMO (necessidade x disponivel)")
    print(f"   Peso necessario ....... {_kg(res.peso_necessario_kg)}")
    print(f"   Peso consumido ........ {_kg(res.peso_consumido_kg)}")
    print(f"   Peso produzido (util) . {_kg(res.peso_produzido_kg)}")
    print(f"   Perda (refilo) ........ {_kg(res.perda_kg)}  ({res.perda_pct:.1f}%)")
    print(f"   Aproveitamento global . {res.aproveitamento_pct:.1f}%")
    if res.falta_total_kg > 1:
        print(f"   FALTA de material ..... {_kg(res.falta_total_kg)}  (comprar/repor)")
    if res.sobra_total_kg > 1:
        print(f"   Sobra (excedente) ..... {_kg(res.sobra_total_kg)}")

    print("\n>> PROGRAMACAO POR BOBINA (composicoes)")
    for pl in res.planos:
        comp = " + ".join(f"{w:g}" for w in pl.larguras)
        print(
            f"   [{pl.bobina_id}] {pl.material} {pl.largura_bobina_mm:g}x{pl.espessura_mm:g}mm  "
            f"| {comp} mm  | {_kg(pl.peso_alocado_kg)}  "
            f"| aprov {pl.aproveitamento*100:.1f}%  | perda {_kg(pl.perda_kg)}  "
            f"| {pl.comprimento_m():,.0f} m".replace(",", ".")
        )

    print("\n>> ATENDIMENTO POR ITEM")
    for it in res.itens:
        estado = "OK" if it.falta_kg < 1 else f"FALTA {_kg(it.falta_kg)}"
        sobra = f" | sobra {_kg(it.sobra_kg)}" if it.sobra_kg > 1 else ""
        print(
            f"   {it.material} {it.largura_mm:g}mm ({it.tipo}): "
            f"nec {_kg(it.necessidade_kg)} -> prod {_kg(it.produzido_kg)} "
            f"({it.atendimento_pct:.0f}%) [{estado}]{sobra}"
        )
    print("=" * 68)


def main() -> None:
    res = otimizar(BOBINAS_EXEMPLO, PEDIDOS_EXEMPLO, PARAMETROS_EXEMPLO)
    imprimir_relatorio(res)


if __name__ == "__main__":
    main()
