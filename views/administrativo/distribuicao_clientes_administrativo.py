import streamlit as st
import pandas as pd
from datetime import date, timedelta

def render_distribuicao_clientes_administrativo(df_distribuicao):
    """
    Renderiza a tela de distribuição de clientes.
    """
    st.subheader("Distribuição de Clientes por Status de Ultrassom")

    if df_distribuicao.empty:
        st.warning("Não há dados para exibir.")
        return

    # --- Filtros Específicos para esta Aba ---
    st.markdown("#### Filtros")

    # Determina qual coluna de data usar (DATE_CREATE ou BEGINDATE como fallback)
    date_col_venda = None
    if 'DATE_CREATE' in df_distribuicao.columns:
        date_col_venda = 'DATE_CREATE'
    elif 'BEGINDATE' in df_distribuicao.columns:
        date_col_venda = 'BEGINDATE'

    # Criar colunas para os filtros
    col1, col2, col3 = st.columns(3)

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

    st.markdown(f"**Total de Clientes Encontrados:** {len(df_filtrado)}")

    # Exibição da tabela
    cols_to_display = [
        'ID',
        'TITLE',
        'ASSIGNED_BY_NAME',
        'ULTRASSOM_STATUS',
        'GRUPO_OPERADORAS'
    ]
    
    rename_map = {
        'ID': 'ID do Card',
        'TITLE': 'Título do Negócio',
        'ASSIGNED_BY_NAME': 'Responsável Original',
        'ULTRASSOM_STATUS': 'Status Ultrassom',
        'GRUPO_OPERADORAS': 'Grupo de Operadoras Designado'
    }

    if date_col_venda:
        cols_to_display.append(date_col_venda)
        rename_map[date_col_venda] = 'Data da Venda'
    
    # Garante que apenas colunas existentes sejam selecionadas
    cols_to_display_existing = [col for col in cols_to_display if col in df_filtrado.columns]

    st.dataframe(df_filtrado[cols_to_display_existing].rename(columns=rename_map))

    # --- Contagens Separadas ---
    st.markdown("#### Contagem por Grupo e Responsável")

    # Tabela para C/ ULTRASSOM
    st.markdown("**Com Ultrassom**")
    df_com_ultrassom = df_filtrado[df_filtrado['ULTRASSOM_STATUS'] == 'C/ ULTRASSOM']
    if not df_com_ultrassom.empty:
        contagem_com_ultrassom = df_com_ultrassom.groupby('ASSIGNED_BY_NAME').size().reset_index(name='Quantidade')
        st.table(contagem_com_ultrassom)
    else:
        st.info("Nenhum cliente 'Com Ultrassom' encontrado para os filtros selecionados.")

    # Tabela para S/ ULTRASSOM
    st.markdown("**Sem Ultrassom**")
    df_sem_ultrassom = df_filtrado[df_filtrado['ULTRASSOM_STATUS'] == 'S/ ULTRASSOM']
    if not df_sem_ultrassom.empty:
        contagem_sem_ultrassom = df_sem_ultrassom.groupby('ASSIGNED_BY_NAME').size().reset_index(name='Quantidade')
        st.table(contagem_sem_ultrassom)
    else:
        st.info("Nenhum cliente 'Sem Ultrassom' encontrado para os filtros selecionados.") 