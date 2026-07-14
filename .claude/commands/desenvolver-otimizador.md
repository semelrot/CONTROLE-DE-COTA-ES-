---
description: Prompt completo para o Claude Code desenvolver todo o Otimizador de Composicao de Corte de Aco (PCP)
---

# TAREFA: Desenvolver o Otimizador de Composição de Corte de Aço Carbono (PCP)

Você vai construir (ou evoluir, se já existir) um sistema de **PCP** para uma empresa
de **service center / distribuição de aço carbono** que faz **corte e recorte de aço
em bobina, chapa, tiras e blanks**. O sistema calcula a **melhor composição de corte**
para atender uma necessidade expressa em **peso**, a partir do **estoque de bobinas**,
com o **maior aproveitamento** e a **menor perda** possível, e compara **peso da
necessidade × peso disponível em estoque**.

Trabalhe de forma incremental: implemente, **rode/valide de verdade** (não só escreva
código), e só então siga. Todo código, comentários e interface em **português**.

---

## 1. Contexto e conceito central (leia antes de codar)

- O corte longitudinal de bobina em tiras chama-se **slitting**; o corte transversal em
  chapas chama-se **cut-to-length (CTL)**. Uma **composição** (padrão de corte) é um
  conjunto de larguras posicionadas lado a lado ao longo da largura da bobina.
- **Peso proporcional à largura:** dentro de uma bobina de largura `Wc`, o peso se
  distribui proporcionalmente à largura. Uma tira de largura `w` rendida ao longo de
  toda a bobina rende, em peso, `peso_bobina × w / Wc`. Vale independentemente da
  espessura/comprimento.
- **Consequência:** tira e chapa são **equivalentes no nível de peso** para a composição
  (a diferença — corte transversal em chapas — é um passo posterior). Isso permite, na
  **mesma bobina**, rodar parte em tira e parte em chapa ("aliviar a bobina em duas e
  fazer recortes diferentes").
- **Regra física:** `Σ(larguras da composição) + refilo_de_borda ≤ largura_da_bobina`.
  O que sobra é a **perda (refilo/scrap)**.
- Peso do aço carbono: densidade 7,85 g/cm³ → `peso_por_metro(kg/m) = largura_mm ×
  espessura_mm × 7,85 / 1000`.

---

## 2. Requisitos funcionais

1. **Entrada:** o usuário preenche (a) o **estoque de bobinas-mãe** (id, material/liga,
   largura, espessura, peso) e (b) a **necessidade** (material, tipo `tira`/`chapa`,
   largura, peso necessário e, opcionalmente, peso já pronto em estoque).
2. **Geração de composições:** montar todos os padrões de corte **maximais** (larguras
   iguais ou diferentes) que cabem na largura útil da bobina, respeitando **refilo
   mínimo de borda** e **número máximo de facas**. Evitar explosão combinatória (só
   padrões bem preenchidos; trava de segurança na quantidade).
3. **Otimização (exata):** decidir **quanto peso** de cada bobina roda em cada composição
   para atender o peso pedido de cada largura, **minimizando o material consumido**
   (logo, a perda). Usar **programação linear com PuLP + solver CBC**. Só materiais/
   espessuras compatíveis podem compartilhar composição.
4. **Necessidade × disponível:** para cada item, calcular **produzido**, **falta**
   (peso que o estoque não cobre → comprar/repor) e **sobra** (excedente). Usar variável
   de folga penalizada para o modelo sempre ser viável e revelar a falta.
5. **Aliviar bobina:** ao mapear as composições em bobinas físicas, permitir que uma
   mesma bobina rode **mais de uma composição** (partição por peso), inclusive
   misturando tira e chapa.
6. **Saída/indicadores:** peso necessário, peso consumido, peso produzido (útil), **perda
   (kg e %)**, **aproveitamento global (%)**, falta e sobra totais; e, por bobina, a
   composição escolhida, peso alocado, comprimento (m), aproveitamento e perda.

---

## 3. Parâmetros operacionais (configuráveis)

- Refilo mínimo por borda (mm).
- Número máximo de facas (tiras) por composição.
- Largura mínima de tira aceita pela slitter (mm).
- (Evolução) Peso mínimo por corrida e custo de troca de facas (setups).

---

## 4. Arquitetura e stack

- **Python 3.11+**, **PuLP** (solver CBC), **pandas**, **Streamlit** (interface).
- Estrutura sugerida:
  ```
  otimizador_corte/
    __init__.py        # exporta a API publica
    modelos.py         # dataclasses: BobinaMae, Pedido, Parametros, Plano,
                       #   ItemResultado, Resultado + calculo de peso
    engine.py          # gerar_composicoes(...) + otimizar(...)
    dados_exemplo.py   # dados de demonstracao
    cli.py             # relatorio em texto (python -m otimizador_corte.cli)
    README.md
  app.py               # interface visual (Streamlit)
  requirements.txt
  otimizar.sh          # comando unico: instala deps e abre a interface
  ```
- **Camadas do problema** (implementar em ordem):
  1. Nível 2a — motor de **slitting 1.5D** por peso (MVP; prioridade).
  2. Nível 1 — **partição da bobina** (quanto peso vai para cada composição/processo).
  3. Nível 2b — **CTL/chapa** com apara de ponta específica.
  4. Nível 3 — **nesting 2D** para blanks (peças irregulares).

---

## 5. Interface visual (Streamlit) — layout limpo e de fácil entendimento

- Duas tabelas editáveis (`st.data_editor`): **estoque de bobinas** e **necessidade**.
- Barra lateral com os **parâmetros**.
- Botão **"Otimizar composição"**.
- Resultado: **cartões de indicadores** (necessidade, consumido, aproveitamento, perda,
  falta), **desenho de cada composição por bobina** (barra horizontal proporcional às
  larguras, com o refilo hachurado) e **tabela de atendimento por item**.
- Aviso claro quando houver **falta de material**.

---

## 6. Acesso: comando único e Claude Code

- `otimizar.sh`: instala dependências na primeira vez e abre a interface
  (`streamlit run app.py`); `otimizar.sh cli` roda o relatório no terminal.
- Slash command `.claude/commands/otimizar.md` para abrir o otimizador pelo Claude Code.

---

## 7. Critérios de aceite (valide rodando)

- `python -m otimizador_corte.cli` roda e imprime o relatório com aproveitamento,
  perda e atendimento por item.
- Com os dados de exemplo, o atendimento dos itens deve fechar em ~100% e o
  aproveitamento global deve ficar alto (> 90%).
- Uma **mesma bobina** deve aparecer rodando **composições diferentes** (prova do
  "aliviar bobina").
- Com **estoque insuficiente**, o sistema **não quebra** e reporta a **falta (kg)** por
  item.
- `app.py` sobe sem erro (`streamlit run app.py`, HTTP 200) e renderiza os resultados.

---

## 8. Roadmap (implementar após o MVP, se solicitado)

- Peso mínimo por corrida (semi-contínuo) e custo de setup (troca de facas) → variáveis
  binárias no modelo.
- Apara de ponta do corte transversal (CTL) para chapas.
- Nesting 2D para blanks.
- Persistência (banco) de estoque/pedidos e importação/exportação por planilha.
- Relatório imprimível (PDF) da programação por bobina.

---

**Comece pelo MVP (seções 1–7), rodando e validando cada etapa. Ao final, faça commit
com mensagem descritiva e mostre o resumo do que foi entregue.**
