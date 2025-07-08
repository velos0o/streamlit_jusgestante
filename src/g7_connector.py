"""
Conector para a API de BI do Bitrix24 da G7 Assessoria.
Responsável por montar e executar consultas otimizadas.
"""

import streamlit as st
import requests
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass

class G7ApiError(Exception):
    """Exceção específica para erros da API G7."""
    pass

@dataclass
class G7Credentials:
    """Encapsula credenciais da API G7."""
    base_url: str
    token: str
    timeout: int
    max_retries: int

class G7Connector:
    """Conector para o Bitrix24 BI Connector da G7."""

    def __init__(self):
        self._credentials = self._load_credentials()
        self._session = self._create_session()

    def _load_credentials(self) -> G7Credentials:
        """Carrega credenciais do secrets.toml."""
        try:
            return G7Credentials(
                base_url=st.secrets["g7_bitrix"]["base_url"],
                token=st.secrets["g7_bitrix"]["token"],
                timeout=st.secrets.get("api", {}).get("timeout", 60),
                max_retries=st.secrets.get("api", {}).get("max_retries", 3)
            )
        except KeyError as e:
            raise G7ApiError(f"Credencial para 'g7_bitrix' não encontrada no secrets.toml: {e}")

    def _create_session(self) -> requests.Session:
        """Cria uma sessão HTTP configurada."""
        session = requests.Session()
        session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'Streamlit-JusGestante/1.0'
        })
        return session

    def _execute_bi_query(self, table_name: str, payload: Dict) -> pd.DataFrame:
        """Executa uma consulta genérica no BI Connector e retorna um DataFrame."""
        url = f"{self._credentials.base_url}?token={self._credentials.token}&table={table_name}"
        
        for attempt in range(self._credentials.max_retries):
            try:
                response = self._session.post(url, json=payload, timeout=self._credentials.timeout)
                response.raise_for_status()
                response_data = response.json()
                
                if isinstance(response_data, list) and len(response_data) > 1:
                    column_names = response_data[0]
                    data_rows = response_data[1:]
                    return pd.DataFrame(data_rows, columns=column_names)
                elif isinstance(response_data, list) and len(response_data) <= 1:
                    return pd.DataFrame()
                else:
                    raise G7ApiError(f"Formato de resposta inesperado da API para {table_name}: {response_data}")

            except requests.exceptions.RequestException as e:
                if attempt == self._credentials.max_retries - 1:
                    raise G7ApiError(f"Falha na requisição para {table_name} após {self._credentials.max_retries} tentativas: {e}")
                continue
        
        return pd.DataFrame()

    def get_processo_won_deals(self) -> pd.DataFrame:
        """
        Busca deals 'GANHOS' (WON) para produtos específicos, com filtro robusto.
        """
        # Etapa 1: Buscar deals da tabela principal
        deals_payload = {
            "dimensionsFilters": [
                [
                    {"fieldName": "CATEGORY_ID", "values": [0], "type": "INCLUDE", "operator": "EQUALS"},
                    {"fieldName": "STAGE_ID", "values": ["WON"], "type": "INCLUDE", "operator": "EQUALS"}
                ]
            ],
            "fields": [{"name": "ID"}, {"name": "ASSIGNED_BY"}]
        }
        initial_deals_df = self._execute_bi_query("crm_deal", deals_payload)

        if initial_deals_df.empty:
            return pd.DataFrame()

        initial_deals_df['ID'] = pd.to_numeric(initial_deals_df['ID'], errors='coerce')
        deal_ids = initial_deals_df['ID'].dropna().astype(int).tolist()

        if not deal_ids:
            return pd.DataFrame()

        # Etapa 2: Buscar campos customizados
        uf_payload = {
            "dimensionsFilters": [[{"fieldName": "DEAL_ID", "values": deal_ids, "type": "INCLUDE", "operator": "EQUALS"}]],
            "fields": [{"name": "DEAL_ID"}, {"name": "UF_CRM_PRODUTO"}]
        }
        all_uf_df = self._execute_bi_query("crm_deal_uf", uf_payload)

        if all_uf_df.empty:
            return pd.DataFrame()

        # Etapa 3: Aplicar filtro de produto localmente, com limpeza de dados robusta
        if 'UF_CRM_PRODUTO' in all_uf_df.columns:
            produtos_desejados = ["PROCESSO", "PROCESSO + AUXÍLIO"]
            
            # Limpa e normaliza a coluna de produtos de forma definitiva
            # O .str.strip() remove o espaço no final que encontramos
            produtos_limpos = all_uf_df['UF_CRM_PRODUTO'].astype(str).str.strip().str.upper()
            
            # Filtra o dataframe de campos customizados
            mask = produtos_limpos.isin(produtos_desejados)
            filtered_uf_df = all_uf_df[mask]

            if filtered_uf_df.empty:
                return pd.DataFrame()

            # Etapa 4: Juntar resultados
            filtered_uf_df['DEAL_ID'] = pd.to_numeric(filtered_uf_df['DEAL_ID'], errors='coerce')
            filtered_deal_ids = filtered_uf_df['DEAL_ID'].dropna().unique()
            final_deals_df = initial_deals_df[initial_deals_df['ID'].isin(filtered_deal_ids)]
            return final_deals_df
        else:
            return pd.DataFrame()

    def get_users(self) -> pd.DataFrame:
        """Busca todos os usuários da conta G7 para mapear IDs para nomes."""
        st.warning("A busca de nomes de usuários da conta G7 não está implementada. A tabela mostrará o nome do campo 'ASSIGNED_BY'.")
        return pd.DataFrame(columns=['ID', 'NAME', 'LAST_NAME']) 