"""
Relatório do Funil Comercial
Análise completa das etapas de vendas e negociação
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
import sys
import os
# Adiciona src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'config'))

from src.data_service import DataService
from config.funis_config import FunilConfig

# Importa as novas funções dos sub-dashboards
from views.comercial.metricas_gerais import render_metricas_gerais
from views.comercial.funil_comercial import render_funil_comercial
from views.comercial.tabela_detalhada import render_tabela_detalhada
from views.comercial.analise_responsaveis import render_analise_responsaveis


def render_relatorio_comercial():
    """Renderiza o relatório completo do funil comercial"""
    
    # CSS para tamanho normal das fontes e configurar mensagens
    st.markdown("""
    <style>
    /* Tamanho normal das fontes */
    .main .block-container {
        font-size: 1em;
    }
    
    h1 {
        font-size: 1.5em !important;
    }
    
    h2 {
        font-size: 1.25em !important;
    }
    
    h3 {
        font-size: 1em !important;
    }
    
    .metric-container {
        font-size: 1em !important;
    }
    
    /* Configurar mensagens para 10s */
    .stAlert {
        animation: fadeOut 10s forwards;
    }
    
    @keyframes fadeOut {
        0% { opacity: 1; }
        90% { opacity: 1; }
        100% { opacity: 0; display: none; }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Cabeçalho
    st.title("Relatório Comercial")
    
    # Inicializa serviço de dados
    data_service = DataService()
    
    # Filtros na sidebar
    with st.sidebar:
        st.markdown("🔍 Filtros")
        
        # Filtro por UF_CRM_DATA_FECHAMENTO1 (Data Venda)
        st.markdown("📅 Data de Venda:")
        col1, col2 = st.columns(2)
        with col1:
            data_venda_inicio = st.date_input(
                "Início",
                value=date.today() - timedelta(days=365),
                key="data_venda_inicio"
            )
        with col2:
            data_venda_fim = st.date_input(
                "Fim", 
                value=date.today(),
                key="data_venda_fim"
            )
        
        # Opção para aplicar filtro de data de venda
        aplicar_filtro_data_venda = st.checkbox(
            "Aplicar filtro por Data de Venda",
            value=True, # Por padrão, o filtro estará ativo
            key="aplicar_filtro_data_venda"
        )
        
        # Filtro por Data de Criação
        st.markdown("📅 Data de Criação:")
        col3, col4 = st.columns(2)
        with col3:
            data_criacao_inicio = st.date_input(
                "Início",
                value=date.today() - timedelta(days=90),
                key="data_criacao_inicio"
            )
        with col4:
            data_criacao_fim = st.date_input(
                "Fim", 
                value=date.today(),
                key="data_criacao_fim"
            )
        
        # Opção para aplicar filtro de data de criação
        aplicar_filtro_data_criacao = st.checkbox(
            "Aplicar filtro por Data de Criação",
            value=True, # Por padrão, o filtro estará ativo
            key="aplicar_filtro_data_criacao"
        )

        df_temp = data_service.get_comercial_data() # Carrega dados sem filtro de data para obter todas as etapas
        if not df_temp.empty and 'STAGE_NAME' in df_temp.columns:
            etapas_disponiveis = sorted(df_temp['STAGE_NAME'].dropna().unique())
        else:
            etapas_disponiveis = []
        
        if etapas_disponiveis:
            st.markdown("**🎯 Etapas:**")
            etapas_selecionadas = st.multiselect(
                "Selecione as etapas",
                etapas_disponiveis,
                default=etapas_disponiveis # Alterado para selecionar todas por padrão
            )
        else:
            etapas_selecionadas = []
        
        # Filtro por pessoa responsável
        st.markdown("**👤 Responsável:**")
        
        if not df_temp.empty and 'ASSIGNED_BY_NAME' in df_temp.columns:
            responsaveis_disponiveis = sorted(df_temp['ASSIGNED_BY_NAME'].dropna().unique())
        else:
            responsaveis_disponiveis = []

        if responsaveis_disponiveis:
            responsaveis_selecionados = st.multiselect(
                "Selecione os responsáveis",
                responsaveis_disponiveis,
                default=responsaveis_disponiveis # Seleciona todos por padrão
            )
        else:
            responsaveis_selecionados = []

    # Carrega dados do funil comercial
    with st.spinner("Carregando dados..."):
        try:
            # Carrega todos os dados comerciais
            # Se o filtro de data de criação não estiver aplicado, passe None para as datas
            if aplicar_filtro_data_criacao:
                df_comercial = data_service.get_comercial_data(data_criacao_inicio, data_criacao_fim)
            else:
                df_comercial = data_service.get_comercial_data(None, None)
            
            if df_comercial.empty:
                st.warning("Nenhum dado encontrado")
                return
            
            # Aplica filtros adicionais
            if etapas_selecionadas and 'STAGE_NAME' in df_comercial.columns:
                df_comercial = df_comercial[df_comercial['STAGE_NAME'].isin(etapas_selecionadas)]
            
            # Aplica filtro por responsável selecionado
            if responsaveis_selecionados and 'ASSIGNED_BY_NAME' in df_comercial.columns:
                df_comercial = df_comercial[df_comercial['ASSIGNED_BY_NAME'].isin(responsaveis_selecionados)]

            if df_comercial.empty:
                st.warning("Nenhum dado após filtros")   
                return
            
            # Renderiza as sub-abas
            st.markdown("## ") # Espaço para o título das sub-abas
            tab_metricas, tab_funil, tab_detalhes, tab_analise_resp = st.tabs([
                "Métricas Gerais", 
                "Funil Comercial", 
                "Detalhes dos Negócios",
                "Análise por Responsável"
            ])

            with tab_metricas:
                render_metricas_gerais(df_comercial, data_venda_inicio, data_venda_fim, aplicar_filtro_data_venda)
            
            with tab_funil:
                render_funil_comercial(df_comercial)
            
            with tab_detalhes:
                render_tabela_detalhada(df_comercial)
            
            with tab_analise_resp:
                render_analise_responsaveis(df_comercial)

        except Exception as e:
            st.error(f"Erro ao carregar dados: {str(e)}")
            st.exception(e)


if __name__ == "__main__":
    render_relatorio_comercial() 