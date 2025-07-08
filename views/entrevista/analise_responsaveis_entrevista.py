import streamlit as st
import pandas as pd
from config.funis_config import FunilConfig

def render_analise_responsaveis_entrevista(df_entrevista: pd.DataFrame):
    """
    Renderiza a análise de desempenho por responsável para o funil de entrevista.
    Exibe uma tabela com vendas recebidas, validados e aproveitamento.
    """
    st.header("Análise de Desempenho por Responsável")

    if df_entrevista.empty:
        st.warning("Não há dados disponíveis para exibir a análise por responsável.")
        return

    colunas_necessarias = ['ASSIGNED_BY_NAME', 'STAGE_ID', 'STAGE_NAME']
    for col in colunas_necessarias:
        if col not in df_entrevista.columns:
            st.error(f"A coluna necessária '{col}' não foi encontrada nos dados.")
            return

    df_filtrado = df_entrevista.dropna(subset=['ASSIGNED_BY_NAME'])
    if df_filtrado.empty:
        st.warning("Não há dados de responsáveis para exibir.")
        return

    # --- Tabela 1: Aproveitamento por Responsável ---
    df_analise = _criar_tabela_aproveitamento(df_filtrado)
    st.dataframe(
        df_analise,
        use_container_width=True,
        column_config={
            "Aproveitamento (%)": st.column_config.NumberColumn(
                label="Aproveitamento (%)",
                format="%.2f%%"
            )
        },
        hide_index=True
    )

    st.markdown("---")

    # --- Tabela 2: Detalhamento por Etapa e Responsável ---
    st.header("Detalhamento por Etapa")
    df_detalhe_etapa = _criar_tabela_detalhe_etapa(df_filtrado)
    st.dataframe(df_detalhe_etapa, use_container_width=True)


def _criar_tabela_aproveitamento(df: pd.DataFrame) -> pd.DataFrame:
    """Cria a tabela de resumo de aproveitamento por responsável."""
    vendas_recebidas = df.groupby('ASSIGNED_BY_NAME').size().reset_index(name='Vendas Recebidas')
    df_validados = df[df['STAGE_ID'] == 'C11:WON']
    validados = df_validados.groupby('ASSIGNED_BY_NAME').size().reset_index(name='Validados')

    df_analise = pd.merge(vendas_recebidas, validados, on='ASSIGNED_BY_NAME', how='left').fillna(0)
    df_analise['Validados'] = df_analise['Validados'].astype(int)

    df_analise['Aproveitamento (%)'] = (df_analise['Validados'] / df_analise['Vendas Recebidas'].replace(0, pd.NA) * 100).round(2)
    df_analise['Aproveitamento (%)'] = df_analise['Aproveitamento (%)'].fillna(0)
    
    df_analise.rename(columns={'ASSIGNED_BY_NAME': 'Responsável'}, inplace=True)

    total_row = pd.DataFrame({
        'Responsável': ['Total'],
        'Vendas Recebidas': [df_analise['Vendas Recebidas'].sum()],
        'Validados': [df_analise['Validados'].sum()]
    })
    total_aproveitamento = (total_row['Validados'].iloc[0] / total_row['Vendas Recebidas'].iloc[0] * 100) if total_row['Vendas Recebidas'].iloc[0] > 0 else 0
    total_row['Aproveitamento (%)'] = round(total_aproveitamento, 2)
    
    df_analise = pd.concat([df_analise, total_row], ignore_index=True)

    return df_analise[['Responsável', 'Vendas Recebidas', 'Validados', 'Aproveitamento (%)']]

def _criar_tabela_detalhe_etapa(df: pd.DataFrame) -> pd.DataFrame:
    """Cria a tabela de detalhamento de negócios por etapa e responsável."""
    # Pivot para ter etapas nas linhas e responsáveis nas colunas
    pivot_df = pd.pivot_table(
        df,
        index='STAGE_NAME',
        columns='ASSIGNED_BY_NAME',
        aggfunc='size',
        fill_value=0
    )

    # Obter a ordem correta das etapas a partir da configuração
    entrevista_config = FunilConfig.get_entrevista_config()
    ordem_etapas = [stage.stage_name for stage in sorted(entrevista_config.stages, key=lambda s: s.sort_order)]

    # Reordenar o índice do pivot de acordo com a configuração
    pivot_df = pivot_df.reindex(ordem_etapas).fillna(0).astype(int)

    # Adicionar coluna de Total (soma das linhas)
    pivot_df['Total'] = pivot_df.sum(axis=1)

    # Adicionar linha de Total (soma das colunas)
    total_row = pivot_df.sum().rename('Total')
    pivot_df = pd.concat([pivot_df, pd.DataFrame(total_row).T])

    return pivot_df 