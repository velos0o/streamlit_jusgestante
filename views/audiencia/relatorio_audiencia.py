import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
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

# Mapeamento para sub-páginas (abas) do relatório de Audiência
SUB_PAGE_URL_MAP_AUD = {
    "visao_geral_aud": "Visão Geral",
    "analise_responsavel_aud": "Análise por Responsável",
    "agenda_audiencia_aud": "Agenda de Audiências",
}
SUB_PAGE_STATE_TO_URL_MAP_AUD = {v: k for k, v in SUB_PAGE_URL_MAP_AUD.items()}

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

CATEGORY_ID_AUDIENCIA = 4

# Função cacheada para carregar e processar os dados base
@st.cache_data(ttl=1800) # Cache por 30 minutos
def load_audiencia_data_base(_data_service_instance, category_id, start_date_str, end_date_str):
    """Carrega e processa os dados base para o relatório de audiência."""
    # Converte strings de data de volta para objetos date, se não forem None
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else None
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None
    
    # print(f"Cache miss: Carregando dados para load_audiencia_data_base com {category_id}, {start_dt}, {end_dt}") # Para depuração
    return _data_service_instance.get_deals_by_category(
        category_ids=[category_id],
        start_date=start_dt,
        end_date=end_dt
    )

# Função cacheada para carregar dados para os seletores da sidebar
@st.cache_data(ttl=3600) # Cache por 1 hora, pois as opções mudam menos
def load_data_for_selectors_audiencia(_data_service_instance, category_id):
    """Carrega dados minimos para popular seletores (etapas, responsáveis)."""
    two_years_ago = date.today() - timedelta(days=2*365)
    today = date.today()
    
    fields_needed_for_selectors = ['STAGE_NAME', 'ASSIGNED_BY_NAME']
    # Nota: 'CATEGORY_ID' e 'STAGE_ID' são implicitamente usados por get_minimal_data_for_selectors
    # para derivar 'STAGE_NAME' se não vier diretamente, mas não precisam ser listados aqui
    # explicitamente se não forem usados diretamente para construir as listas de seletores.

    # print("Cache miss ou chamada para: load_data_for_selectors_audiencia") # Para depuração
    # st.info("Chamando get_minimal_data_for_selectors...") # Para depuração no Streamlit UI
    df_minimal = _data_service_instance.get_minimal_data_for_selectors(
        category_ids=[category_id],
        fields_to_extract=fields_needed_for_selectors,
        start_date=two_years_ago,
        end_date=today
    )
    # st.info(f"get_minimal_data_for_selectors retornou {df_minimal.shape[0]} linhas.") # Para depuração
    
    etapas = []
    responsaveis = []

    if not df_minimal.empty:
        if 'STAGE_NAME' in df_minimal.columns:
            # Certifica-se de que apenas strings não nulas sejam processadas para evitar erros com .unique()
            etapas_raw = df_minimal['STAGE_NAME'].dropna()
            if not etapas_raw.empty:
                etapas = sorted(
                    list(etapas_raw.unique()), 
                    key=lambda x: ETAPAS_AUDIENCIA_ORDEM.index(x) if x in ETAPAS_AUDIENCIA_ORDEM else float('inf')
                )
        if 'ASSIGNED_BY_NAME' in df_minimal.columns:
            # Certifica-se de que apenas strings não nulas sejam processadas
            responsaveis_raw = df_minimal['ASSIGNED_BY_NAME'].dropna()
            if not responsaveis_raw.empty:
                responsaveis = sorted(list(responsaveis_raw.unique()))
    
    # print(f"Etapas para seletor: {etapas}") # Para depuração
    # print(f"Responsáveis para seletor: {responsaveis}") # Para depuração
    # st.info(f"Seletores: {len(etapas)} etapas, {len(responsaveis)} responsáveis.") # Para depuração
    return etapas, responsaveis

