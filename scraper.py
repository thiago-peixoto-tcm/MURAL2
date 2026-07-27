import os
import json
import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials

def extrair_licitacoes(paginas=1):
    api_key = os.environ.get('SCRAPER_API_KEY')
    dados = []
    
    for page in range(1, paginas + 1):
        print(f"Buscando página {page} via ScraperAPI...")
        target_url = f"https://www.tcmpa.tc.br/mural-de-licitacoes/licitacoes/listagem?page={page}&per-page=100"
        
        # ScraperAPI fura o Cloudflare usando IP residencial do Brasil
        scraper_url = f"http://api.scraperapi.com?api_key={api_key}&url={target_url}&country_code=br"
        
        try:
            response = requests.get(scraper_url, timeout=90)
            if response.status_code != 200:
                print(f"Erro na requisição. Status: {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            tbody = soup.find('tbody')
            
            if not tbody:
                print(f"Tabela não encontrada na página {page}.")
                continue
                
            linhas = tbody.find_all('tr')
            print(f"✅ SUCESSO! Encontradas {len(linhas)} licitações na página {page}.")
            
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
        except Exception as e:
            print(f"Erro ao processar página {page}: {e}")
            
    return dados

def atualizar_google_sheets(dados):
    if not dados:
        print("Nenhum dado capturado.")
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
