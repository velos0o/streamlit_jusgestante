import streamlit as st
import pandas as pd
from datetime import date, timedelta
import sys
import os

# Adiciona src e config ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'config'))

from src.data_service import DataService
# Funções dos sub-dashboards que serão criadas
from views.administrativo.funil_administrativo import render_funil_administrativo
from views.administrativo.analise_responsaveis_administrativo import render_analise_responsaveis_administrativo

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
            value=True,
            key="aplicar_filtro_data_criacao_adm"
        )

        # Carrega dados brutos para obter listas de filtros (etapas, responsáveis)
        # Passando None para as datas se o filtro não estiver aplicado inicialmente
        # para garantir que todas as opções estejam disponíveis.
        df_temp_adm = data_service.get_tramites_data(
            None if not aplicar_filtro_data_criacao_adm else data_criacao_inicio_adm,
            None if not aplicar_filtro_data_criacao_adm else data_criacao_fim_adm
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

            # Renderiza as sub-abas
            st.markdown("## ") 
            tab_funil_adm, tab_analise_resp_adm = st.tabs([
                "Visão do Funil", 
                "Análise por Responsável"
            ])

            with tab_funil_adm:
                # Esta função será criada no arquivo funil_administrativo.py
                render_funil_administrativo(df_administrativo, ETAPAS_ADMINISTRATIVO_ORDEM)
            
            with tab_analise_resp_adm:
                # Esta função será criada no arquivo analise_responsaveis_administrativo.py
                render_analise_responsaveis_administrativo(df_administrativo, ETAPAS_ADMINISTRATIVO_ORDEM)

        except Exception as e:
            st.error(f"Erro ao carregar dados administrativos: {str(e)}")
            st.exception(e) 