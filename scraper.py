import os
import json
import time
from bs4 import BeautifulSoup
from DrissionPage import ChromiumPage, ChromiumOptions
import gspread
from google.oauth2.service_account import Credentials

def extrair_licitacoes(paginas=1):
    # Configura o navegador para rodar em modo Linux sem ser detectado como automação
    co = ChromiumOptions()
    co.set_argument('--headless=new')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    
    page_driver = ChromiumPage(co)
    dados = []
    
    try:
        for page_num in range(1, paginas + 1):
            print(f"Buscando página {page_num}...")
            url = f"https://www.tcmpa.tc.br/mural-de-licitacoes/licitacoes/listagem?page={page_num}&per-page=100"
            
            page_driver.get(url)
            
            # Aguarda e tenta contornar o desafio do Cloudflare
            for tempo in range(15):
                title = page_driver.title
                if "Attention Required" not in title and "Cloudflare" not in title:
                    break
                print(f"Aguardando liberação do Cloudflare ({tempo+1}s)...")
                time.sleep(1)

            html = page_driver.html
            soup = BeautifulSoup(html, 'html.parser')
            tbody = soup.find('tbody')
            
            if not tbody:
                print(f"Tabela vazia na página {page_num}. Título atual: {page_driver.title}")
                continue
                
            linhas = tbody.find_all('tr')
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
        page_driver.quit()
        
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
