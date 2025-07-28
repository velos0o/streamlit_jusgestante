"""
Relatório do Funil de Entrevista
Análise de aproveitamento e Vendas de Processos G7.
"""

import streamlit as st
from datetime import date, timedelta
import sys
import os
import pandas as pd
from datetime import datetime

# Adiciona src e config ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'config'))

from src.data_service import DataService
from views.entrevista.analise_responsaveis_entrevista import render_analise_responsaveis_entrevista
from views.entrevista.vendas_g7_tab import render_vendas_g7_tab, get_cached_g7_data, get_g7_deals_for_sync_check

def _render_persistent_alert_popup(count: int):
    """Renderiza um pop-up de alerta fixo e animado, saindo da borda da tela."""
    
    alert_html = f"""
    <style>
        @keyframes pulse-red-strong {{
            0% {{ box-shadow: -5px 5px 15px -3px rgba(0,0,0,0.3); }}
            70% {{ box-shadow: -5px 5px 30px 5px rgba(255, 82, 82, 0.9); }} /* Brilho vermelho mais forte */
            100% {{ box-shadow: -5px 5px 15px -3px rgba(0,0,0,0.3); }}
        }}
        .edge-alert {{
            position: fixed;
            top: 100px;
            right: 0; /* Colado na borda direita */
            padding: 1rem 1.5rem 1rem 2rem; /* Mais padding à esquerda */
            border-top-left-radius: 0.5rem;
            border-bottom-left-radius: 0.5rem;
            border-top-right-radius: 0; /* Canto reto na borda */
            border-bottom-right-radius: 0; /* Canto reto na borda */
            background-color: #ff5252; /* Fundo vermelho */
            color: white;
            font-weight: normal; /* Texto "Vendas Paradas" com peso normal */
            text-align: center;
            box-shadow: -5px 5px 15px -3px rgba(0,0,0,0.3);
            animation: pulse-red-strong 2s infinite;
            z-index: 9999;
        }}
        .edge-alert .count {{
            color: white; /* Número branco */
            font-size: 2.5rem;
            font-weight: 900; /* Número em negrito forte */
            display: block;
            line-height: 1;
        }}
    </style>
    <div class="edge-alert">
        <span class="count">{count}</span>
        Vendas Paradas
    </div>
    """
    st.markdown(alert_html, unsafe_allow_html=True)

def _format_time_delta(delta):
    """Formata o tempo parado em horas ou dias."""
    hours = delta.total_seconds() / 3600
    if hours < 24:
        return f"{int(hours)} horas"
    else:
        days = delta.days
        return f"{days} dias"

