import streamlit as st
import locale
from decimal import Decimal
from src.google_sheets_service import GoogleSheetsService, carregar_dados
from src.finance_analyzer import analyse_data, clean_currency, format_parcela_display, analyze_parcelas
import pandas as pd
import plotly.express as px

def autenticar_usuario():
    """Função para autenticação do usuário."""
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        senha = st.text_input("Digite a senha para acessar o relatório financeiro:", type="password")
        if senha == st.secrets["financeiro"]["password"]:
            st.session_state.autenticado = True
        else:
            return False
    return True

def calcular_metricas_medias(df_analisado):
    """Calcula as métricas médias para um DataFrame."""
    total_clientes = len(df_analisado)
    if total_clientes == 0:
        return {
            'acordo_medio': Decimal('0'),
            'honorarios_medio': Decimal('0'),
            'valor_medio_parcela': Decimal('0'),
            'media_parcelas': 0
        }

    # Acordo médio por cliente
    acordo_medio = df_analisado['VALOR_ACORDO_NUM'].sum() / total_clientes

    # Honorários médio por cliente
    honorarios_medio = df_analisado['HONORARIOS_NUM'].sum() / total_clientes

    # Cálculo das métricas de parcelas
    total_parcelas = 0
    soma_valores_parcelas = Decimal('0')
    total_valores_validos = 0

    for _, row in df_analisado.iterrows():
        if isinstance(row['ANALISE_PARCELAS'], list):
            num_parcelas = len(row['ANALISE_PARCELAS'])
            total_parcelas += num_parcelas
            
            # Soma os valores das parcelas quando são decimais
            for parcela in row['ANALISE_PARCELAS']:
                if isinstance(parcela['valor'], Decimal):
                    soma_valores_parcelas += parcela['valor']
                    total_valores_validos += 1

    # Média de parcelas por acordo
    media_parcelas = total_parcelas / total_clientes if total_clientes > 0 else 0

    # Valor médio por parcela
    valor_medio_parcela = soma_valores_parcelas / total_valores_validos if total_valores_validos > 0 else Decimal('0')

    return {
        'acordo_medio': acordo_medio,
        'honorarios_medio': honorarios_medio,
        'valor_medio_parcela': valor_medio_parcela,
        'media_parcelas': media_parcelas
    }

def exibir_parcelas(parcelas):
    """Formata as parcelas para exibição na tabela."""
    if isinstance(parcelas, list):
        parcelas_analisadas = [format_parcela_display(p) for p in parcelas]
        return "\n".join(parcelas_analisadas)
    return str(parcelas)

