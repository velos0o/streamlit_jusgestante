"""
Serviço de dados para relatórios
Camada de serviço que aplica regras de negócio aos dados do Bitrix24
"""

import pandas as pd
from datetime import datetime, date
from typing import List, Optional, Dict, Any
import streamlit as st

from .bitrix_connector import BitrixConnector, DateRange, BitrixDataCache
from config.funis_config import FunilConfig, Category


class DataService:
    """Serviço responsável por fornecer dados processados para os relatórios"""
    
    def __init__(self):
        self._connector = BitrixConnector()
        self._cache = BitrixDataCache()
    
    def get_deals_by_category(self, category_ids: List[int], 
                             start_date: Optional[date] = None,
                             end_date: Optional[date] = None) -> pd.DataFrame:
        """Obtém deals filtrados por categoria e período"""
        
        # Gera chave de cache
        cache_key = self._cache.get_cache_key(
            "deals", 
            f"categories_{'-'.join(map(str, category_ids))}_{start_date}_{end_date}"
        )
        
        # Verifica cache
        cached_data = self._cache.get_cached_data(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Prepara range de datas
        date_range = None
        if start_date and end_date:
            date_range = DateRange(
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
        
        # Obtém dados do Bitrix
        deals_df = self._connector.get_deals_data(
            category_ids=category_ids,
            date_range=date_range
        )
        
        uf_df = self._connector.get_deals_uf_data(
            date_range=date_range  # Passa o range de datas para filtrar dados UF também
        )
        
        # Processa dados
        processed_data = self._process_deals_data(deals_df, uf_df) # Passa uf_df
        
        # Armazena no cache
        self._cache.set_cache_data(cache_key, processed_data)
        
        return processed_data
    
    def get_comercial_data(self, start_date: Optional[date] = None,
                          end_date: Optional[date] = None) -> pd.DataFrame:
        """Obtém dados específicos do funil comercial"""
        return self.get_deals_by_category(
            category_ids=[FunilConfig.COMERCIAL_ID],
            start_date=start_date,
            end_date=end_date
        )
    
    def get_tramites_data(self, start_date: Optional[date] = None,
                         end_date: Optional[date] = None) -> pd.DataFrame:
        """Obtém dados específicos do funil de trâmites"""
        return self.get_deals_by_category(
            category_ids=[FunilConfig.TRAMITES_ID],
            start_date=start_date,
            end_date=end_date
        )
    
    def get_audiencia_data(self, start_date: Optional[date] = None,
                          end_date: Optional[date] = None) -> pd.DataFrame:
        """Obtém dados específicos do funil de audiências"""
        return self.get_deals_by_category(
            category_ids=[FunilConfig.AUDIENCIA_ID],
            start_date=start_date,
            end_date=end_date
        )
    
    def get_all_funis_data(self, start_date: Optional[date] = None,
                          end_date: Optional[date] = None) -> pd.DataFrame:
        """Obtém dados de todos os funis principais"""
        return self.get_deals_by_category(
            category_ids=[
                FunilConfig.COMERCIAL_ID,
                FunilConfig.TRAMITES_ID,
                FunilConfig.AUDIENCIA_ID
            ],
            start_date=start_date,
            end_date=end_date
        )
    
    def get_users_data(self) -> pd.DataFrame:
        """Obtém dados dos usuários do Bitrix24 e aplica cache."""
        cache_key = self._cache.get_cache_key("users", "all_users_data")
        
        cached_data = self._cache.get_cached_data(cache_key)
        if cached_data is not None:
            # st.caption("📝 Users data from cache") # Log para debug
            return cached_data
        
        # st.caption("📝 Fetching users data from Bitrix") # Log para debug
        users_df = self._connector.get_users_data()
        
        # Adiciona uma verificação simples para retornar um DataFrame vazio se a busca falhar
        if users_df is None or not isinstance(users_df, pd.DataFrame):
            users_df = pd.DataFrame() # Retorna DataFrame vazio para evitar erros no merge
            
        self._cache.set_cache_data(cache_key, users_df, expires_in_seconds=3600) # Cache por 1 hora
        return users_df
    
    def _process_deals_data(self, df: pd.DataFrame, uf_df: pd.DataFrame) -> pd.DataFrame:
        """Processa dados dos deals aplicando regras de negócio"""
        if df.empty:
            return df

        # Mescla dados de deals com dados UF
        if not uf_df.empty and 'DEAL_ID' in uf_df.columns:
            # Garante que as colunas de merge tenham o mesmo tipo
            df['ID'] = df['ID'].astype(str)
            uf_df['DEAL_ID'] = uf_df['DEAL_ID'].astype(str)
            
            df = pd.merge(df, uf_df, left_on='ID', right_on='DEAL_ID', how='left', suffixes= (' ', '_uf'))
            
            # Converte a coluna UF_CRM_DATA_FECHAMENTO1 para datetime após a mesclagem
            if 'UF_CRM_DATA_FECHAMENTO1' in df.columns:
                df['UF_CRM_DATA_FECHAMENTO1'] = pd.to_datetime(df['UF_CRM_DATA_FECHAMENTO1'], errors='coerce').dt.date

            # Converter a coluna de Data de Audiência (UF_CRM_1731693426655)
            DATA_AUDIENCIA_FIELD = 'UF_CRM_1731693426655'
            if DATA_AUDIENCIA_FIELD in df.columns:
                # Tenta converter para datetime. O formato 'dd/mm/yyyy' será tratado se pd.to_datetime inferir corretamente.
                # Usar dayfirst=True se o formato for ambiguo e for de fato dd/mm/yyyy.
                # Se o campo já for datetime ou timestamp numérico, pd.to_datetime geralmente lida bem.
                df[DATA_AUDIENCIA_FIELD] = pd.to_datetime(df[DATA_AUDIENCIA_FIELD], errors='coerce', dayfirst=True) 
                # Apenas a data, zerando o componente de hora, ou .dt.date para objeto date.
                # df[DATA_AUDIENCIA_FIELD] = df[DATA_AUDIENCIA_FIELD].dt.normalize() # Para manter como datetime64[ns] com hora 00:00:00
                # Ou, para converter para objeto date do Python (pode ser mais simples para algumas manipulações)
                # df[DATA_AUDIENCIA_FIELD] = df[DATA_AUDIENCIA_FIELD].dt.date # Isso altera o dtype para object

        # Enriquece com informações dos funis
        df = self._enrich_with_category_info(df)
        
        # Enriquece com informações dos stages
        df = self._enrich_with_stage_info(df)
        
        # Calcula métricas adicionais
        df = self._calculate_metrics(df)
        
        return df
    
    def _enrich_with_category_info(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adiciona informações das categorias aos dados"""
        if 'CATEGORY_ID' not in df.columns:
            return df
        
        category_mapping = {
            FunilConfig.COMERCIAL_ID: 'COMERCIAL',
            FunilConfig.TRAMITES_ID: 'TRÂMITES ADMINISTRATIVO',
            FunilConfig.AUDIENCIA_ID: 'AUDIÊNCIA'
        }
        
        df['CATEGORY_NAME'] = df['CATEGORY_ID'].map(category_mapping)
        
        return df
    
    def _enrich_with_stage_info(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adiciona informações dos estágios aos dados"""
        if df.empty:
            return df
        
        # Se já temos STAGE_SEMANTICS da API, usa para criar flags básicas
        if 'STAGE_SEMANTIC' in df.columns:
            # Mapeia semânticas para nomes mais legíveis
            semantic_mapping = {
                'WON': 'NEGÓCIO FECHADO',
                'LOST': 'NEGÓCIO PERDIDO', 
                'PROCESS': 'EM ANDAMENTO'
            }
            
            # Se não temos STAGE_NAME, cria baseado na semântica
            if 'STAGE_NAME' not in df.columns:
                df['STAGE_NAME'] = df['STAGE_SEMANTIC'].map(semantic_mapping).fillna('INDEFINIDO')
        
        # Se temos CATEGORY_ID e STAGE_ID, tenta mapear com configuração
        if 'CATEGORY_ID' in df.columns and 'STAGE_ID' in df.columns:
            stage_mapping = {}
            
            for category in FunilConfig.get_all_categories().values():
                for stage in category.stages:
                    key = f"{category.category_id}_{stage.stage_id}"
                    stage_mapping[key] = stage.stage_name
            
            # Aplica mapeamento se disponível
            df['STAGE_KEY'] = df['CATEGORY_ID'].astype(str) + '_' + df['STAGE_ID'].astype(str)
            mapped_names = df['STAGE_KEY'].map(stage_mapping)
            
            # Usa mapeamento da configuração se disponível, senão mantém o existente
            if 'STAGE_NAME' in df.columns:
                df['STAGE_NAME'] = mapped_names.fillna(df['STAGE_NAME'])
            else:
                df['STAGE_NAME'] = mapped_names.fillna('INDEFINIDO')
            
            # Remove coluna auxiliar
            df = df.drop('STAGE_KEY', axis=1)
        
        return df
    
    def _calculate_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula métricas adicionais"""
        if df.empty:
            return df
        
        # Converte datas se necessário
        if 'DATE_CREATE' in df.columns:
            df['DATE_CREATE'] = pd.to_datetime(df['DATE_CREATE'], errors='coerce')
        
        if 'DATE_MODIFY' in df.columns:
            df['DATE_MODIFY'] = pd.to_datetime(df['DATE_MODIFY'], errors='coerce')
        
        # Calcula tempo no funil
        if 'DATE_CREATE' in df.columns:
            df['DAYS_IN_FUNNEL'] = (datetime.now() - df['DATE_CREATE']).dt.days
        
        # Inicializa colunas de status
        df['IS_WON'] = False
        df['IS_LOST'] = False

        # Define IS_WON e IS_LOST baseado em STAGE_ID, condicionado pela CATEGORY_ID
        if 'STAGE_ID' in df.columns and 'CATEGORY_ID' in df.columns:
            df['STAGE_ID'] = df['STAGE_ID'].astype(str).str.strip()
            
            # Lógica para o Funil Comercial
            comercial_mask = df['CATEGORY_ID'] == FunilConfig.COMERCIAL_ID
            df.loc[comercial_mask & (df['STAGE_ID'] == 'WON'), 'IS_WON'] = True
            df.loc[comercial_mask & (df['STAGE_ID'] == 'LOSE'), 'IS_LOST'] = True
            
            # Lógica para o Funil de Trâmites Administrativos
            tramites_mask = df['CATEGORY_ID'] == FunilConfig.TRAMITES_ID
            df.loc[tramites_mask & (df['STAGE_ID'] == 'C2:WON'), 'IS_WON'] = True
            df.loc[tramites_mask & (df['STAGE_ID'] == 'C2:LOSE'), 'IS_LOST'] = True
            
            # Lógica para o Funil de Audiências
            audiencia_mask = df['CATEGORY_ID'] == FunilConfig.AUDIENCIA_ID
            df.loc[audiencia_mask & (df['STAGE_ID'] == 'C4:WON'), 'IS_WON'] = True
            df.loc[audiencia_mask & (df['STAGE_ID'].isin(['C4:LOSE', 'C4:UC_PP1J4N', 'C4:UC_QK3BDP'])), 'IS_LOST'] = True

        elif 'STAGE_SEMANTIC' in df.columns: # Fallback se STAGE_ID ou CATEGORY_ID não estiverem disponíveis
            st.info("Usando fallback para STAGE_SEMANTIC pois STAGE_ID ou CATEGORY_ID não foram encontrados ou não cobriram todos os casos.")
            df['__TEMP_SEMANTIC__'] = df['STAGE_SEMANTIC'].astype(str).str.strip().str.upper()
            df.loc[df['__TEMP_SEMANTIC__'] == 'S', 'IS_WON'] = True
            df.loc[df['__TEMP_SEMANTIC__'] == 'F', 'IS_LOST'] = True
            if '__TEMP_SEMANTIC__' in df.columns:
                df.drop(columns=['__TEMP_SEMANTIC__'], inplace=True)
        else:
            st.warning("Colunas 'STAGE_ID'/'CATEGORY_ID' ou 'STAGE_SEMANTIC' não encontradas. Métricas IS_WON/IS_LOST podem estar incompletas.")

        # Define IS_ACTIVE: qualquer deal que não é WON nem LOST é considerado ativo.
        df['IS_ACTIVE'] = (~df['IS_WON']) & (~df['IS_LOST'])
        
        # Converte e limpa valores de oportunidade
        if 'OPPORTUNITY' in df.columns:
            df['OPPORTUNITY'] = pd.to_numeric(df['OPPORTUNITY'], errors='coerce').fillna(0)
        
        return df
    
    def get_performance_summary(self, category_id: Optional[int] = None,
                               start_date: Optional[date] = None,
                               end_date: Optional[date] = None) -> Dict[str, Any]:
        """Obtém resumo de performance dos funis"""
        
        # Obtém dados baseado no filtro
        if category_id:
            df = self.get_deals_by_category([category_id], start_date, end_date)
        else:
            df = self.get_all_funis_data(start_date, end_date)
        
        if df.empty:
            return self._get_empty_summary()
        
        return {
            'total_deals': len(df),
            'deals_won': len(df[df.get('IS_WON', False)]) if 'IS_WON' in df.columns else 0,
            'deals_lost': len(df[df.get('IS_LOST', False)]) if 'IS_LOST' in df.columns else 0,
            'deals_active': len(df[df.get('IS_ACTIVE', False)]) if 'IS_ACTIVE' in df.columns else 0,
            'conversion_rate': self._calculate_conversion_rate(df),
            'total_opportunity': df['OPPORTUNITY'].sum() if 'OPPORTUNITY' in df.columns else 0,
            'avg_opportunity': df['OPPORTUNITY'].mean() if 'OPPORTUNITY' in df.columns else 0,
            'avg_days_funnel': df['DAYS_IN_FUNNEL'].mean() if 'DAYS_IN_FUNNEL' in df.columns else 0
        }
    
    def _calculate_conversion_rate(self, df: pd.DataFrame) -> float:
        """Calcula taxa de conversão"""
        if df.empty or 'IS_WON' not in df.columns:
            return 0.0
        
        total_closed = len(df[df['IS_WON'] | df.get('IS_LOST', False)])
        if total_closed == 0:
            return 0.0
        
        won_deals = len(df[df['IS_WON']])
        return (won_deals / total_closed) * 100
    
    def _get_empty_summary(self) -> Dict[str, Any]:
        """Retorna resumo vazio"""
        return {
            'total_deals': 0,
            'deals_won': 0,
            'deals_lost': 0,
            'deals_active': 0,
            'conversion_rate': 0.0,
            'total_opportunity': 0.0,
            'avg_opportunity': 0.0,
            'avg_days_funnel': 0.0
        }
    
    def get_stage_distribution(self, category_id: int,
                              start_date: Optional[date] = None,
                              end_date: Optional[date] = None) -> pd.DataFrame:
        """Obtém distribuição de deals por estágio"""
        df = self.get_deals_by_category([category_id], start_date, end_date)
        
        if df.empty or 'STAGE_NAME' not in df.columns:
            return pd.DataFrame()
        
        stage_counts = df.groupby('STAGE_NAME').agg({
            'ID': 'count',
            'OPPORTUNITY': 'sum'
        }).rename(columns={'ID': 'COUNT', 'OPPORTUNITY': 'TOTAL_VALUE'})
        
        stage_counts['PERCENTAGE'] = (stage_counts['COUNT'] / stage_counts['COUNT'].sum()) * 100
        
        return stage_counts.reset_index()


class DataValidator:
    """Valida dados antes do processamento"""
    
    @staticmethod
    def validate_date_range(start_date: date, end_date: date) -> bool:
        """Valida se o range de datas é válido"""
        if start_date > end_date:
            st.error("Data inicial não pode ser maior que data final")
            return False
        
        if end_date > date.today():
            st.warning("Data final é maior que hoje")
        
        return True
    
    @staticmethod
    def validate_category_id(category_id: int) -> bool:
        """Valida se o ID da categoria é válido"""
        valid_ids = [
            FunilConfig.COMERCIAL_ID,
            FunilConfig.TRAMITES_ID,
            FunilConfig.AUDIENCIA_ID
        ]
        
        if category_id not in valid_ids:
            st.error(f"Category ID {category_id} não é válido")
            return False
        
        return True 