def display_relatorio_audiencia():
    st.title("⚖️ Relatório de Audiências") # Emoji alterado para diferenciar

    data_service = DataService()

    # Carregar dados para seletores (cacheado)
    etapas_disponiveis_aud, responsaveis_disponiveis_aud = load_data_for_selectors_audiencia(data_service, CATEGORY_ID_AUDIENCIA)

    with st.sidebar:
        st.markdown("---") 
        st.markdown("### 🔍 Filtros de Audiência")

        st.markdown("📅 Data de Criação do Deal:")
        col1_sidebar, col2_sidebar = st.columns(2)
        default_start_date = date.today() - timedelta(days=365)
        default_end_date = date.today()

        data_criacao_inicio_aud = col1_sidebar.date_input("Início", value=default_start_date, key="data_criacao_inicio_aud")
        data_criacao_fim_aud = col2_sidebar.date_input("Fim", value=default_end_date, key="data_criacao_fim_aud")
        
        aplicar_filtro_data_criacao_aud = st.checkbox("Aplicar filtro por Data de Criação", value=False, key="aplicar_filtro_data_criacao_aud")

        if etapas_disponiveis_aud:
            st.markdown("**🎯 Etapas (Audiência):**")
            etapas_selecionadas_aud = st.multiselect("Selecione as etapas", etapas_disponiveis_aud, default=etapas_disponiveis_aud, key="etapas_selecionadas_aud")
        else:
            etapas_selecionadas_aud = []
            st.markdown("**🎯 Etapas (Audiência):** Nenhuma etapa encontrada.")

        if responsaveis_disponiveis_aud:
            st.markdown("**👤 Responsável (Audiência):**")
            responsaveis_selecionados_aud = st.multiselect("Selecione os responsáveis", responsaveis_disponiveis_aud, default=responsaveis_disponiveis_aud, key="responsaveis_selecionados_aud")
        else:
            responsaveis_selecionados_aud = []
            st.markdown("**👤 Responsável (Audiência):** Nenhum responsável encontrado.")

    # Define as datas para a consulta principal com base na checkbox
    query_start_date = data_criacao_inicio_aud if aplicar_filtro_data_criacao_aud else None
    query_end_date = data_criacao_fim_aud if aplicar_filtro_data_criacao_aud else None

    # Converte datas para string para a chave do cache (ou None)
    start_date_key = query_start_date.strftime("%Y-%m-%d") if query_start_date else None
    end_date_key = query_end_date.strftime("%Y-%m-%d") if query_end_date else None

    with st.spinner("Carregando dados de audiências..."):
        try:
            df_audiencia_base = load_audiencia_data_base(data_service, CATEGORY_ID_AUDIENCIA, start_date_key, end_date_key)
            
            if df_audiencia_base.empty:
                st.warning("Nenhum dado encontrado para audiências com os filtros de data atuais.")
                return

            # Aplica filtros de etapas e responsáveis no DataFrame já processado e cacheado
            df_audiencia_filtrado = df_audiencia_base.copy()
            if etapas_selecionadas_aud and 'STAGE_NAME' in df_audiencia_filtrado.columns:
                df_audiencia_filtrado = df_audiencia_filtrado[df_audiencia_filtrado['STAGE_NAME'].isin(etapas_selecionadas_aud)]
            
            if responsaveis_selecionados_aud and 'ASSIGNED_BY_NAME' in df_audiencia_filtrado.columns:
                df_audiencia_filtrado = df_audiencia_filtrado[df_audiencia_filtrado['ASSIGNED_BY_NAME'].isin(responsaveis_selecionados_aud)]

            if df_audiencia_filtrado.empty:
                st.warning("Nenhum dado encontrado para audiências após aplicar todos os filtros (etapas, responsáveis).")
                return
            
            num_deals_filtrados = len(df_audiencia_filtrado)
            
            # --- Lógica de Roteamento para Sub-páginas com st.tabs ---
            base_tab_titles_aud = list(SUB_PAGE_URL_MAP_AUD.values()) # Nomes base para lógica e mapeamento
            display_tab_titles_aud = [
                f"📊 {base_tab_titles_aud[0]} ({num_deals_filtrados})", 
                f"👤 {base_tab_titles_aud[1]} ({num_deals_filtrados})",
                f"🗓️ {base_tab_titles_aud[2]} ({num_deals_filtrados})"
            ]
            
            # st.tabs não suporta `index` ou `value` para seleção inicial programática.
            # O primeiro tab sempre estará ativo no carregamento da página ou F5.
            tab_visao_geral, tab_analise_resp, tab_agenda = st.tabs(display_tab_titles_aud)

            # Para manter o URL atualizado com o tab clicado:
            if 'current_audiencia_sub_page_display_base' not in st.session_state:
                 # Usa o nome base para o estado, pois os nomes de display são dinâmicos
                st.session_state.current_audiencia_sub_page_display_base = base_tab_titles_aud[0]
            
            current_active_tab_url_key_aud = None

            with tab_visao_geral:
                # Compara com o nome base do tab
                if st.session_state.get('current_audiencia_sub_page_display_base') != base_tab_titles_aud[0]:
                    st.session_state.current_audiencia_sub_page_display_base = base_tab_titles_aud[0]
                    current_active_tab_url_key_aud = SUB_PAGE_STATE_TO_URL_MAP_AUD.get(base_tab_titles_aud[0])
                
                display_visao_geral_audiencia(df_audiencia_filtrado, data_service, ETAPAS_AUDIENCIA_ORDEM)
            
            with tab_analise_resp:
                if st.session_state.get('current_audiencia_sub_page_display_base') != base_tab_titles_aud[1]:
                    st.session_state.current_audiencia_sub_page_display_base = base_tab_titles_aud[1]
                    current_active_tab_url_key_aud = SUB_PAGE_STATE_TO_URL_MAP_AUD.get(base_tab_titles_aud[1])
                
                display_analise_responsavel_audiencia(df_audiencia_filtrado, data_service, ETAPAS_AUDIENCIA_ORDEM)
            
            with tab_agenda:
                if st.session_state.get('current_audiencia_sub_page_display_base') != base_tab_titles_aud[2]:
                    st.session_state.current_audiencia_sub_page_display_base = base_tab_titles_aud[2]
                    current_active_tab_url_key_aud = SUB_PAGE_STATE_TO_URL_MAP_AUD.get(base_tab_titles_aud[2])
                
                display_agenda_audiencia_tab(df_audiencia_filtrado)

            # Atualiza o URL fora dos blocos 'with'
            current_url_sub_page_aud = st.query_params.get("sub_pagina")
            if current_active_tab_url_key_aud and current_url_sub_page_aud != current_active_tab_url_key_aud:
                st.query_params.sub_pagina = current_active_tab_url_key_aud
                st.rerun()
            elif not current_active_tab_url_key_aud and st.session_state.current_audiencia_sub_page_display_base == base_tab_titles_aud[0] and current_url_sub_page_aud is not None:
                # Se o tab ativo é o primeiro (default) e existe sub_pagina no URL, remove-o
                del st.query_params["sub_pagina"]
                st.rerun()

        except Exception as e:
            st.error(f"Erro ao carregar ou processar dados de audiências: {str(e)}")
            st.exception(e)
            return

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
    