def render_relatorio_financeiro():
    """Renderiza a página completa do relatório financeiro."""
    st.title("Relatório Financeiro")
    
    # Autenticação
    if not autenticar_usuario():
        st.info("A página será carregada após a inserção da senha correta.")
        return
    
    try:
        # Configura a localidade para moeda brasileira
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        
        # Carregar dados
        df = carregar_dados()
        if df is None or df.empty:
            st.error("Não foi possível carregar os dados. Verifique a conexão com o Google Sheets.")
            return
            
        # Análise dos dados
        resultado = analyse_data(df)
        df = resultado["dataframe"]  # Usar o DataFrame processado
        
        # Exibir métricas globais
        st.header("Totais Globais")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total de Acordos", len(df))
        
        with col2:
            st.metric("Valor Total dos Acordos", f"R$ {resultado['total_acordos']:,.2f}")
        
        with col3:
            if 'ANALISE_PARCELAS' in df.columns:
                total_parcelas = sum(len(p) if isinstance(p, list) else 0 for p in df['ANALISE_PARCELAS'])
            else:
                total_parcelas = 0
            st.metric("Total de Parcelas", total_parcelas)
        
        with col4:
            st.metric("Total de Honorários", f"R$ {resultado['total_honorarios']:,.2f}")
        
        with col5:
            total_repasse = resultado['total_acordos'] - resultado['total_honorarios']
            st.metric("Total de Repasse", f"R$ {total_repasse:,.2f}")
        
        # Exibir métricas de médias
        st.header("Médias")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            media_acordo = resultado['total_acordos'] / len(df) if len(df) > 0 else 0
            st.metric("Média por Acordo", f"R$ {media_acordo:,.2f}")
        
        with col2:
            media_honorarios = resultado['total_honorarios'] / len(df) if len(df) > 0 else 0
            st.metric("Média de Honorários", f"R$ {media_honorarios:,.2f}")
        
        with col3:
            media_parcelas = total_parcelas / len(df) if len(df) > 0 else 0
            st.metric("Média de Parcelas", f"{media_parcelas:.1f}")
        
        with col4:
            media_valor_parcela = resultado['total_acordos'] / total_parcelas if total_parcelas > 0 else 0
            st.metric("Média por Parcela", f"R$ {media_valor_parcela:,.2f}")

        # Tabela consolidada por mês
        st.header("Consolidado por Mês")
        
        # Criar DataFrame consolidado
        meses = sorted(df['MÊS'].unique())
        dados_consolidados = []
        
        for mes in meses:
            df_mes = df[df['MÊS'] == mes]
            valor_total = df_mes['VALOR_ACORDO_NUM'].sum()
            honorarios = df_mes['HONORARIOS_NUM'].sum()
            
            if 'ANALISE_PARCELAS' in df_mes.columns:
                parcelas = sum(len(p) if isinstance(p, list) else 0 for p in df_mes['ANALISE_PARCELAS'])
            else:
                parcelas = 0
            
            dados_consolidados.append({
                'Mês': mes,
                'Quantidade de Acordos': len(df_mes),
                'Valor Total dos Acordos': valor_total,
                'Valor Total dos Honorários': honorarios,
                'Total de Parcelas': parcelas,
                'Média por Acordo': valor_total / len(df_mes) if len(df_mes) > 0 else 0,
                'Média de Honorários': honorarios / len(df_mes) if len(df_mes) > 0 else 0,
                'Média de Parcelas': parcelas / len(df_mes) if len(df_mes) > 0 else 0
            })
        
        df_consolidado = pd.DataFrame(dados_consolidados)
        
        # Formatar valores monetários
        for col in ['Valor Total dos Acordos', 'Valor Total dos Honorários', 'Média por Acordo', 'Média de Honorários']:
            df_consolidado[col] = df_consolidado[col].apply(lambda x: f"R$ {x:,.2f}")
        
        # Formatar médias de parcelas
        df_consolidado['Média de Parcelas'] = df_consolidado['Média de Parcelas'].apply(lambda x: f"{x:.1f}")
        
        # Exibir tabela consolidada
        st.dataframe(df_consolidado, use_container_width=True)
        
        # --- NOVA SEÇÃO: PREVISÃO DE RECEBIMENTOS ---
        st.header("Previsão de Recebimento de Honorários")
        
        recebimentos_futuros = []
        if 'ANALISE_PARCELAS' in df.columns:
            for _, row in df.iterrows():
                parcelas = row['ANALISE_PARCELAS']
                if isinstance(parcelas, list):
                    for p in parcelas:
                        if p.get('status') == 'Pendente' and p.get('data_vencimento'):
                            # Correção para lidar com valores de honorários que podem ser None
                            valor_honorarios = p.get('valor_honorarios') or 0
                            valor_honorarios_adicionais = p.get('valor_honorarios_adicionais', [])
                            total_honorarios = valor_honorarios + sum(valor_honorarios_adicionais)
                            
                            recebimentos_futuros.append({
                                'Data Vencimento': p['data_vencimento'],
                                'Valor da Parcela': p.get('valor_acordo', 0),
                                'Valor Honorários': total_honorarios,
                                'Valor Repasse': p.get('valor_liquido', 0)
                            })
        
        if recebimentos_futuros:
            df_recebiveis = pd.DataFrame(recebimentos_futuros)
            df_recebiveis['Data Vencimento'] = pd.to_datetime(df_recebiveis['Data Vencimento'])
            df_recebiveis['Mês/Ano'] = df_recebiveis['Data Vencimento'].dt.to_period('M')
            
            df_previsao = df_recebiveis.groupby('Mês/Ano').agg({
                'Valor da Parcela': 'sum',
                'Valor Honorários': 'sum',
                'Valor Repasse': 'sum'
            }).reset_index()
            
            df_previsao = df_previsao.sort_values('Mês/Ano')
            df_previsao['Mês/Ano'] = df_previsao['Mês/Ano'].dt.strftime('%B/%Y').str.capitalize()

            # Formatar para exibição
            df_previsao_display = df_previsao.copy()
            for col in ['Valor da Parcela', 'Valor Honorários', 'Valor Repasse']:
                df_previsao_display[col] = df_previsao_display[col].apply(lambda x: f"R$ {x:,.2f}")
            
            st.dataframe(df_previsao_display, use_container_width=True)

            # Gráfico de Previsão
            fig_previsao = px.bar(
                df_previsao,
                x='Mês/Ano',
                y='Valor Honorários',
                title='Previsão de Honorários a Receber por Mês',
                text_auto='.2s' # Formata o texto no topo da barra
            )
            fig_previsao.update_traces(textposition='outside')
            st.plotly_chart(fig_previsao, use_container_width=True)

        else:
            st.info("Não há recebimentos futuros pendentes.")
        
        # Gráfico de barras para quantidade de acordos por mês
        st.header("Quantidade de Acordos por Mês")
        fig = px.bar(
            df_consolidado,
            x='Mês',
            y='Quantidade de Acordos',
            title='Quantidade de Acordos por Mês'
        )
        fig.update_layout(
            xaxis_title='Mês',
            yaxis_title='Quantidade de Acordos'
        )
        # Adiciona o texto com os valores no topo das barras
        fig.update_traces(
            texttemplate='%{y}',
            textposition='outside',
            textfont=dict(size=14)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Análise por mês
        st.header("Análise por Mês")
        
        # Criar tabs para cada mês
        tabs = st.tabs([mes for mes in meses])
        
        for tab, mes in zip(tabs, meses):
            with tab:
                df_mes = df[df['MÊS'] == mes]
                
                # Métricas do mês
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.metric("Acordos", len(df_mes))
                
                with col2:
                    valor_mes = df_mes['VALOR_ACORDO_NUM'].sum()
                    st.metric("Valor Total", f"R$ {valor_mes:,.2f}")
                
                with col3:
                    if 'ANALISE_PARCELAS' in df_mes.columns:
                        parcelas_mes = sum(len(p) if isinstance(p, list) else 0 for p in df_mes['ANALISE_PARCELAS'])
                    else:
                        parcelas_mes = 0
                    st.metric("Parcelas", parcelas_mes)
                
                with col4:
                    honorarios_mes = df_mes['HONORARIOS_NUM'].sum()
                    st.metric("Honorários", f"R$ {honorarios_mes:,.2f}")
                
                with col5:
                    repasse_mes = valor_mes - honorarios_mes
                    st.metric("Repasse", f"R$ {repasse_mes:,.2f}")
                
                # Médias do mês
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    media_acordo_mes = valor_mes / len(df_mes) if len(df_mes) > 0 else 0
                    st.metric("Média por Acordo", f"R$ {media_acordo_mes:,.2f}")
                
                with col2:
                    media_honorarios_mes = honorarios_mes / len(df_mes) if len(df_mes) > 0 else 0
                    st.metric("Média de Honorários", f"R$ {media_honorarios_mes:,.2f}")
                
                with col3:
                    media_parcelas_mes = parcelas_mes / len(df_mes) if len(df_mes) > 0 else 0
                    st.metric("Média de Parcelas", f"{media_parcelas_mes:.1f}")
                
                with col4:
                    media_valor_parcela_mes = valor_mes / parcelas_mes if parcelas_mes > 0 else 0
                    st.metric("Média por Parcela", f"R$ {media_valor_parcela_mes:,.2f}")
                
                # Tabela de acordos do mês
                st.subheader("Detalhamento dos Acordos")
                df_exibir = df_mes[['CPF', 'NOME', 'VALOR DO ACORDO', 'HONORÁRIOS (30%)', 'PARCELAS DESCRITIVAS']].copy()
                if 'ANALISE_PARCELAS' in df_mes.columns:
                    df_exibir['PARCELAS DESCRITIVAS'] = df_exibir['PARCELAS DESCRITIVAS'].apply(exibir_parcelas)
                st.dataframe(df_exibir, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erro ao processar os dados: {str(e)}")
        st.error("Detalhes do erro:")
        st.exception(e) 