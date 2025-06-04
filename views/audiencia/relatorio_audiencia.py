import streamlit as st
import pandas as pd
from datetime import date, timedelta
import sys
import os

# Adiciona src e config ao path se necessário (similar ao administrativo)
# Isso pode não ser estritamente necessário se o DataService já for importável
# diretamente, mas é uma boa prática para consistência se outros módulos fazem.
# sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
# sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'config'))

from src.data_service import DataService
# Removido FunilConfig daqui, pois não é mais usado diretamente para stage_distribution

# Importar as funções das abas
from .tabs.visao_geral_tab import display_visao_geral_audiencia
from .tabs.analise_responsavel_tab import display_analise_responsavel_audiencia
from .tabs.agenda_audiencia_tab import display_agenda_audiencia_tab

# Definindo as etapas do funil de Audiência com base no fornecido
ETAPAS_AUDIENCIA_ORDEM = [
    "PEND. HORÁRIO E LOCAL",
    "CLIENTE AVISADO",  # Existem duas etapas com este nome, IDs 244 e 242. O filtro de multiselect tratará isso.
    "1º AUDIÊNCIA MARCADA",
    # "CLIENTE AVISADO", # Já listado - para a ORDEM, consideramos o nome uma vez.
    "EM ACORDO",
    "CONTESTAÇÃO (RAZÕES FINAIS)",
    "AGUARDANDO SENTENÇA",
    "ACORDO",
    "RECURSO",
    "CANCELADOS",
    "SENTENÇA PROCEDENTE"
]
# Para o filtro multiselect, é melhor ter uma lista de nomes únicos que aparecem nos dados.
# A ETAPAS_AUDIENCIA_ORDEM pode ser usada para ordenar, mas a lista de seleção deve vir dos dados.