def _render_sincronizacao_alerta(df_entrevista: pd.DataFrame):
    """Verifica e exibe um alerta se houver vendas na G7 não sincronizadas no funil de entrevista."""
    st.subheader("Sincronização de Vendas (G7 vs. JusGestante)")

    try:
        df_g7 = get_cached_g7_data()

        if df_g7.empty:
            st.info("Nenhum dado de vendas encontrado na G7 para verificação.")
            return
            
        if 'UF_CRM_ID_G7' not in df_entrevista.columns:
            st.warning("Coluna 'UF_CRM_ID_G7' não encontrada nos dados da entrevista. Não é possível verificar a sincronização.")
            return

        # Limpeza "forense" dos IDs para garantir uma comparação robusta
        # Remove espaços, converte para string, e lida com formatos como '12345.0'
        
        # Limpa IDs da G7
        cleaned_g7_ids = df_g7['ID'].astype(str).str.strip().str.split('.').str[0]
        ids_g7 = set(cleaned_g7_ids[cleaned_g7_ids.str.len() > 0])

        # Limpa IDs da JusGestante
        cleaned_jusgestante_ids = df_entrevista['UF_CRM_ID_G7'].dropna().astype(str).str.strip().str.split('.').str[0]
        ids_jusgestante_link = set(cleaned_jusgestante_ids[cleaned_jusgestante_ids.str.len() > 0])
        
        g7_ids_not_in_jusgestante = ids_g7 - ids_jusgestante_link

        if not g7_ids_not_in_jusgestante:
            st.markdown("""
            <div style="background-color: #E8F5E9; color: #1B5E20; padding: 1rem; border-radius: 0.5rem; border-left: 6px solid #4CAF50; display: flex; align-items: center; margin-top: 1rem; margin-bottom: 1rem;">
                <span style="font-size: 1.5rem; margin-right: 1rem;">✅</span>
                <div>
                    <h5 style="margin: 0; padding: 0; color: #1B5E20; font-weight: bold;">Tudo Certo!</h5>
                    <p style="margin: 0; padding: 0; color: #1B5E20;">Nenhuma pendência de sincronização encontrada.</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            total_divergencias = len(g7_ids_not_in_jusgestante)
            divergencias_df = df_g7[df_g7['ID'].astype(str).isin(g7_ids_not_in_jusgestante)].copy()

            # Calcula o tempo parado (horas/dias) usando o novo campo de data
            oldest_time_str = "N/A"
            if 'UF_CRM_DEAL_ENVIADA_PROCESS' in divergencias_df.columns:
                # Ajusta o fuso horário (-6 horas) ao converter para datetime
                divergencias_df['FECHAMENTO_DT'] = pd.to_datetime(divergencias_df['UF_CRM_DEAL_ENVIADA_PROCESS'], errors='coerce')
                if not divergencias_df['FECHAMENTO_DT'].isna().all():
                    divergencias_df['FECHAMENTO_DT'] = divergencias_df['FECHAMENTO_DT'] - pd.Timedelta(hours=6)
                
                # Calcula o tempo parado para cada linha
                now = datetime.now()
                divergencias_df['TEMPO_PARADO_DELTA'] = divergencias_df['FECHAMENTO_DT'].apply(lambda x: now - x if pd.notna(x) else pd.Timedelta(seconds=0))
                divergencias_df['TEMPO_PARADO'] = divergencias_df['TEMPO_PARADO_DELTA'].apply(_format_time_delta)

                # Encontra a divergência mais antiga para o alerta
                data_mais_antiga = divergencias_df['FECHAMENTO_DT'].min()
                if pd.notna(data_mais_antiga):
                    oldest_time_str = _format_time_delta(now - data_mais_antiga)
            else:
                divergencias_df['TEMPO_PARADO'] = "N/A"

            # Exibe o pop-up de alerta fixo
            _render_persistent_alert_popup(total_divergencias)
            
            # Mensagens dinâmicas
            texto_tempo = f"e estão sem atendimento há até {oldest_time_str}." if oldest_time_str != "N/A" else "e precisam ser sincronizadas."
            titulo_alerta = f"⚠️ Alerta: {total_divergencias} Vendas da G7 não foram enviadas para o Funil de Entrevista {texto_tempo}"
            texto_ajuda = "A lista abaixo mostra os negócios da G7 que foram movidos para a etapa de formalização e precisam ser criados no funil de Entrevista. A coluna 'Tempo Parado' indica há quanto tempo o negócio foi movido."

            with st.expander(titulo_alerta, expanded=True):
                st.markdown(texto_ajuda)
                
                # Prepara o DataFrame para exibição
                colunas_para_exibir = ['ID', 'TITLE', 'ASSIGNED_BY', 'TEMPO_PARADO']
                rename_map = {
                    'ID': 'ID do Card (G7)', 
                    'TITLE': 'Nome do Negócio', 
                    'ASSIGNED_BY': 'Responsável',
                    'TEMPO_PARADO': 'Tempo Parado'
                }

                st.dataframe(
                    divergencias_df[colunas_para_exibir].rename(columns=rename_map),
                    use_container_width=True,
                    hide_index=True
                )

    except Exception as e:
        st.error(f"Ocorreu um erro ao verificar a sincronização: {e}")


def _render_sincronizacao_jusgestante_para_g7_alerta(df_entrevista: pd.DataFrame):
    """
    Verifica se negócios marcados para finalização ou como perdidos na JusGestante 
    existem e estão ativos (não estão na etapa 'UC_IV0DI0') na G7.
    """
    st.subheader("Sincronização JusGestante -> G7 (Status de Negócios)")

    try:
        # 1. Filtrar negócios na JusGestante que devem ser finalizados ou que foram perdidos
        stages_to_check = ['C11:UC_VDDDMG', 'C11:LOSE']
        df_a_verificar = df_entrevista[df_entrevista['STAGE_ID'].isin(stages_to_check)].copy()

        if 'UF_CRM_ID_G7' not in df_a_verificar.columns:
            st.warning("Coluna 'UF_CRM_ID_G7' não encontrada. Não é possível verificar a finalização.")
            # Movemos a verificação de df vazio para depois, para que a seção de debug sempre apareça
            # se houver a coluna necessária.
        
        # 2. Buscar os negócios válidos da G7 (todos, exceto etapa 'UC_IV0DI0')
        df_g7_valid = get_g7_deals_for_sync_check()
        ids_g7_valid = set(df_g7_valid['ID'].astype(str).str.strip()) if not df_g7_valid.empty else set()
        
        if df_a_verificar.empty:
            st.info("Nenhum negócio aguardando finalização ou perdido para verificar no momento.")
            return

        # 3. Identificar os que estão pendentes
        df_a_verificar['UF_CRM_ID_G7_CLEAN'] = df_a_verificar['UF_CRM_ID_G7'].dropna().astype(str).str.strip().str.split('.').str[0]
        
        pendentes_mask = ~df_a_verificar['UF_CRM_ID_G7_CLEAN'].isin(ids_g7_valid)
        df_pendentes = df_a_verificar[pendentes_mask]

        # 4. Exibir o resultado
        if df_pendentes.empty:
            st.markdown("""
            <div style="background-color: #E8F5E9; color: #1B5E20; padding: 1rem; border-radius: 0.5rem; border-left: 6px solid #4CAF50; display: flex; align-items: center; margin-top: 1rem; margin-bottom: 1rem;">
                <span style="font-size: 1.5rem; margin-right: 1rem;">✅</span>
                <div>
                    <h5 style="margin: 0; padding: 0; color: #1B5E20; font-weight: bold;">Sincronização em Dia!</h5>
                    <p style="margin: 0; padding: 0; color: #1B5E20;">Todos os negócios que saíram do funil de Entrevista estão com status válido na G7.</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            total_pendencias = len(df_pendentes)
            titulo_alerta = f"⚠️ Alerta: {total_pendencias} Negócios com status inconsistente na G7"
            texto_ajuda = "A lista abaixo mostra negócios que estão 'Perdidos' ou 'Aguardando Assinatura' na JusGestante, mas não foram encontrados ou estão em uma etapa de exclusão ('UC_IV0DI0') na G7."

            with st.expander(titulo_alerta, expanded=True):
                st.markdown(texto_ajuda)
                
                colunas_para_exibir = ['TITLE', 'ASSIGNED_BY_NAME', 'STAGE_ID', 'UF_CRM_ID_G7']
                rename_map = {
                    'TITLE': 'Nome do Negócio', 
                    'ASSIGNED_BY_NAME': 'Responsável (JusGestante)',
                    'STAGE_ID': 'Etapa (JusGestante)',
                    'UF_CRM_ID_G7': 'ID do Card (G7)'
                }

                st.dataframe(
                    df_pendentes[colunas_para_exibir].rename(columns=rename_map),
                    use_container_width=True,
                    hide_index=True
                )

    except Exception as e:
        st.error(f"Ocorreu um erro ao verificar a sincronização para a G7: {e}")


def render_relatorio_entrevista():
    """Renderiza um relatório consolidado com a análise de desempenho, as vendas da G7 e a análise de validação."""
    st.title("Relatório de Entrevista")

    data_service = DataService()

    # --- Carregamento de Dados para Sincronização (SEM FILTROS) ---
    df_entrevista_sync = None
    with st.spinner("Verificando sincronização de dados..."):
        try:
            # Carrega todos os dados do funil de entrevista para garantir que a sincronização seja completa
            df_entrevista_sync = data_service.get_entrevista_data(start_date=None, end_date=None)
        except Exception as e:
            st.error(f"Falha ao carregar dados para a verificação de sincronização: {e}")
            # O relatório continua, mas as seções de sincronização podem não aparecer.

    # --- Filtros de Data e Responsável (para análises de desempenho) ---
    with st.expander("🔍 Filtros (Análise de Desempenho)", expanded=True):
        st.markdown("📅 **Data de Criação:**")
        col1, col2 = st.columns(2)
        with col1:
            data_criacao_inicio = st.date_input("Início", value=date.today() - timedelta(days=90), key="entrevista_data_criacao_inicio")
        with col2:
            data_criacao_fim = st.date_input("Fim", value=date.today(), key="entrevista_data_criacao_fim")
        
        aplicar_filtro_data_criacao = st.checkbox("Aplicar filtro por Data de Criação", value=False, key="entrevista_aplicar_filtro_data_criacao")

    # --- Carregamento de Dados para Análise (com filtros) ---
    df_entrevista_analise = None
    with st.spinner("Carregando dados da análise de desempenho..."):
        try:
            if aplicar_filtro_data_criacao:
                df_entrevista_analise = data_service.get_entrevista_data(data_criacao_inicio, data_criacao_fim)
            else:
                # Se o filtro não for aplicado, usamos os dados já carregados para a sincronização
                df_entrevista_analise = df_entrevista_sync
        except Exception as e:
            st.error(f"Ocorreu um erro ao carregar os dados para análise: {e}")
            st.stop()
            
    if df_entrevista_analise is None or df_entrevista_analise.empty:
        st.warning("Nenhum dado encontrado para o período selecionado.")
        # Não paramos o relatório aqui para permitir que a seção de sincronia ainda seja exibida
    
    # --- Seção de Alerta de Sincronização (usa dados NÃO filtrados) ---
    if df_entrevista_sync is not None:
        _render_sincronizacao_alerta(df_entrevista_sync)
        st.markdown("---") # Divisor
        _render_sincronizacao_jusgestante_para_g7_alerta(df_entrevista_sync)
    else:
        st.info("Não foi possível carregar os dados para a verificação de sincronização.")

    # --- Seções de Análise (usam dados FILTRADOS) ---
    if df_entrevista_analise is not None and not df_entrevista_analise.empty:
        st.markdown("---")
        st.subheader("Análise de Desempenho (Funil de Entrevista)")
        _render_analise_desempenho(df_entrevista_analise)

        st.markdown("---")
        render_vendas_g7_tab()
        
        st.markdown("---")
        _render_analise_validacao(df_entrevista_analise)
    else:
        st.markdown("---")
        st.warning("Nenhum dado de análise para exibir com os filtros atuais.")


def _render_analise_desempenho(df_entrevista: pd.DataFrame):
    """Renderiza a seção de análise de desempenho do funil de entrevista."""
    render_analise_responsaveis_entrevista(df_entrevista)


def _render_analise_validacao(df_entrevista: pd.DataFrame):
    """Renderiza a seção de análise de clientes convertidos (validados)."""
    st.subheader("Análise de Validação (Clientes Convertidos)")

    if 'UF_CRM_VALIDADO_DATA' not in df_entrevista.columns or df_entrevista['UF_CRM_VALIDADO_DATA'].isnull().all():
        st.warning("A coluna 'UF_CRM_VALIDADO_DATA' não foi encontrada ou está vazia. A análise de validação não pode ser exibida.")
        return

    # Filtro de data específico para esta tabela
    st.markdown("📅 **Filtro por Data de Validação:**")
    
    valid_dates = df_entrevista['UF_CRM_VALIDADO_DATA'].dropna()

    col_val_1, col_val_2 = st.columns(2)
    with col_val_1:
        data_validacao_inicio = st.date_input(
            "Início",
            value=valid_dates.min() if not valid_dates.empty else date.today() - timedelta(days=30),
            key="entrevista_data_validacao_inicio"
        )
    with col_val_2:
        data_validacao_fim = st.date_input(
            "Fim",
            value=valid_dates.max() if not valid_dates.empty else date.today(),
            key="entrevista_data_validacao_fim"
        )
    
    aplicar_filtro_validacao = st.checkbox(
        "Aplicar filtro por Data de Validação",
        value=True,  # Alterado para True para filtrar por padrão
        key="entrevista_aplicar_filtro_validacao"
    )

    df_validados = df_entrevista[df_entrevista['STAGE_ID'] == 'C11:WON'].copy()

    if aplicar_filtro_validacao:
        df_filtrado_val = df_validados.dropna(subset=['UF_CRM_VALIDADO_DATA'])
        if not df_filtrado_val.empty:
            # Garante que a data no dataframe é um objeto date para comparação
            # Ajusta o fuso horário (-6 horas) ao converter para datetime
            df_filtrado_val['UF_CRM_VALIDADO_DATA'] = pd.to_datetime(df_filtrado_val['UF_CRM_VALIDADO_DATA'], errors='coerce')
            if not df_filtrado_val['UF_CRM_VALIDADO_DATA'].isna().all():
                df_filtrado_val['UF_CRM_VALIDADO_DATA'] = df_filtrado_val['UF_CRM_VALIDADO_DATA'] - pd.Timedelta(hours=6)
            df_filtrado_val['UF_CRM_VALIDADO_DATA_DATE'] = df_filtrado_val['UF_CRM_VALIDADO_DATA'].dt.date
            df_validados = df_filtrado_val[
                (df_filtrado_val['UF_CRM_VALIDADO_DATA_DATE'] >= data_validacao_inicio) &
                (df_filtrado_val['UF_CRM_VALIDADO_DATA_DATE'] <= data_validacao_fim)
            ]

    if df_validados.empty:
        st.info("Nenhum cliente convertido (validado) encontrado com os filtros selecionados.")
    else:
        st.markdown("##### Total de Clientes Validados por Responsável")
        
        tabela_validados = df_validados.groupby('ASSIGNED_BY_NAME').agg(
            TOTAL_VALIDADOS=('ID', 'count')
        ).reset_index().rename(columns={'ASSIGNED_BY_NAME': 'Responsável'})

        tabela_validados = tabela_validados.sort_values(by='TOTAL_VALIDADOS', ascending=False)
        
        st.dataframe(tabela_validados, use_container_width=True, hide_index=True) 