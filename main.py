
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from playwright.sync_api import sync_playwright
from datetime import datetime
import re

app = FastAPI()

# Libera CORS para frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UNIDADES = [
    {
        "nome": "Eco Resort Praia Dos Carneiros - Flat Colina",
        "id": "614621079133481740"
    },
    {
        "nome": "Eco Resort Praia Dos Carneiros - Flat Praia",
        "id": "1077091916761243151"
    }
]

@app.get("/executar")
def executar(checkin: str = Query(...), checkout: str = Query(...), adultos: int = Query(...), criancas: int = Query(0)):
    try:
        # Corrigido: adultos vem direto do parâmetro, hospedes é a soma
        hospedes = adultos + criancas
        data_in = datetime.strptime(checkin, "%Y-%m-%d")
        data_out = datetime.strptime(checkout, "%Y-%m-%d")
        numero_noites = (data_out - data_in).days

        resultados = []

        with sync_playwright() as p:
            for unidade in UNIDADES:
                # Abre novo browser para cada unidade (sem proxy pois não usa Decodo)
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                
                # Bloqueia recursos desnecessários para economizar banda
                def handle_route(route):
                    url = route.request.url
                    if any(domain in url for domain in [
                        'a0.muscache.com',
                        'www.googletagmanager.com',
                        'google-analytics.com',
                        'facebook.com',
                        'doubleclick.net',
                        'googlesyndication.com',
                        'googleadservices.com',
                        'googletag',
                        'analytics.js',
                        'gtag',
                        'fbevents.js'
                    ]):
                        route.abort()
                    else:
                        route.continue_()
                
                context.route("**/*", handle_route)
                page = context.new_page()
                
                print(f"🔍 Verificando: {unidade['nome']} ({unidade['id']})")
                url = (
                    f"https://www.airbnb.com.br/book/stays/{unidade['id']}"
                    f"?checkin={checkin}"
                    f"&checkout={checkout}"
                    f"&numberOfGuests={hospedes}"
                    f"&numberOfAdults={adultos}"
                    f"&numberOfChildren={criancas}"
                    f"&guestCurrency=BRL"
                    f"&productId={unidade['id']}"
                    f"&isWorkTrip=false"
                    f"&numberOfInfants=0&numberOfPets=0"
                )
                print(f"🌐 URL acessada: {url}")
                page.goto(url)
                page.wait_for_timeout(5000)

                content = page.content()
                match = re.search(r'R\$\s?\d{1,3}(\.\d{3})*,\d{2}', content)
                if match:
                    preco_texto = match.group()
                    preco_limpo = preco_texto.replace("R$", "").replace(".", "").replace(",", ".").strip()
                    preco_total = float(preco_limpo)
                    media_diaria = preco_total / numero_noites
                    print(f"✅ Preço encontrado para {unidade['nome']}: {match.group()}")
                    resultados.append({
                        "nome": unidade["nome"],
                        "preco": f"R$ {preco_total:.2f}",
                        "nota": "9.0",
                        "urlretorno": url,
                    })
                
                # Fecha o navegador após cada consulta para evitar interferências
                browser.close()
                print(f"🔄 Navegador fechado para {unidade['nome']}")

            print("🔚 Consulta finalizada.")

        return {"status": "ok", "resultado": resultados}

    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}
