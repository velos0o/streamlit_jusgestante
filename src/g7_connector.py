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

    def get_all_entities(self, entity_name: str, filter_params: Optional[Dict] = None, select_fields: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Busca entidades do Bitrix24 BI Connector com filtros e seleção de campos dinâmicos.

        Args:
            entity_name (str): Nome da tabela no BI Connector (ex: 'crm_deal', 'crm_deal_uf').
            filter_params (Optional[Dict]): Dicionário com filtros a serem aplicados. 
                                            Ex: {'STAGE_ID': 'WON', 'CATEGORY_ID': 0}
            select_fields (Optional[List[str]]): Lista de campos a serem retornados. 
                                                 Ex: ['ID', 'TITLE']

        Returns:
            pd.DataFrame: DataFrame com os resultados.
        """
        payload = {"fields": []}

        # Constrói a lista de campos para o 'select' da consulta
        if select_fields:
            payload["fields"] = [{"name": field} for field in select_fields]
        
        # Constrói a cláusula de filtro
        if filter_params:
            dimensions_filter = []
            for field, value in filter_params.items():
                # Garante que o valor seja uma lista para a API
                values_list = value if isinstance(value, list) else [value]
                dimensions_filter.append({
                    "fieldName": field,
                    "values": values_list,
                    "type": "INCLUDE",
                    "operator": "EQUALS"
                })
            payload["dimensionsFilters"] = [dimensions_filter]

        return self._execute_bi_query(entity_name, payload)

    def get_users(self) -> pd.DataFrame:
        """Busca todos os usuários da conta G7 para mapear IDs para nomes."""
        st.warning("A busca de nomes de usuários da conta G7 não está implementada. A tabela mostrará o nome do campo 'ASSIGNED_BY'.")
        return pd.DataFrame(columns=['ID', 'NAME', 'LAST_NAME'])

# A função get_processo_won_deals() foi removida pois sua funcionalidade
# agora é coberta pela nova get_all_entities() e pela lógica em vendas_g7_tab.py 