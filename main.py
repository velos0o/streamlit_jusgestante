import streamlit as st
import sys
import os

# Adiciona src ao path para imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'config'))

from src.data_service import DataService
from config.funis_config import FunilConfig

# --- Configuração de Roteamento ---
PAGE_URL_MAP = {
    "comercial": "🏢 Relatório Comercial",
    "administrativo": "📋 Trâmites Administrativos",
    "audiencia": "⚖️ Relatório de Audiência",
    "financeiro": "💰 Relatório Financeiro",
    "entrevista": "🎙️ Relatório de Entrevista",
}
PAGE_STATE_TO_URL_MAP = {v: k for k, v in PAGE_URL_MAP.items()}
# --- Fim Configuração de Roteamento ---

def load_styles():
    """Carrega estilos CSS personalizados"""
    # CSS global para fontes normais e design padronizado
    st.markdown("""
    <style>
    /* Configurações globais */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        font-size: 1em;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* Variáveis CSS */
    :root {
        --primary-color: #1f77b4;
        --secondary-color: #ff7f0e;
        --success-color: #2ca02c;
        --warning-color: #ff7f0e;
        --danger-color: #d62728;
        --text-primary: #212529;
        --text-secondary: #6c757d;
        --spacing-md: 1rem;
        --spacing-lg: 1.5rem;
        --border-radius: 8px;
        --shadow-sm: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
    }
    
    /* Cards de métricas */
    .metric-card {
        background: white;
        border-radius: var(--border-radius);
        box-shadow: var(--shadow-sm);
        padding: var(--spacing-lg);
        margin-bottom: var(--spacing-md);
        border: 1px solid #e9ecef;
    }
    
    /* Títulos */
    .metric-title {
        font-size: 1.8rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: var(--spacing-md);
    }
    
    /* Mensagens temporárias (10s) */
    .stAlert {
        animation: fadeOut 10s forwards;
    }
    
    @keyframes fadeOut {
        0% { opacity: 1; }
        90% { opacity: 1; }
        100% { opacity: 0; pointer-events: none; }
    }
    
    /* Animação de entrada */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .fade-in {
        animation: fadeIn 0.6s ease-out;
    }

    /* Estilos para sub-abas */
    .stTabs [data-baseweb="tab-list"] button {
        font-size: 0.9em; /* Tamanho da fonte menor */
        padding: 0.5rem 1rem; /* Menor padding */
        margin-right: 0.5rem; /* Menor espaçamento */
        border-radius: 5px; /* Bordas arredondadas */
        background-color: #f0f2f6; /* Cor de fundo suave */
        color: #495057; /* Cor do texto */
        border: none; /* Sem borda */
        box-shadow: none; /* Sem sombra */
        transition: all 0.2s ease-in-out;
    }

    .stTabs [data-baseweb="tab-list"] button:hover {
        background-color: #e2e6ea; /* Cor de fundo ao passar o mouse */
        color: #212529; /* Cor do texto ao passar o mouse */
    }

    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: var(--primary-color); /* Cor principal quando selecionado */
        color: white; /* Texto branco quando selecionado */
        font-weight: 600; /* Negrito */
        box-shadow: var(--shadow-sm); /* Sombra sutil */
    }

    /* Indentação para a aba principal (ajuste conforme a necessidade do layout) */
    .stTabs {
        margin-left: 20px; /* Adiciona um recuo visual para as sub-abas */
    }
    
    </style>
    """, unsafe_allow_html=True)


def setup_page():
    """Configura página principal"""
    st.set_page_config(
        page_title="JusGestante - Sistema Bitrix24",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded"
    )


def render_sidebar_navigation():
    """Renderiza navegação na sidebar"""
    with st.sidebar:
        st.title("🚀 JusGestante")
        st.markdown("---")
        
        st.markdown("### 📊 Dashboards")
        
        # # Botão para selecionar o Relatório Comercial
        # if st.button("🏢 Relatório Comercial", key="relatorio_comercial_btn", use_container_width=True):
        #     if st.session_state.get('pagina_selecionada') != "🏢 Relatório Comercial":
        #         st.session_state.pagina_selecionada = "🏢 Relatório Comercial"
        #         new_url_param = PAGE_STATE_TO_URL_MAP.get("🏢 Relatório Comercial")
        #         if new_url_param:
        #             st.query_params.pagina = new_url_param
        #         st.rerun()
            
        # # Novo Botão para Trâmites Administrativos
        # if st.button("📋 Trâmites Administrativos", key="relatorio_administrativo_btn", use_container_width=True):
        #     if st.session_state.get('pagina_selecionada') != "📋 Trâmites Administrativos":
        #         st.session_state.pagina_selecionada = "📋 Trâmites Administrativos"
        #         new_url_param = PAGE_STATE_TO_URL_MAP.get("📋 Trâmites Administrativos")
        #         if new_url_param:
        #             st.query_params.pagina = new_url_param
        #         st.rerun()

        # # Novo Botão para Relatório de Audiência
        # if st.button("⚖️ Relatório de Audiência", key="relatorio_audiencia_btn", use_container_width=True):
        #     if st.session_state.get('pagina_selecionada') != "⚖️ Relatório de Audiência":
        #         st.session_state.pagina_selecionada = "⚖️ Relatório de Audiência"
        #         new_url_param = PAGE_STATE_TO_URL_MAP.get("⚖️ Relatório de Audiência")
        #         if new_url_param:
        #             st.query_params.pagina = new_url_param
        #         st.rerun()

        # Botão para Relatório de Entrevista
        if st.button("🎙️ Relatório de Entrevista", key="relatorio_entrevista_btn", use_container_width=True):
            if st.session_state.get('pagina_selecionada') != "🎙️ Relatório de Entrevista":
                st.session_state.pagina_selecionada = "🎙️ Relatório de Entrevista"
                new_url_param = PAGE_STATE_TO_URL_MAP.get("🎙️ Relatório de Entrevista")
                if new_url_param:
                    st.query_params.pagina = new_url_param
                st.rerun()

        # # Botão para Relatório Financeiro
        # if st.button("💰 Relatório Financeiro", key="relatorio_financeiro_btn", use_container_width=True):
        #     if st.session_state.get('pagina_selecionada') != "💰 Relatório Financeiro":
        #         st.session_state.pagina_selecionada = "💰 Relatório Financeiro"
        #         new_url_param = PAGE_STATE_TO_URL_MAP.get("💰 Relatório Financeiro")
        #         if new_url_param:
        #             st.query_params.pagina = new_url_param
        #         st.rerun()

        # O estado da página é gerenciado via st.session_state

