import pandas as pd
import re
import locale
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
import streamlit as st
from dateutil.relativedelta import relativedelta

def clean_currency(value):
    """Converte uma string de moeda para um valor numérico (Decimal)."""
    if isinstance(value, str):
        # Remove 'R$', espaços em branco e pontos de milhar
        value = value.replace('R$', '').strip().replace('.', '')
        # Substitui a vírgula decimal por um ponto
        value = value.replace(',', '.')
        try:
            return Decimal(value)
        except InvalidOperation:
            return Decimal('0.0')
    return Decimal('0.0')

def parse_installments(description):
    """Analisa a descrição das parcelas para extrair valor e data."""
    if not isinstance(description, str):
        return []

    installments = []
    
    # Padrão 1: "Xª parcela, no valor de R$Y, até DD/MM/AAAA"
    pattern1 = re.findall(r'(\d+)ª\s*parcela,?\s*no\s*valor\s*de\s*R\$([0-9.,]+),?\s*at[ée]\s*(\d{2}/\d{2}/\d{4})', description, re.IGNORECASE)
    if pattern1:
        for match in pattern1:
            valor_str = match[1]
            data = match[2]
            installments.append({
                'valor': clean_currency(valor_str),
                'data_vencimento': data
            })

    # Padrão 2: "X (palavra) parcelas de R$ Y com vencimento da 1ª parcelas em DD/MM/AAAA e as demais ocorrerão até o dia D dos meses subsequentes"
    pattern2 = re.search(r'(\d+)\s*(?:\([^)]+\))?\s*parcelas?\s*de\s*R\$\s*([0-9.,]+)\s*com\s*vencimento\s*da\s*1ª\s*parcelas?\s*em\s*(\d{2}/\d{2}/\d{4})\s*e\s*as\s*demais\s*ocorrerão\s*at[ée]\s*o\s*dia\s*(\d+)', description, re.IGNORECASE)
    if pattern2:
        num_parcelas = int(pattern2.group(1))
        valor_str = pattern2.group(2)
        data_primeira = pattern2.group(3)
        dia_vencimento = int(pattern2.group(4))
        
        # Converter a data da primeira parcela
        data_atual = datetime.strptime(data_primeira, '%d/%m/%Y')
        valor = clean_currency(valor_str)
        
        # Adicionar a primeira parcela
        installments.append({
            'valor': valor,
            'data_vencimento': data_atual.strftime('%d/%m/%Y')
        })
        
        # Adicionar as parcelas subsequentes
        for i in range(1, num_parcelas):
            # Avançar um mês
            if data_atual.month == 12:
                data_atual = data_atual.replace(year=data_atual.year + 1, month=1)
            else:
                data_atual = data_atual.replace(month=data_atual.month + 1)
            
            # Ajustar para o dia de vencimento
            data_atual = data_atual.replace(day=min(dia_vencimento, 28))
            
            installments.append({
                'valor': valor,
                'data_vencimento': data_atual.strftime('%d/%m/%Y')
            })

    # Padrão 3: "Parecela única até DD/MM/AAAA" (com erro de digitação)
    pattern3 = re.search(r'[Pp]arecela\s*[úu]nica\s*at[ée]\s*(\d{2}/\d{2}/\d{4})', description)
    if pattern3:
        data = pattern3.group(1)
        installments.append({
            'valor': 'Única',
            'data_vencimento': data
        })

    # Padrão 4: "Parcela única até DD/MM/AAAA"
    pattern4 = re.search(r'[Pp]arcela\s*[úu]nica\s*at[ée]\s*(\d{2}/\d{2}/\d{4})', description)
    if pattern4 and not pattern3:  # Evitar duplicação com pattern3
        data = pattern4.group(1)
        installments.append({
            'valor': 'Única',
            'data_vencimento': data
        })

    # Padrão 5: "Xx de R$ Y dia DD/MM/AAAA e DD/MM/AAAA"
    pattern5 = re.search(r'(\d+)x\s*de\s*R\$\s*([0-9.,]+)\s*dia\s*(\d{2}/\d{2}/\d{4})\s*e\s*(\d{2}/\d{2}/\d{4})', description, re.IGNORECASE)
    if pattern5:
        valor_str = pattern5.group(2)
        data1 = pattern5.group(3)
        data2 = pattern5.group(4)
        valor = clean_currency(valor_str)
        installments.extend([
            {'valor': valor, 'data_vencimento': data1},
            {'valor': valor, 'data_vencimento': data2}
        ])

    return installments if installments else "Padrão não identificado"

def _to_float(s: str) -> float:
    """
    Converte uma string de moeda (em formato brasileiro ou americano) para float.
    É robusto a diferentes separadores de milhar e decimal.
    """
    s = s.strip()
    if not s:
        return 0.0
        
    # Se uma vírgula está presente, assume-se formato brasileiro (ex: 1.234,56)
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    # Se não há vírgula, mas há um ponto
    elif '.' in s:
        parts = s.split('.')
        # Heurística: se a parte final tem 3 dígitos e não é a única,
        # provavelmente é um separador de milhar para um inteiro (ex: 2.100)
        if len(parts) > 1 and len(parts[-1]) == 3:
            s = s.replace('.', '')
        # Caso contrário, o ponto é um separador decimal (ex: 1500.00) e nada precisa ser feito.
            
    try:
        return float(s)
    except ValueError:
        return 0.0

