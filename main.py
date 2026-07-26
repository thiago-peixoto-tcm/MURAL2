import concurrent.futures
import requests
import pandas as pd
from bs4 import BeautifulSoup
import math
import time
import re
import os
import json
import gspread
from google.oauth2.service_account import Credentials

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
# MODO_TESTE:
# True  -> Baixa apenas as 3 primeiras páginas (~90 registros) para teste rápido.
# False -> Baixa TODAS as páginas do site dinamicamente.
MODO_TESTE = True

# Nome exato da planilha criada e compartilhada no seu Google Drive
NOME_PLANILHA = "Base Licitacoes TCMPA"
# ==============================================================================


def autenticar_google_sheets():
    """Autentica na API do Google Sheets usando o Segredo configurado no GitHub."""
    escopos = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # Carrega a chave JSON da variável de ambiente setada pelo GitHub Actions
    key_info = json.loads(os.environ['GOOGLE_KEY_JSON'])
    creds = Credentials.from_service_account_info(key_info, scopes=escopos)
    client = gspread.authorize(creds)
    
    # Abre a primeira aba da planilha
    return client.open(NOME_PLANILHA).sheet1


def descobrir_total_paginas():
    """Acessa a primeira página para ler a contagem total de itens no HTML."""
    url = "https://www.tcmpa.tc.br/mural-de-licitacoes/licitacoes/listagem?page=1&per-page=30"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    for tentativa in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                texto_pagina = " ".join(soup.get_text().split())
                
                # Busca por expressões como "de 140.439 itens"
                match = re.search(r'de\s+([\d\.]+)\s+itens', texto_pagina, re.IGNORECASE)
                if match:
                    total_itens = int(match.group(1).replace('.', ''))
                    paginas = math.ceil(total_itens / 30)
                    print(f"📊 Total de licitações identificadas no site: {total_itens:,}".replace(',', '.'))
                    return paginas
        except Exception as e:
            time.sleep(2)
            
    print("⚠️ Não foi possível identificar o total dinamicamente. Usando estimativa padrão.")
    return 4682


def baixar_pagina(page):
    """Realiza a raspagem de dados de uma página específica da listagem."""
    url = f"https://www.tcmpa.tc.br/mural-de-licitacoes/licitacoes/listagem?page={page}&per-page=30"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    for tentativa in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                tabela = soup.find('table')
                if not tabela:
                    return []
                
                linhas_pagina = []
                for row in tabela.find_all('tr'):
                    # Pula cabeçalhos e elementos de filtro
                    if row.find('th') or row.find('select') or row.find('input'):
                        continue
                        
                    tds = row.find_all('td')
                    if tds and len(tds) >= 10:
                        cols = [td.get_text(strip=True) for td in tds]
                        
                        # Captura o link do número da licitação
                        tag_a = tds[1].find('a')
                        link_ficha = ""
                        if tag_a and tag_a.has_attr('href'):
                            link_ficha = tag_a['href']
                            if not link_ficha.startswith('http'):
                                link_ficha = "https://www.tcmpa.tc.br" + link_ficha
                        
                        # Retorna em formato de lista simples (compatível com Google Sheets)
                        linha = [
                            cols[0],                                        # Legisl
                            cols[1],                                        # Número LIC
                            link_ficha,                                     # Link_Ficha
                            cols[2],                                        # Modalidade
                            cols[3],                                        # Tipo
                            cols[4],                                        # Objeto
                            cols[5],                                        # Abertura
                            cols[6],                                        # Publicação
                            cols[7],                                        # Município
                            cols[8],                                        # UG
                            cols[9],                                        # Situação
                            cols[10] if len(cols) > 10 else "0,00",          # VLR Referência
                            cols[11] if len(cols) > 11 else "0,00"           # VLR Adjudicado
                        ]
                        linhas_pagina.append(linha)
                return linhas_pagina
        except Exception:
            time.sleep(1.5)
            
    return []


def main():
    print("🚀 Iniciando extração do TCM-PA...")
    
    total_paginas_site = descobrir_total_paginas()
    
    # Aplica a trava do MODO TESTE se estiver ativada
    if MODO_TESTE:
        paginas_para_rodar = 3
        print(f"🧪 MODO TESTE ATIVADO: Baixando apenas as primeiras {paginas_para_rodar} páginas (~90 registros).")
    else:
        paginas_para_rodar = total_paginas_site
        print(f"🔄 MODO COMPLETO: Baixando todas as {paginas_para_rodar} páginas.")

    lista_final = []
    cabecalho = [[
        "Legisl", "Número LIC", "Link_Ficha", "Modalidade", "Tipo", 
        "Objeto", "Abertura", "Publicação", "Município", "UG", 
        "Situação", "VLR Referência", "VLR Adjudicado"
    ]]

    # Processamento paralelo de requisições
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futuros = {executor.submit(baixar_pagina, p): p for p in range(1, paginas_para_rodar + 1)}
        
        paginas_concluidas = 0
        for futuro in concurrent.futures.as_completed(futuros):
            paginas_concluidas += 1
            resultado = futuro.result()
            if resultado:
                lista_final.extend(resultado)
                
            if paginas_concluidas % 50 == 0 or paginas_concluidas == paginas_para_rodar:
                print(f"⏳ Progresso: {paginas_concluidas}/{paginas_para_rodar} páginas concluídas...")

    # Envio para o Google Drive / Sheets
    if lista_final:
        print(f"💾 Conectando ao Google Sheets para gravar {len(lista_final)} registros...")
        try:
            sheet = autenticar_google_sheets()
            
            # Limpa o conteúdo antigo para não encavalar dados
            sheet.clear()
            
            # Atualiza o cabeçalho e todas as linhas extraídas de uma só vez
            dados_completos = cabecalho + lista_final
            sheet.update('A1', dados_completos)
            
            print("✅ SUCESSO! A planilha no Google Drive foi atualizada com sucesso.")
        except Exception as e:
            print(f"❌ Erro ao enviar os dados para o Google Sheets: {e}")
    else:
        print("❌ Nenhuma linha pôde ser extraída do site.")


if __name__ == "__main__":
    main()
