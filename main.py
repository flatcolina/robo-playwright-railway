
from fastapi import FastAPI
import asyncio
from playwright.async_api import async_playwright

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "message": "API do Robô está online."}

@app.get("/executar")
async def executar_robo():
    checkin = "2025-07-28"
    checkout = "2025-07-31"
    hospedes = "5"

    url = (
        "https://www.booking.com/hotel/br/eco-resort-praia-dos-carneiros-ao-lado-da-igrejinha-praia-dos-carneiros1.pt-br.html"
        f"?checkin={checkin}"
        f"&checkout={checkout}"
        f"&group_adults={hospedes}"
        f"&group_children=0"
        f"&no_rooms=1"
        f"&selected_currency=BRL"
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0.0.0 Safari/537.36")
        page = await context.new_page()

        await page.goto(url, timeout=60000)

        try:
            await page.wait_for_selector('.hprt-roomtype-link', timeout=30000)
        except:
            await browser.close()
            return {"erro": "Página não carregou os quartos."}

        quartos = await page.locator('.hprt-roomtype-link').all_text_contents()
        precos = await page.locator('.bui-price-display__value, .prco-valign-middle-helper').all_text_contents()

        await browser.close()

        resultados = []
        for q, p in zip(quartos, precos):
            resultados.append({
                "quarto": q.strip(),
                "preco": p.strip()
            })

        return {"status": "ok", "resultado": resultados}
