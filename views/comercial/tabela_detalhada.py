import streamlit as st
import pandas as pd
from datetime import date

def render_tabela_detalhada(df: pd.DataFrame):
    """Renderiza tabela simplificada dos negócios"""
    st.markdown("---")
    st.subheader("Detalhes dos Negócios")
    
    # Exibe informação resumida
    st.info(f"Negócios encontrados: {len(df)}")
    
    # Seleciona apenas colunas essenciais
    colunas_essenciais = []
    colunas_mapeamento = {
        'ID': 'ID',
        'TITLE': 'Cliente',
        'STAGE_NAME': 'Etapa',
        'DATE_CREATE': 'Criação',
        'UF_CRM_DATA_FECHAMENTO1': 'Data Venda',
        'ASSIGNED_BY_NAME': 'Responsável'
    }
    
    for col, nome in colunas_mapeamento.items():
        if col in df.columns:
            colunas_essenciais.append(col)
    
    if colunas_essenciais:
        # Cria DataFrame simplificado
        df_simples = df[colunas_essenciais].copy()
        
        # Renomeia colunas para nomes mais amigáveis
        df_simples.columns = [colunas_mapeamento.get(col, col) for col in df_simples.columns]
        
        # Configura formatação
        column_config = {
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "Cliente": st.column_config.TextColumn("Cliente", width="large"),
            "Etapa": st.column_config.TextColumn("Etapa", width="medium"),
            "Criação": st.column_config.DateColumn("Data Criação", width="small"),
            "Data Venda": st.column_config.DateColumn("Data Venda", width="small"),
            "Responsável": st.column_config.TextColumn("Responsável", width="medium")
        }
        
        # Exibe tabela com fonte normal
        st.markdown("""
        <style>
        .stDataFrame {
            font-size: 1em !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.dataframe(
            df_simples,
            use_container_width=True,
            column_config=column_config,
            hide_index=True,
            height=400
        )
        
        # Botão de download simples
        csv = df_simples.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"comercial_simples_{date.today()}.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True
        )
        
    else:
        st.warning("Colunas essenciais não encontradas") 