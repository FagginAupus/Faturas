import os
import re
from PIL import Image
from io import BytesIO
import PyPDF2
import fitz

uc_to_name = {
    "10676740": "CISPERTECH",
    "13095584": "DJ",
    "13540798": "LAVA MAX",
    "14643390": "MS1",
    "15654229": "RESIDENCIAL PAINEIRAS",
    "15794234": "ROYAL RESIDENCE",
    "17064521": "SOLAR DE FRANCE",
    "17477402": "MS2",
    "10001355552": "CHATEAU DE VERSAILLES",
    "10010980120": "MARCELO PRIME",
    "10023289897": "MOISES",
    "10024492297": "FLAMBOYANT",
    "10030116641": "MARCOS CELESTINO",
    "10034673260": "CLEITON",
    "10037841597": "RONY",
    "10038116985": "MALBEC",
    "10009103722": "SAMARA",
    "10015637660": "WINNER RESIDENCE",
    "10038444915": "CAMILA",
    "14012844": "LE HERMITAGE",
    "11036308": "BULKING",
    "10003298777": "ERIC",
    "10029223090": "EDUARDO SALA 1",
    "690283738": "EDUARDO CASA",
    "10029222956": "EDUARDO SALA 2",
    "10025220410": "MARCO TULIO"
}

# Defina o caminho da imagem que será adicionada aos PDFs

mes = input("Digite o mês (MM): ")
ano = input("Digite o ano (YYYY): ")
pasta_pdf = f"C:\\Users\\arthu\\Dropbox\\AUPUS SMART\\01. Club AUPUS\\01. Usineiros\\01. AUPUS ENERGIA\\01. FATURAS\\{ano}\\{mes}.{ano}"
pasta_net = f"C:\\Users\\arthu\\Dropbox\\AUPUS SMART\\01. Club AUPUS\\01. Usineiros\\01. AUPUS ENERGIA\\02. NET\\{ano}\\{mes}.{ano}"
pasta_faturas = f"C:\\Users\\arthu\\Dropbox\\AUPUS SMART\\01. Club AUPUS\\01. Usineiros\\01. AUPUS ENERGIA\\03. BOLETOS\\{ano}\\{mes}.{ano}"
caminho_saida_base = f"C:\\Users\\arthu\\Dropbox\\AUPUS SMART\\01. Club AUPUS\\01. Usineiros\\01. AUPUS ENERGIA\\04. PDF COMBINADO\\{ano}\\{mes}.{ano}"
pasta_imagens = "C:\\Users\\arthu\\Dropbox\\AUPUS SMART\\01. Club AUPUS\\01. Usineiros\\01. AUPUS ENERGIA\\_Controles"
nome_imagem = "PAGO"
formato_imagem = "png"
imagem_path = os.path.join(pasta_imagens, f"{nome_imagem}.{formato_imagem}")

# Atualizando a lista removendo UCs cujos arquivos já existem na pasta de saída
def atualizar_lista_uc(uc_to_name, caminho_saida_base):
    nova_lista_uc = {}
    for uc, nome in uc_to_name.items():
        # Verifica se há um arquivo na pasta de saída que contenha o número da UC
        encontrado = False
        for arquivo in os.listdir(caminho_saida_base):
            if re.search(uc, arquivo):
                encontrado = True
                break
        if not encontrado:
            nova_lista_uc[uc] = nome
    return nova_lista_uc

def encontrar_arquivos_correspondentes(uc, nome, pasta_pdf, pasta_net, pasta_faturas):

    arquivos_encontrados = {}

    def verificar_pasta(pasta, uc, nome):
        for arquivo in os.listdir(pasta):
            if re.search(uc, arquivo) or re.search(nome, arquivo, re.IGNORECASE):
                return os.path.join(pasta, arquivo)
        return None

    arquivos_encontrados["pdf"] = verificar_pasta(pasta_pdf, uc, nome)
    arquivos_encontrados["net"] = verificar_pasta(pasta_net, uc, nome)
    arquivos_encontrados["faturas"] = verificar_pasta(pasta_faturas, uc, nome)

    if all(arquivos_encontrados.values()):
        return arquivos_encontrados
    return None

