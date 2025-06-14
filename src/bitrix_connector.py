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
                token=st.secrets["bitrix24"].get("token", ""),
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
            'User-Agent': 'Streamlit-JusGestante/1.0'
        })
        return session
    
    def _build_query_payload(self, table: str, date_range: Optional[DateRange] = None,
                           filters: Optional[List[QueryFilter]] = None,
                           fields: Optional[List[str]] = None) -> Dict:
        """Constrói payload da consulta"""
        payload = {}
        
        if date_range:
            payload["dateRange"] = {
                "startDate": date_range.start_date,
                "endDate": date_range.end_date
            }
            payload["configParams"] = {
                "timeFilterColumn": "DATE_CREATE"
            }
        
        if fields:
            payload["fields"] = [{"name": field} for field in fields]
        
        if filters:
            payload["dimensionsFilters"] = self._build_dimensions_filters(filters)
        
        return payload
    
    def _build_dimensions_filters(self, filters: List[QueryFilter]) -> List[List[Dict]]:
        """Constrói filtros dimensionais"""
        return [[{
            "fieldName": filter_obj.field_name,
            "values": filter_obj.values,
            "type": filter_obj.filter_type,
            "operator": filter_obj.operator
        } for filter_obj in filters]]
    
    def _execute_request(self, table: str, payload: Dict) -> Dict:
        """Executa requisição à API"""
        url = f"{self._credentials.base_url}?token={self._credentials.token}&table={table}"
        
        for attempt in range(self._credentials.max_retries):
            try:
                response = self._session.post(
                    url,
                    json=payload,
                    timeout=self._credentials.timeout
                )
                response.raise_for_status()
                return response.json()
            
            except requests.exceptions.RequestException as e:
                if attempt == self._credentials.max_retries - 1:
                    raise BitrixApiError(f"Falha na requisição após {self._credentials.max_retries} tentativas: {e}")
                continue
    
    def get_deals_data(self, category_ids: Optional[List[int]] = None,
                      date_range: Optional[DateRange] = None,
                      fields: Optional[List[str]] = None) -> pd.DataFrame:
        """Obtém dados de negócios (deals) do Bitrix24"""
        
        # Para esta API, usamos requisição GET simples (payload vazio funciona melhor)
        url = f"{self._credentials.base_url}?token={self._credentials.token}&table=crm_deal"
        
        try:
            response = self._session.get(url, timeout=self._credentials.timeout)
            response.raise_for_status()
            
            response_data = response.json()
            df = self._convert_to_dataframe(response_data, fields or [])
            
            # Aplica filtros após carregar os dados
            if not df.empty:
                df = self._apply_filters(df, category_ids, date_range)
            
            return df
        
        except Exception as e:
            st.error(f"Erro ao obter dados de deals: {e}")
            return pd.DataFrame()
    
    def _apply_filters(self, df: pd.DataFrame, category_ids: Optional[List[int]] = None,
                      date_range: Optional[DateRange] = None) -> pd.DataFrame:
        """Aplica filtros nos dados carregados"""
        if df.empty:
            return df
        
        # Cria cópia para evitar warnings do pandas
        df = df.copy()
        
        # Filtro por categoria
        if category_ids and 'CATEGORY_ID' in df.columns:
            df = df[df['CATEGORY_ID'].isin(category_ids)]
        
        # Filtro por data
        if date_range and 'DATE_CREATE' in df.columns:
            df.loc[:, 'DATE_CREATE'] = pd.to_datetime(df['DATE_CREATE'], errors='coerce')
            start_date = pd.to_datetime(date_range.start_date)
            end_date = pd.to_datetime(date_range.end_date)
            df = df[(df['DATE_CREATE'] >= start_date) & (df['DATE_CREATE'] <= end_date)]
        
        return df
    
    def get_deals_uf_data(self, date_range: Optional[DateRange] = None) -> pd.DataFrame:
        """Obtém dados de UF dos negócios"""
        url = f"{self._credentials.base_url}?token={self._credentials.token}&table=crm_deal_uf"
        
        try:
            response = self._session.get(url, timeout=self._credentials.timeout)
            response.raise_for_status()
            
            response_data = response.json()
            df = self._convert_to_dataframe(response_data, [])
            
            # Aplica filtro de data se necessário
            if not df.empty and date_range:
                df = self._apply_filters(df, None, date_range)
            
            return df
        
        except Exception as e:
            st.error(f"Erro ao obter dados de UF: {e}")
            return pd.DataFrame()
    
    def _convert_to_dataframe(self, response_data, fields: List[str]) -> pd.DataFrame:
        """Converte resposta da API em DataFrame"""
        try:
            # A API retorna uma lista diretamente (não um objeto com chave 'data')
            if isinstance(response_data, list) and response_data:
                # Primeiro elemento é o cabeçalho com nomes das colunas
                column_names = response_data[0]
                data_rows = response_data[1:]  # Demais elementos são os dados
                
                if not data_rows:
                    return pd.DataFrame()
                
                # Cria DataFrame com os nomes das colunas do cabeçalho
                df = pd.DataFrame(data_rows, columns=column_names)
                
                return self._clean_dataframe(df)
            
            # Fallback: se for objeto com chave 'data' (formato antigo)
            elif isinstance(response_data, dict) and 'data' in response_data:
                data_arrays = response_data['data']
                
                if not data_arrays:
                    return pd.DataFrame()
                
                df = pd.DataFrame(data_arrays, columns=fields[:len(data_arrays[0])])
                return self._clean_dataframe(df)
            
            else:
                st.warning("Formato de resposta da API não reconhecido")
                return pd.DataFrame()
        
        except Exception as e:
            st.error(f"Erro ao converter dados para DataFrame: {e}")
            return pd.DataFrame()
    
    def _get_column_mapping(self, num_columns: int) -> List[str]:
        """Retorna mapeamento de colunas baseado no número de colunas"""
        # Mapeamento padrão baseado na estrutura da API Bitrix24
        base_columns = [
            'ID', 'TITLE', 'CATEGORY_ID', 'STAGE_SEMANTICS', 'OPPORTUNITY',
            'CURRENCY_ID', 'DATE_CREATE', 'DATE_MODIFY', 'STAGE_ID', 
            'ASSIGNED_BY_ID', 'CREATED_BY_ID', 'MOVED_BY_ID', 'MOVED_TIME',
            'COMPANY_ID', 'CONTACT_ID', 'IS_RETURN_CUSTOMER', 'PROBABILITY',
            'BEGINDATE', 'CLOSEDATE', 'OPENED', 'CLOSED', 'TYPE_ID',
            'LEAD_ID', 'IS_NEW', 'IS_RECURRING', 'IS_WON', 'IS_LOST'
        ]
        
        # Retorna apenas as colunas necessárias baseado no número disponível
        if num_columns <= len(base_columns):
            return base_columns[:num_columns]
        else:
            # Se há mais colunas que o esperado, adiciona genéricas
            extra_cols = [f'COLUMN_{i}' for i in range(len(base_columns), num_columns)]
            return base_columns + extra_cols
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpa e formata o DataFrame"""
        if df.empty:
            return df
        
        # Converte colunas de data
        date_columns = [col for col in df.columns if 'DATE' in col.upper()]
        for col in date_columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Converte colunas numéricas
        numeric_columns = ['OPPORTUNITY', 'CURRENCY_ID', 'CATEGORY_ID']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df

    def get_users_data(self) -> pd.DataFrame:
        """Obtém dados de usuários do Bitrix24."""
        # Retornando DataFrame vazio temporariamente para evitar erro de API com credenciais do PowerBI.
        # A URL de webhook atual não suporta o método 'user.get'.
        st.warning("A busca de dados de usuários está desabilitada temporariamente devido à configuração de credenciais.")
        return pd.DataFrame()

        # O código abaixo fica comentado até que um webhook de API REST funcional seja configurado.
        # url = f"{self._credentials.base_url}user.get.json"
        # params = {
        #     'FILTER[ACTIVE]': 'Y',
        # }

        # try:
        #     response = self._session.get(
        #         url,
        #         params=params,
        #         timeout=self._credentials.timeout
        #     )
        #     response.raise_for_status()
        #     response_data = response.json()

        #     if 'result' in response_data and isinstance(response_data['result'], list):
        #         users_list = response_data['result']
        #         if not users_list:
        #             st.info("Nenhum usuário encontrado ou lista de usuários vazia.")
        #             return pd.DataFrame()
                
        #         df = pd.DataFrame(users_list)
                
        #         required_cols = ['ID', 'NAME', 'LAST_NAME']
                
        #         for col in required_cols:
        #             if col not in df.columns:
        #                 st.error(f"Coluna '{col}' não encontrada nos dados dos usuários da API.")
        #                 return pd.DataFrame() 

        #         df['ID'] = df['ID'].astype(str)
                
        #         return df[required_cols]
            
        #     elif 'error' in response_data:
        #         st.error(f"Erro da API Bitrix ao buscar usuários: {response_data.get('error_description', response_data['error'])}")
        #         return pd.DataFrame()
        #     else:
        #         st.warning("Resposta da API de usuários não contém 'result' ou está em formato inesperado.")
        #         return pd.DataFrame()

        # except requests.exceptions.RequestException as e:
        #     st.error(f"Falha na requisição ao buscar usuários: {e}")
        #     return pd.DataFrame()
        # except Exception as e:
        #     st.error(f"Erro inesperado ao processar dados dos usuários: {e}")
        #     return pd.DataFrame()


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