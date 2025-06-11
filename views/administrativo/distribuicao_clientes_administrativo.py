import streamlit as st
import pandas as pd
from datetime import date, timedelta
import plotly.graph_objects as go

def render_universo_section(title, df_universo):
    """
    Renderiza uma seção de análise completa para um 'universo' de dados (ex: C/ Ultrassom).
    Inclui uma tabela de resumo, um gráfico de rosca e um gráfico de barras.
    """
    st.markdown(f"### {title}")

    if df_universo.empty or 'ASSIGNED_BY_NAME' not in df_universo.columns:
        st.info("Não há dados para exibir nesta seção com os filtros selecionados.")
        return

    # --- Lógica do Responsável da Análise ---
    # Para cards em "Ganho", o responsável é o Assistente Jurídico. Para os demais, é o responsável atual.
    df_universo['RESPONSAVEL_ANALISE'] = df_universo['ASSIGNED_BY_NAME']
    condicao_ganho = df_universo['STATUS_ETAPA'] == 'Ganho'
    if 'UF_CRM_ASSISTENTE_JURIDICO' in df_universo.columns:
        # Aplica a lógica, usando o responsável atual como fallback se o campo de assistente estiver vazio
        df_universo.loc[condicao_ganho, 'RESPONSAVEL_ANALISE'] = df_universo.loc[condicao_ganho, 'UF_CRM_ASSISTENTE_JURIDICO'].fillna(df_universo.loc[condicao_ganho, 'ASSIGNED_BY_NAME'])

    # --- Cálculos para o Resumo ---
    # Total recebido no universo
    recebidos = df_universo.groupby('RESPONSAVEL_ANALISE').size().reset_index(name='Quantidade Recebida')
    
    # Total em ganho no universo
    ganhos = df_universo[df_universo['STATUS_ETAPA'] == 'Ganho'].groupby('RESPONSAVEL_ANALISE').size().reset_index(name='Quantidade em Ganho')
    
    # Total em andamento no universo
    andamento = df_universo[df_universo['STATUS_ETAPA'] == 'Em Andamento'].groupby('RESPONSAVEL_ANALISE').size().reset_index(name='Quantidade em Andamento')

    # Juntar os dados
    resumo_df = pd.merge(recebidos, ganhos, on='RESPONSAVEL_ANALISE', how='left')
    resumo_df = pd.merge(resumo_df, andamento, on='RESPONSAVEL_ANALISE', how='left').fillna(0)

    # Converter colunas para inteiro
    resumo_df[['Quantidade em Ganho', 'Quantidade em Andamento']] = resumo_df[['Quantidade em Ganho', 'Quantidade em Andamento']].astype(int)

    # Calcular percentual de ganho
    resumo_df['Percentual de Ganho'] = (resumo_df['Quantidade em Ganho'] / resumo_df['Quantidade Recebida'] * 100).fillna(0)
    resumo_df = resumo_df.rename(columns={'RESPONSAVEL_ANALISE': 'Responsável'})

    # --- Layout da Seção ---
    st.markdown("**Resumo por Responsável**")
    st.dataframe(resumo_df[['Responsável', 'Quantidade Recebida', 'Quantidade em Ganho', 'Percentual de Ganho']].style.format({
        'Percentual de Ganho': '{:.2f}%'
    }).set_properties(**{'text-align': 'center'}), hide_index=True)

    col_rosca, col_barras = st.columns(2)

    with col_rosca:
        # Gráfico de Rosca
        st.markdown("**Distribuição por Responsável**")
        fig_rosca = go.Figure(data=[go.Pie(
            labels=resumo_df['Responsável'], 
            values=resumo_df['Quantidade Recebida'], 
            hole=.4,
            hoverinfo='label+percent+value'
        )])
        fig_rosca.update_layout(showlegend=True, margin=dict(l=0, r=0, t=20, b=20), height=300)
        st.plotly_chart(fig_rosca, use_container_width=True)

    with col_barras:
        # Gráfico de Barras
        st.markdown("**Andamento vs. Ganho por Responsável**")
        fig_barras = go.Figure()
        fig_barras.add_trace(go.Bar(
            x=resumo_df['Responsável'],
            y=resumo_df['Quantidade em Andamento'],
            name='Em Andamento',
            marker_color='gold'
        ))
        fig_barras.add_trace(go.Bar(
            x=resumo_df['Responsável'],
            y=resumo_df['Quantidade em Ganho'],
            name='Ganho',
            marker_color='mediumseagreen'
        ))
        fig_barras.update_layout(barmode='group', margin=dict(l=0, r=0, t=20, b=0), height=300)
        st.plotly_chart(fig_barras, use_container_width=True)