def parse_summary_format(texto):
    """
    Analisa formatos de resumo como "6 parcelas de R$ 2.000,00...".
    """
    try:
        texto_limpo = texto.replace('\n', ' ').replace('\r', ' ')

        summary_pattern = re.search(r'(\d+)\s*parcelas\s+de\s+R\$\s*([\d.,]*\d)', texto_limpo, re.IGNORECASE)
        if not summary_pattern:
            return []

        date_pattern = re.search(r'venc[íi]vel\s+a\s+primeira\s*(?:dia)?\s*(\d{2}\/\d{2}\/\d{4})', texto_limpo, re.IGNORECASE)
        if not date_pattern:
            return []
            
        num_parcelas = int(summary_pattern.group(1))
        valor_str = summary_pattern.group(2)
        valor = _to_float(valor_str)
        data_inicio_str = date_pattern.group(1)
        
        data_inicio = datetime.strptime(data_inicio_str, '%d/%m/%Y').date()

        parcelas = []
        for i in range(num_parcelas):
            data_vencimento = data_inicio + relativedelta(months=i)
            parcelas.append({
                'numero': i + 1,
                'valor_acordo': valor,
                'valor_honorarios': None,
                'valor_honorarios_adicionais': [],
                'valor_liquido': None,
                'data_vencimento': data_vencimento,
                'status': 'Pendente',
                'data_pagamento': None
            })
        return parcelas
    except (ValueError, IndexError):
        return []

def extract_parcela_info(texto_parcela):
    """
    Extrai informações de uma única linha de parcela.
    """
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except:
        pass

    numero_pattern = re.search(r'(\d+)[ªº°]?\s*parcela', texto_parcela, re.IGNORECASE)
    data_pattern = re.search(r'até\s*(?:o\s+dia\s+|dia\s+)?(\d{2}\/\d{2}\/\d{4})', texto_parcela, re.IGNORECASE)
    realizado_pattern = re.search(r'(?:realizado|reliazado|pago|efetuado|pix)\s*(?:em)?\s*(\d{2}\/\d{2}\/\d{4})', texto_parcela, re.IGNORECASE)
    
    # Regex ajustado para não capturar pontuação no final do número
    valores = re.findall(r'R\$\s*([\d.,]*\d)', texto_parcela)
    valores_float = [_to_float(v) for v in valores]

    parcela_info = {
        'numero': int(numero_pattern.group(1)) if numero_pattern else None,
        'valor_acordo': None, 'valor_honorarios': None, 'valor_honorarios_adicionais': [], 'valor_liquido': None,
        'data_vencimento': datetime.strptime(data_pattern.group(1), '%d/%m/%Y').date() if data_pattern else None,
        'status': 'Pendente', 'data_pagamento': None
    }

    if realizado_pattern:
        parcela_info['status'] = 'Pago'
        if realizado_pattern.group(1):
            try:
                parcela_info['data_pagamento'] = datetime.strptime(realizado_pattern.group(1), '%d/%m/%Y').date()
            except (ValueError, IndexError):
                pass
    
    if valores_float:
        parcela_info['valor_acordo'] = valores_float[0]
        
        liquido_match = re.search(r'=\s*R\$\s*([\d.,]*\d)', texto_parcela)
        if liquido_match:
            parcela_info['valor_liquido'] = _to_float(liquido_match.group(1))
        
        honorarios_candidatos = []
        if len(valores_float) > 1:
            outros_valores = valores_float[1:]
            if parcela_info['valor_liquido'] is not None:
                # Se o líquido é conhecido, todos os outros valores (exceto o do acordo) são honorários
                honorarios_candidatos = [v for v in outros_valores if v != parcela_info['valor_liquido']]
            else:
                # Se não, todos os outros são honorários
                honorarios_candidatos = outros_valores

        if honorarios_candidatos:
            parcela_info['valor_honorarios'] = honorarios_candidatos[0]
            if len(honorarios_candidatos) > 1:
                parcela_info['valor_honorarios_adicionais'] = honorarios_candidatos[1:]

        if parcela_info['valor_liquido'] is None and parcela_info['valor_acordo'] and parcela_info['valor_honorarios']:
            total_honorarios = parcela_info['valor_honorarios'] + sum(parcela_info['valor_honorarios_adicionais'])
            parcela_info['valor_liquido'] = parcela_info['valor_acordo'] - total_honorarios
            
    return parcela_info

