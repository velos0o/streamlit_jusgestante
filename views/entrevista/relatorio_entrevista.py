"""
Relatório do Funil de Entrevista
Análise de aproveitamento e Vendas de Processos G7.
"""

import streamlit as st
from datetime import date, timedelta
import sys
import os
import pandas as pd

# Adiciona src e config ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'config'))

from src.data_service import DataService
from views.entrevista.analise_responsaveis_entrevista import render_analise_responsaveis_entrevista
from views.entrevista.vendas_g7_tab import render_vendas_g7_tab

def render_relatorio_entrevista():
    """Renderiza um relatório consolidado com a análise de desempenho, as vendas da G7 e a análise de validação."""
    
    st.title("Relatório de Entrevista")
    data_service = DataService()

    # --- Filtros na Sidebar ---
    with st.sidebar:
        st.markdown("🔍 Filtros (Análise de Desempenho)")
        st.markdown("📅 Data de Criação:")
        col1, col2 = st.columns(2)
        with col1:
            data_criacao_inicio = st.date_input("Início", value=date.today() - timedelta(days=90), key="entrevista_data_criacao_inicio")
        with col2:
            data_criacao_fim = st.date_input("Fim", value=date.today(), key="entrevista_data_criacao_fim")
        
        aplicar_filtro_data_criacao = st.checkbox("Aplicar filtro por Data de Criação", value=False, key="entrevista_aplicar_filtro_data_criacao")

    # --- Carregamento de Dados Centralizado ---
    df_entrevista = None
    with st.spinner("Carregando dados da análise de desempenho..."):
        try:
            if aplicar_filtro_data_criacao:
                df_entrevista = data_service.get_entrevista_data(data_criacao_inicio, data_criacao_fim)
            else:
                df_entrevista = data_service.get_entrevista_data(None, None)
        except Exception as e:
            st.error(f"Ocorreu um erro ao carregar os dados: {e}")
            st.stop()
            
    if df_entrevista is None or df_entrevista.empty:
        st.warning("Nenhum dado encontrado para o período selecionado.")
        st.stop()

    # --- Seção de Análise de Desempenho (JusGestante) ---
    _render_analise_desempenho(df_entrevista)

    # --- Divisor e Seção de Vendas (G7) ---
    st.markdown("---")
    render_vendas_g7_tab()
    
    # --- Divisor e Seção de Análise de Validação (movida para o final) ---
    st.markdown("---")
    _render_analise_validacao(df_entrevista)


def _render_analise_desempenho(df_entrevista: pd.DataFrame):
    """Renderiza a seção de análise de desempenho do funil de entrevista."""
    render_analise_responsaveis_entrevista(df_entrevista)


def _render_analise_validacao(df_entrevista: pd.DataFrame):
    """Renderiza a seção de análise de clientes convertidos (validados)."""
    st.subheader("Análise de Validação (Clientes Convertidos)")

    if 'UF_CRM_VALIDADO_DATA' not in df_entrevista.columns or df_entrevista['UF_CRM_VALIDADO_DATA'].isnull().all():
        st.warning("A coluna 'UF_CRM_VALIDADO_DATA' não foi encontrada ou está vazia. A análise de validação não pode ser exibida.")
        return

    # Filtro de data específico para esta tabela
    st.markdown("📅 **Filtro por Data de Validação:**")
    
    valid_dates = df_entrevista['UF_CRM_VALIDADO_DATA'].dropna()

    col_val_1, col_val_2 = st.columns(2)
    with col_val_1:
        data_validacao_inicio = st.date_input(
            "Início",
            value=valid_dates.min() if not valid_dates.empty else date.today() - timedelta(days=30),
            key="entrevista_data_validacao_inicio"
        )
    with col_val_2:
        data_validacao_fim = st.date_input(
            "Fim",
            value=valid_dates.max() if not valid_dates.empty else date.today(),
            key="entrevista_data_validacao_fim"
        )
    
    aplicar_filtro_validacao = st.checkbox(
        "Aplicar filtro por Data de Validação",
        value=True,  # Alterado para True para filtrar por padrão
        key="entrevista_aplicar_filtro_validacao"
    )

    df_validados = df_entrevista[df_entrevista['STAGE_ID'] == 'C11:WON'].copy()

    if aplicar_filtro_validacao:
        df_filtrado_val = df_validados.dropna(subset=['UF_CRM_VALIDADO_DATA'])
        if not df_filtrado_val.empty:
            # Garante que a data no dataframe é um objeto date para comparação
            df_filtrado_val['UF_CRM_VALIDADO_DATA_DATE'] = pd.to_datetime(df_filtrado_val['UF_CRM_VALIDADO_DATA']).dt.date
            df_validados = df_filtrado_val[
                (df_filtrado_val['UF_CRM_VALIDADO_DATA_DATE'] >= data_validacao_inicio) &
                (df_filtrado_val['UF_CRM_VALIDADO_DATA_DATE'] <= data_validacao_fim)
            ]

    if df_validados.empty:
        st.info("Nenhum cliente convertido (validado) encontrado com os filtros selecionados.")
    else:
        st.markdown("##### Total de Clientes Validados por Responsável")
        
        tabela_validados = df_validados.groupby('ASSIGNED_BY_NAME').agg(
            TOTAL_VALIDADOS=('ID', 'count')
        ).reset_index().rename(columns={'ASSIGNED_BY_NAME': 'Responsável'})

        tabela_validados = tabela_validados.sort_values(by='TOTAL_VALIDADOS', ascending=False)
        
        st.dataframe(tabela_validados, use_container_width=True, hide_index=True) 