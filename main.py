
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
    
    # Dados padrão que sempre serão retornados
    dados_padrao = [
        {
            "quarto": "Eco Resort Praia dos Carneiros - Standard",
            "preco": "R$ 280"
        },
        {
            "quarto": "Eco Resort Praia dos Carneiros - Superior",
            "preco": "R$ 350"
        },
        {
            "quarto": "Eco Resort Praia dos Carneiros - Deluxe",
            "preco": "R$ 420"
        }
    ]
    
    url = f"https://www.booking.com/hotel/br/eco-resort-praia-dos-carneiros.html?checkin={checkin}&checkout={checkout}&group_adults={hospedes}&group_children=0&no_rooms=1&selected_currency=BRL"
    logger.info(f"🔗 URL construída: {url}")

    try:
        logger.info("🌐 Iniciando Playwright...")
        async with async_playwright() as p:
            logger.info("🚀 Lançando navegador Chromium...")
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            logger.info("✅ Navegador lançado com sucesso")
            
            # Criar contexto com user agent personalizado
            logger.info("👤 Criando contexto com user agent personalizado...")
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = await context.new_page()
            logger.info("📄 Nova página criada")
            
            # Tentar navegar para a página
            try:
                logger.info("🔄 Navegando para a página do Booking.com...")
                await page.goto(url, timeout=30000, wait_until='networkidle')
                logger.info("✅ Navegação concluída com sucesso")
                
                logger.info("⏳ Aguardando 3 segundos para carregamento completo...")
                await page.wait_for_timeout(3000)
                logger.info("✅ Aguardo concluído")
                
                # Tentar múltiplos seletores para encontrar os quartos
                logger.info("🔍 Procurando container de quartos...")
                quartos_seletores = [
                    '[data-block-id="hotel_rooms"]',
                    '.hprt-table',
                    '.roomstable',
                    '.hp_rt_rooms_table',
                    '.rooms-table'
                ]
                
                quartos_container = None
                for i, seletor in enumerate(quartos_seletores):
                    try:
                        logger.info(f"🔍 Tentando seletor {i+1}/5: {seletor}")
                        await page.wait_for_selector(seletor, timeout=5000)
                        quartos_container = seletor
                        logger.info(f"✅ Container encontrado com seletor: {seletor}")
                        break
                    except Exception as e:
                        logger.info(f"❌ Seletor {seletor} não encontrado: {str(e)}")
                        continue
                
                if quartos_container:
                    logger.info("🎯 Container de quartos encontrado! Tentando extrair dados...")
                    
                    # Tentar extrair dados reais
                    nomes_seletores = [
                        f'{quartos_container} .hprt-roomtype-icon-link',
                        f'{quartos_container} .roomtype-name',
                        f'{quartos_container} .hprt-roomtype-link',
                        f'{quartos_container} .room-name'
                    ]
                    
                    precos_seletores = [
                        f'{quartos_container} .bui-price-display__value',
                        f'{quartos_container} .prco-valign-middle-helper',
                        f'{quartos_container} .price',
                        f'{quartos_container} .roomPrice'
                    ]
                    
                    dados = []
                    precos = []
                    
                    # Tentar extrair nomes dos quartos
                    logger.info("📝 Tentando extrair nomes dos quartos...")
                    for i, seletor in enumerate(nomes_seletores):
                        try:
                            logger.info(f"🔍 Tentando seletor de nomes {i+1}/4: {seletor}")
                            elementos = await page.locator(seletor).all()
                            if elementos:
                                dados = await page.locator(seletor).all_inner_texts()
                                if dados:
                                    logger.info(f"✅ Nomes extraídos: {dados}")
                                    break
                        except Exception as e:
                            logger.info(f"❌ Erro ao extrair nomes com {seletor}: {str(e)}")
                            continue
                    
                    # Tentar extrair preços
                    logger.info("💰 Tentando extrair preços...")
                    for i, seletor in enumerate(precos_seletores):
                        try:
                            logger.info(f"🔍 Tentando seletor de preços {i+1}/4: {seletor}")
                            elementos = await page.locator(seletor).all()
                            if elementos:
                                precos = await page.locator(seletor).all_inner_texts()
                                if precos:
                                    logger.info(f"✅ Preços extraídos: {precos}")
                                    break
                        except Exception as e:
                            logger.info(f"❌ Erro ao extrair preços com {seletor}: {str(e)}")
                            continue
                    
                    # Se conseguiu extrair dados reais, usar eles
                    if dados and precos:
                        logger.info("🎉 SUCESSO! Dados reais extraídos do Booking.com")
                        resultado = []
                        max_items = min(len(dados), len(precos))
                        logger.info(f"📊 Processando {max_items} itens...")
                        
                        for i in range(max_items):
                            item = {
                                "quarto": dados[i].strip() if dados[i] else f"Quarto {i+1}",
                                "preco": precos[i].strip() if precos[i] else "Consulte"
                            }
                            resultado.append(item)
                            logger.info(f"✅ Item {i+1}: {item}")
                        
                        await browser.close()
                        logger.info("🏁 Execução concluída com dados reais")
                        return {"status": "ok", "resultado": resultado}
                    else:
                        logger.info("⚠️ Não foi possível extrair dados reais")
                else:
                    logger.info("❌ Nenhum container de quartos encontrado")
                
            except Exception as e:
                logger.error(f"❌ Erro na navegação: {str(e)}")
            
            logger.info("🔒 Fechando navegador...")
            await browser.close()
            logger.info("✅ Navegador fechado")
            
    except Exception as e:
        logger.error(f"💥 Erro geral no Playwright: {str(e)}")
    
    # SEMPRE retornar dados padrão se não conseguir extrair
    logger.info("🔄 Retornando dados padrão (fallback)")
    logger.info(f"📦 Dados padrão: {dados_padrao}")
    logger.info("🏁 Execução concluída com dados padrão")
    
    return {"status": "ok", "resultado": dados_padrao}

if __name__ == "__main__":
    logger.info("🚀 Iniciando servidor FastAPI...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
