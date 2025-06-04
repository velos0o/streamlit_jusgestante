import streamlit as st
import pandas as pd
import plotly.express as px # Adicionado para gráficos
from datetime import date, timedelta # Adicionado para manipulação de datas

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

    st.markdown("---")
    st.subheader("📅 Vendas Diárias (Negócios Fechados)")

    if 'UF_CRM_DATA_FECHAMENTO1' not in df_comercial.columns or 'IS_WON' not in df_comercial.columns:
        st.warning("Colunas 'UF_CRM_DATA_FECHAMENTO1' ou 'IS_WON' não encontradas. Não é possível gerar o gráfico de vendas diárias.")
        return

    df_vendas_original = df_comercial[
        (df_comercial['IS_WON'] == True) & 
        (df_comercial['UF_CRM_DATA_FECHAMENTO1'].notna())
    ].copy()

    if df_vendas_original.empty:
        st.info("Não há dados de vendas fechadas com data para exibir no gráfico.")
        return

    df_vendas_original.loc[:, 'DATA_VENDA'] = pd.to_datetime(df_vendas_original['UF_CRM_DATA_FECHAMENTO1'], errors='coerce').dt.date
    df_vendas_original.dropna(subset=['DATA_VENDA'], inplace=True)

    if df_vendas_original.empty:
        st.info("Não há dados de vendas válidos após o processamento inicial das datas.")
        return

    # Filtro por pessoa responsável para o gráfico de vendas diárias
    responsaveis_vendas_disponiveis = sorted(df_vendas_original['ASSIGNED_BY_NAME'].dropna().unique())

    if not responsaveis_vendas_disponiveis:
        st.info("Não há responsáveis com vendas fechadas para filtrar.")
        # Ainda permite que o gráfico seja exibido, mas sem filtro de responsável
        responsaveis_selecionados_grafico = [] 
    else:
        responsaveis_selecionados_grafico = st.multiselect(
            "Filtrar por Responsável (Gráfico de Vendas)",
            responsaveis_vendas_disponiveis,
            default=responsaveis_vendas_disponiveis, # Seleciona todos por padrão
            key="graf_vendas_responsavel_filtro"
        )

    if responsaveis_selecionados_grafico:
        df_vendas_original = df_vendas_original[df_vendas_original['ASSIGNED_BY_NAME'].isin(responsaveis_selecionados_grafico)].copy()
    else:
        st.info("Nenhum responsável selecionado para o gráfico de vendas diárias. Exibindo todos.")

    # Re-verifica se há dados após o filtro de responsável
    if df_vendas_original.empty:
        st.info("Não há dados após o filtro de responsáveis para o gráfico de vendas diárias.")
        return # Retorna para evitar erro se dataframe estiver vazio

    # Date slider para filtrar o gráfico
    min_data_venda_geral = df_vendas_original['DATA_VENDA'].min()
    max_data_venda_geral = df_vendas_original['DATA_VENDA'].max()

    # Se houver apenas um dia ou nenhum, define um intervalo padrão razoável para o slider
    if min_data_venda_geral == max_data_venda_geral or pd.isna(min_data_venda_geral):
        data_inicial_filtro = date.today() - timedelta(days=30)
        data_final_filtro = date.today()
        if not pd.isna(min_data_venda_geral): # Usa a data existente se houver apenas uma
             data_inicial_filtro = min_data_venda_geral
             data_final_filtro = min_data_venda_geral   
    else:
        data_inicial_filtro = min_data_venda_geral
        data_final_filtro = max_data_venda_geral
    
    col_slider1, col_slider2 = st.columns(2)
    with col_slider1:
        data_inicio_selecionada = st.date_input(
            "Data Início (gráfico)", 
            value=data_inicial_filtro,
            min_value=min_data_venda_geral if not pd.isna(min_data_venda_geral) else date.today() - timedelta(days=365*2), # Fallback para min_value
            max_value=max_data_venda_geral if not pd.isna(max_data_venda_geral) else date.today(), # Fallback para max_value
            key="graf_vendas_data_inicio"
        )
    with col_slider2:
        data_fim_selecionada = st.date_input(
            "Data Fim (gráfico)", 
            value=data_final_filtro,
            min_value=min_data_venda_geral if not pd.isna(min_data_venda_geral) else date.today() - timedelta(days=365*2), # Fallback
            max_value=max_data_venda_geral if not pd.isna(max_data_venda_geral) else date.today(), # Fallback
            key="graf_vendas_data_fim"
        )
    
    if data_inicio_selecionada > data_fim_selecionada:
        st.error("A data de início não pode ser posterior à data de fim.")
        return

    # Filtra df_vendas com base no slider
    df_vendas_filtrado = df_vendas_original[
        (df_vendas_original['DATA_VENDA'] >= data_inicio_selecionada) &
        (df_vendas_original['DATA_VENDA'] <= data_fim_selecionada)
    ]

    if df_vendas_filtrado.empty:
        st.info(f"Não há dados de vendas entre {data_inicio_selecionada.strftime('%d/%m/%Y')} e {data_fim_selecionada.strftime('%d/%m/%Y')}.")
        # Para garantir que o gráfico apareça vazio com o range completo, criamos um dataframe com o range e 0 vendas
        all_days_range = pd.date_range(start=data_inicio_selecionada, end=data_fim_selecionada, freq='D')
        vendas_por_dia = pd.DataFrame({'DATA_VENDA': all_days_range, 'Quantidade de Vendas': 0})
        # Converte DATA_VENDA de volta para objeto date se necessário (pd.date_range cria datetime64)
        vendas_por_dia['DATA_VENDA'] = vendas_por_dia['DATA_VENDA'].dt.date

    else:
        # Agrupar por data e contar o número de vendas
        vendas_agrupadas = df_vendas_filtrado.groupby('DATA_VENDA').size().reset_index(name='Quantidade de Vendas')
        
        # Garantir que todos os dias no intervalo selecionado estejam presentes
        # Usa as datas do slider para o range completo
        all_days_range = pd.date_range(start=data_inicio_selecionada, end=data_fim_selecionada, freq='D')
        all_days_df = pd.DataFrame(all_days_range, columns=['DATA_VENDA'])
        all_days_df['DATA_VENDA'] = all_days_df['DATA_VENDA'].dt.date # Converte para objeto date para o merge

        vendas_por_dia = pd.merge(all_days_df, vendas_agrupadas, on='DATA_VENDA', how='left').fillna(0)
        vendas_por_dia = vendas_por_dia.sort_values(by='DATA_VENDA')


    fig_vendas_diarias = px.bar(
        vendas_por_dia,
        x='DATA_VENDA',
        y='Quantidade de Vendas',
        title="Volume de Vendas Diárias",
        labels={'DATA_VENDA': 'Data da Venda', 'Quantidade de Vendas': 'Número de Vendas Fechadas'},
        text_auto=True
    )
    
    fig_vendas_diarias.update_layout(
        xaxis_title="Data da Venda",
        yaxis_title="Número de Vendas Fechadas",
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis_tickangle=-45,
        xaxis = dict(
            tickmode = 'array', # Garante que todos os ticks sejam mostrados se possível
            tickvals = vendas_por_dia['DATA_VENDA'], # Especifica os valores dos ticks
            ticktext = [d.strftime("%d/%m/%Y") for d in vendas_por_dia['DATA_VENDA']] # Formata os labels dos ticks
        )
    )
    fig_vendas_diarias.update_traces(marker_color='#2ca02c', textposition='outside')

    st.plotly_chart(fig_vendas_diarias, use_container_width=True) 