import asyncio
import csv
import re
import httpx
import pandas as pd

INPUT_CSV = "dominios.csv"      # CSV com coluna "Dominio"
OUTPUT_CSV = "resultado.csv"
CONCURRENCY = 100                # requisições simultâneas
TIMEOUT = 10                     # segundos por requisição

async def testar(client, sem, dominio):
    url = f"https://www.{dominio}"
    async with sem:
        for tentativa_url in [url, f"http://www.{dominio}", f"https://{dominio}"]:
            try:
                r = await client.get(tentativa_url, follow_redirects=True, timeout=TIMEOUT)
                if r.status_code < 400:
                    return dominio, "OK", r.status_code, str(r.url)
                ultimo_status = r.status_code
            except httpx.ConnectError:
                ultimo_status = "DNS/Conexao"
            except httpx.TimeoutException:
                ultimo_status = "Timeout"
            except Exception as e:
                ultimo_status = type(e).__name__
        return dominio, "FALHA", ultimo_status, ""

def _norm(dominio):
    # tira "http(s)://" e caminho, mantendo so o host (o "www." e tratado em testar)
    d = re.sub(r"^https?://", "", dominio.strip(), flags=re.I).strip("/")
    return d.split("/")[0]

def carregar_dominios(caminho):
    # Excel pt-BR exporta com ";" e cp1252, e as vezes com campos extras sem aspas.
    # Usa o modulo csv (tolera linhas com nº de colunas variavel) e le a coluna do dominio.
    texto = None
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(caminho, encoding=enc, newline="") as fh:
                texto = fh.read()
            break
        except UnicodeDecodeError:
            continue
    if texto is None:
        raise SystemExit(f"Nao consegui ler {caminho} (tente salvar como 'CSV UTF-8').")
    linhas = texto.splitlines()
    if not linhas:
        return []
    sep = max([";", ",", "\t"], key=linhas[0].count)
    leitor = csv.reader(linhas, delimiter=sep)
    cabecalho = next(leitor, [])
    idx = next((i for i, nome in enumerate(cabecalho)
                if nome.strip().lower() in ("dominio", "domínio", "site", "url")), 0)
    if idx == 0 and cabecalho and cabecalho[0].strip().lower() not in ("dominio", "domínio"):
        print(f"Aviso: coluna 'Dominio' nao encontrada; usando '{cabecalho[0]}'.")
    dominios = []
    for linha in leitor:
        if len(linha) > idx:
            d = _norm(linha[idx])
            if d:
                dominios.append(d)
    return dominios

async def main():
    dominios = carregar_dominios(INPUT_CSV)
    sem = asyncio.Semaphore(CONCURRENCY)
    limits = httpx.Limits(max_connections=CONCURRENCY, max_keepalive_connections=20)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; SiteCheck/1.0)"}

    async with httpx.AsyncClient(limits=limits, headers=headers, verify=False) as client:
        tarefas = [testar(client, sem, d) for d in dominios]
        resultados = []
        for i, coro in enumerate(asyncio.as_completed(tarefas), 1):
            resultados.append(await coro)
            if i % 200 == 0:
                print(f"{i}/{len(dominios)}")

    out = pd.DataFrame(resultados, columns=["Dominio", "Status", "Codigo", "URL_Final"])
    out.to_csv(OUTPUT_CSV, index=False)
    print(f"Pronto. {len(out)} linhas em {OUTPUT_CSV}")
    print(out["Status"].value_counts())

if __name__ == "__main__":
    asyncio.run(main())
