import os
import json
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import gspread
from google.oauth2.service_account import Credentials

def extrair_licitacoes(paginas=1):
    dados = []
    
    with sync_playwright() as p:
        # Lança o Firefox real no Playwright
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
            locale="pt-BR"
        )
        page = context.new_page()
        
        for page_num in range(1, paginas + 1):
            print(f"Buscando página {page_num} via Playwright...")
            url = f"https://www.tcmpa.tc.br/mural-de-licitacoes/licitacoes/listagem?page={page_num}&per-page=100"
            
            try:
                # Navega até o site e aguarda o carregamento do DOM
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
                time.sleep(5)  # Tempo de tolerância
                
                print(f"Título da página obtido: {page.title()}")
                
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                tbody = soup.find('tbody')
                
                if not tbody:
                    print(f"Tabela vazia ou não encontrada na página {page_num}.")
                    continue
                    
                linhas = tbody.find_all('tr')
                print(f"Encontradas {len(linhas)} linhas na tabela!")
                
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
                print(f"Erro na página {page_num}: {e}")
                
        browser.close()
        
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
