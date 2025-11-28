
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from playwright.sync_api import sync_playwright
from datetime import datetime
import re
import gspread
from google.oauth2.service_account import Credentials
import json
import os

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

# ID da planilha Google Sheets
SPREADSHEET_ID = "1cFibFKZKS5hStukgHNifc63MRB5j47wUwngSVP3oL1w"

def obter_credenciais_google():
    """
    Obtém as credenciais do Google a partir da variável de ambiente ou arquivo
    """
    try:
        # Tenta obter do arquivo de credenciais
        if os.path.exists('credentials.json'):
            creds = Credentials.from_service_account_file(
                'credentials.json',
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            return creds
        
        # Tenta obter da variável de ambiente
        creds_json = os.environ.get('GOOGLE_CREDENTIALS')
        if creds_json:
            creds_dict = json.loads(creds_json)
            creds = Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            return creds
        
        return None
    except Exception as e:
        print(f"⚠️  Erro ao obter credenciais: {e}")
        return None

def exportar_para_google_sheets(dados):
    """
    Exporta os dados coletados para a planilha Google Sheets
    Função não-bloqueante que não afeta o resultado da API
    """
    try:
        creds = obter_credenciais_google()
        
        if not creds:
            print("⚠️  Google Sheets não configurado - dados não serão exportados")
            return False
        
        # Autenticar com Google Sheets
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        
        # Obter ou criar a aba "Dados"
        try:
            worksheet = spreadsheet.worksheet("Dados")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title="Dados", rows=1000, cols=5)
        
        # Definir cabeçalhos se não existirem
        if worksheet.row_count == 0 or not worksheet.row_values(1):
            headers = ["Data Check-in", "Data Check-out", "Número de Hóspedes", "Apartamento", "Valor"]
            worksheet.insert_row(headers, 1)
        
        # Inserir dados
        if dados:
            rows = []
            for item in dados:
                rows.append([
                    item.get('checkin', ''),
                    item.get('checkout', ''),
                    str(item.get('hospedes', '')),
                    item.get('apartamento', ''),
                    item.get('valor', 'Indisponível')
                ])
            
            # Inserir todas as linhas de uma vez
            worksheet.insert_rows(rows, 2)
            print(f"✅ Dados exportados para Google Sheets")
            return True
        
        return False
            
    except Exception as e:
        print(f"⚠️  Erro ao exportar para Google Sheets: {e}")
        return False

@app.get("/executar")
def executar(checkin: str = Query(...), checkout: str = Query(...), adultos: int = Query(...), criancas: int = Query(0)):
    try:
        # Corrigido: adultos vem direto do parâmetro, hospedes é a soma
        hospedes = adultos + criancas
        data_in = datetime.strptime(checkin, "%Y-%m-%d")
        data_out = datetime.strptime(checkout, "%Y-%m-%d")
        numero_noites = (data_out - data_in).days

        resultados = []
        dados_exportacao = []  # Lista para armazenar dados para exportação

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
                
                valor_encontrado = "Indisponível"
                
                if match:
                    preco_texto = match.group()
                    preco_limpo = preco_texto.replace("R$", "").replace(".", "").replace(",", ".").strip()
                    preco_total = float(preco_limpo)
                    media_diaria = preco_total / numero_noites
                    print(f"✅ Preço encontrado para {unidade['nome']}: {match.group()}")
                    valor_encontrado = f"R$ {preco_total:.2f}"
                    resultados.append({
                        "nome": unidade["nome"],
                        "preco": f"R$ {preco_total:.2f}",
                        "nota": "9.0",
                        "urlretorno": url,
                    })
                else:
                    resultados.append({
                        "nome": unidade["nome"],
                        "preco": "Indisponível",
                        "nota": "9.0",
                        "urlretorno": url,
                    })
                
                # Adicionar aos dados de exportação
                dados_exportacao.append({
                    'checkin': checkin,
                    'checkout': checkout,
                    'hospedes': hospedes,
                    'apartamento': unidade['nome'],
                    'valor': valor_encontrado
                })
                
                # Fecha o navegador após cada consulta para evitar interferências
                browser.close()
                print(f"🔄 Navegador fechado para {unidade['nome']}")

            print("🔚 Consulta finalizada.")
            
            # Exportar dados para Google Sheets (não bloqueia a resposta)
            if dados_exportacao:
                exportar_para_google_sheets(dados_exportacao)

        return {"status": "ok", "resultado": resultados}

    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}
