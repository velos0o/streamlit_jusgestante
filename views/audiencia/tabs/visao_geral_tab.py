import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.data_service import DataService

def display_visao_geral_audiencia(df_audiencia: pd.DataFrame, data_service: DataService, etapas_ordem: list):
    st.subheader("Distribuição por Estágio")

    if df_audiencia.empty:
        st.info("Não há dados de audiência para exibir na visão geral.")
        return

    # Calcular a distribuição de estágios a partir do DataFrame fornecido
    if 'STAGE_NAME' in df_audiencia.columns:
        stage_distribution = df_audiencia['STAGE_NAME'].value_counts().reset_index()
        stage_distribution.columns = ['STAGE_NAME', 'COUNT']
        
        # Ordenar os estágios de acordo com a etapas_ordem fornecida
        # Converte STAGE_NAME para tipo Categoria com a ordem definida
        stage_distribution['STAGE_NAME'] = pd.Categorical(
            stage_distribution['STAGE_NAME'],
            categories=etapas_ordem,
            ordered=True
        )
        stage_distribution = stage_distribution.sort_values('STAGE_NAME').dropna(subset=['STAGE_NAME'])
        
    else:
        st.warning("Coluna 'STAGE_NAME' não encontrada no DataFrame de audiência.")
        return

    if stage_distribution.empty:
        st.info("Não há dados de distribuição por estágio para exibir após o processamento.")
        return
        
    # Criação do gráfico de funil com Plotly
    fig = go.Figure()

    fig.add_trace(go.Funnel(
        name = 'Deals',
        y = stage_distribution['STAGE_NAME'],
        x = stage_distribution['COUNT'],
        textinfo = "value+percent initial", # Mostra valor e % em relação ao total inicial
        marker = {"color": ["#004c99", "#005cbf", "#006de6", "#007fff", "#1a8cff", 
                           "#3399ff", "#4da6ff", "#66b3ff", "#80c0ff", "#99ccff", "#b3d9ff", "#cce6ff"]}, # Cores para os estágios (adicionei mais uma)
        connector = {"line": {"color": "royalblue", "dash": "dot", "width": 3}}
    ))
    
    fig.update_layout(
        title_text='Funil de Audiência',
        title_x=0.5,
        plot_bgcolor='rgba(0,0,0,0)', 
        paper_bgcolor='rgba(0,0,0,0)', 
        font=dict(color="black") 
    )

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Ver dados da distribuição por estágio"):
        # Mostrar o dataframe com 'STAGE_NAME' como string para melhor legibilidade
        display_df = stage_distribution.copy()
        display_df['STAGE_NAME'] = display_df['STAGE_NAME'].astype(str)
        st.dataframe(display_df) 