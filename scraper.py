import os
import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
import gspread
from google.oauth2.service_account import Credentials

def iniciar_driver_firefox():
    options = Options()
    options.add_argument("--headless")  # Modo sem interface gráfica
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference('useAutomationExtension', False)
    options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0")
    
    # Inicia o Firefox
    driver = webdriver.Firefox(
        service=Service(GeckoDriverManager().install()), 
        options=options
    )
    return driver

def extrair_licitacoes(paginas=1):
    driver = iniciar_driver_firefox()
    dados = []
    
    try:
        for page in range(1, paginas + 1):
            print(f"Buscando página {page} no Firefox...")
            url = f"https://www.tcmpa.tc.br/mural-de-licitacoes/licitacoes/listagem?page={page}&per-page=100"
            
            driver.get(url)
            
            # Aguarda a página carregar e superar eventuais verificações
            time.sleep(10)
            
            print(f"Título retornado pela página: {driver.title}")
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            tbody = soup.find('tbody')
            
            if not tbody:
                print(f"Tabela vazia ou não encontrada na página {page}.")
                continue
                
            linhas = tbody.find_all('tr')
            print(f"Encontradas {len(linhas)} linhas!")
            
            for linha in linhas:
                colunas = linha.find_all('td')
                if len(colunas) < 11:
                    continue
                    
                link_tag = colunas[1].find('a')
                link_ficha = ""
                if link_tag and 'href' in link_tag.attrs:
                    href = link_tag['href']
                    link_ficha = href if href.startswith('http') else f"https://www.tcmpa.tc.br{href}"

                item = [
                    colunas[0].get_text(strip=True),
                    colunas[1].get_text(strip=True),
                    colunas[2].get_text(strip=True),
                    colunas[3].get_text(strip=True),
                    colunas[4].get_text(strip=True),
                    colunas[5].get_text(strip=True),
                    colunas[6].get_text(strip=True),
                    colunas[7].get_text(strip=True),
                    colunas[8].get_text(strip=True),
                    colunas[9].get_text(strip=True),
                    colunas[10].get_text(strip=True),
                    colunas[11].get_text(strip=True) if len(colunas) > 11 else "",
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
    
    creds_json = json.loads(os.environ['GCP_CREDENTIALS'])
    creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
    client = gspread.authorize(creds)
    
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
