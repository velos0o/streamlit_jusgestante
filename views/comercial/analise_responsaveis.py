import streamlit as st
import pandas as pd

def render_analise_responsaveis(df_comercial: pd.DataFrame):
    st.header("Análise de Desempenho por Responsável")

    if df_comercial.empty:
        st.warning("Não há dados disponíveis para exibir a análise por responsável.")
        return

    # Definir as colunas de etapas que queremos exibir individualmente
    # Estas são as etapas com semantics: null na configuração fornecida
    etapas_colunas = [
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
        "SEM INTERESSE"
    ]

    # Colunas necessárias no DataFrame
    colunas_necessarias = ['ASSIGNED_BY_NAME', 'STAGE_NAME', 'IS_WON']
    for col in colunas_necessarias:
        if col not in df_comercial.columns:
            st.error(f"A coluna necessária '{col}' não foi encontrada nos dados.")
            return

    # Certificar que ASSIGNED_BY_NAME não tem NaNs para o groupby
    df_comercial_filtrado = df_comercial.dropna(subset=['ASSIGNED_BY_NAME'])
    if df_comercial_filtrado.empty:
        st.warning("Não há dados de responsáveis para exibir.")
        return
        
    # Agrupar por responsável e contar negócios em cada etapa específica
    # Usamos pivot_table para transformar STAGE_NAME em colunas
    df_pivot = pd.pivot_table(
        df_comercial_filtrado,
        index='ASSIGNED_BY_NAME',
        columns='STAGE_NAME',
        aggfunc='size',
        fill_value=0
    )

    # Selecionar e reordenar as colunas de etapas desejadas
    # Se uma etapa não existir nos dados do pivot, será preenchida com 0
    df_analise = pd.DataFrame(index=df_pivot.index)
    for etapa in etapas_colunas:
        if etapa in df_pivot.columns:
            df_analise[etapa] = df_pivot[etapa]
        else:
            df_analise[etapa] = 0

    # Calcular Negócios Fechados (IS_WON == True)
    negocios_fechados_por_responsavel = df_comercial_filtrado[df_comercial_filtrado['IS_WON'] == True].groupby('ASSIGNED_BY_NAME').size()
    df_analise['NEGÓCIO FECHADO'] = negocios_fechados_por_responsavel.reindex(df_analise.index, fill_value=0)

    # Calcular Total de Negócios por Responsável
    # O total de negócios inclui todos os negócios, independentemente da etapa final.
    total_negocios_por_responsavel = df_comercial_filtrado.groupby('ASSIGNED_BY_NAME').size()
    df_analise['Total de Negócios'] = total_negocios_por_responsavel.reindex(df_analise.index, fill_value=0)
    
    # Calcular Percentual de Conversão
    # Evitar divisão por zero se 'Total de Negócios' for 0
    df_analise['Conversão (%)'] = (df_analise['NEGÓCIO FECHADO'] / df_analise['Total de Negócios'].replace(0, pd.NA) * 100).round(2)
    df_analise['Conversão (%)'] = df_analise['Conversão (%)'].fillna(0) # Preenche NaNs (resultantes da divisão por zero) com 0

    # Resetar o índice para ASSIGNED_BY_NAME se tornar uma coluna
    df_analise = df_analise.reset_index()
    df_analise.rename(columns={'ASSIGNED_BY_NAME': 'Responsável'}, inplace=True)
    
    # Reordenar colunas para a exibição final
    colunas_finais = ['Responsável'] + etapas_colunas + ['NEGÓCIO FECHADO', 'Total de Negócios', 'Conversão (%)']
    df_analise = df_analise[colunas_finais]

    st.dataframe(
        df_analise, 
        use_container_width=True,
        column_config={
            "Conversão (%)": st.column_config.NumberColumn(
                label="Conversão (%)",
                format="%.2f%%"  # Formata como número com 2 casas decimais e adiciona %
            )
        }
    ) 