import os
import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import gspread
from google.oauth2.service_account import Credentials

def iniciar_driver():
    chrome_options = Options()
    # Configurações para simular um navegador desktop comum e ignorar o WAF
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

def extrair_licitacoes(paginas=1):
    driver = iniciar_driver()
    dados = []
    
    try:
        for page in range(1, paginas + 1):
            print(f"Buscando página {page}...")
            url = f"https://www.tcmpa.tc.br/mural-de-licitacoes/licitacoes/listagem?page={page}&per-page=100"
            
            driver.get(url)
            time.sleep(5)  # Tempo para renderização da página e contorno do WAF
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            tbody = soup.find('tbody')
            
            if not tbody:
                print(f"Tabela vazia ou não encontrada na página {page}.")
                continue
                
            linhas = tbody.find_all('tr')
            for linha in linhas:
                colunas = linha.find_all('td')
                if len(colunas) < 11:
                    continue
                    
                # Extração do link da ficha
                link_tag = colunas[1].find('a')
                link_ficha = ""
                if link_tag and 'href' in link_tag.attrs:
                    href = link_tag['href']
                    link_ficha = href if href.startswith('http') else f"https://www.tcmpa.tc.br{href}"

                item = [
                    colunas[0].get_text(strip=True),  # Legislação
                    colunas[1].get_text(strip=True),  # Número
                    colunas[2].get_text(strip=True),  # Modalidade
                    colunas[3].get_text(strip=True),  # Tipo
                    colunas[4].get_text(strip=True),  # Objeto
                    colunas[5].get_text(strip=True),  # Abertura
                    colunas[6].get_text(strip=True),  # Publicação
                    colunas[7].get_text(strip=True),  # Município
                    colunas[8].get_text(strip=True),  # Órgão
                    colunas[9].get_text(strip=True),  # Situação
                    colunas[10].get_text(strip=True), # Referência
                    colunas[11].get_text(strip=True) if len(colunas) > 11 else "", # Adjudicado
                    link_ficha
                ]
                dados.append(item)
    finally:
        driver.quit()
        
    return dados

def atualizar_google_sheets(dados):
    if not dados:
        print("Nenhum dado para atualizar.")
        return

    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    # Lendo as credenciais da variável de ambiente do GitHub Secrets
    creds_json = json.loads(os.environ['GCP_CREDENTIALS'])
    creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
    client = gspread.authorize(creds)
    
    # Nome exato da sua planilha no Google Drive
    sheet = client.open("BaseLicitacoes").sheet1
    
    cabecalhos = [
        "Legislação", "Número", "Modalidade", "Tipo", "Objeto", 
        "Abertura", "Publicação", "Município", "Órgão", "Situação", 
        "Referência", "Adjudicado", "Link_Ficha"
    ]
    
    sheet.clear()
    sheet.append_row(cabecalhos)
    sheet.append_rows(dados)
    print("Planilha BaseLicitacoes atualizada com sucesso no Google Drive!")

if __name__ == "__main__":
    licitacoes = extrair_licitacoes(paginas=1)
    print(f"Total de itens raspados: {len(licitacoes)}")
    atualizar_google_sheets(licitacoes)
