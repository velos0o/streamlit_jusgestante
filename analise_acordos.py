import pandas as pd
import re
import locale
from decimal import Decimal, InvalidOperation

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
    pattern1 = re.findall(r'(\d+)ª\s*parcela,?\s*no\s*valor\s*de\s*R\$([0-9\.]*,\d{2}),?\s*at[éÉ]\s*(\d{2}/\d{2}/\d{4})', description, re.IGNORECASE)
    if pattern1:
        for match in pattern1:
            # O match é uma tupla (num_parcela, valor_str, data_str)
            valor_str = match[1]
            data = match[2]
            installments.append({
                'valor': clean_currency(valor_str),
                'data_vencimento': data
            })

    # Padrão 2: "Xª PARCELA - R$Y EM DD/MM/AAAA"
    pattern2 = re.findall(r'(\d+)ª\s*PARCELA\s*-\s*R\$([0-9.,]+)\s*EM\s*(\d{2}/\d{2}/\d{4})', description, re.IGNORECASE)
    if pattern2:
         for match in pattern2:
            # O match é uma tupla (num_parcela, valor_str, data_str)
            valor_str = match[1]
            data = match[2]
            installments.append({
                'valor': clean_currency(valor_str),
                'data_vencimento': data
            })

    # Padrão 3: "Xª PARCELA DIA DD/MM/AAAA" (com valor total a ser dividido)
    pattern3 = re.findall(r'(\d+)ª\s*PARCELA\s*DIA\s*(\d{2}/\d{2}/\d{4})', description, re.IGNORECASE)
    if pattern3 and not pattern1 and not pattern2:
        # Este padrão não tem valor individual, pode ser necessário lógica adicional
        # para dividir o "VALOR DO REPASSE" ou "VALOR DA PARCELA"
        for match in pattern3:
            data = match[1]
            installments.append({
                'valor': 'Não especificado na descrição',
                'data_vencimento': data
            })

    # Padrão 4: "parcela única, até o dia DD/MM/AAAA"
    pattern4 = re.search(r'parcela\s*[úÚ]nica,?\s*at[éÉ]\s*o\s*dia\s*(\d{2}/\d{2}/\d{4})', description, re.IGNORECASE)
    if pattern4:
        data = pattern4.group(1)
        installments.append({
            'valor': 'Única',
            'data_vencimento': data
        })

    # Padrão 5: "Parecela única até DD/MM/AAAA" (com erro de digitação)
    pattern5 = re.search(r'Parecela\s*[úÚ]nica\s*at[éÉ]\s*(\d{2}/\d{2}/\d{4})', description, re.IGNORECASE)
    if pattern5:
        data = pattern5.group(1)
        installments.append({
            'valor': 'Única',
            'data_vencimento': data
        })
        
    # Padrão 6: Xª PARCELA DE R$Y DIA DD/MM/AAAA
    pattern6 = re.findall(r'(\d+)ª\s*PARCELA\s*DE\s*R\$([0-9.,]+)\s*DIA\s*(\d{2}/\d{2}/\d{4})', description, re.IGNORECASE)
    if pattern6:
        for match in pattern6:
            # O match é uma tupla (num_parcela, valor_str, data_str)
            valor_str = match[1]
            data = match[2]
            installments.append({
                'valor': clean_currency(valor_str),
                'data_vencimento': data
            })

    return installments if installments else "Padrão não identificado"


def analisar_acordos(filepath):
    """
    Função principal para ler e analisar o CSV de acordos.
    """
    try:
        # Carrega o CSV, pulando a primeira linha (título) e usando a segunda como cabeçalho.
        df = pd.read_csv(filepath, header=1)
        
        # Remove linhas no final que não têm um CPF válido (limpeza de dados)
        df.dropna(subset=['CPF'], inplace=True)
        df.reset_index(drop=True, inplace=True)

        # --- Análise 1 e 2: Soma de Valores ---
        df['VALOR_ACORDO_NUM'] = df['VALOR DO ACORDO'].apply(clean_currency)
        df['HONORARIOS_NUM'] = df['HONORÁRIOS (30%)'].apply(clean_currency)

        total_acordos = df['VALOR_ACORDO_NUM'].sum()
        total_honorarios = df['HONORARIOS_NUM'].sum()

        # Configura a localidade para formatar como moeda brasileira
        try:
            locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        except locale.Error:
            locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252') # Para Windows

        print("--- Análise de Viabilidade de Acordos ---")
        print("\nAnálise 1: Valor Total dos Acordos")
        print(f"Soma Total: {locale.currency(total_acordos, grouping=True)}")

        print("\nAnálise 2: Valor Total de Honorários")
        print(f"Soma Total: {locale.currency(total_honorarios, grouping=True)}")

        # --- Análise 3: Análise Descritiva das Parcelas ---
        print("\nAnálise 3: Extração de Dados da Coluna 'PARCELAS DESCRITIVAS'")
        df['ANALISE_PARCELAS'] = df['PARCELAS DESCRITIVAS'].apply(parse_installments)

        for index, row in df.iterrows():
            print(f"\n--- Cliente: {row['NOME'].strip()} ---")
            print(f"Descrição Original: \"{row['PARCELAS DESCRITIVAS']}\"")
            print("Resultado da Análise:")
            if isinstance(row['ANALISE_PARCELAS'], list):
                total_valor_extraido = Decimal('0.0')
                for parcela in row['ANALISE_PARCELAS']:
                    if isinstance(parcela['valor'], Decimal):
                         print(f"  - Parcela: {locale.currency(parcela['valor'], grouping=True)} | Vencimento: {parcela['data_vencimento']}")
                         total_valor_extraido += parcela['valor']
                    else:
                        print(f"  - Parcela: {parcela['valor']} | Vencimento: {parcela['data_vencimento']}")
                
                # Validação cruzada
                valor_repassado = clean_currency(row['VALOR DO REPASSE'])
                valor_acordo = clean_currency(row['VALOR DO ACORDO'])

                # A soma extraída deve bater com o valor do repasse para o cliente
                # ou com o valor total do acordo, dependendo do que está sendo descrito.
                # Aqui, vamos comparar com o valor do REPASSE, pois é o mais comum.
                if total_valor_extraido > 0 and abs(total_valor_extraido - valor_repassado) > Decimal('0.01'):
                    # Adicionamos uma verificação secundária contra o VALOR DO ACORDO, 
                    # pois a descrição pode detalhar o valor total antes dos honorários.
                    if abs(total_valor_extraido - valor_acordo) > Decimal('0.01'):
                        print(f"  -> ATENÇÃO: Soma extraída ({locale.currency(total_valor_extraido, grouping=True)}) não bate com 'VALOR DO REPASSE' ({locale.currency(valor_repassado, grouping=True)}) nem com 'VALOR DO ACORDO' ({locale.currency(valor_acordo, grouping=True)})")
                    else:
                        print(f"  -> INFO: Soma extraída ({locale.currency(total_valor_extraido, grouping=True)}) corresponde ao 'VALOR DO ACORDO' ({locale.currency(valor_acordo, grouping=True)})")

            else:
                print(f"  - {row['ANALISE_PARCELAS']}")


    except FileNotFoundError:
        print(f"Erro: O arquivo '{filepath}' não foi encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    analisar_acordos('ACORDOS - JUNHO.csv') 