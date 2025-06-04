import streamlit as st
import pandas as pd

def render_analise_responsaveis_administrativo(df_administrativo: pd.DataFrame, etapas_ordem_completa: list):
    st.subheader("Análise de Desempenho por Responsável (Trâmites Administrativos)")

    if df_administrativo.empty:
        st.warning("Não há dados disponíveis para exibir a análise por responsável.")
        return

    # Colunas necessárias no DataFrame
    colunas_necessarias = ['ASSIGNED_BY_NAME', 'STAGE_NAME', 'IS_WON'] # IS_WON será usado para "PROTOCOLADO COM SUCESSO"
    for col in colunas_necessarias:
        if col not in df_administrativo.columns:
            st.error(f"A coluna necessária '{col}' não foi encontrada nos dados. Detalhe: {colunas_necessarias}")
            # Adiciona um log para depuração, caso STAGE_SEMANTIC precise ser usado.
            if 'STAGE_SEMANTIC' in df_administrativo.columns:
                st.info(f"Coluna STAGE_SEMANTIC encontrada: {df_administrativo['STAGE_SEMANTIC'].unique()[:5]}")
            else:
                st.info("Coluna STAGE_SEMANTIC não encontrada.")
            return

    # Certificar que ASSIGNED_BY_NAME não tem NaNs para o groupby
    df_filtrado_resp = df_administrativo.dropna(subset=['ASSIGNED_BY_NAME'])
    if df_filtrado_resp.empty:
        st.warning("Não há dados de responsáveis para exibir após limpeza de NaNs.")
        return

    # Definir as etapas que são consideradas "em progresso" (não finais de sucesso/falha)
    # para exibição individual na tabela de análise por responsável.
    etapas_em_progresso = [etapa for etapa in etapas_ordem_completa if etapa not in ["PROTOCOLADO COM SUCESSO", "CANCELAMENTO"]]

    # Agrupar por responsável e contar negócios em cada etapa específica
    df_pivot_resp = pd.pivot_table(
        df_filtrado_resp,
        index='ASSIGNED_BY_NAME',
        columns='STAGE_NAME',
        aggfunc='size',
        fill_value=0
    )

    # Montar o DataFrame de análise
    df_analise_resp = pd.DataFrame(index=df_pivot_resp.index)

    # Adicionar contagens para etapas em progresso
    for etapa in etapas_em_progresso:
        if etapa in df_pivot_resp.columns:
            df_analise_resp[etapa] = df_pivot_resp[etapa]
        else:
            df_analise_resp[etapa] = 0 # Adiciona a coluna com zeros se não houver dados para essa etapa
    
    # Calcular "PROTOCOLADO COM SUCESSO" por responsável
    # Assumindo que IS_WON == True corresponde a "PROTOCOLADO COM SUCESSO" (via STAGE_ID C2:WON ou STAGE_SEMANTIC S/WON)
    protocolados_sucesso = df_filtrado_resp[df_filtrado_resp['IS_WON'] == True].groupby('ASSIGNED_BY_NAME').size()
    df_analise_resp['PROTOCOLADO COM SUCESSO'] = protocolados_sucesso.reindex(df_analise_resp.index, fill_value=0)

    # Calcular Total de Trâmites por Responsável
    total_tramites_responsavel = df_filtrado_resp.groupby('ASSIGNED_BY_NAME').size()
    df_analise_resp['Total de Trâmites'] = total_tramites_responsavel.reindex(df_analise_resp.index, fill_value=0)
    
    # Calcular Percentual de Sucesso
    df_analise_resp['Sucesso (%)'] = (df_analise_resp['PROTOCOLADO COM SUCESSO'] / df_analise_resp['Total de Trâmites'].replace(0, pd.NA) * 100)
    df_analise_resp['Sucesso (%)'] = df_analise_resp['Sucesso (%)'].fillna(0).round(2)

    # Resetar o índice para ASSIGNED_BY_NAME se tornar uma coluna e renomear
    df_analise_resp = df_analise_resp.reset_index()
    df_analise_resp.rename(columns={'ASSIGNED_BY_NAME': 'Responsável'}, inplace=True)
    
    # Reordenar colunas para a exibição final
    colunas_finais_resp = ['Responsável'] + etapas_em_progresso + ['PROTOCOLADO COM SUCESSO', 'Total de Trâmites', 'Sucesso (%)']
    df_analise_resp = df_analise_resp[colunas_finais_resp]

    st.dataframe(
        df_analise_resp,
        use_container_width=True,
        column_config={
            "Sucesso (%)": st.column_config.NumberColumn(
                label="Sucesso (%)",
                format="%.2f%%"
            )
        }
    ) 