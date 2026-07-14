---
description: Instala as dependencias e abre o Otimizador de Composicao de Corte de Aco (interface visual)
---

Execute o comando unico do otimizador de corte de aco carbono:

1. Rode no terminal: `bash otimizar.sh`
2. Isso instala as dependencias (streamlit, pulp, pandas) na primeira vez e abre a
   interface visual no navegador (`streamlit run app.py`).
3. Informe ao usuario a URL local exibida pelo Streamlit (ex.: http://localhost:8501).

Se o usuario pedir apenas o relatorio em texto (sem interface), rode `bash otimizar.sh cli`.
