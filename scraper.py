import os
import json
import time
import cloudscraper
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials

def extrair_licitacoes(paginas=1):
    # Cria uma instância do Cloudscraper simulando um navegador Chrome no Windows
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    # Cabeçalhos extras para reforçar a navegação em Português do Brasil
    scraper.headers.update({
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.tcmpa.tc.br/mural-de-licitacoes/'
    })
    
    dados = []
    
    for page in range(1, paginas + 1):
        print(f"Buscando página {page}...")
        url = f"https://www.tcmpa.tc.br/mural-de-licitacoes/licitacoes/listagem?page={page}&per-page=100"
        
        try:
            response = scraper.get(url, timeout=30)
            
            if response.status_code != 200:
                print(f"Erro na requisição. Status: {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            tbody = soup.find('tbody')
            
            if not tbody:
                print(f"Tabela vazia na página {page}.")
                # Verifica se ainda caiu no Cloudflare
                if "Attention Required" in response.text or "Cloudflare" in response.text:
                    print("AVISO: Cloudflare ainda interceptou a chamada.")
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
            print(f"Erro ao processar página {page}: {e}")
            
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
