import pandas as pd

def ler_correspondencias_planilha(caminho_arquivo):
    """
    Lê a planilha e extrai um dicionário de correspondências.

    Parâmetro:
        caminho_arquivo (str): Caminho do arquivo Excel.

    Retorna:
        dict: Dicionário com as correspondências extraídas.
    """
    # Abrir a planilha na aba "Controle"
    df = pd.read_excel(caminho_arquivo, sheet_name="Controle", dtype=str)

    correspondencias = {}

    for index, row in df.iterrows():
        id_valor = str(row.iloc[0]).strip()  # Coluna 1 (ID)
        nome = str(row.iloc[1]).strip()  # Coluna 2 (Usado para filtragem)
        sigla = str(row.iloc[2]).strip()  # Coluna 3 (Sigla)
        uc = str(row.iloc[4]).strip()  # Coluna 5 (UC)
        desconto_fatura = str(row.iloc[5]).strip()  # Coluna 6 (Desconto Fatura)
        desconto_bandeira = str(row.iloc[6]).strip()  # Coluna 7 (Desconto Bandeira)
        vencimento_consorcio =  str(row.iloc[7]).strip()  # Coluna 8 (Vencimento Aupus)
        modo_calc = str(row.iloc[8]).strip()  # Coluna 9 (Modo de calculo)

        # Parar quando a coluna UC estiver vazia
        if not uc:
            break

        # Ignorar IDs que começam com "UG "
        
        '''
        if nome.startswith("UG "):
            continue
        '''

        # Adicionar ao dicionário
        correspondencias[id_valor] = {
            "id_planilha": id_valor,
            "uc": uc,
            "nome": nome,
            "sigla": sigla,
            "desconto_fatura": desconto_fatura,
            "desconto_bandeira": desconto_bandeira,
            "vencimento_consorcio": vencimento_consorcio,
            "modo_calc": modo_calc,
        }

    return correspondencias
