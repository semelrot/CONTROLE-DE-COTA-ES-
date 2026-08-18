# Localizador de certificados de qualidade de material

Encontra, dentro de uma árvore de diretórios (ex.: `Y:\`), quais PDFs são
certificados de qualidade de material — e separa dos que não são (notas
fiscais, cotações, manuais, catálogos, FISPQ, certificados ISO da empresa).

Roda **na máquina que tem acesso ao caminho**. A varredura é local ao seu
Windows/rede; nada é enviado para fora.

## Uso rápido

```powershell
# 1. Reconhecimento: quais padrões de nome existem? (não abre nenhum PDF)
py ferramentas\certificados\analisar_padroes.py -r "Y:\"

# 2. Varredura completa, abrindo só amostras de cada padrão ambíguo
py ferramentas\certificados\localizar_certificados.py -r "Y:\" ^
   --por-padrao -s certificados.csv --saida-padroes padroes.csv
```

Abra `certificados.csv` no Excel (separador `;`, UTF-8) e filtre pela coluna
`classificacao`.

Sem Python instalado, use a versão PowerShell — classifica só por nome/pasta:

```powershell
.\ferramentas\certificados\Localizar-Certificados.ps1 -Raiz "Y:\" -Abrir
```

Para ler o conteúdo dos PDFs (mais preciso), instale a biblioteca:
`pip install pypdf`. Sem ela, a ferramenta avisa e cai no modo nome/pasta.

## Como decide

Três níveis de evidência, somados com peso maior quando o termo aparece no
**nome do arquivo** do que quando aparece no corpo:

| Nível | Exemplos | Efeito |
|---|---|---|
| Forte | "certificado de qualidade", "certificado de matéria-prima", "mill test certificate", "EN 10204", "MTC/MTR", "análise química" | define o documento |
| Apoio | corrida / heat number, propriedades mecânicas, ensaio de tração, limite de escoamento, dureza, Charpy, ASTM/NBR/AISI/SAE, tratamento térmico | corrobora |
| Veto | nota fiscal, DANFE, boleto, cotação, orçamento, FISPQ, ISO 9001/14001, manual, catálogo, certidão negativa, certificado de conclusão | derruba para `NAO` |

**Tabela de composição química.** O sinal mais discriminante não é uma
palavra, é a estrutura: vários símbolos de elemento (`C Si Mn P S Cr Ni Mo…`)
como tokens isolados **junto com** valores decimais no formato de percentual de
liga (`0,18` / `0.045`). Detectada com 5+ elementos, ela classifica o PDF como
certificado mesmo que o arquivo se chame `0001_0042.pdf` e a palavra
"certificado" não apareça em lugar nenhum. É o que resolve as digitalizações.

Um veto não derruba um certificado legítimo que cite a nota fiscal ou o pedido
de compra: termos exclusivos de material (e uma tabela de composição completa)
são imunes ao veto.

### Classificações

| Valor | Significado |
|---|---|
| `CERTIFICADO` | alta confiança |
| `PROVAVEL` | quase certo, vale conferir por amostragem |
| `REVISAR` | sinais fracos ou PDF sem texto extraível (digitalizado) — precisa de olho humano ou OCR |
| `NAO` | outro tipo de documento |
| `ERRO` | PDF ilegível/corrompido; ver a coluna `obs` |

## Padrões de nome: por que isso economiza a varredura

Abrir cada PDF num drive de rede é o gargalo. Mas arquivos gerados pelo mesmo
processo compartilham o molde do nome. A ferramenta reduz cada nome a uma
**assinatura** (números viram `<n>`, datas viram `<data>`), agrupa e decide o
grupo inteiro:

```
CQ_4471-2024.pdf ┐
CQ_4472-2024.pdf ├─► "cq <n> <data>.pdf"  (40 arquivos)
CQ_4473-2024.pdf ┘
```

- Padrão **conclusivo pelo nome** → nenhum arquivo é aberto.
  Vale para `CERTIFICADO` (o nome afirma o que é) e para `NAO` **com veto**
  (o nome afirma que é outra coisa: "Nota Fiscal 88213.pdf").
- Padrão **ambíguo** → abre até `--amostra` arquivos (padrão: 3), espalhados
  pelo início/meio/fim do grupo, e propaga o veredito aos demais.

`NAO` por nome genérico **não** é conclusivo: `scan_2025-03-11_07.pdf` não diz
nada, então o grupo é obrigatoriamente amostrado. É exatamente o caso em que a
composição química no conteúdo decide — pular esses arquivos perderia
certificados digitalizados em silêncio.

Num teste com 99 PDFs em 5 padrões: **6 aberturas** em vez de 99 (94% a menos),
com os 30 scans de nome genérico corretamente identificados como certificados.

As colunas `origem` e `arquivos_no_padrao` do CSV registram como cada linha foi
decidida — `padrao-nome` (não aberto), `amostra-lida` (aberto),
`padrao-amostra` (inferido do grupo). Nada é classificado por atalho sem que o
CSV diga que foi.

## Opções principais

| Opção | Para quê |
|---|---|
| `-r, --raiz` | caminho inicial (padrão `Y:\`) |
| `-s, --saida` | CSV de saída, uma linha por PDF |
| `--saida-padroes` | CSV resumido por padrão de nomenclatura |
| `--por-padrao` | agrupa e abre só amostras (recomendado em rede) |
| `-a, --amostra` | arquivos abertos por padrão ambíguo (padrão 3) |
| `--so-nome` | nunca abre PDF; só nome/pasta (varredura mais rápida) |
| `-p, --paginas` | páginas lidas por PDF (padrão 2) |
| `-t, --threads` | leituras simultâneas (padrão 8) |
| `--minimo` | classe mínima gravada no CSV (padrão `REVISAR`) |
| `--profundidade` | limita níveis de subpasta |
| `--ignorar` | pastas a pular |

## Ajuste

Os termos e pesos ficam no topo de `classificador.py`. Se a sua nomenclatura
usar convenções próprias (código de fornecedor, sigla interna), acrescente o
termo na lista correspondente e rode a bateria de testes:

```bash
python3 ferramentas/certificados/testar_classificador.py
```

## Arquivos

| Arquivo | Papel |
|---|---|
| `classificador.py` | heurística de decisão (termos, pesos, vetos, composição química) |
| `padroes.py` | assinatura de nome/pasta, agrupamento e amostragem |
| `localizar_certificados.py` | CLI da varredura e geração do CSV |
| `analisar_padroes.py` | reconhecimento dos padrões, sem abrir arquivos |
| `Localizar-Certificados.ps1` | versão PowerShell, sem dependências, nome/pasta |
| `testar_classificador.py` | 18 casos de teste da heurística |

## Limites conhecidos

- PDF digitalizado sem camada de texto sai como `REVISAR`: a ferramenta não faz
  OCR. Para resolver esses, rode um OCR (ex.: OCRmyPDF) antes da varredura.
- A versão PowerShell não abre PDFs, então não detecta composição química —
  use-a como triagem, não como veredito.
- O agrupamento por assinatura separa `cq <n>.pdf` de `cq <n> <data>.pdf`. São
  grupos distintos, o que apenas gera um pouco mais de amostragem.