def render_distribuicao_clientes_administrativo(df_distribuicao):
    """
    Renderiza a tela de distribuição de clientes.
    """
    st.subheader("Distribuição de Clientes por Status de Ultrassom e Etapa")

    if df_distribuicao.empty:
        st.warning("Não há dados para exibir.")
        return

    # --- Filtro de Data de Corte (Universo) ---
    st.markdown("#### Filtro de Data de Corte")
    
    creation_date_col = 'DATE_CREATE' if 'DATE_CREATE' in df_distribuicao.columns else 'BEGINDATE'
    
    if creation_date_col in df_distribuicao.columns:
        df_distribuicao[creation_date_col] = pd.to_datetime(df_distribuicao[creation_date_col], errors='coerce').dt.date
        
        data_corte = st.date_input(
            "Mostrar cards criados a partir de:",
            value=date.today(),
            key="data_corte_universo"
        )
        
        # Aplica o filtro de corte principal no início
        df_distribuicao = df_distribuicao[df_distribuicao[creation_date_col] >= data_corte].copy()

        if df_distribuicao.empty:
            st.warning("Nenhum card encontrado a partir da data de corte selecionada.")
            return
    else:
        st.error("Coluna de data de criação ('DATE_CREATE' ou 'BEGINDATE') não encontrada para aplicar o filtro de corte.")
        return

    # --- Lógica de Etapas ---
    def map_etapa_status(stage_id):
        if stage_id == 'C2:EXECUTING':
            return 'Ganho'
        elif stage_id in ['C2:PREPARATION', 'C2:NEW']:
            return 'Em Andamento'
        return 'Outra Etapa'

    if 'STAGE_ID' in df_distribuicao.columns:
        df_distribuicao['STATUS_ETAPA'] = df_distribuicao['STAGE_ID'].astype(str).apply(map_etapa_status)
        status_etapa_options = ['Todos'] + sorted(df_distribuicao['STATUS_ETAPA'].unique().tolist())
    else:
        df_distribuicao['STATUS_ETAPA'] = 'Etapa Indisponível'
        status_etapa_options = ['Todos', 'Etapa Indisponível']

    # --- Filtros Específicos para esta Aba ---
    st.markdown("#### Filtros")

    # Determina qual coluna de data usar (DATE_CREATE ou BEGINDATE como fallback)
    date_col_venda = None
    if 'DATE_CREATE' in df_distribuicao.columns:
        date_col_venda = 'DATE_CREATE'
    elif 'BEGINDATE' in df_distribuicao.columns:
        date_col_venda = 'BEGINDATE'

    # Criar colunas para os filtros
    col1, col2, col3, col4 = st.columns(4)

    # Filtro de Data da Venda (baseado na data encontrada)
    with col1:
        if date_col_venda:
            # Garante que a coluna de data esteja no formato correto
            df_distribuicao[date_col_venda] = pd.to_datetime(df_distribuicao[date_col_venda], errors='coerce').dt.date
            datas_validas = df_distribuicao[date_col_venda].dropna()
            
            if not datas_validas.empty:
                min_date = datas_validas.min()
                max_date = datas_validas.max()
                
                data_venda_inicio = st.date_input(
                    "Data da Venda - Início",
                    value=min_date,
                    min_value=min_date,
                    max_value=max_date,
                    key="dist_data_venda_inicio"
                )
                data_venda_fim = st.date_input(
                    "Data da Venda - Fim",
                    value=max_date,
                    min_value=min_date,
                    max_value=max_date,
                    key="dist_data_venda_fim"
                )
            else:
                 st.info("Não há datas de venda disponíveis.")
                 data_venda_inicio, data_venda_fim = None, None
        else:
            st.warning("Nenhuma coluna de data (DATE_CREATE ou BEGINDATE) encontrada para o filtro.")
            data_venda_inicio, data_venda_fim = None, None

    # Filtro C/ ou S/ Ultrassom (UF_CRM_1742837922053)
    with col2:
        ultrassom_options = ['Todos', 'Com Ultrassom', 'Sem Ultrassom']
        ultrassom_selecionado = st.selectbox(
            "Status Ultrassom",
            options=ultrassom_options,
            key="dist_ultrassom_status"
        )

    # Filtro de Responsáveis
    with col3:
        if 'ASSIGNED_BY_NAME' in df_distribuicao.columns:
            responsaveis_disponiveis = sorted(df_distribuicao['ASSIGNED_BY_NAME'].dropna().unique())
            responsaveis_selecionados = st.multiselect(
                "Responsáveis",
                options=responsaveis_disponiveis,
                default=responsaveis_disponiveis,
                key="dist_responsaveis"
            )
        else:
            responsaveis_selecionados = []
            st.info("Não há responsáveis disponíveis.")

    # Filtro de Etapa
    with col4:
        etapa_selecionada = st.selectbox(
            "Status da Etapa",
            options=status_etapa_options,
            key="dist_etapa_status"
        )

    # --- Aplicação dos Filtros ---
    df_filtrado = df_distribuicao.copy()

    # Aplicar filtro de data de venda (usando a coluna de data encontrada)
    if data_venda_inicio and data_venda_fim and date_col_venda:
        # Garante que a coluna no df_filtrado também seja do tipo date para comparação
        df_filtrado[date_col_venda] = pd.to_datetime(df_filtrado[date_col_venda], errors='coerce').dt.date
        df_filtrado = df_filtrado[
            (df_filtrado[date_col_venda] >= data_venda_inicio) &
            (df_filtrado[date_col_venda] <= data_venda_fim)
        ]

    # Aplicar filtro de ultrassom
    if 'UF_CRM_1742837922053' in df_filtrado.columns:
        # Garante que a coluna seja string para comparação
        df_filtrado['UF_CRM_1742837922053'] = df_filtrado['UF_CRM_1742837922053'].astype(str).str.upper()
        
        if ultrassom_selecionado == 'Com Ultrassom':
            # Verifica tanto o ID ('107') quanto o texto ('SIM')
            df_filtrado = df_filtrado[df_filtrado['UF_CRM_1742837922053'].isin(['107', 'SIM'])]
        elif ultrassom_selecionado == 'Sem Ultrassom':
            # Verifica tanto o ID ('109') quanto o texto ('NÃO', 'NAO')
            df_filtrado = df_filtrado[df_filtrado['UF_CRM_1742837922053'].isin(['109', 'NÃO', 'NAO'])]
    
    # Aplicar filtro de responsáveis
    if responsaveis_selecionados:
        df_filtrado = df_filtrado[df_filtrado['ASSIGNED_BY_NAME'].isin(responsaveis_selecionados)]

    # Aplicar filtro de Etapa
    if etapa_selecionada != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['STATUS_ETAPA'] == etapa_selecionada]

    st.markdown("---")

    # --- Tabela de Distribuição ---
    if df_filtrado.empty:
        st.warning("Nenhum cliente encontrado com os filtros selecionados.")
        return
        
    # Mapeamento de valores para o status do ultrassom
    # Bitrix armazena 'SIM' como ID 107 e 'NÃO' como ID 109 em campos de lista
    map_ultrassom = {
        '107': 'C/ ULTRASSOM',
        'SIM': 'C/ ULTRASSOM',
        '109': 'S/ ULTRASSOM',
        'NÃO': 'S/ ULTRASSOM',
        'NAO': 'S/ ULTRASSOM'
    }
    
    if 'UF_CRM_1742837922053' in df_filtrado.columns:
        df_filtrado['ULTRASSOM_STATUS'] = df_filtrado['UF_CRM_1742837922053'].str.upper().map(map_ultrassom).fillna('Não Especificado')
    else:
        st.error("A coluna 'UF_CRM_1742837922053' do ultrassom não foi encontrada.")
        df_filtrado['ULTRASSOM_STATUS'] = 'Informação Indisponível'

    # Mapeamento do grupo de operadoras
    def map_operadora(row):
        if row['ULTRASSOM_STATUS'] == 'C/ ULTRASSOM':
            return 'Deborah Almeida'
        elif row['ULTRASSOM_STATUS'] == 'S/ ULTRASSOM':
            return 'Ananda Kethlen, Leticia Reis'
        return 'N/A'

    df_filtrado['GRUPO_OPERADORAS'] = df_filtrado.apply(map_operadora, axis=1)

    st.markdown("---")

    # --- Divisão por Universos ---
    df_com_ultrassom = df_filtrado[df_filtrado['ULTRASSOM_STATUS'] == 'C/ ULTRASSOM'].copy()
    df_sem_ultrassom = df_filtrado[df_filtrado['ULTRASSOM_STATUS'] == 'S/ ULTRASSOM'].copy()
    
    # Renderizar seção para C/ Ultrassom
    render_universo_section("Com Ultrassom", df_com_ultrassom)

    st.markdown("---")
    
    # Renderizar seção para S/ Ultrassom
    render_universo_section("Sem Ultrassom", df_sem_ultrassom)

    st.markdown("---")
    
    st.markdown(f"**Total de Clientes Encontrados:** {len(df_filtrado)}")

    # Exibição da tabela principal em um expander
    with st.expander("Visualizar dados detalhados dos clientes"):
        # Exibição da tabela principal
        cols_to_display = [
            'ID',
            'TITLE',
            'ASSIGNED_BY_NAME',
            'STAGE_ID',
            'STATUS_ETAPA',
            'UF_CRM_ASSISTENTE_JURIDICO',
            'UF_CRM_DATA_GANHO_ASSISTENTE_JURIDICO',
            'ULTRASSOM_STATUS',
            'GRUPO_OPERADORAS'
        ]
        
        rename_map = {
            'ID': 'ID do Card',
            'TITLE': 'Título do Negócio',
            'ASSIGNED_BY_NAME': 'Responsável Original',
            'STAGE_ID': 'ID da Etapa',
            'STATUS_ETAPA': 'Status da Etapa',
            'UF_CRM_ASSISTENTE_JURIDICO': 'Assistente Jurídico',
            'UF_CRM_DATA_GANHO_ASSISTENTE_JURIDICO': 'Data Ganho Assistente',
            'ULTRASSOM_STATUS': 'Status Ultrassom',
            'GRUPO_OPERADORAS': 'Grupo de Operadoras Designado'
        }

        if date_col_venda:
            cols_to_display.append(date_col_venda)
            rename_map[date_col_venda] = 'Data da Venda'
        
        # Garante que apenas colunas existentes sejam selecionadas
        cols_to_display_existing = [col for col in cols_to_display if col in df_filtrado.columns]

        st.dataframe(df_filtrado[cols_to_display_existing].rename(columns=rename_map)) 