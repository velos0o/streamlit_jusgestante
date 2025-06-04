import streamlit as st
import pandas as pd
from datetime import date, timedelta

# Importações de serviços e configurações
from src.data_service import DataService

def render_metricas_gerais(df: pd.DataFrame):
    """Renderiza métricas simplificadas do funil comercial"""
    st.markdown("---")
    st.subheader("Métricas")
    
    # Calcula métricas simplificadas
    total_negocios = len(df)

    # Negócios fechados: critério exato definido pelo usuário
    negocios_fechados = 0
    estrategia_usada = "Nenhuma"

    if 'IS_WON' in df.columns and 'UF_CRM_DATA_FECHAMENTO1' in df.columns:
        # Garante que a coluna de data de venda seja do tipo date
        df['UF_CRM_DATA_FECHAMENTO1'] = df['UF_CRM_DATA_FECHAMENTO1'].apply(lambda x: x.date() if isinstance(x, pd.Timestamp) else x)
        
        # Inicia a condição de filtro com IS_WON
        condicao_filtro = (df['IS_WON'] == True)

        # A estratégia agora é sempre baseada apenas em IS_WON
        estrategia_usada = "IS_WON"

        # Remove a condição de data de venda, independentemente do filtro estar ativado
        # if aplicar_filtro_data_venda:
        #     condicao_filtro &= \
        #         (df['UF_CRM_DATA_FECHAMENTO1'].notna()) & \
        #         (df['UF_CRM_DATA_FECHAMENTO1'] >= data_venda_inicio) & \
        #         (df['UF_CRM_DATA_FECHAMENTO1'] <= data_venda_fim)
        #     estrategia_usada = "IS_WON e UF_CRM_DATA_FECHAMENTO1 entre {} e {}".format(data_venda_inicio, data_venda_fim)
        # else:
        #     estrategia_usada = "IS_WON (sem filtro de data de venda)"

        # Aplica o filtro
        fechados_filtrados = df[condicao_filtro]
        negocios_fechados = len(fechados_filtrados)
    else:
        st.warning("Colunas 'IS_WON' ou 'UF_CRM_DATA_FECHAMENTO1' não encontradas para calcular 'Negócios Fechados'.")
        negocios_fechados = 0 # Garante que seja zero explicitamente se as colunas não existirem

    # Perdas: OUTROS ADVOGADOS ou NÃO HÁBIL
    perdas = 0
    if 'STAGE_NAME' in df.columns:
        perdas = len(df[df['STAGE_NAME'].isin(['OUTROS ADVOGADOS', 'NÃO HÁBIL'])])
    
    # Exibe métricas em 3 colunas grandes
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem; background: #1f1f1f; border-radius: 8px; margin: 0.5rem 0;">
            <h3 style="color: #00d4aa; margin: 0; font-size: 1.5rem;">📋 {total_negocios}</h3>
            <p style="color: white; margin: 0.3rem 0; font-size: 0.9rem;">Total de Negócios</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem; background: #1f1f1f; border-radius: 8px; margin: 0.5rem 0;">
            <h3 style="color: #00ff00; margin: 0; font-size: 1.5rem;">✅ {negocios_fechados}</h3>
            <p style="color: white; margin: 0.3rem 0; font-size: 0.9rem;">Negócios Fechados</p>
            <small style="color: #aaa; font-size: 0.8rem;">{estrategia_usada}</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem; background: #1f1f1f; border-radius: 8px; margin: 0.5rem 0;">
            <h3 style="color: #ff4444; margin: 0; font-size: 1.5rem;">❌ {perdas}</h3>
            <p style="color: white; margin: 0.3rem 0; font-size: 0.9rem;">Perdas</p>
            <small style="color: #aaa; font-size: 0.8rem;">Outros Advogados + Não Hábil</small>
        </div>
        """, unsafe_allow_html=True) 