def main():
    """Função principal"""
    setup_page()
    load_styles()
    
    # --- Lógica de Roteamento ---
    url_page_param = st.query_params.get("pagina", None)

    # Prioridade 1: URL param para definir o estado, se válido e diferente do estado atual, ou se estado não existe.
    if url_page_param and url_page_param in PAGE_URL_MAP:
        if st.session_state.get('pagina_selecionada') != PAGE_URL_MAP[url_page_param]:
            st.session_state.pagina_selecionada = PAGE_URL_MAP[url_page_param]
            # Não fazer st.rerun() aqui para evitar loop se set_query_params abaixo também causar rerun.
            # A mudança de estado será refletida naturalmente no fluxo da página.
    elif 'pagina_selecionada' not in st.session_state:
        # Prioridade 2: Se nenhum URL param válido e o estado não existe, definir padrão.
        st.session_state.pagina_selecionada = "🎙️ Relatório de Entrevista"

    # Garantir que a URL reflita o estado atual (canônico)
    # Isso é útil se o estado foi definido por padrão ou se a URL estava "suja"
    current_page_in_state = st.session_state.get('pagina_selecionada', "🎙️ Relatório de Entrevista") # Default if somehow still not set
    expected_url_param_for_state = PAGE_STATE_TO_URL_MAP.get(current_page_in_state)

    if expected_url_param_for_state and url_page_param != expected_url_param_for_state:
        st.query_params.pagina = expected_url_param_for_state
        # Se set_query_params não causar um rerun que atualize get_query_params para o próximo ciclo,
        # e isso for um problema, um st.rerun() PODE ser necessário aqui, mas use com cautela.
        # Para a maioria dos casos, Streamlit lida bem com a atualização da URL e o estado interno.
    # --- Fim Lógica de Roteamento ---
    
    render_sidebar_navigation()
    
    # Carrega o dashboard selecionado com base no st.session_state
    pagina_atual = st.session_state.get('pagina_selecionada')

    if pagina_atual == "🏢 Relatório Comercial":
        try:
            from views.comercial.relatorio_comercial import render_relatorio_comercial
            render_relatorio_comercial()
        except ImportError as e:
            st.error(f"❌ Erro ao carregar relatório comercial: {str(e)}")
            st.info("Verifique se o módulo comercial está instalado corretamente")
            
    elif pagina_atual == "📋 Trâmites Administrativos":
        try:
            # Este arquivo e função serão criados nas próximas etapas
            from views.administrativo.relatorio_administrativo import render_relatorio_administrativo
            render_relatorio_administrativo()
        except ImportError as e:
            st.error(f"❌ Erro ao carregar relatório de trâmites administrativos: {str(e)}")
            st.info("Verifique se o módulo de trâmites administrativos está configurado.")
            # Adicionar uma mensagem mais específica de que está em desenvolvimento
            st.warning("🚧 O relatório de Trâmites Administrativos está em desenvolvimento.")

    elif pagina_atual == "⚖️ Relatório de Audiência":
        try:
            from views.audiencia.relatorio_audiencia import display_relatorio_audiencia
            display_relatorio_audiencia()
        except ImportError as e:
            st.error(f"❌ Erro ao carregar relatório de audiência: {str(e)}")
            st.info("Verifique se o módulo de audiência está configurado.")
            st.warning("🚧 O relatório de Audiência está em desenvolvimento.")

    elif pagina_atual == "🎙️ Relatório de Entrevista":
        try:
            from views.entrevista.relatorio_entrevista import render_relatorio_entrevista
            render_relatorio_entrevista()
        except ImportError as e:
            st.error(f"❌ Erro ao carregar relatório de entrevista: {str(e)}")
            st.info("Verifique se o módulo de entrevista está configurado.")

    elif pagina_atual == "💰 Relatório Financeiro":
        try:
            from views.financeiro.relatorio_financeiro import render_relatorio_financeiro
            render_relatorio_financeiro()
        except ImportError as e:
            st.error(f"❌ Erro ao carregar relatório financeiro: {str(e)}")
            st.info("Verifique se o módulo financeiro está configurado.")


if __name__ == "__main__":
    main() 