def analyze_parcelas(texto):
    """
    Analisa o texto completo das parcelas, tentando vários métodos.
    """
    if not isinstance(texto, str):
        return []

    # Método 1: Tentar parsear linha por linha
    linhas = texto.split('\n')
    parcelas = []
    for linha in linhas:
        linha_strip = linha.strip()
        if not linha_strip:
            continue
        
        if 'parcela' in linha_strip.lower():
            parcela_info = extract_parcela_info(linha_strip)
            if parcela_info.get('numero') and parcela_info.get('data_vencimento'):
                parcelas.append(parcela_info)

    if parcelas:
        parcelas.sort(key=lambda x: x['numero'])
        return parcelas

    # Método 2: Se o primeiro falhar, tentar o formato de resumo
    parcelas_resumo = parse_summary_format(texto)
    if parcelas_resumo:
        return parcelas_resumo

    return []

def format_currency(value):
    """
    Formata um valor monetário para o padrão brasileiro.
    """
    try:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def format_date(date):
    """
    Formata uma data para o padrão brasileiro.
    """
    if date:
        return date.strftime('%d/%m/%Y')
    return ""

def format_parcela_display(parcela):
    """
    Formata as informações da parcela para exibição.
    """
    numero = parcela['numero']
    valor_acordo = format_currency(parcela['valor_acordo']) if parcela['valor_acordo'] else "N/A"
    valor_honorarios = format_currency(parcela['valor_honorarios']) if parcela['valor_honorarios'] else "N/A"
    valor_liquido = format_currency(parcela['valor_liquido']) if parcela['valor_liquido'] else "N/A"
    data_vencimento = format_date(parcela['data_vencimento'])
    status = parcela['status']
    data_pagamento = format_date(parcela['data_pagamento']) if parcela['status'] == 'Pago' else ""

    texto = f"{numero}ª parcela: {valor_acordo}"
    
    # Adiciona honorários principais
    if parcela['valor_honorarios']:
        texto += f" - {valor_honorarios} (honorários)"
    
    # Adiciona honorários adicionais
    for hon_adicional in parcela['valor_honorarios_adicionais']:
        texto += f" - {format_currency(hon_adicional)} (honorários adicionais)"
    
    texto += f" = {valor_liquido} até {data_vencimento}"
    
    if status == 'Pago':
        texto += f" - {status}"
        if data_pagamento:
            texto += f" em {data_pagamento}"

    return texto

def analyse_data(df):
    """
    Realiza a análise completa do DataFrame.
    """
    # Verificar e renomear colunas se necessário
    column_mapping = {
        'CPF': ['CPF', 'CPF_2', 'CPF_1'],
        'VALOR DO ACORDO': ['VALOR DO ACORDO', 'VALOR DO ACORDO_2', 'VALOR DO ACORDO_1', 'VALOR ACORDO'],
        'HONORÁRIOS (30%)': ['HONORÁRIOS (30%)', 'HONORÁRIOS (30%)_2', 'HONORÁRIOS (30%)_1', 'HONORARIOS'],
        'PARCELAS DESCRITIVAS': ['PARCELAS DESCRITIVAS', 'PARCELAS DESCRITIVAS_2', 'PARCELAS DESCRITIVAS_1', 'PARCELAS']
    }

    # Tentar encontrar e renomear as colunas corretas
    for target_col, possible_names in column_mapping.items():
        for col_name in possible_names:
            if col_name in df.columns:
                df = df.rename(columns={col_name: target_col})
                break

    # Verificar se todas as colunas necessárias existem
    required_columns = ['CPF', 'VALOR DO ACORDO', 'HONORÁRIOS (30%)', 'PARCELAS DESCRITIVAS']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        st.error(f"Colunas ausentes na planilha: {', '.join(missing_columns)}")
        st.write("Colunas disponíveis:", df.columns.tolist())
        return {
            "total_acordos": Decimal('0'),
            "total_honorarios": Decimal('0'),
            "dataframe": df
        }

    # Limpeza de dados
    df = df.copy()
    df.dropna(subset=['CPF'], inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Criar uma nova coluna com os resultados da análise
    coluna_parcelas_descritivas = next((col for col in ['PARCELAS', 'PARCELAS DESCRITIVAS'] if col in df.columns), None)
    
    if coluna_parcelas_descritivas:
        # FORÇA a coluna a ser do tipo string, preenchendo valores nulos/NaN com string vazia.
        # Isso garante que a função de análise sempre receba o tipo de dado correto e não falhe silenciosamente.
        df['ANALISE_PARCELAS'] = df[coluna_parcelas_descritivas].astype(str).fillna('').apply(analyze_parcelas)
    else:
        df['ANALISE_PARCELAS'] = [[] for _ in range(len(df))]

    # Análise 1 e 2: Soma de Valores
    df['VALOR_ACORDO_NUM'] = df['VALOR DO ACORDO'].apply(clean_currency)
    df['HONORARIOS_NUM'] = df['HONORÁRIOS (30%)'].apply(clean_currency)
    
    total_acordos = df['VALOR_ACORDO_NUM'].sum()
    total_honorarios = df['HONORARIOS_NUM'].sum()

    return {
        "total_acordos": total_acordos,
        "total_honorarios": total_honorarios,
        "dataframe": df
    } 