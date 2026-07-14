# Otimizador de Composição de Corte — Aço Carbono

Ferramenta de **PCP** que calcula a **melhor composição de corte** (slitting de tiras
e chapas) para atender uma necessidade expressa em **peso**, a partir do **estoque de
bobinas-mãe**, maximizando o **aproveitamento** e minimizando a **perda (refilo)**.

Responde à pergunta central do planejamento:
> *"Dada esta carteira de pedidos (em kg) e este estoque de bobinas (em kg), qual a
> melhor composição de corte — misturando tira e chapa, aliviando bobinas quando
> compensar — com o maior aproveitamento, e o que falta ou sobra?"*

---

## Como funciona

1. **Geração de composições** (`engine.gerar_composicoes`): monta os padrões de corte
   — conjuntos de larguras (iguais ou diferentes) que cabem na largura da bobina,
   respeitando o **refilo mínimo de borda** e o **número máximo de facas**.
2. **Seleção ótima** (`engine.otimizar`): via programação linear (PuLP + solver CBC),
   decide **quanto peso** de cada bobina roda em cada composição para atender o peso
   pedido de cada largura, **minimizando o material consumido** (logo, a perda).

### Conceito-chave: peso proporcional à largura
Dentro de uma bobina de largura `Wc`, o peso se distribui proporcionalmente à largura.
Uma tira de largura `w` rende, em peso, `peso_bobina × w / Wc`. Por isso **tira e chapa
são equivalentes no nível de peso** — a diferença (corte transversal em chapas) é um
passo posterior. Isso permite, na **mesma bobina**, rodar parte em tira e parte em
chapa ("aliviar a bobina em duas e fazer recortes diferentes").

### Necessidade × disponível
A folga (`falta`) de cada item mostra o **peso da necessidade que o estoque não cobre**
— o comparativo necessidade × material disponível que o PCP precisa.

---

## Como usar

### Interface visual (recomendado)
```bash
pip install -r requirements.txt
streamlit run app.py
```
Preencha o **estoque de bobinas** e a **necessidade** (tabelas editáveis), ajuste os
**parâmetros** na barra lateral e clique em **Otimizar composição**. O resultado mostra
os indicadores, o desenho de cada composição por bobina e o atendimento por item.

### Linha de comando (relatório em texto)
```bash
python -m otimizador_corte.cli
```

### Como biblioteca (integração com outros sistemas)
```python
from otimizador_corte import BobinaMae, Pedido, Parametros, otimizar

bobinas = [BobinaMae("BOB-001", "SAE1008", 1200, 2.0, 12000)]
pedidos = [Pedido("SAE1008", "tira", 300, 6000)]
res = otimizar(bobinas, pedidos, Parametros(refilo_por_lado_mm=6, num_max_facas=12))

print(res.aproveitamento_pct, res.perda_kg, res.falta_total_kg)
for pl in res.planos:
    print(pl.bobina_id, pl.larguras, pl.peso_alocado_kg)
```

---

## Estrutura

| Arquivo | Papel |
|---|---|
| `modelos.py` | Estruturas de dados (bobina, pedido, plano, resultado) e cálculo de peso. |
| `engine.py` | Geração de composições + otimização (PuLP/CBC). |
| `dados_exemplo.py` | Dados de demonstração (substitua pelos seus valores reais). |
| `cli.py` | Relatório em texto no terminal. |
| `../app.py` | Interface visual (Streamlit). |

---

## Escopo atual e evolução (roteiro)

**Já contempla (MVP):**
- Composições com larguras iguais ou diferentes, por material/espessura.
- Demanda em peso × estoque em peso, com falta/sobra por item.
- Tira e chapa na mesma bobina (partição por peso — "aliviar a bobina").
- Otimização exata (mínimo consumo de material / máxima utilização).

**Próximos passos sugeridos:**
- Peso mínimo por corrida (semi-contínuo) e custo de troca de facas (setups).
- Apara de ponta específica do corte transversal (CTL) para chapas.
- Nesting 2D para blanks (peças irregulares).
- Persistência do estoque/pedidos em banco e importação de planilha.
