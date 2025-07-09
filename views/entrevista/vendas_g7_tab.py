import streamlit as st
import pandas as pd
import sys
import os

# Adiciona src ao path para imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from src.g7_connector import G7Connector, G7ApiError

@st.cache_data(ttl=1800) # Cache dos dados por 30 minutos (1800 segundos)
def get_cached_g7_data():
    """Função cacheada para buscar os dados da G7."""
    connector = G7Connector()
    deals_df = connector.get_processo_won_deals()
    return deals_df

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