def display_relatorio_audiencia():
    st.title("⚖️ Relatório de Audiências") # Emoji alterado para diferenciar

    data_service = DataService()
    CATEGORY_ID_AUDIENCIA = 4

    # Filtros na sidebar
    with st.sidebar:
        st.markdown("---") 
        st.markdown("### 🔍 Filtros de Audiência")

        st.markdown("📅 Data de Criação do Deal:")
        col1_sidebar, col2_sidebar = st.columns(2)
        with col1_sidebar:
            data_criacao_inicio_aud = st.date_input(
                "Início",
                value=date.today() - timedelta(days=365), # Default para 1 ano
                key="data_criacao_inicio_aud"
            )
        with col2_sidebar:
            data_criacao_fim_aud = st.date_input(
                "Fim",
                value=date.today(),
                key="data_criacao_fim_aud"
            )
        
        aplicar_filtro_data_criacao_aud = st.checkbox(
            "Aplicar filtro por Data de Criação",
            value=True,
            key="aplicar_filtro_data_criacao_aud"
        )

        # Carrega dados brutos TEMPORARIAMENTE para obter listas de filtros (etapas, responsáveis)
        # Idealmente, o DataService teria métodos para buscar essas listas de forma eficiente.
        # Usaremos a CATEGORY_ID_AUDIENCIA para carregar os dados relevantes.
        
        # Ajuste na chamada para obter dados para os filtros:
        # Passa datas apenas se o filtro estiver ativo, para popular os seletores com todas as opções possíveis
        # Se o filtro de data não estiver ativo, não faz sentido filtrar aqui ainda.
        initial_start_date = data_criacao_inicio_aud if aplicar_filtro_data_criacao_aud else None
        initial_end_date = data_criacao_fim_aud if aplicar_filtro_data_criacao_aud else None

        # Tentativa de carregar dados para popular filtros.
        # Idealmente, o método get_deals_data lidaria com category_id e datas.
        # Se get_audiencia_data() já faz isso ou pode ser adaptado, ótimo.
        # Por agora, vou assumir que precisamos de uma chamada mais genérica ou que get_audiencia_data
        # pode ser modificada para aceitar category_id e filtros de data.
        # Para simplificar a transição, vou manter a chamada a get_audiencia_data por enquanto,
        # mas com a ressalva que ela precisará buscar dados da category_id=4
        # e idealmente aceitar os filtros de data para popular os seletores.
        # df_temp_aud = data_service.get_audiencia_data(start_date_filter=initial_start_date, end_date_filter=initial_end_date, category_id_filter=CATEGORY_ID_AUDIENCIA)
        # Como get_audiencia_data não aceita category_id_filter, vamos chamar get_deals_data
        # Assumindo que DataService.get_deals_data(category_id, start_date, end_date) existe ou será criado.
        # df_temp_aud = data_service.get_deals_data(
        #     category_id=CATEGORY_ID_AUDIENCIA,
        #     start_date=initial_start_date,
        #     end_date=initial_end_date
        # )
        # Ajustado para usar get_deals_by_category, que espera uma lista de IDs
        df_temp_aud = data_service.get_deals_by_category(
            category_ids=[CATEGORY_ID_AUDIENCIA],
            start_date=initial_start_date,
            end_date=initial_end_date
        )


        etapas_disponiveis_aud = []
        if not df_temp_aud.empty and 'STAGE_NAME' in df_temp_aud.columns:
            etapas_presentes_dados_aud = df_temp_aud['STAGE_NAME'].dropna().unique()
            # Usar ETAPAS_AUDIENCIA_ORDEM para popular e ordenar, se necessário, mas garantir que apenas etapas existentes sejam mostradas.
            # Ou simplesmente usar o que vem dos dados e ordenar pela ETAPAS_AUDIENCIA_ORDEM depois.
            etapas_disponiveis_aud = sorted(list(etapas_presentes_dados_aud), key=lambda x: ETAPAS_AUDIENCIA_ORDEM.index(x) if x in ETAPAS_AUDIENCIA_ORDEM else float('inf'))
            # Se ETAPAS_AUDIENCIA_ORDEM não contiver todas as etapas dos dados, elas irão para o final.
        
        if etapas_disponiveis_aud:
            st.markdown("**🎯 Etapas (Audiência):**")
            etapas_selecionadas_aud = st.multiselect(
                "Selecione as etapas",
                etapas_disponiveis_aud,
                default=etapas_disponiveis_aud, # Seleciona todas por padrão
                key="etapas_selecionadas_aud"
            )
        else:
            etapas_selecionadas_aud = []
            st.markdown("**🎯 Etapas (Audiência):** Nenhuma etapa encontrada para os filtros atuais.")

        responsaveis_disponiveis_aud = []
        if not df_temp_aud.empty and 'ASSIGNED_BY_NAME' in df_temp_aud.columns:
            responsaveis_disponiveis_aud = sorted(df_temp_aud['ASSIGNED_BY_NAME'].dropna().unique())

        if responsaveis_disponiveis_aud:
            st.markdown("**👤 Responsável (Audiência):**")
            responsaveis_selecionados_aud = st.multiselect(
                "Selecione os responsáveis",
                responsaveis_disponiveis_aud,
                default=responsaveis_disponiveis_aud, # Seleciona todos por padrão
                key="responsaveis_selecionados_aud"
            )
        else:
            responsaveis_selecionados_aud = []
            st.markdown("**👤 Responsável (Audiência):** Nenhum responsável encontrado.")

    # Carrega dados do funil de audiência com base nos filtros
    with st.spinner("Carregando dados de audiências..."):
        try:
            # Define as datas para a consulta principal com base na checkbox
            query_start_date = data_criacao_inicio_aud if aplicar_filtro_data_criacao_aud else None
            query_end_date = data_criacao_fim_aud if aplicar_filtro_data_criacao_aud else None

            # Chamada principal para obter os dados
            # Assumindo que get_deals_data é o método apropriado que aceita category_id e datas.
            # df_audiencia = data_service.get_deals_data(
            #     category_id=CATEGORY_ID_AUDIENCIA,
            #     start_date=query_start_date,
            #     end_date=query_end_date
            # )
            # Ajustado para usar get_deals_by_category
            df_audiencia = data_service.get_deals_by_category(
                category_ids=[CATEGORY_ID_AUDIENCIA],
                start_date=query_start_date,
                end_date=query_end_date
            )
            
            if df_audiencia.empty:
                st.warning("Nenhum dado encontrado para audiências com os filtros de data atuais.")
                return # Retorna se não houver dados após o filtro de data

            # Aplica filtros adicionais de etapas e responsáveis no DataFrame carregado
            if etapas_selecionadas_aud and 'STAGE_NAME' in df_audiencia.columns:
                df_audiencia = df_audiencia[df_audiencia['STAGE_NAME'].isin(etapas_selecionadas_aud)]
            
            if responsaveis_selecionados_aud and 'ASSIGNED_BY_NAME' in df_audiencia.columns:
                df_audiencia = df_audiencia[df_audiencia['ASSIGNED_BY_NAME'].isin(responsaveis_selecionados_aud)]

            if df_audiencia.empty:
                st.warning("Nenhum dado encontrado para audiências após aplicar todos os filtros (etapas, responsáveis).")
                return
            
            # st.success(f"{len(df_audiencia)} deals de audiência carregados.") # Para depuração

            # Criação das abas
            tab_visao_geral, tab_analise_resp, tab_agenda = st.tabs([
                f"📊 Visão Geral ({len(df_audiencia)})", 
                f"👤 Análise por Responsável ({len(df_audiencia)})",
                f"🗓️ Agenda de Audiências"
            ])

            with tab_visao_geral:
                display_visao_geral_audiencia(df_audiencia, data_service, ETAPAS_AUDIENCIA_ORDEM)

            with tab_analise_resp:
                display_analise_responsavel_audiencia(df_audiencia, data_service, ETAPAS_AUDIENCIA_ORDEM)
            
            with tab_agenda:
                display_agenda_audiencia_tab(df_audiencia)

        except Exception as e:
            st.error(f"Erro ao carregar dados de audiências: {str(e)}")
            st.exception(e)
            return # Adicionado para não prosseguir em caso de erro

    # Comentários sobre métricas chave mantidos caso queira reativar no futuro
    # st.subheader("Métricas Chave do Funil de Audiência")
    # summary = data_service.get_performance_summary(FunilConfig.AUDIENCIA_ID) # Precisaria ser adaptado para category_id=4
    # if summary:
    #     cols = st.columns(4)
    #     cols[0].metric("Total de Deals", summary.get('total_deals',0))
    #     cols[1].metric("Deals Ganhos", summary.get('deals_won',0))
    #     cols[2].metric("Deals Perdidos", summary.get('deals_lost',0))
    #     cols[3].metric("Taxa de Conversão", f"{summary.get('conversion_rate',0):.2f}%")
    # else:
    #     st.info("Não foi possível calcular as métricas chave.")
    