def encontrar_arquivos_ms(pasta_pdf, pasta_net, pasta_faturas):
    """
    Encontra os arquivos necessários para MS1 e MS2.
    Retorna um dicionário com os caminhos corretos.
    """
    arquivos_ms = {
        "ms1_pdf": None,
        "ms1_net": None,
        "ms2_pdf": None,
        "ms2_net": None,
        "ms_fatura": None
    }

    # Procurando MS1 na pasta PDF e net
    for arquivo in os.listdir(pasta_pdf):
        if "14643390" in arquivo and arquivo.endswith(".pdf"):
            arquivos_ms["ms1_pdf"] = os.path.join(pasta_pdf, arquivo)

    for arquivo in os.listdir(pasta_net):
        if "14643390" in arquivo and arquivo.endswith(".pdf"):
            arquivos_ms["ms1_net"] = os.path.join(pasta_net, arquivo)

    # Procurando MS2 na pasta PDF e net
    for arquivo in os.listdir(pasta_pdf):
        if "17477402" in arquivo and arquivo.endswith(".pdf"):
            arquivos_ms["ms2_pdf"] = os.path.join(pasta_pdf, arquivo)

    for arquivo in os.listdir(pasta_net):
        if "17477402" in arquivo and arquivo.endswith(".pdf"):
            arquivos_ms["ms2_net"] = os.path.join(pasta_net, arquivo)

    # Procurando MS na pasta FATURAS (Boleto MS)
    for arquivo in os.listdir(pasta_faturas):
        if "Boleto MS" in arquivo and arquivo.endswith(".pdf"):
            arquivos_ms["ms_fatura"] = os.path.join(pasta_faturas, arquivo)

    return arquivos_ms

def adicionar_imagem_no_pdf(pdf_path, imagem_path):
    pdf_document = fitz.open(pdf_path)
    imagem = Image.open(imagem_path)

    for pagina_num in range(pdf_document.page_count):
        pagina = pdf_document[pagina_num]
        pdf_width, pdf_height = int(pagina.rect.width), int(pagina.rect.height)
        imagem_resized = imagem.resize((pdf_width, pdf_height), Image.LANCZOS)
        png_buffer = BytesIO()
        imagem_resized.save(png_buffer, format="PNG", optimize=True, quality=85)
        png_data = png_buffer.getvalue()
        imagem_rect = fitz.Rect(0, 0, pdf_width, pdf_height)
        pagina.insert_image(imagem_rect, stream=png_data, keep_proportion=False)

    return pdf_document

def otimizar_pdf(pdf_path, output_path):
    pdf_document = fitz.open(pdf_path)
    pdf_document.save(output_path, garbage=4, deflate=True)
    pdf_document.close()

