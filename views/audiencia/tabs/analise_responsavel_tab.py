import streamlit as st
import pandas as pd
from src.data_service import DataService

def display_analise_responsavel_audiencia(df_audiencia: pd.DataFrame, data_service: DataService, etapas_ordem: list):
    st.subheader("Análise de Deals por Responsável e Etapa")

    if df_audiencia.empty:
        st.info("Não há dados de audiência para analisar.")
        return

    # Colunas necessárias para esta análise
    colunas_necessarias = ['ASSIGNED_BY_NAME', 'ID', 'STAGE_NAME']
    for col in colunas_necessarias:
        if col not in df_audiencia.columns:
            st.error(f"A coluna necessária '{col}' não foi encontrada nos dados de audiência. Verifique a fonte de dados.")
            return

    # Garantir que ASSIGNED_BY_NAME não tem NaNs para o groupby e pivot
    df_audiencia_filtrado = df_audiencia.dropna(subset=['ASSIGNED_BY_NAME'])
    if df_audiencia_filtrado.empty:
        st.info("Não há dados de responsáveis (ASSIGNED_BY_NAME) para exibir após remover valores nulos.")
        return

    # 1. Agrupar por responsável (usando ASSIGNED_BY_NAME) e etapa para contar deals
    # Usamos pivot_table para transformar STAGE_NAME em colunas
    pivot_df = pd.pivot_table(
        df_audiencia_filtrado,
        index='ASSIGNED_BY_NAME', # Usar diretamente o nome do responsável
        columns='STAGE_NAME',
        values='ID', # Contar ocorrências de ID (deals)
        aggfunc='size', # Equivalente a count() para groupby
        fill_value=0
    )

    # 2. Reordenar colunas de acordo com etapas_ordem e adicionar etapas faltantes
    # Garante que todas as etapas da lista 'etapas_ordem' estejam presentes como colunas
    for etapa in etapas_ordem:
        if etapa not in pivot_df.columns:
            pivot_df[etapa] = 0 # Adiciona coluna com zeros se a etapa não existir nos dados
    
    # Seleciona apenas as colunas que estão em etapas_ordem e na ordem correta
    # Isso também remove colunas de etapas que podem estar nos dados mas não em etapas_ordem
    pivot_df = pivot_df[[col for col in etapas_ordem if col in pivot_df.columns]]

    # 3. Adicionar coluna de Total de Deals por responsável
    pivot_df['TOTAL DEALS'] = pivot_df.sum(axis=1)
    
    # Reordenar para colocar 'TOTAL DEALS' no início
    cols = ['TOTAL DEALS'] + [col for col in pivot_df.columns if col != 'TOTAL DEALS']
    pivot_df = pivot_df[cols]

    # Resetar o índice para ASSIGNED_BY_NAME (que agora é o índice) se tornar uma coluna chamada 'Responsável'
    pivot_df = pivot_df.reset_index()
    pivot_df.rename(columns={'ASSIGNED_BY_NAME': 'Responsável'}, inplace=True)
    
    st.info(f"Exibindo análise para {len(pivot_df)} responsáveis.")
    st.dataframe(pivot_df, use_container_width=True)

    # 4. Gráfico de Barras Empilhadas (REMOVIDO CONFORME SOLICITAÇÃO)
    # if not pivot_df.empty and 'Responsável' in pivot_df.columns:
    #     st.markdown("### Gráfico de Deals por Responsável e Etapa")
    #     # Para o gráfico, não incluímos a coluna 'TOTAL DEALS' nas barras empilhadas
    #     # e usamos 'Responsável' como índice
    #     chart_df_source = pivot_df.set_index('Responsável')
    #     chart_df = chart_df_source.drop(columns=['TOTAL DEALS'], errors='ignore')
    #     
    #     if not chart_df.empty:
    #         colors = ["#004c99", "#005cbf", "#006de6", "#007fff", "#1a8cff", 
    #                   "#3399ff", "#4da6ff", "#66b3ff", "#80c0ff", "#99ccff", 
    #                   "#b3d9ff", "#cce6ff", "#e6f2ff"]
    #         st.bar_chart(chart_df, color=colors[:len(chart_df.columns)])
    #     else:
    #         st.info("Não há dados de etapas para exibir no gráfico.")
    # else:
    #     st.info("Não há dados para exibir no gráfico de responsáveis.") 