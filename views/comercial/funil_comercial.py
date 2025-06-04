import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Importações de serviços e configurações
from config.funis_config import FunilConfig

def render_funil_comercial(df: pd.DataFrame):
    """Renderiza visualização do funil comercial"""
    st.markdown("---")
    st.subheader("📈 Etapas do Funil Comercial")
    
    if 'STAGE_NAME' not in df.columns:
        st.warning("Dados de etapas não disponíveis")
        return
    
    # Agrupa dados por etapa
    funil_data = df.groupby('STAGE_NAME').agg({
        'ID': 'count',
        'OPPORTUNITY': 'sum'
    }).rename(columns={'ID': 'Quantidade', 'OPPORTUNITY': 'Valor_Total'})
    
    # Ordena pelas etapas do funil (usando sort_order da configuração)
    etapas_ordem = [
        "EM ESPERA DE ATENDIMENTO",
        "NÃO INTERAGIU", 
        "QUEBRA NA COMUNICAÇÃO",
        "ABORDAGEM INICIAL",
        "AGENDADO",
        "REMARCA AGENDA", 
        "NEGOCIAÇÃO",
        "CONTRATO/PROCURAÇÃO/TERMOS",
        "DOCUMENTAÇÕES PENDENTES",
        "ASSINATURAS PENDENTES",
        "SEM INTERESSE",
        "NEGÓCIO FECHADO",
        "OUTROS ADVOGADOS",
        "NÃO HÁBIL"
    ]
    
    # Reordena o dataframe
    funil_data = funil_data.reindex([etapa for etapa in etapas_ordem if etapa in funil_data.index])
    funil_data = funil_data.fillna(0)
    
    # Calcula percentuais
    funil_data['Percentual'] = (funil_data['Quantidade'] / funil_data['Quantidade'].sum()) * 100
    
    # Cria visualização em abas (sem gráfico de barras)
    tab1, tab2 = st.tabs(["📊 Funil Visual", "📋 Dados por Etapa"])
    
    with tab1:
        # Gráfico de funil
        fig_funil = go.Figure(go.Funnel(
            y=funil_data.index,
            x=funil_data['Quantidade'],
            textinfo="value+percent total",
            marker_color=['#FF6B35' if 'FECHADO' in stage else 
                         '#EF5350' if stage in ['OUTROS ADVOGADOS', 'NÃO HÁBIL'] else 
                         '#4ECDC4' for stage in funil_data.index]
        ))
        
        fig_funil.update_layout(
            title="Funil Comercial - Distribuição por Etapa",
            height=600,
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig_funil, use_container_width=True)
    
    with tab2:
        # Tabela detalhada por etapa
        st.markdown("Resumo por Etapa do Funil")
        
        # Formata tabela para exibição
        funil_display = funil_data[['Quantidade', 'Percentual']].copy()
        funil_display['Percentual'] = funil_display['Percentual'].apply(lambda x: f"{x:.1f}%")
        
        st.dataframe(
            funil_display,
            use_container_width=True,
            column_config={
                "Quantidade": st.column_config.NumberColumn("Qtd Negócios"),
                "Percentual": "% do Total"
            },
            height=300
        ) 