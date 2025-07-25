from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
import uvicorn
import asyncio
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    logger.info("🏠 Endpoint raiz acessado")
    return {"status": "ok", "message": "API do Robô está online."}

@app.get("/executar")
async def executar_robo(
    checkin: str = Query("2025-07-28"),
    checkout: str = Query("2025-07-30"),
    hospedes: int = Query(2)
):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"🚀 [{timestamp}] INICIANDO EXECUÇÃO DO ROBÔ")
    logger.info(f"📅 Parâmetros recebidos: checkin={checkin}, checkout={checkout}, hospedes={hospedes}")
    
    # Usar a URL original que funcionava
    url = (
        "https://www.booking.com/hotel/br/eco-resort-praia-dos-carneiros-ao-lado-da-igrejinha-praia-dos-carneiros1.pt-br.html"
        f"?checkin={checkin}"
        f"&checkout={checkout}"
        f"&group_adults={hospedes}"
        f"&group_children=0"
        f"&no_rooms=1"
        f"&selected_currency=BRL"
    )
    logger.info(f"🔗 URL construída: {url}")

    try:
        logger.info("🌐 Iniciando Playwright...")
        async with async_playwright() as p:
            logger.info("🚀 Lançando navegador Chromium...")
            browser = await p.chromium.launch(headless=True)
            logger.info("✅ Navegador lançado com sucesso")
            
            logger.info("👤 Criando contexto com user agent...")
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            logger.info("📄 Nova página criada")
            
            logger.info("🔄 Navegando para a página do Booking.com...")
            await page.goto(url, timeout=60000)
            logger.info("✅ Navegação concluída com sucesso")
            
            try:
                logger.info("🔍 Aguardando seletor '.hprt-roomtype-link'...")
                await page.wait_for_selector('.hprt-roomtype-link', timeout=30000)
                logger.info("✅ Seletor encontrado!")
            except Exception as e:
                logger.error(f"❌ Página não carregou os quartos: {str(e)}")
                await browser.close()
                return {"status": "erro", "erro": "Não consegui realizar a busca, Por favor, entre em contato"}
            
            logger.info("📝 Extraindo nomes dos quartos...")
            quartos = await page.locator('.hprt-roomtype-link').all_text_contents()
            logger.info(f"✅ Quartos encontrados: {quartos}")
            
            logger.info("💰 Extraindo preços...")
            precos = await page.locator('.bui-price-display__value, .prco-valign-middle-helper').all_text_contents()
            logger.info(f"✅ Preços encontrados: {precos}")
            
            logger.info("🔒 Fechando navegador...")
            await browser.close()
            logger.info("✅ Navegador fechado")
            
            logger.info("📊 Processando resultados...")
            resultados = []
            for q, p in zip(quartos, precos):
                item = {
                    "quarto": q.strip(),
                    "preco": p.strip()
                }
                resultados.append(item)
                logger.info(f"✅ Item processado: {item}")
            
            logger.info("🎉 SUCESSO! Dados extraídos com sucesso")
            logger.info("🏁 Execução concluída com dados reais")
            
            return {"status": "ok", "resultado": resultados}
            
    except Exception as e:
        logger.error(f"💥 Erro geral: {str(e)}")
        return {"status": "erro", "erro": "Não consegui realizar a busca, Por favor, entre em contato"}

if __name__ == "__main__":
    logger.info("🚀 Iniciando servidor FastAPI...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

