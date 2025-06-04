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

# Mapeamento para sub-páginas (abas)
SUB_PAGE_URL_MAP = {
    "visao_geral": "Visão Geral",
    "analise_responsavel": "Análise por Responsável",
    "detalhes_negocios": "Detalhes dos Negócios",
}
SUB_PAGE_STATE_TO_URL_MAP = {v: k for k, v in SUB_PAGE_URL_MAP.items()}

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

    /* Estilo para o conteúdo da Visão Geral */
    .visao-geral-content {
        background-color: white;
        padding: 1rem; /* Adiciona algum preenchimento interno */
        border-radius: 8px; /* Bordas arredondadas para o container */
    }
    
    /* Removendo estilos para st.radio e revertendo para st.tabs, que tem seus próprios estilos padrao */
    /* st.tabs já tem estilos que simulam botoes */

    /* Indentação para as abas (ajuste conforme a necessidade do layout) */
    .stTabs {
        margin-left: 20px; /* Adiciona um recuo visual para as sub-abas */
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
            value=False, # Alterado para False para iniciar desmarcado
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
            value=False, # Alterado para False para iniciar desmarcado
            key="aplicar_filtro_data_criacao"
        )

        # Usa get_minimal_data_for_selectors para popular filtros de forma eficiente
        # Define os campos necessários para os seletores
        fields_for_selectors = ['STAGE_NAME', 'ASSIGNED_BY_NAME']
        
        # Chama o método para obter dados minimos para seletores.
        # Passa FunilConfig.COMERCIAL_ID como uma lista.
        # Para os seletores, geralmente não aplicamos filtros de data de criação aqui,
        # pois queremos todas as etapas e responsáveis históricos.
        # Se for necessário filtrar por data de criação para os seletores,
        # as datas data_criacao_inicio e data_criacao_fim poderiam ser passadas.
        df_temp_selectors = data_service.get_minimal_data_for_selectors(
            category_ids=[FunilConfig.COMERCIAL_ID], 
            fields_to_extract=fields_for_selectors
            # start_date=data_criacao_inicio if aplicar_filtro_data_criacao else None, # Opcional: se os seletores devem ser filtrados por data
            # end_date=data_criacao_fim if aplicar_filtro_data_criacao else None      # Opcional
        )

        if not df_temp_selectors.empty:
            if 'STAGE_NAME' in df_temp_selectors.columns:
                etapas_disponiveis = sorted(df_temp_selectors['STAGE_NAME'].dropna().unique())
            else:
                etapas_disponiveis = []
                st.warning("Coluna 'STAGE_NAME' não encontrada nos dados para seletores.")

            if 'ASSIGNED_BY_NAME' in df_temp_selectors.columns:
                responsaveis_disponiveis = sorted(df_temp_selectors['ASSIGNED_BY_NAME'].dropna().unique())
            else:
                responsaveis_disponiveis = []
                st.warning("Coluna 'ASSIGNED_BY_NAME' não encontrada nos dados para seletores.")
        else:
            etapas_disponiveis = []
            responsaveis_disponiveis = []
            st.info("Não foram encontrados dados para popular os filtros de etapas e responsáveis.")
        
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
                st.warning("Nenhum dado após filtros de etapa e responsável.")
                return

            # Aplicar filtro de Data de Venda (UF_CRM_DATA_FECHAMENTO1) se estiver ativo
            if aplicar_filtro_data_venda and 'UF_CRM_DATA_FECHAMENTO1' in df_comercial.columns:
                # Certificar que a coluna de data de venda seja do tipo date para comparação
                # A conversão para datetime e depois para date é mais robusta
                df_comercial['UF_CRM_DATA_FECHAMENTO1'] = pd.to_datetime(df_comercial['UF_CRM_DATA_FECHAMENTO1'], errors='coerce').dt.date
                
                # Filtrar o DataFrame
                df_comercial = df_comercial[
                    df_comercial['UF_CRM_DATA_FECHAMENTO1'].notna() &
                    (df_comercial['UF_CRM_DATA_FECHAMENTO1'] >= data_venda_inicio) &
                    (df_comercial['UF_CRM_DATA_FECHAMENTO1'] <= data_venda_fim)
                ]
                if df_comercial.empty:
                    st.warning("Nenhum dado após filtro de Data de Venda.")
                    return
            elif aplicar_filtro_data_venda and 'UF_CRM_DATA_FECHAMENTO1' not in df_comercial.columns:
                st.warning("Coluna 'UF_CRM_DATA_FECHAMENTO1' não encontrada para aplicar o filtro de Data de Venda.")
                # Decide-se prosseguir sem este filtro ou retornar, dependendo do requisito.
                # Aqui, vamos prosseguir, mas com o aviso.

            if df_comercial.empty: # Checagem final após todos os filtros
                st.warning("Nenhum dado encontrado após a aplicação de todos os filtros.")
                return
            
            # --- Lógica de Roteamento para Sub-páginas com st.tabs ---
            st.markdown("## ") # Espaço para o título das abas

            tab_titles = list(SUB_PAGE_URL_MAP.values())
            
            # st.tabs não suporta `index` ou `value` para seleção inicial programática.
            # O primeiro tab sempre estará ativo no carregamento da página ou F5.
            # A URL só refletirá o tab clicado pelo usuário, mas não o controlará inicialmente.
            tab_visao_geral, tab_analise_resp, tab_detalhes = st.tabs(tab_titles)

            # Para manter o URL atualizado com o tab clicado:
            # Usamos st.session_state para guardar o tab selecionado e atualizar o URL
            # Isso será atualizado APÓS o usuário clicar em um tab, nao no carregamento inicial.
            if 'current_commercial_sub_page_display' not in st.session_state:
                # Inicializa com o primeiro tab por padrao, que é o que st.tabs faz visualmente
                st.session_state.current_commercial_sub_page_display = tab_titles[0]
            
            # Determine qual tab foi clicado e atualize o URL
            # Isso requer que cada bloco 'with' seja executado para verificar o click
            current_active_tab_url_key = None

            with tab_visao_geral:
                # Se este tab está ativo, atualize o estado e URL
                if st.session_state.get('current_commercial_sub_page_display') != "Visão Geral":
                    st.session_state.current_commercial_sub_page_display = "Visão Geral"
                    current_active_tab_url_key = SUB_PAGE_STATE_TO_URL_MAP.get("Visão Geral")
                    # st.rerun() será chamado no final, se o URL precisar de atualização

                st.markdown('<div class="visao-geral-content">', unsafe_allow_html=True)
                render_metricas_gerais(df_comercial)
                st.markdown("---") # Separador visual
                render_funil_comercial(df_comercial)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with tab_analise_resp:
                # Se este tab está ativo, atualize o estado e URL
                if st.session_state.get('current_commercial_sub_page_display') != "Análise por Responsável":
                    st.session_state.current_commercial_sub_page_display = "Análise por Responsável"
                    current_active_tab_url_key = SUB_PAGE_STATE_TO_URL_MAP.get("Análise por Responsável")

                render_analise_responsaveis(df_comercial)

            with tab_detalhes:
                # Se este tab está ativo, atualize o estado e URL
                if st.session_state.get('current_commercial_sub_page_display') != "Detalhes dos Negócios":
                    st.session_state.current_commercial_sub_page_display = "Detalhes dos Negócios"
                    current_active_tab_url_key = SUB_PAGE_STATE_TO_URL_MAP.get("Detalhes dos Negócios")

                render_tabela_detalhada(df_comercial)
            
            # Atualiza o URL fora dos blocos 'with' para evitar múltiplos reruns
            current_url_sub_page = st.query_params.get("sub_pagina")
            if current_active_tab_url_key and current_url_sub_page != current_active_tab_url_key:
                st.query_params.sub_pagina = current_active_tab_url_key
                st.rerun()
            elif not current_active_tab_url_key and "sub_pagina" in st.query_params:
                # Remove sub_pagina se o tab atual não tiver um mapeamento URL (ex: padrao, se for o caso)
                # ou se o usuario navegou de volta para o tab padrao que nao tem um parametro URL
                del st.query_params["sub_pagina"]
                st.rerun()

        except Exception as e:
            st.error(f"Erro ao carregar dados: {str(e)}")
            st.exception(e)


if __name__ == "__main__":
    render_relatorio_comercial() 