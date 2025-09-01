import streamlit as st
import pandas as pd
import sys
import os

# Adiciona src ao path para imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from src.g7_connector import G7Connector, G7ApiError
from datetime import datetime, timedelta

@st.cache_data(ttl=1800) # Cache dos dados por 30 minutos (1800 segundos)
def get_cached_g7_data():
    """Função de wrapper para cachear os dados da G7 (APENAS etapa UC_IV0DI0, usado na sincronização)."""
    return get_g7_data()

@st.cache_data(ttl=1800)
def get_cached_g7_data_all():
    """Cache para dados da G7 sem filtro de etapa (usado na aba de Vendas)."""
    return get_g7_data_all()

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


def get_g7_data_all():
    """
    Busca dados de vendas da G7 sem restrição por etapa, enriquecendo com campos personalizados.
    Filtra pelo funil de Vendas (category_id = 0).
    """
    g7_connector = G7Connector()
    
    filter_params = {'CATEGORY_ID': 0}
    
    main_select_fields = ['ID', 'TITLE', 'ASSIGNED_BY', 'OPPORTUNITY', 'CATEGORY_ID']

    try:
        main_df = g7_connector.get_all_entities(
            entity_name='crm_deal',
            filter_params=filter_params, 
            select_fields=main_select_fields
        )

        if main_df.empty:
            return pd.DataFrame()

        deal_ids = main_df['ID'].tolist()
        uf_select_fields = ['DEAL_ID', 'UF_CRM_DEAL_ENVIADA_PROCESS', 'UF_CRM_DATA_FECHAMENTO1']
        uf_df = g7_connector.get_all_entities(
            entity_name='crm_deal_uf',
            filter_params={'DEAL_ID': deal_ids},
            select_fields=uf_select_fields
        )

        if not uf_df.empty:
            main_df['ID'] = main_df['ID'].astype(str)
            uf_df['DEAL_ID'] = uf_df['DEAL_ID'].astype(str)
            full_df = pd.merge(main_df, uf_df, left_on='ID', right_on='DEAL_ID', how='left')
        else:
            full_df = main_df
            if 'UF_CRM_DEAL_ENVIADA_PROCESS' not in full_df.columns:
                full_df['UF_CRM_DEAL_ENVIADA_PROCESS'] = pd.NaT
            if 'UF_CRM_DATA_FECHAMENTO1' not in full_df.columns:
                 full_df['UF_CRM_DATA_FECHAMENTO1'] = pd.NaT

        if 'OPPORTUNITY' in full_df.columns:
            full_df['OPPORTUNITY'] = pd.to_numeric(full_df['OPPORTUNITY'], errors='coerce').fillna(0)
            
        return full_df

    except Exception as e:
        st.error(f"Erro ao buscar dados detalhados da G7 (all): {e}")
        return pd.DataFrame()


def render_vendas_g7_tab():
    """Renderiza a tabela de 'Vendas - Process G7'."""
    st.header("Vendas de Processos - G7 Assessoria")

    # Adiciona os filtros de data
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Data de Início", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("Data de Fim", datetime.now())

    debug_mode = st.checkbox("Modo Depuração (Contagem de Vendas)", key="g7_vendas_debug_mode")

    # Converte as datas para o formato datetime para filtrar
    start_date_dt = datetime.combine(start_date, datetime.min.time())
    end_date_dt = datetime.combine(end_date, datetime.max.time())

    try:
        # Usa dados sem filtro de etapa para a aba de vendas
        deals_df_raw = get_cached_g7_data_all()

        if deals_df_raw.empty:
            st.info("Nenhuma venda de 'PROCESSO' ou 'PROCESSO + AUXÍLIO' encontrada no período.")
            return

        deals_df_filtered = pd.DataFrame()
        if 'UF_CRM_DEAL_ENVIADA_PROCESS' in deals_df_raw.columns:
            deals_df_with_date = deals_df_raw.copy()
            deals_df_with_date['UF_CRM_DEAL_ENVIADA_PROCESS'] = pd.to_datetime(deals_df_with_date['UF_CRM_DEAL_ENVIADA_PROCESS'], errors='coerce')

            # Filtra o DataFrame com base no intervalo de datas selecionado
            deals_df_filtered = deals_df_with_date[
                (deals_df_with_date['UF_CRM_DEAL_ENVIADA_PROCESS'] >= start_date_dt) &
                (deals_df_with_date['UF_CRM_DEAL_ENVIADA_PROCESS'] <= end_date_dt)
            ]
        else:
            st.warning("A coluna 'Data de Venda' (UF_CRM_DEAL_ENVIADA_PROCESS) não foi encontrada.")
            return

        if debug_mode:
            st.subheader("🕵️‍♂️ Modo Depuração")
            with st.expander("Clique para ver os dados para depuração"):
                st.markdown(f"**Intervalo selecionado:** de `{start_date}` a `{end_date}`")
                
                df_raw_display = deals_df_raw.copy()
                if 'UF_CRM_DEAL_ENVIADA_PROCESS' in df_raw_display.columns:
                     df_raw_display['UF_CRM_DEAL_ENVIADA_PROCESS_DT'] = pd.to_datetime(df_raw_display['UF_CRM_DEAL_ENVIADA_PROCESS'], errors='coerce')
                
                st.markdown("#### Tabela de Vendas (Bruto, ANTES do filtro de data)")
                st.dataframe(df_raw_display[['ID', 'TITLE', 'UF_CRM_DEAL_ENVIADA_PROCESS_DT']].dropna(subset=['UF_CRM_DEAL_ENVIADA_PROCESS_DT']))

                st.markdown(f"#### Tabela de Vendas (APÓS filtro de data) - {len(deals_df_filtered)} registros")
                st.dataframe(deals_df_filtered[['ID', 'TITLE', 'UF_CRM_DEAL_ENVIADA_PROCESS']])
        
        if deals_df_filtered.empty:
            st.info("Nenhuma venda encontrada para o período selecionado.")
            total_row = pd.DataFrame([{'Responsável': 'Total', 'Vendas': 0}])
            st.dataframe(total_row, use_container_width=True, hide_index=True)
            return

        # Recalcula as vendas após a filtragem
        vendas_por_responsavel = deals_df_filtered.groupby('ASSIGNED_BY').size().reset_index(name='Vendas')
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


@st.cache_data(ttl=1800)
def get_g7_deals_for_sync_check():
    """
    Busca todos os negócios de Vendas (category_id=0) da G7, exceto aqueles
    na etapa 'UC_IV0DI0', para a verificação de sincronização.
    """
    g7_connector = G7Connector()
    
    # Buscamos todos os negócios do funil de Vendas, o filtro de etapa será feito em pandas
    filter_params = {
        'CATEGORY_ID': 0
    }
    
    select_fields = ['ID', 'STAGE_ID']

    try:
        df = g7_connector.get_all_entities(
            entity_name='crm_deal',
            filter_params=filter_params, 
            select_fields=select_fields
        )

        if not df.empty:
            # Filtro em pandas para excluir a etapa 'UC_IV0DI0'
            df_filtered = df[df['STAGE_ID'] != 'UC_IV0DI0'].copy()
            return df_filtered
        
        return df

    except Exception as e:
        print(f"Erro ao buscar dados da G7 para verificação de sincronia: {e}") 
        return pd.DataFrame() 