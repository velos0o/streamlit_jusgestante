import streamlit as st
import pandas as pd
from datetime import date, timedelta
import sys
import os

# Adiciona src e config ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'config'))

from src.data_service import DataService
from config.funis_config import FunilConfig # Importar FunilConfig
# Funções dos sub-dashboards que serão criadas
from views.administrativo.funil_administrativo import render_funil_administrativo
from views.administrativo.analise_responsaveis_administrativo import render_analise_responsaveis_administrativo

# Mapeamento para sub-páginas (abas) do relatório Administrativo
SUB_PAGE_URL_MAP_ADM = {
    "visao_funil_adm": "Visão do Funil",
    "analise_responsavel_adm": "Análise por Responsável",
}
SUB_PAGE_STATE_TO_URL_MAP_ADM = {v: k for k, v in SUB_PAGE_URL_MAP_ADM.items()}

# Lista de etapas para o funil administrativo (baseado no fornecido pelo usuário)
ETAPAS_ADMINISTRATIVO_ORDEM = [
    "FILA",
    "PENDENTE DOCUMENTOS",
    "PENDENTE FORMALIZAÇÃO DE CÁLCULO",
    "PENDENTE PETIÇÃO INICIAL",
    "PENDENTE REVISAR PETIÇÃO",
    "REVERSÃO",
    "PROTOCOLADO COM SUCESSO",
    "CANCELAMENTO"
]

