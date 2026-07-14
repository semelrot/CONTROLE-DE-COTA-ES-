"""
Interface visual do Otimizador de Composicao de Corte de Aco Carbono.

Como rodar:
    pip install -r requirements.txt
    streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from otimizador_corte.modelos import BobinaMae, Pedido, Parametros
from otimizador_corte.engine import otimizar
from otimizador_corte.dados_exemplo import (
    BOBINAS_EXEMPLO,
    PEDIDOS_EXEMPLO,
    PARAMETROS_EXEMPLO,
)

st.set_page_config(
    page_title="Otimizador de Corte de Aco",
    page_icon="🪚",
    layout="wide",
)


def _cor(i: int) -> str:  # paleta simples e legivel
    cores = ["#2563eb", "#0891b2", "#059669", "#7c3aed", "#d97706",
             "#dc2626", "#4f46e5", "#0d9488"]
    return cores[i % len(cores)]

# ------------------------------- estilo ------------------------------------ #
st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem; max-width: 1250px;}
      h1 {font-size: 1.7rem;}
      .strip {display:flex; height:26px; border:1px solid #cbd5e1; border-radius:4px;
              overflow:hidden; font-size:11px; color:#fff; font-weight:600;}
      .strip span {display:flex; align-items:center; justify-content:center;
                   border-right:1px solid rgba(255,255,255,.35);}
      .refilo {background:repeating-linear-gradient(45deg,#e2e8f0,#e2e8f0 4px,#cbd5e1 4px,#cbd5e1 8px);
               color:#475569;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🪚 Otimizador de Composição de Corte — Aço Carbono")
st.caption(
    "Preencha o estoque de bobinas e a necessidade (em peso). O sistema calcula a "
    "melhor composição de corte (tiras e chapas), maximizando o aproveitamento e "
    "minimizando a perda, e mostra a necessidade × material disponível."
)

# ------------------------------ parametros --------------------------------- #
with st.sidebar:
    st.header("⚙️ Parâmetros da linha")
    refilo = st.number_input("Refilo por borda (mm)", 0.0, 100.0,
                             PARAMETROS_EXEMPLO.refilo_por_lado_mm, 0.5)
    max_facas = st.number_input("Nº máximo de facas (tiras)", 1, 40,
                                PARAMETROS_EXEMPLO.num_max_facas, 1)
    larg_min = st.number_input("Largura mínima de tira (mm)", 1.0, 500.0,
                               PARAMETROS_EXEMPLO.largura_min_tira_mm, 1.0)
    st.divider()
    st.markdown("**Como usar**\n\n1. Ajuste o estoque de bobinas.\n2. Ajuste a "
                "necessidade.\n3. Clique em **Otimizar composição**.")

# ------------------------------ entradas ----------------------------------- #
col1, col2 = st.columns(2)

with col1:
    st.subheader("🧱 Estoque de bobinas-mãe")
    df_bob = pd.DataFrame(
        [{"id": b.id, "material": b.material, "largura_mm": b.largura_mm,
          "espessura_mm": b.espessura_mm, "peso_kg": b.peso_kg}
         for b in BOBINAS_EXEMPLO]
    )
    df_bob = st.data_editor(
        df_bob, num_rows="dynamic", use_container_width=True, key="bob",
        column_config={
            "peso_kg": st.column_config.NumberColumn("peso_kg", format="%.0f"),
        },
    )

with col2:
    st.subheader("📋 Necessidade (pedidos)")
    df_ped = pd.DataFrame(
        [{"material": p.material, "tipo": p.tipo, "largura_mm": p.largura_mm,
          "peso_kg": p.peso_kg, "peso_estoque_kg": p.peso_estoque_kg,
          "descricao": p.descricao}
         for p in PEDIDOS_EXEMPLO]
    )
    df_ped = st.data_editor(
        df_ped, num_rows="dynamic", use_container_width=True, key="ped",
        column_config={
            "tipo": st.column_config.SelectboxColumn("tipo", options=["tira", "chapa"]),
        },
    )

# ------------------------------ otimizar ----------------------------------- #
if st.button("🚀 Otimizar composição", type="primary", use_container_width=True):
    try:
        bobinas = [
            BobinaMae(str(r.id), str(r.material), float(r.largura_mm),
                      float(r.espessura_mm), float(r.peso_kg))
            for r in df_bob.itertuples() if pd.notna(r.id) and r.peso_kg
        ]
        pedidos = [
            Pedido(str(r.material), str(r.tipo), float(r.largura_mm),
                   float(r.peso_kg),
                   peso_estoque_kg=float(getattr(r, "peso_estoque_kg", 0) or 0),
                   descricao=str(getattr(r, "descricao", "") or ""))
            for r in df_ped.itertuples() if pd.notna(r.material) and r.peso_kg
        ]
        par = Parametros(refilo_por_lado_mm=refilo, num_max_facas=int(max_facas),
                         largura_min_tira_mm=larg_min)
        res = otimizar(bobinas, pedidos, par)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Erro ao otimizar: {exc}")
        st.stop()

    st.divider()
    st.subheader("📊 Resultado")

    m = st.columns(5)
    m[0].metric("Peso necessário", f"{res.peso_necessario_kg:,.0f} kg".replace(",", "."))
    m[1].metric("Peso consumido", f"{res.peso_consumido_kg:,.0f} kg".replace(",", "."))
    m[2].metric("Aproveitamento", f"{res.aproveitamento_pct:.1f}%")
    m[3].metric("Perda (refilo)", f"{res.perda_kg:,.0f} kg".replace(",", "."),
                f"{res.perda_pct:.1f}%", delta_color="inverse")
    m[4].metric("Falta de material", f"{res.falta_total_kg:,.0f} kg".replace(",", "."),
                delta_color="inverse")

    if res.falta_total_kg > 1:
        st.warning(f"O estoque atual não cobre toda a necessidade. "
                   f"Falta produzir/comprar **{res.falta_total_kg:,.0f} kg**."
                   .replace(",", "."))
    else:
        st.success("Necessidade totalmente atendida pelo estoque disponível. ✅")

    # ---- programacao por bobina, com desenho da composicao ---- #
    st.markdown("#### 🪚 Programação por bobina (composições)")
    for pl in res.planos:
        larguras = list(pl.larguras)
        Wc = pl.largura_bobina_mm
        partes = "".join(
            f'<span style="width:{w/Wc*100:.3f}%;background:{_cor(i)}">{w:g}</span>'
            for i, w in enumerate(larguras)
        )
        refilo_pct = pl.perda_borda_mm / Wc * 100
        partes += (f'<span class="refilo" style="width:{refilo_pct:.3f}%">'
                   f'{pl.perda_borda_mm:g}</span>')
        st.markdown(
            f"**{pl.bobina_id}** · {pl.material} {Wc:g}×{pl.espessura_mm:g} mm · "
            f"{pl.peso_alocado_kg:,.0f} kg · {pl.comprimento_m():,.0f} m · "
            f"aprov. **{pl.aproveitamento*100:.1f}%** · perda {pl.perda_kg:,.0f} kg"
            .replace(",", "."),
        )
        st.markdown(f'<div class="strip">{partes}</div>', unsafe_allow_html=True)
        st.write("")

    # ---- atendimento por item ---- #
    st.markdown("#### 📋 Atendimento por item")
    df_res = pd.DataFrame([
        {"material": i.material, "largura (mm)": i.largura_mm, "tipo": i.tipo,
         "necessidade (kg)": round(i.necessidade_kg),
         "produzido (kg)": round(i.produzido_kg),
         "falta (kg)": round(i.falta_kg), "sobra (kg)": round(i.sobra_kg),
         "atendimento (%)": round(i.atendimento_pct, 1)}
        for i in res.itens
    ])
    st.dataframe(df_res, use_container_width=True, hide_index=True)
