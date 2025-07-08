import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
import streamlit as st

class GoogleSheetsService:
    def __init__(self):
        """Inicializa o serviço do Google Sheets."""
        try:
            credentials = Credentials.from_service_account_info(
                st.secrets["google_sheets"],
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"
                ]
            )
            self.client = gspread.authorize(credentials)
        except Exception as e:
            st.error(f"Erro ao inicializar o serviço do Google Sheets: {str(e)}")
            self.client = None

    def get_spreadsheet(self, url):
        """Abre uma planilha pelo URL."""
        try:
            return self.client.open_by_url(url) if self.client else None
        except Exception as e:
            st.error(f"Erro ao abrir a planilha: {str(e)}")
            return None

    def get_worksheet_data(self, spreadsheet, worksheet_name):
        """Obtém os dados de uma worksheet específica."""
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            
            # Obter todos os valores
            all_values = worksheet.get_all_values()
            if not all_values or len(all_values) < 3:  # Precisamos de pelo menos 3 linhas (título, cabeçalho e dados)
                return pd.DataFrame()

            # Encontrar a linha do cabeçalho real (geralmente a segunda linha)
            header_row = 1  # índice da linha do cabeçalho (0-based)
            
            # Procurar a linha que contém "CPF" ou "NOME"
            for i, row in enumerate(all_values[:5]):  # Procurar apenas nas primeiras 5 linhas
                if any(col.strip().upper() in ['CPF', 'NOME'] for col in row):
                    header_row = i
                    break
            
            # Pegar o cabeçalho e os dados
            headers = all_values[header_row]
            data = all_values[header_row + 1:]  # Dados começam após o cabeçalho
            
            # Limpar os cabeçalhos
            headers = [h.strip() for h in headers]
            
            # Criar cabeçalhos únicos para colunas não vazias
            unique_headers = []
            header_count = {}
            
            for i, header in enumerate(headers):
                if not header:  # Se o cabeçalho estiver vazio
                    header = f"Coluna_{i}"
                
                if header in header_count:
                    header_count[header] += 1
                    unique_headers.append(f"{header}_{header_count[header]}")
                else:
                    header_count[header] = 1
                    unique_headers.append(header)
            
            # Criar DataFrame
            df = pd.DataFrame(data, columns=unique_headers)
            
            # Remover linhas vazias ou que contenham apenas valores vazios/None
            df = df.dropna(how='all')
            
            # Remover linhas que não contêm dados válidos (ex: linhas de totais, cabeçalhos repetidos, etc)
            df = df[~df.iloc[:, 0].str.contains('total', case=False, na=False)]
            
            # Mapear as colunas principais
            column_mapping = {
                'CPF': ['CPF', 'CPF_1', 'CPF_2'],
                'NOME': ['NOME', 'NOME_1', 'NOME_2'],
                'VALOR DO ACORDO': ['VALOR DO ACORDO', 'VALOR DO ACORDO_1', 'VALOR DO ACORDO_2', 'VALOR ACORDO'],
                'HONORÁRIOS (30%)': ['HONORÁRIOS (30%)', 'HONORÁRIOS (30%)_1', 'HONORÁRIOS (30%)_2', 'HONORARIOS'],
                'PARCELAS DESCRITIVAS': ['PARCELAS DESCRITIVAS', 'PARCELAS DESCRITIVAS_1', 'PARCELAS DESCRITIVAS_2', 'PARCELAS']
            }

            # Renomear colunas
            for target_col, possible_names in column_mapping.items():
                for col_name in possible_names:
                    if col_name in df.columns:
                        df = df.rename(columns={col_name: target_col})
                        break
            
            return df
            
        except Exception as e:
            st.error(f"Erro ao obter dados da worksheet {worksheet_name}: {str(e)}")
            return pd.DataFrame()

def carregar_dados():
    """Carrega todos os dados da planilha do Google Sheets."""
    try:
        # Inicializa o serviço
        service = GoogleSheetsService()
        
        # Obtém a URL da planilha dos secrets
        spreadsheet_url = st.secrets["financeiro"]["spreadsheet_url"]
        
        # Abre a planilha
        spreadsheet = service.get_spreadsheet(spreadsheet_url)
        if not spreadsheet:
            return None
        
        # Lista todas as worksheets
        worksheet_titles = [ws.title for ws in spreadsheet.worksheets()]
        
        # Lista para armazenar todos os DataFrames
        all_data = []
        
        # Carrega dados de cada worksheet
        for month in worksheet_titles:
            df = service.get_worksheet_data(spreadsheet, month)
            if not df.empty:
                # Adiciona uma coluna com o nome do mês
                df['MÊS'] = month
                all_data.append(df)
        
        # Combina todos os DataFrames
        if all_data:
            df_final = pd.concat(all_data, ignore_index=True)
            
            # Garantir que todas as colunas necessárias existam
            required_columns = ['CPF', 'NOME', 'VALOR DO ACORDO', 'HONORÁRIOS (30%)', 'PARCELAS DESCRITIVAS']
            for col in required_columns:
                if col not in df_final.columns:
                    df_final[col] = None
            
            return df_final
        else:
            return None
            
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return None 