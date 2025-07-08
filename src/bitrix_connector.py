"""
Conector principal para API do Bitrix24
Seguindo Object Calisthenics e princípios SOLID
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json


@dataclass
class DateRange:
    """Encapsula range de datas para filtros"""
    start_date: str
    end_date: str


@dataclass
class ApiCredentials:
    """Encapsula credenciais da API"""
    base_url: str
    token: str
    timeout: int
    max_retries: int


@dataclass
class QueryFilter:
    """Representa um filtro para consulta"""
    field_name: str
    values: List[Any]
    filter_type: str
    operator: str


class BitrixApiError(Exception):
    """Exceção específica para erros da API do Bitrix"""
    pass


class BitrixConnector:
    """Conector responsável pela comunicação com a API do Bitrix24"""
    
    def __init__(self):
        self._credentials = self._load_credentials()
        self._session = self._create_session()
    
    def _load_credentials(self) -> ApiCredentials:
        """Carrega credenciais do secrets"""
        try:
            return ApiCredentials(
                base_url=st.secrets["bitrix24"]["base_url"],
                token=st.secrets["bitrix24"]["token"],
                timeout=st.secrets["api"]["timeout"],
                max_retries=st.secrets["api"]["max_retries"]
            )
        except KeyError as e:
            raise BitrixApiError(f"Credencial não encontrada: {e}")
    
    def _create_session(self) -> requests.Session:
        """Cria sessão HTTP configurada"""
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
                    st.warning(f"Resposta inesperada da API para a tabela {table_name}: {response_data}")
                    return pd.DataFrame()

            except requests.exceptions.RequestException as e:
                if attempt == self._credentials.max_retries - 1:
                    raise BitrixApiError(f"Falha na requisição para a tabela {table_name} após {self._credentials.max_retries} tentativas: {e}")
                continue
        
        return pd.DataFrame()

    def get_deals_data(self, category_ids: Optional[List[int]] = None,
                      date_range: Optional[DateRange] = None) -> pd.DataFrame:
        """Obtém dados de negócios (deals), aplicando filtros via API."""
        payload = {}
        filters = []

        if category_ids:
            filters.append({"fieldName": "CATEGORY_ID", "values": category_ids, "type": "INCLUDE", "operator": "EQUALS"})
        
        if date_range:
            # O BI Connector usa um formato diferente para dateRange
            payload["dateRange"] = {
                "startDate": date_range.start_date,
                "endDate": date_range.end_date
            }
            payload["configParams"] = {
                "timeFilterColumn": "DATE_CREATE"
            }
        
        if filters:
            payload["dimensionsFilters"] = [filters]
            
        return self._execute_bi_query("crm_deal", payload)

    def get_deals_uf_data(self, date_range: Optional[DateRange] = None) -> pd.DataFrame:
        """Obtém dados de UF dos negócios, com filtro de data opcional."""
        payload = {}
        if date_range:
            payload["dateRange"] = {
                "startDate": date_range.start_date,
                "endDate": date_range.end_date
            }
            # Assumindo que a tabela UF também pode ser filtrada por uma data,
            # mas o BI connector não documenta qual campo de data usar para crm_deal_uf.
            # Se isso falhar, o filtro de data terá de ser local para esta tabela.
            # payload["configParams"] = {"timeFilterColumn": "DATE_CREATE"} # Campo incerto
        
        return self._execute_bi_query("crm_deal_uf", payload)

    def get_users_data(self) -> pd.DataFrame:
        """Obtém dados dos usuários do Bitrix24."""
        return self._execute_bi_query("user", {})

    def _convert_to_dataframe(self, response_data, fields: List[str]) -> pd.DataFrame:
        """Converte resposta da API em DataFrame (obsoleto com _fetch_all_pages, mas mantido por segurança)"""
        if isinstance(response_data, list):
            return pd.DataFrame(response_data)
        return pd.DataFrame()

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpa e formata o DataFrame"""
        if df.empty:
            return df

        # Converte colunas numéricas
        numeric_cols = ['ID', 'CATEGORY_ID', 'ASSIGNED_BY_ID', 'CREATED_BY_ID', 'COMPANY_ID', 'CONTACT_ID', 'LEAD_ID']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        # Converte colunas de data
        date_cols = ['DATE_CREATE', 'DATE_MODIFY', 'BEGINDATE', 'CLOSEDATE']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df


class BitrixDataCache:
    """Gerencia cache de dados do Bitrix"""
    
    CACHE_DURATION_MINUTES = 30 # Duração padrão do cache em minutos
    
    @classmethod
    def get_cache_key(cls, table: str, filters: str = "") -> str:
        """Gera chave única para cache"""
        return f"bitrix_{table}_{filters}"
    
    @classmethod
    def is_cache_valid(cls, cache_key: str) -> bool:
        """Verifica se cache é válido"""
        if cache_key not in st.session_state:
            return False
        
        cache_data = st.session_state[cache_key]
        # Verifica se a estrutura esperada do cache existe
        if not isinstance(cache_data, dict) or 'timestamp' not in cache_data or 'duration_seconds' not in cache_data:
            return False 
        
        cache_time = cache_data['timestamp']
        duration_seconds = cache_data['duration_seconds']
        
        # Se duration_seconds for None ou inválido, podemos tratar como sempre expirado ou usar um padrão.
        # Aqui, se for None ou não numérico, consideraremos expirado para segurança.
        if not isinstance(duration_seconds, (int, float)) or duration_seconds <= 0:
             # Fallback para a duração padrão da classe se 'duration_seconds' for inválida ou não definida
             # No entanto, set_cache_data deve sempre definir um valor numérico para duration_seconds.
             # Se chegou aqui com duration_seconds inválido, é um estado inesperado.
             # Poderíamos também logar um aviso aqui.
             # Para simplificar, vamos considerar que duration_seconds sempre será um int positivo.
             pass # Assume que set_cache_data garante duration_seconds válido.

        expiry_time = cache_time + timedelta(seconds=duration_seconds)
        return datetime.now() < expiry_time
    
    @classmethod
    def get_cached_data(cls, cache_key: str) -> Optional[pd.DataFrame]:
        """Obtém dados do cache"""
        if not cls.is_cache_valid(cache_key):
            # Limpar cache inválido/expirado
            if cache_key in st.session_state:
                del st.session_state[cache_key]
            return None
        
        return st.session_state[cache_key].get('data') # Usar .get para segurança
    
    @classmethod
    def set_cache_data(cls, cache_key: str, data: pd.DataFrame, expires_in_seconds: Optional[int] = None) -> None:
        """Armazena dados no cache com tempo de expiração customizável."""
        
        if expires_in_seconds is not None and expires_in_seconds > 0:
            duration_to_set_seconds = expires_in_seconds
        else:
            duration_to_set_seconds = cls.CACHE_DURATION_MINUTES * 60
            
        st.session_state[cache_key] = {
            'data': data,
            'timestamp': datetime.now(),
            'duration_seconds': duration_to_set_seconds
        } 