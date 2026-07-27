import os
import json
import requests
import gspread
from google.oauth2.service_account import Credentials

def testar_api_tcm():
    # Endpoints comuns usados pelo framework do TCM-PA
    endpoints = [
        "https://www.tcmpa.tc.br/mural-de-licitacoes/licitacoes/listagem-json?page=1&per-page=100",
        "https://www.tcmpa.tc.br/mural-de-licitacoes/api/licitacoes?page=1&per-page=100",
        "https://www.tcmpa.tc.br/mural-de-licitacoes/licitacoes/get-dados?page=1&per-page=100",
        "https://www.tcmpa.tc.br/mural-de-licitacoes/licitacoes/listagem?page=1&per-page=100&_format=json"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest', # Identifica requisição AJAX/API
        'Referer': 'https://www.tcmpa.tc.br/mural-de-licitacoes/licitacoes/listagem'
    }
    
    dados_extraidos = []

    for url in endpoints:
        print(f"Testando endpoint: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=15)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print("✅ SUCESSO! A API respondeu com dados JSON válidos.")
                    
                    # Tenta mapear os itens retornados no JSON
                    items = data.get('items', data if isinstance(data, list) else [])
                    
                    for item in items:
                        # Extrai os campos se existirem na estrutura JSON
                        dados_extraidos.append([
                            str(item.get('legislacao', '')),
                            str(item.get('numero', '')),
                            str(item.get('modalidade', '')),
                            str(item.get('tipo', '')),
                            str(item.get('objeto', '')),
                            str(item.get('abertura', '')),
                            str(item.get('publicacao', '')),
                            str(item.get('municipio', '')),
                            str(item.get('orgao', '')),
                            str(item.get('situacao', '')),
                            str(item.get('referencia', '')),
                            str(item.get('adjudicado', '')),
                            str(item.get('link', ''))
                        ])
                    
                    if dados_extraidos:
                        return dados_extraidos
                except Exception as json_err:
                    print(f"Resposta de {url} não é um JSON válido: {json_err}")
        except Exception as e:
            print(f"Erro ao acessar {url}: {e}")
            
    return dados_extraidos

def atualizar_google_sheets(dados):
    if not dados:
        print("Nenhum dado capturado via API.")
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
    print("Planilha BaseLicitacoes atualizada com sucesso via API!")

if __name__ == "__main__":
    licitacoes = testar_api_tcm()
    print(f"Total de itens raspados via API: {len(licitacoes)}")
    atualizar_google_sheets(licitacoes)