def render_relatorio_administrativo():
    """Renderiza o relatório completo de trâmites administrativos."""
    st.title("📋 Relatório de Trâmites Administrativos")

    data_service = DataService()

    # Filtros na sidebar
    with st.sidebar:
        st.markdown("---") # Separador visual
        st.markdown("### 🔍 Filtros do Administrativo")

        # Filtro por Data de Criação
        st.markdown("📅 Data de Criação:")
        col1, col2 = st.columns(2)
        with col1:
            data_criacao_inicio_adm = st.date_input(
                "Início",
                value=date.today() - timedelta(days=90),
                key="data_criacao_inicio_adm"
            )
        with col2:
            data_criacao_fim_adm = st.date_input(
                "Fim",
                value=date.today(),
                key="data_criacao_fim_adm"
            )
        
        aplicar_filtro_data_criacao_adm = st.checkbox(
            "Aplicar filtro por Data de Criação",
            value=False,
            key="aplicar_filtro_data_criacao_adm"
        )

        # Carrega dados minimos para obter listas de filtros (etapas, responsáveis)
        fields_for_selectors_adm = ['STAGE_NAME', 'ASSIGNED_BY_NAME']
        df_temp_adm = data_service.get_minimal_data_for_selectors(
            category_ids=[FunilConfig.TRAMITES_ID],
            fields_to_extract=fields_for_selectors_adm
        )
        
        etapas_disponiveis_adm = []
        if not df_temp_adm.empty and 'STAGE_NAME' in df_temp_adm.columns:
            # Filtra para mostrar apenas as etapas relevantes do funil administrativo
            etapas_presentes_dados = df_temp_adm['STAGE_NAME'].dropna().unique()
            etapas_disponiveis_adm = [etapa for etapa in ETAPAS_ADMINISTRATIVO_ORDEM if etapa in etapas_presentes_dados]
            if not etapas_disponiveis_adm: # Fallback se o mapeamento não encontrar nenhuma
                 etapas_disponiveis_adm = sorted(list(etapas_presentes_dados))
        
        if etapas_disponiveis_adm:
            st.markdown("**🎯 Etapas (Administrativo):**")
            etapas_selecionadas_adm = st.multiselect(
                "Selecione as etapas",
                etapas_disponiveis_adm,
                default=etapas_disponiveis_adm,
                key="etapas_selecionadas_adm"
            )
        else:
            etapas_selecionadas_adm = []
            st.markdown("**🎯 Etapas (Administrativo):** Nenhuma etapa encontrada para os filtros atuais.")

        responsaveis_disponiveis_adm = []
        if not df_temp_adm.empty and 'ASSIGNED_BY_NAME' in df_temp_adm.columns:
            responsaveis_disponiveis_adm = sorted(df_temp_adm['ASSIGNED_BY_NAME'].dropna().unique())

        if responsaveis_disponiveis_adm:
            st.markdown("**👤 Responsável (Administrativo):**")
            responsaveis_selecionados_adm = st.multiselect(
                "Selecione os responsáveis",
                responsaveis_disponiveis_adm,
                default=responsaveis_disponiveis_adm,
                key="responsaveis_selecionados_adm"
            )
        else:
            responsaveis_selecionados_adm = []
            st.markdown("**👤 Responsável (Administrativo):** Nenhum responsável encontrado.")

    # Carrega dados do funil administrativo com base nos filtros
    with st.spinner("Carregando dados administrativos..."):
        try:
            if aplicar_filtro_data_criacao_adm:
                df_administrativo = data_service.get_tramites_data(data_criacao_inicio_adm, data_criacao_fim_adm)
            else:
                df_administrativo = data_service.get_tramites_data(None, None) # Carrega todos os dados se filtro de data não aplicado
            
            if df_administrativo.empty:
                st.warning("Nenhum dado encontrado para os trâmites administrativos com os filtros atuais.")
                return

            # Aplica filtros adicionais de etapas e responsáveis
            if etapas_selecionadas_adm and 'STAGE_NAME' in df_administrativo.columns:
                df_administrativo = df_administrativo[df_administrativo['STAGE_NAME'].isin(etapas_selecionadas_adm)]
            
            if responsaveis_selecionados_adm and 'ASSIGNED_BY_NAME' in df_administrativo.columns:
                df_administrativo = df_administrativo[df_administrativo['ASSIGNED_BY_NAME'].isin(responsaveis_selecionados_adm)]

            if df_administrativo.empty:
                st.warning("Nenhum dado encontrado após aplicar os filtros de etapas e responsáveis.")
                return
            
            st.success(f"{len(df_administrativo)} trâmites carregados.") # Linha de depuração temporária

            # --- Lógica de Roteamento para Sub-páginas com st.tabs ---
            st.markdown("## ") 
            tab_titles_adm = list(SUB_PAGE_URL_MAP_ADM.values())
            default_tab_display_name = tab_titles_adm[0]
            
            # st.tabs não suporta `index` ou `value` para seleção inicial programática.
            # O primeiro tab sempre estará ativo no carregamento da página ou F5.
            tab_funil_adm, tab_analise_resp_adm = st.tabs(tab_titles_adm)

            # Tenta manter o URL atualizado com o tab clicado.
            # Esta é uma heurística devido às limitações do st.tabs.
            # Inicializa o estado do display do sub-tab se não existir.
            if 'current_administrativo_sub_page_display' not in st.session_state:
                st.session_state.current_administrativo_sub_page_display = default_tab_display_name
            
            # Esta variável irá armazenar a chave de URL do tab que parece estar ativo.
            # Será None para o tab padrão para limpar o sub_pagina da URL.
            determined_active_tab_url_key = None

            with tab_funil_adm:
                # Se este tab está ativo, atualize o estado e prepare a chave URL (None para default)
                if st.session_state.current_administrativo_sub_page_display != tab_titles_adm[0]:
                    # Esta condição significa que um *outro* tab estava no estado, e agora este está sendo renderizado.
                    # Isso sugere que o usuário pode ter clicado neste tab.
                    st.session_state.current_administrativo_sub_page_display = tab_titles_adm[0]
                    determined_active_tab_url_key = None # Default tab, no sub_pagina
                elif st.query_params.get("sub_pagina") is not None:
                     # Se este é o tab padrão, mas há um sub_pagina na URL, significa que precisamos limpar a URL
                     determined_active_tab_url_key = None 
                
                render_funil_administrativo(df_administrativo, ETAPAS_ADMINISTRATIVO_ORDEM)
            
            with tab_analise_resp_adm:
                # Se este tab está ativo, atualize o estado e prepare a chave URL
                if st.session_state.current_administrativo_sub_page_display != tab_titles_adm[1]:
                    st.session_state.current_administrativo_sub_page_display = tab_titles_adm[1]
                    determined_active_tab_url_key = SUB_PAGE_STATE_TO_URL_MAP_ADM.get(tab_titles_adm[1])
                elif st.query_params.get("sub_pagina") != SUB_PAGE_STATE_TO_URL_MAP_ADM.get(tab_titles_adm[1]):
                    # Se este tab está no estado, mas a URL não corresponde, atualize a URL
                    if st.session_state.current_administrativo_sub_page_display == tab_titles_adm[1]:
                         determined_active_tab_url_key = SUB_PAGE_STATE_TO_URL_MAP_ADM.get(tab_titles_adm[1])

                render_analise_responsaveis_administrativo(df_administrativo, ETAPAS_ADMINISTRATIVO_ORDEM)

            # Atualiza o URL fora dos blocos 'with' para evitar múltiplos reruns
            current_url_sub_page = st.query_params.get("sub_pagina")

            if determined_active_tab_url_key:
                if current_url_sub_page != determined_active_tab_url_key:
                    st.query_params.sub_pagina = determined_active_tab_url_key
                    st.rerun()
            elif current_url_sub_page is not None: # Should be None for default tab
                del st.query_params["sub_pagina"]
                st.rerun()

        except Exception as e:
            st.error(f"Erro ao carregar dados administrativos: {str(e)}")
            st.exception(e) 