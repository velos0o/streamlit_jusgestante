import streamlit as st
import pandas as pd
import sys
import os

# Adiciona src ao path para imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from src.g7_connector import G7Connector, G7ApiError

@st.cache_data(ttl=1800) # Cache dos dados por 30 minutos (1800 segundos)
def get_cached_g7_data():
    """Função de wrapper para cachear os dados da G7."""
    return get_g7_data()

def get_g7_data():
    """
    Busca dados de vendas da G7 Assessoria, enriquecendo-os com campos personalizados.
    Filtra negócios EXCLUSIVAMENTE na etapa 'ENVIADO P/ FORMALIZAÇÃO' (UC_IV0DI0).
    """
    g7_connector = G7Connector()
    
    filter_params = {'STAGE_ID': 'UC_IV0DI0'}
    
    # Seleciona apenas os campos principais da entidade 'crm.deal'
    main_select_fields = ['ID', 'TITLE', 'ASSIGNED_BY', 'OPPORTUNITY']

    try:
        # 1. Buscar os dados da entidade principal (crm_deal)
        main_df = g7_connector.get_all_entities(
            entity_name='crm_deal', # Correção: de 'crm.deal' para 'crm_deal'
            filter_params=filter_params, 
            select_fields=main_select_fields
        )

        if main_df.empty:
            return pd.DataFrame()

        # 2. Obter os IDs dos negócios encontrados para buscar os campos UF
        deal_ids = main_df['ID'].tolist()
        
        # 3. Buscar os dados da tabela de campos personalizados (crm_deal_uf)
        # CORREÇÃO: A chave correta para filtrar e selecionar é DEAL_ID, não VALUE_ID.
        uf_select_fields = ['DEAL_ID', 'UF_CRM_DEAL_ENVIADA_PROCESS', 'UF_CRM_DATA_FECHAMENTO1']
        uf_df = g7_connector.get_all_entities(
            entity_name='crm_deal_uf',
            filter_params={'DEAL_ID': deal_ids},
            select_fields=uf_select_fields
        )

        # 4. Juntar os dois DataFrames
        if not uf_df.empty:
            # Converte IDs para o mesmo tipo para garantir a junção correta
            main_df['ID'] = main_df['ID'].astype(str)
            uf_df['DEAL_ID'] = uf_df['DEAL_ID'].astype(str)
            # Junta os dataframes usando as chaves corretas: ID (principal) e DEAL_ID (campos UF)
            full_df = pd.merge(main_df, uf_df, left_on='ID', right_on='DEAL_ID', how='left')
        else:
            full_df = main_df
            # Adiciona colunas UF vazias para evitar erros posteriores se não houver dados UF
            if 'UF_CRM_DEAL_ENVIADA_PROCESS' not in full_df.columns:
                full_df['UF_CRM_DEAL_ENVIADA_PROCESS'] = pd.NaT
            if 'UF_CRM_DATA_FECHAMENTO1' not in full_df.columns:
                 full_df['UF_CRM_DATA_FECHAMENTO1'] = pd.NaT

        if 'OPPORTUNITY' in full_df.columns:
            full_df['OPPORTUNITY'] = pd.to_numeric(full_df['OPPORTUNITY'], errors='coerce').fillna(0)
            
        return full_df

    except Exception as e:
        st.error(f"Erro ao buscar dados detalhados da G7: {e}")
        return pd.DataFrame()


def render_vendas_g7_tab():
    """Renderiza a tabela de 'Vendas - Process G7'."""
    st.header("Vendas de Processos - G7 Assessoria")

    try:
        deals_df = get_cached_g7_data()

        if deals_df.empty:
            st.info("Nenhuma venda de 'PROCESSO' ou 'PROCESSO + AUXÍLIO' encontrada no período.")
            return

        vendas_por_responsavel = deals_df.groupby('ASSIGNED_BY').size().reset_index(name='Vendas')
        vendas_por_responsavel.rename(columns={'ASSIGNED_BY': 'Responsável'}, inplace=True)

        # Ordena os responsáveis por número de vendas
        vendas_por_responsavel.sort_values(by='Vendas', ascending=False, inplace=True)

        # Adiciona a linha de total ao final
        total_vendas = vendas_por_responsavel['Vendas'].sum()
        total_row = pd.DataFrame([{'Responsável': 'Total', 'Vendas': total_vendas}])
        
        resultado_df = pd.concat([vendas_por_responsavel, total_row], ignore_index=True)
        
        st.dataframe(resultado_df, use_container_width=True, hide_index=True)

    except G7ApiError as e:
        st.error(f"Erro de API ao buscar dados da G7: {e}")
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}") 

@st.cache_data(ttl=1800) # Cache dos dados por 30 minutos (1800 segundos)
def get_g7_vendas_won_data():
    """
    Busca todos os negócios de Vendas (category_id=0) da G7 que estão na etapa 'Ganho' (WON).
    Aplica um filtro duplo (API e pandas) para garantir a precisão.
    """
    g7_connector = G7Connector()
    
    filter_params = {
        'CATEGORY_ID': 0,
        'STAGE_ID': 'WON'
    }
    
    # Pedimos também o STAGE_ID para a verificação em pandas
    select_fields = ['ID', 'STAGE_ID']

    try:
        df = g7_connector.get_all_entities(
            entity_name='crm_deal',
            filter_params=filter_params, 
            select_fields=select_fields
        )

        if not df.empty:
            # Filtro de segurança em pandas para garantir que apenas 'WON' passe
            df_won = df[df['STAGE_ID'] == 'WON'].copy()
            return df_won
        
        return df

    except Exception as e:
        # Log para o console em vez de mostrar erro na UI para verificação em segundo plano
        print(f"Erro ao buscar dados de vendas ganhas da G7: {e}") 
        return pd.DataFrame() 