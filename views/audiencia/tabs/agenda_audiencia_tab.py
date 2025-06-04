import streamlit as st
import pandas as pd
from datetime import datetime

DATA_AUDIENCIA_FIELD = 'UF_CRM_1731693426655' # Campo da Data da Audiência

def display_agenda_audiencia_tab(df_audiencia: pd.DataFrame):
    st.subheader("📅 Agenda de Audiências")

    if df_audiencia.empty or DATA_AUDIENCIA_FIELD not in df_audiencia.columns:
        st.warning(f"Não há dados de audiência ou a coluna '{DATA_AUDIENCIA_FIELD}' não foi encontrada.")
        return

    # Garante que a coluna de data da audiência é do tipo datetime e remove NaT
    df_agenda = df_audiencia.copy()
    df_agenda[DATA_AUDIENCIA_FIELD] = pd.to_datetime(df_agenda[DATA_AUDIENCIA_FIELD], errors='coerce')
    df_agenda.dropna(subset=[DATA_AUDIENCIA_FIELD], inplace=True)

    if df_agenda.empty:
        st.info("Não foram encontradas audiências com datas válidas.")
        return

    # --- Seção 1: Tabela de Totais Mensais com Filtro de Ano ---
    st.markdown("#### Audiências Agrupadas por Mês")
    
    # Filtro de Ano
    anos_disponiveis = sorted(df_agenda[DATA_AUDIENCIA_FIELD].dt.year.unique(), reverse=True)
    if not anos_disponiveis:
        st.info("Nenhum ano disponível para filtro.")
        return

    ano_selecionado = st.selectbox(
        "Selecione o Ano", 
        options=anos_disponiveis, 
        index=0 # Seleciona o ano mais recente por padrão
    )

    df_filtrado_ano = df_agenda[df_agenda[DATA_AUDIENCIA_FIELD].dt.year == ano_selecionado]

    if df_filtrado_ano.empty:
        st.info(f"Nenhuma audiência encontrada para o ano de {ano_selecionado}.")
    else:
        # Agrupar por mês e contar audiências
        df_filtrado_ano['Mês Num'] = df_filtrado_ano[DATA_AUDIENCIA_FIELD].dt.month
        # df_filtrado_ano['Mês'] = df_filtrado_ano[DATA_AUDIENCIA_FIELD].dt.strftime('%B') # Nome do mês por extenso - original

        # Mapeamento para nomes dos meses em português
        mapa_meses_pt = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
        }
        df_filtrado_ano['Mês'] = df_filtrado_ano['Mês Num'].map(mapa_meses_pt)
        
        audiencias_por_mes = df_filtrado_ano.groupby(['Mês Num', 'Mês']).size().reset_index(name='Total de Audiências')
        audiencias_por_mes = audiencias_por_mes.sort_values(by='Mês Num')
        audiencias_por_mes_display = audiencias_por_mes[['Mês', 'Total de Audiências']]
        
        st.table(audiencias_por_mes_display.set_index('Mês'))

    # --- Seção 2: Visualização Detalhada (Estilo Calendário/Agenda) ---
    st.markdown("--- ") # Separador
    st.markdown("#### Detalhes das Audiências (por Data)")

    # Ordenar pela data da audiência mais recente primeiro, ou mais antiga - a decidir
    df_agenda_sorted = df_agenda.sort_values(by=DATA_AUDIENCIA_FIELD, ascending=True)

    # Selecionar colunas relevantes para exibição
    colunas_exibir = [
        DATA_AUDIENCIA_FIELD,
        'TITLE', # Título do Deal/Processo
        'STAGE_NAME', # Etapa atual
        'ASSIGNED_BY_NAME' # Responsável
    ]
    # Adicionar outras colunas se existirem e forem úteis, ex: 'COMPANY_TITLE' ou 'CONTACT_NAME'
    # if 'COMPANY_TITLE' in df_agenda_sorted.columns: colunas_exibir.append('COMPANY_TITLE')

    df_display_agenda = df_agenda_sorted[[col for col in colunas_exibir if col in df_agenda_sorted.columns]].copy()
    
    # Formatar a data para exibição
    df_display_agenda[DATA_AUDIENCIA_FIELD] = df_display_agenda[DATA_AUDIENCIA_FIELD].dt.strftime('%d/%m/%Y')
    df_display_agenda.rename(columns={
        DATA_AUDIENCIA_FIELD: 'Data da Audiência',
        'TITLE': 'Processo/Deal',
        'STAGE_NAME': 'Etapa Atual',
        'ASSIGNED_BY_NAME': 'Responsável'
    }, inplace=True)

    if df_display_agenda.empty:
        st.info("Não há detalhes de audiências para exibir.")
    else:
        st.dataframe(df_display_agenda, height=600, use_container_width=True)

    # TODO: Adicionar mais interatividade ou visualizações se necessário,
    # como um calendário visual real (se uma biblioteca for permitida no futuro)
    # ou agrupar por semana, etc. 