
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
import uvicorn
import asyncio

app = FastAPI()

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todas as origens
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos os métodos
    allow_headers=["*"],  # Permite todos os headers
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "API do Robô está online."}

@app.get("/executar")
async def executar_robo(
    checkin: str = Query("2025-07-28"),
    checkout: str = Query("2025-07-30"),
    hospedes: int = Query(2)
):
    url = f"https://www.booking.com/hotel/br/eco-resort-praia-dos-carneiros.html?checkin={checkin}&checkout={checkout}&group_adults={hospedes}&group_children=0&no_rooms=1&selected_currency=BRL"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url, timeout=60000)
            await page.wait_for_selector('[data-block-id="hotel_rooms"]', timeout=15000)

            dados = await page.locator('[data-block-id="hotel_rooms"] .hprt-roomtype-icon-link').all_inner_texts()
            precos = await page.locator('[data-block-id="hotel_rooms"] .bui-price-display__value').all_inner_texts()

            resultado = []
            for i in range(min(len(dados), len(precos))):
                resultado.append({
                    "quarto": dados[i].strip(),
                    "preco": precos[i].strip()
                })

            await browser.close()
            return {"status": "ok", "resultado": resultado}

    except Exception as e:
        return {"status": "erro", "erro": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
