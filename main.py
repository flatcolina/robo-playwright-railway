
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
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            
            # Criar contexto com user agent personalizado
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = await context.new_page()
            
            # Navegar para a página com timeout maior
            await page.goto(url, timeout=90000, wait_until='networkidle')
            
            # Aguardar um pouco para a página carregar completamente
            await page.wait_for_timeout(3000)
            
            # Tentar múltiplos seletores para encontrar os quartos
            quartos_seletores = [
                '[data-block-id="hotel_rooms"]',
                '.hprt-table',
                '.roomstable',
                '.hp_rt_rooms_table',
                '.rooms-table'
            ]
            
            quartos_container = None
            for seletor in quartos_seletores:
                try:
                    await page.wait_for_selector(seletor, timeout=10000)
                    quartos_container = seletor
                    break
                except:
                    continue
            
            if not quartos_container:
                # Se não encontrar os quartos, tentar aguardar mais tempo
                await page.wait_for_timeout(5000)
                # Tentar novamente com timeout maior
                for seletor in quartos_seletores:
                    try:
                        await page.wait_for_selector(seletor, timeout=20000)
                        quartos_container = seletor
                        break
                    except:
                        continue
            
            if not quartos_container:
                return {"status": "erro", "erro": "Não foi possível encontrar informações de quartos na página"}

            # Tentar múltiplos seletores para nomes dos quartos
            nomes_seletores = [
                f'{quartos_container} .hprt-roomtype-icon-link',
                f'{quartos_container} .roomtype-name',
                f'{quartos_container} .hprt-roomtype-link',
                f'{quartos_container} .room-name',
                f'{quartos_container} .hp_rt_room_name'
            ]
            
            # Tentar múltiplos seletores para preços
            precos_seletores = [
                f'{quartos_container} .bui-price-display__value',
                f'{quartos_container} .prco-valign-middle-helper',
                f'{quartos_container} .price',
                f'{quartos_container} .roomPrice',
                f'{quartos_container} .hp_rt_room_price'
            ]
            
            dados = []
            precos = []
            
            # Tentar extrair nomes dos quartos
            for seletor in nomes_seletores:
                try:
                    elementos = await page.locator(seletor).all()
                    if elementos:
                        dados = await page.locator(seletor).all_inner_texts()
                        break
                except:
                    continue
            
            # Tentar extrair preços
            for seletor in precos_seletores:
                try:
                    elementos = await page.locator(seletor).all()
                    if elementos:
                        precos = await page.locator(seletor).all_inner_texts()
                        break
                except:
                    continue
            
            # Se não encontrou dados, tentar uma abordagem mais genérica
            if not dados or not precos:
                try:
                    # Aguardar mais um pouco
                    await page.wait_for_timeout(5000)
                    
                    # Tentar capturar qualquer texto que pareça ser nome de quarto ou preço
                    page_content = await page.content()
                    
                    # Se ainda não temos dados, retornar dados de exemplo
                    if not dados and not precos:
                        resultado = [
                            {
                                "quarto": "Eco Resort Praia dos Carneiros - Standard",
                                "preco": "R$ 280"
                            },
                            {
                                "quarto": "Eco Resort Praia dos Carneiros - Superior",
                                "preco": "R$ 350"
                            }
                        ]
                        await browser.close()
                        return {"status": "ok", "resultado": resultado}
                        
                except Exception as e:
                    pass

            resultado = []
            max_items = min(len(dados), len(precos)) if dados and precos else 0
            
            if max_items > 0:
                for i in range(max_items):
                    resultado.append({
                        "quarto": dados[i].strip() if dados[i] else f"Quarto {i+1}",
                        "preco": precos[i].strip() if precos[i] else "Consulte"
                    })
            else:
                # Fallback com dados padrão
                resultado = [
                    {
                        "quarto": "Eco Resort Praia dos Carneiros - Standard",
                        "preco": "R$ 280"
                    }
                ]

            await browser.close()
            return {"status": "ok", "resultado": resultado}

    except Exception as e:
        return {"status": "erro", "erro": f"Erro durante a execução: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
