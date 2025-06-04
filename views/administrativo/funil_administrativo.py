import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def render_funil_administrativo(df: pd.DataFrame, etapas_ordem: list):
    st.subheader("Visão do Funil de Trâmites Administrativos")

    if df.empty:
        st.warning("Não há dados para exibir o funil administrativo.")
        return

    if 'STAGE_NAME' not in df.columns:
        st.error("A coluna 'STAGE_NAME' é necessária para o funil e não foi encontrada.")
        return
    
    # Agrupa dados por etapa contando os IDs (ou qualquer coluna não nula para contagem)
    funil_data_adm = df.groupby('STAGE_NAME').size().reset_index(name='Quantidade')
    funil_data_adm = funil_data_adm.set_index('STAGE_NAME')

    # Reordena o dataframe de acordo com a ordem das etapas fornecida
    # e garante que todas as etapas da ordem estejam presentes, preenchendo com 0 se não houver dados
    funil_data_adm = funil_data_adm.reindex(etapas_ordem, fill_value=0).reset_index()

    # Remove etapas com quantidade zero APÓS a ordenação para manter a estrutura do funil
    # mas só se não forem as etapas finais de sucesso/falha que podem legitimamente ter zero e ainda serem mostradas.
    # Por simplicidade, vamos manter todas as etapas da ordem por enquanto, mesmo que zeradas.
    # funil_data_adm = funil_data_adm[funil_data_adm['Quantidade'] > 0]

    if funil_data_adm.empty:
        st.warning("Nenhum dado de etapa para exibir no funil após o processamento.")
        return

    # Gráfico de funil
    fig_funil_adm = go.Figure(go.Funnel(
        y=funil_data_adm['STAGE_NAME'],
        x=funil_data_adm['Quantidade'],
        textinfo="value+percent total", # Mostra valor e percentual do total de itens no funil
        marker={"color": ["#28a745" if stage == "PROTOCOLADO COM SUCESSO" 
                          else "#dc3545" if stage == "CANCELAMENTO" 
                          else "#007bff" for stage in funil_data_adm['STAGE_NAME']]} 
    ))

    fig_funil_adm.update_layout(
        title_text="Funil de Trâmites - Distribuição por Etapa",
        height=600,
        # paper_bgcolor='rgba(0,0,0,0)', # Para fundo transparente se desejado
        # plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_funil_adm, use_container_width=True)

    # Tabela de dados do funil (opcional, mas útil)
    st.markdown("Resumo por Etapa do Funil Administrativo")
    funil_display_adm = funil_data_adm.copy()
    funil_display_adm.rename(columns={'STAGE_NAME': 'Etapa', 'Quantidade': 'Qtd. Trâmites'}, inplace=True)
    
    # Calcula percentual em relação ao total de itens que entram no funil (primeira etapa com dados)
    total_inicial_funil = funil_display_adm['Qtd. Trâmites'].iloc[0] if not funil_display_adm.empty else 0
    if total_inicial_funil > 0:
        funil_display_adm['% em Relação ao Início'] = (funil_display_adm['Qtd. Trâmites'] / total_inicial_funil * 100).round(1).astype(str) + '%'
    else:
        funil_display_adm['% em Relação ao Início'] = '0.0%'

    st.dataframe(
        funil_display_adm,
        use_container_width=True,
        column_config={
            "Etapa": "Etapa do Funil",
            "Qtd. Trâmites": st.column_config.NumberColumn("Quantidade"),
            "% em Relação ao Início": "% do Início do Funil"
        }
    ) 