def combinar_pdfs(pdf_files, output_path):
    pdf_writer = PyPDF2.PdfWriter()

    for pdf_file in pdf_files:
        with open(pdf_file, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page_num in range(len(pdf_reader.pages)):
                pdf_writer.add_page(pdf_reader.pages[page_num])

    with open(output_path, "wb") as output_pdf:
        pdf_writer.write(output_pdf)

# Passo 1: Verifica os arquivos na pasta caminho_saida_base e remove os UCs já presentes
lista_atualizada = atualizar_lista_uc(uc_to_name, caminho_saida_base)

# Passo 2: Verifica a presença de arquivos "MS" na pasta de saída
ms_uc = ["14643390", "17477402"]
ms_nome = "MS"
arquivos_existentes = any(re.search(ms_nome, arquivo, re.IGNORECASE) for arquivo in os.listdir(caminho_saida_base))

if arquivos_existentes:
    # Se já houver um arquivo com "MS", remove MS1 e MS2 da lista atualizada
    lista_atualizada = {uc: nome for uc, nome in lista_atualizada.items() if uc not in ms_uc}

# Passo 3: Processa UCs normais
for uc, nome in lista_atualizada.items():
    resultado = encontrar_arquivos_correspondentes(uc, nome, pasta_pdf, pasta_net, pasta_faturas)
    if resultado:
        print(f"Arquivos correspondentes encontrados para {uc}: {resultado}")
        pdf_modificado = adicionar_imagem_no_pdf(resultado["pdf"], imagem_path)
        pdf_modificado_path = os.path.join(pasta_pdf, f"{uc}_modificado.pdf")
        pdf_modificado.save(pdf_modificado_path)
        pdf_modificado.close()

        pdf_modificado_otimizado_path = os.path.join(pasta_pdf, f"{uc}_modificado_otimizado.pdf")
        otimizar_pdf(pdf_modificado_path, pdf_modificado_otimizado_path)

        pdf_combined_path = os.path.join(caminho_saida_base, f"Fatura AUPUS - {uc} - {nome}.pdf")
        combinar_pdfs([resultado["net"], pdf_modificado_otimizado_path, resultado["faturas"]], pdf_combined_path)

        os.remove(pdf_modificado_path)
        os.remove(pdf_modificado_otimizado_path)
    else:
        print(f"Nenhuma correspondência completa para {uc}")

# Passo 4: Processa MS1 e MS2 em conjunto
if not arquivos_existentes:

    ms_arquivos = encontrar_arquivos_ms(pasta_pdf, pasta_net, pasta_faturas)


    if ms_arquivos["ms1_pdf"] and ms_arquivos["ms1_net"] and ms_arquivos["ms2_pdf"] and ms_arquivos["ms2_net"] and ms_arquivos["ms_fatura"]:

        ms1_pdf_modificado = adicionar_imagem_no_pdf(ms_arquivos["ms1_pdf"], imagem_path)
        ms2_pdf_modificado = adicionar_imagem_no_pdf(ms_arquivos["ms2_pdf"], imagem_path)

        ms1_pdf_modificado_path = os.path.join(pasta_pdf, "14643390_modificado.pdf")
        ms2_pdf_modificado_path = os.path.join(pasta_pdf, "17477402_modificado.pdf")

        ms1_pdf_modificado.save(ms1_pdf_modificado_path)
        ms2_pdf_modificado.save(ms2_pdf_modificado_path)

        ms1_pdf_modificado.close()
        ms2_pdf_modificado.close()

        ms1_pdf_modificado_otimizado_path = os.path.join(pasta_pdf, "14643390_modificado_otimizado.pdf")
        ms2_pdf_modificado_otimizado_path = os.path.join(pasta_pdf, "17477402_modificado_otimizado.pdf")

        otimizar_pdf(ms1_pdf_modificado_path, ms1_pdf_modificado_otimizado_path)
        otimizar_pdf(ms2_pdf_modificado_path, ms2_pdf_modificado_otimizado_path)

        ms_combined_path = os.path.join(caminho_saida_base, "Fatura AUPUS - MS.pdf")

        combinar_pdfs([
            ms_arquivos["ms1_net"],
            ms_arquivos["ms2_net"],
            ms1_pdf_modificado_otimizado_path,
            ms2_pdf_modificado_otimizado_path,
            ms_arquivos["ms_fatura"]
        ], ms_combined_path)

        os.remove(ms1_pdf_modificado_path)
        os.remove(ms2_pdf_modificado_path)
        os.remove(ms1_pdf_modificado_otimizado_path)
        os.remove(ms2_pdf_modificado_otimizado_path)

    else:
        print("Não foi possível encontrar todos os arquivos necessários para MS1 e MS2")
        if not ms_arquivos["ms1_pdf"]:
            print("Arquivo PDF para MS1 não encontrado.")
        if not ms_arquivos["ms1_net"]:
            print("Arquivo net para MS1 não encontrado.")
        if not ms_arquivos["ms2_pdf"]:
            print("Arquivo PDF para MS2 não encontrado.")
        if not ms_arquivos["ms2_net"]:
            print("Arquivo net para MS2 não encontrado.")
        if not ms_arquivos["ms_fatura"]:
            print("Arquivo de fatura MS não encontrado.")
