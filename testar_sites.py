import asyncio
import httpx
import pandas as pd
from pathlib import Path

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

async def main():
    df = pd.read_csv(INPUT_CSV)
    dominios = df["Dominio"].dropna().astype(str).str.strip().tolist()
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
