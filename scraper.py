import os
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configurações de Cabeçalho para Simular Navegador Real
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.tcmpa.tc.br/mural-de-licitacoes/licitacoes/listagem'
}

def raspar_pagina(page):
    url = f"https://www.tcmpa.tc.br/mural-de-licitacoes/licitacoes/listagem?page={page}"
    
    for tentativa in range(3):
        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                tbody = soup.find('tbody')
                if not tbody:
                    return page, []
                
                linhas = tbody.find_all('tr')
                if not linhas:
                    return page, []
                
                dados_pagina = []
                for linha in linhas:
                    colunas = linha.find_all('td')
                    if len(colunas) < 11:
                        continue
                        
                    link_tag = colunas[1].find('a')
                    link_ficha = ""
                    if link_tag and 'href' in link_tag.attrs:
                        href = link_tag['href']
                        link_ficha = href if href.startswith('http') else f"https://www.tcmpa.tc.br{href}"

                    item = {
                        "Legislacao": colunas[0].get_text(strip=True),
                        "Numero": colunas[1].get_text(strip=True),
                        "Modalidade": colunas[2].get_text(strip=True),
                        "Tipo": colunas[3].get_text(strip=True),
                        "Objeto": colunas[4].get_text(strip=True),
                        "Abertura": colunas[5].get_text(strip=True),
                        "Publicacao": colunas[6].get_text(strip=True),
                        "Municipio": colunas[7].get_text(strip=True),
                        "Orgao": colunas[8].get_text(strip=True),
                        "Situacao": colunas[9].get_text(strip=True),
                        "Referencia": colunas[10].get_text(strip=True),
                        "Adjudicado": colunas[11].get_text(strip=True) if len(colunas) > 11 else "",
                        "Link_Ficha": link_ficha
                    }
                    dados_pagina.append(item)
                return page, dados_pagina
            elif response.status_code == 403:
                time.sleep(1) # Se der 403 temporário, aguarda e tenta de novo
        except Exception as e:
            time.sleep(1)
            
    return page, []

def executar_raspagem_total(max_paginas_estimado=4700, max_threads=10):
    print(f"🚀 Iniciando raspagem massiva paralela (até {max_paginas_estimado} páginas)...")
    todos_dados = []
    paginas_vazias_seguidas = 0
    
    # Processa em lotes de páginas para controlar a memória e progresso
    lote_tamanho = 100
    for inicio in range(1, max_paginas_estimado + 1, lote_tamanho):
        fim = min(inicio + lote_tamanho - 1, max_paginas_estimado)
        print(f"📦 Processando lote de páginas {inicio} a {fim}...")
        
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [executor.submit(raspar_pagina, p) for p in range(inicio, fim + 1)]
            
            # Ordena os resultados para manter a sequência original
            resultados = []
            for future in as_completed(futures):
                p, dados = future.result()
                resultados.append((p, dados))
            
            resultados.sort(key=lambda x: x[0])
            
            for p, dados in resultados:
                if dados:
                    todos_dados.extend(dados)
                    paginas_vazias_seguidas = 0
                else:
                    paginas_vazias_seguidas += 1
        
        print(f"Progresso atual: {len(todos_dados)} licitações capturadas.")
        
        # Se 15 páginas seguidas vierem vazias, encerra o processo
        if paginas_vazias_seguidas >= 15:
            print("Fim do catálogo de licitações detectado.")
            break

    print(f"✅ Raspagem finalizada! Total de licitações extraídas: {len(todos_dados)}")
    
    # Salva os dados em CSV comprimido ou padrão
    df = pd.DataFrame(todos_dados)
    df.to_csv("licitacoes_tcmpa_completo.csv", index=False, encoding='utf-8-sig')
    print("💾 Arquivo licitacoes_tcmpa_completo.csv gerado com sucesso!")
    return df

if __name__ == "__main__":
    executar_raspagem_total()
