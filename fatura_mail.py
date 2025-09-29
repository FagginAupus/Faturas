import os
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from pathlib import Path
import glob  # ← NOVA IMPORTAÇÃO para buscar arquivos

import gc
import time
import shutil

# Importações dos seus módulos
# REMOVIDO: from Leitor_Faturas_PDF import FaturaProcessor
from processors.fatura_processor_v2 import FaturaProcessorV2
from Calculadora_AUPUS import CalculadoraAUPUS
from Exportar_Planilha import exportar_para_excel
from Ler_Planilha import ler_correspondencias_planilha

class ProcessadorFaturasEmail:
    def __init__(self):
        # Configurações de email
        self.EMAIL = "faturas.go@aupusenergia.com.br"
        self.SENHA = "#Aupus2024#"
        self.IMAP_SERVER = "imap.hostinger.com"
        self.ASSUNTO_INICIAL = "Fatura da Equatorial Energia em arquivo"
        # REMOVIDO: self.extractor = FaturaProcessor()
        self.processor_v2 = FaturaProcessorV2()
        self.calculadora = CalculadoraAUPUS()
        
        # Caminhos base
        self.CAMINHO_BASE = Path.home() / "Dropbox" / "AUPUS SMART" / "01. Club AUPUS" / "01. Usineiros" / "01. AUPUS ENERGIA" / "01. FATURAS"
        self.CAMINHO_PLANILHA = Path.home() / "Dropbox" / "AUPUS SMART" / "01. Club AUPUS" / "01. Usineiros" / "01. AUPUS ENERGIA" / "_Controles" / "Controle Clube Aupus.xlsx"
        self.CAMINHO_PASTA_LOCAL = Path.home() / "Dropbox" / "AUPUS SMART" / "01. Club AUPUS" / "01. Usineiros" / "01. AUPUS ENERGIA" / "01. FATURAS" / "2025" / "09.2025" / "Pendentes"
    def processar_pdf_seguro(self, temp_filepath: str) -> dict:
        """
        Processa PDF de forma segura com o NOVO sistema modular V2.
        Adiciona tratamento para tipos não suportados.
        """
        try:
            print(f"\n{'='*60}")
            print(f"PROCESSANDO: {Path(temp_filepath).name}")
            print(f"{'='*60}")

            # USAR NOVO PROCESSADOR V2
            dados_pdf = self.processor_v2.processar_fatura(temp_filepath)

            # VERIFICAR SE É TIPO NÃO SUPORTADO
            if dados_pdf.get('skip_processing'):
                print(f"\n[SKIP] FATURA IGNORADA")
                print(f"   Motivo: {dados_pdf.get('skip_reason', 'Tipo não suportado')}")
                print(f"   UC: {dados_pdf.get('uc', 'não identificada')}")
                print(f"{'='*60}\n")
                return None  # Retornar None para indicar que deve pular

            # VALIDAR CAMPOS OBRIGATÓRIOS
            if not dados_pdf.get("uc"):
                print(f"\n[ERRO] UC não encontrada no PDF")
                return None

            print(f"\n[OK] EXTRAÇÃO CONCLUÍDA")
            print(f"   UC: {dados_pdf.get('uc')}")
            print(f"   Grupo: {dados_pdf.get('grupo')}")
            print(f"   Modalidade: {dados_pdf.get('modalidade_tarifaria')}")
            print(f"   Consumo: {dados_pdf.get('consumo')} kWh")
            print(f"{'='*60}\n")

            return dados_pdf

        except Exception as e:
            print(f"\n[ERRO] Erro ao processar PDF: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _aguardar_liberacao_arquivo(self, filepath, max_tentativas=10):
        """
        Aguarda até que o arquivo seja liberado pelo sistema
        """
        for tentativa in range(max_tentativas):
            try:
                # Tentar abrir o arquivo em modo exclusivo para verificar se está livre
                with open(filepath, 'r+b') as f:
                    pass
                return True
            except (OSError, PermissionError):
                gc.collect()
                time.sleep(0.3)
        
        return False
    
    def _converter_decimals_para_float(self, dados):
        """
        Converte todos os valores Decimal para float para resolver conflitos de tipos
        """
        from decimal import Decimal
        
        dados_convertidos = dados.copy()
        
        for chave, valor in dados_convertidos.items():
            if isinstance(valor, Decimal):
                try:
                    dados_convertidos[chave] = float(valor)
                    print(f"      🔄 Convertido {chave}: Decimal → float")
                except (ValueError, OverflowError) as e:
                    print(f"      ⚠️ Erro ao converter {chave}: {e}")
                    dados_convertidos[chave] = 0.0
        
        return dados_convertidos
    
    def _copiar_arquivo_seguro(self, origem, destino, max_tentativas=5):
        """
        Copia arquivo de forma mais segura usando shutil
        """
        for tentativa in range(max_tentativas):
            try:
                # Aguardar liberação do arquivo
                if not self._aguardar_liberacao_arquivo(origem):
                    print(f"   ⚠️ Arquivo ainda bloqueado após tentativas: {os.path.basename(origem)}")
                    continue
                
                # Copiar arquivo
                shutil.copy2(origem, destino)
                return True
                
            except Exception as e:
                print(f"   ⚠️ Tentativa {tentativa + 1} falhou: {e}")
                gc.collect()
                time.sleep(0.5)
        
        return False
    
    def _remover_arquivo_seguro(self, filepath, max_tentativas=10):
        """Remove arquivo com retry mais robusto"""
        for tentativa in range(max_tentativas):
            try:
                # Aguardar liberação
                if self._aguardar_liberacao_arquivo(filepath, 3):
                    os.remove(filepath)
                    return True
            except OSError as e:
                gc.collect()
                time.sleep(0.3)
        
        print(f"   ⚠️ Não foi possível remover: {os.path.basename(filepath)}")
        return False
    
    def _mover_arquivo_seguro(self, origem, destino, max_tentativas=5):
        """
        Move arquivo de forma mais robusta
        """
        for tentativa in range(max_tentativas):
            try:
                # Aguardar liberação do arquivo
                if not self._aguardar_liberacao_arquivo(origem):
                    print(f"   ⚠️ Arquivo ainda bloqueado: {os.path.basename(origem)}")
                    time.sleep(0.5)
                    continue
                
                # Tentar mover diretamente
                shutil.move(origem, destino)
                return True
                
            except Exception as e:
                print(f"   ⚠️ Tentativa {tentativa + 1} de mover arquivo falhou: {e}")
                
                # Se falhou, tentar copiar + remover
                try:
                    if self._copiar_arquivo_seguro(origem, destino, 2):
                        if self._remover_arquivo_seguro(origem, 5):
                            return True
                        else:
                            print(f"   ⚠️ Arquivo copiado mas não removido: {os.path.basename(origem)}")
                            return True  # Pelo menos temos a cópia
                except Exception as e2:
                    print(f"   ⚠️ Fallback copy+remove falhou: {e2}")
                
                gc.collect()
                time.sleep(0.5)
        
        print(f"   ❌ Não foi possível mover: {os.path.basename(origem)}")
        return False

    # ========== MÉTODOS PARA PROCESSAMENTO VIA EMAIL (EXISTENTES) ==========

    def buscar_emails_por_data(self, data_inicio):
        """
        Busca emails apenas dentro do mês da data inicial
        """
        try:
            # Converter data para formato IMAP
            data_obj = datetime.strptime(data_inicio, "%d/%m/%Y")
            
            # Calcular primeiro e último dia do mês
            primeiro_dia = data_obj.replace(day=1)
            
            # Último dia do mês (próximo mês - 1 dia)
            if data_obj.month == 12:
                ultimo_dia = data_obj.replace(year=data_obj.year + 1, month=1, day=1)
            else:
                ultimo_dia = data_obj.replace(month=data_obj.month + 1, day=1)
            ultimo_dia = ultimo_dia - timedelta(days=1)
            
            # Converter para formato IMAP
            data_inicio_imap = primeiro_dia.strftime("%d-%b-%Y")
            data_fim_imap = ultimo_dia.strftime("%d-%b-%Y")
            
            print(f"📡 Conectando ao servidor IMAP...")
            mail = imaplib.IMAP4_SSL(self.IMAP_SERVER)
            mail.login(self.EMAIL, self.SENHA)
            mail.select("inbox")
            print("✅ Conexão realizada com sucesso.")
            
            # Buscar emails APENAS no mês especificado
            print(f"🔍 Buscando emails de {primeiro_dia.strftime('%d/%m/%Y')} até {ultimo_dia.strftime('%d/%m/%Y')}...")
            status, mensagens = mail.search(None, f'(SINCE "{data_inicio_imap}" BEFORE "{data_fim_imap}")')
            
            if status != 'OK':
                print("❌ Erro ao buscar emails")
                return []
            
            emails_ids = mensagens[0].split()
            print(f"📧 Encontrados {len(emails_ids)} emails no mês {data_obj.strftime('%m/%Y')}")
            
            return mail, emails_ids
            
        except Exception as e:
            print(f"❌ Erro ao conectar: {e}")
            return None, []
    
    def criar_pasta_destino(self, data_inicio):
        """
        Cria a pasta de destino baseada na data fornecida
        """
        data_obj = datetime.strptime(data_inicio, "%d/%m/%Y")
        ano = data_obj.strftime("%Y")
        mes_ano = data_obj.strftime("%m.%Y")
        
        pasta_destino = os.path.join(self.CAMINHO_BASE, ano, mes_ano)
        os.makedirs(pasta_destino, exist_ok=True)
        
        print(f"📁 Pasta de destino: {pasta_destino}")
        return pasta_destino

    def baixar_e_processar_pdfs(self, mail, emails_ids, pasta_destino, correspondencias):
        """
        VERSÃO COM VERIFICAÇÃO DE SIGLA: Baixa e processa PDFs
        Apenas clientes com sigla "CLA" prosseguem para cálculos AUPUS
        """
        dados_extraidos = []
        dados_nao_cla = []  # ← NOVA LISTA para clientes não-CLA
        total_baixados = 0
        total_ignorados = 0
        total_cla = 0  # ← NOVO CONTADOR
        total_nao_cla = 0  # ← NOVO CONTADOR
        
        print(f"\n📥 Verificando {len(emails_ids)} emails...")
        
        for num in reversed(emails_ids):
            try:
                status, dados = mail.fetch(num, "(RFC822)")
                raw_email = dados[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Decodificar assunto
                subject_raw = msg["Subject"]
                if subject_raw:
                    subject, encoding = decode_header(subject_raw)[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8", errors="ignore")
                    
                    # Verificar se é o tipo de email que queremos
                    if subject.startswith(self.ASSUNTO_INICIAL):
                        print(f"\n📧 Processando: {subject}")
                        
                        # Buscar anexos
                        for part in msg.walk():
                            if part.get_content_maintype() == 'multipart':
                                continue
                            if part.get('Content-Disposition') is None:
                                continue
                            
                            filename = part.get_filename()
                            if filename:
                                decoded_name, encoding = decode_header(filename)[0]
                                if isinstance(decoded_name, bytes):
                                    filename = decoded_name.decode(encoding or 'utf-8', errors="ignore")
                                
                                # Verificar se é PDF
                                if filename.lower().endswith(".pdf"):
                                    # Criar nome de arquivo temporário mais único
                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                                    temp_filename = f"temp_{timestamp}_{filename.replace(' ', '_')[:50]}.pdf"
                                    temp_filepath = os.path.join(pasta_destino, temp_filename)
                                    
                                    # Salvar arquivo temporário
                                    try:
                                        with open(temp_filepath, "wb") as f:
                                            f.write(part.get_payload(decode=True))
                                        
                                        # Aguardar um pouco para o sistema liberar o arquivo
                                        time.sleep(0.1)
                                        
                                    except Exception as e:
                                        print(f"   ❌ Erro ao salvar arquivo temporário: {e}")
                                        continue
                                    
                                    # PROCESSAR PDF COM NOVO SISTEMA V2
                                    dados_pdf = None
                                    try:
                                        print(f"   📋 Extraindo dados do PDF...")
                                        dados_pdf = self.processar_pdf_seguro(temp_filepath)

                                        # ADICIONAR VERIFICAÇÃO DE SKIP:
                                        if dados_pdf is None:
                                            print(f"   [SKIP] PULANDO: {filename}")
                                            # Remover arquivo temporário
                                            self._remover_arquivo_seguro(temp_filepath)
                                            continue  # Pular para próximo PDF
                                        
                                        if dados_pdf and dados_pdf.get("uc"):
                                            uc_pdf = dados_pdf.get("uc")
                                            print(f"   🔍 UC encontrada: {uc_pdf}")
                                            
                                            # ========== BUSCAR DADOS NA PLANILHA ==========
                                            nome_cliente = None
                                            sigla_cliente = None  # ← NOVA VARIÁVEL
                                            
                                            for id_corresp, info_corresp in correspondencias.items():
                                                if info_corresp["uc"] == uc_pdf:
                                                    nome_cliente = info_corresp["nome"]
                                                    sigla_cliente = info_corresp.get("sigla", "")  # ← OBTER SIGLA
                                                    
                                                    # Adicionar dados da planilha
                                                    dados_pdf["id_planilha"] = info_corresp["id_planilha"]
                                                    dados_pdf["nome"] = info_corresp["nome"]
                                                    dados_pdf["sigla"] = sigla_cliente  # ← ADICIONAR SIGLA AOS DADOS
                                                    dados_pdf["desconto_fatura"] = float(info_corresp["desconto_fatura"].replace(",", "."))
                                                    dados_pdf["desconto_bandeira"] = float(info_corresp["desconto_bandeira"].replace(",", "."))
                                                    dados_pdf["vencimento_consorcio"] = info_corresp["vencimento_consorcio"]
                                                    
                                                    print(f"   ✅ Cliente: {info_corresp['nome']} | Sigla: {sigla_cliente}")
                                                    break
                                            
                                            # ========== VERIFICAÇÃO DE SIGLA ==========
                                            eh_cliente_cla = (sigla_cliente == "CLA")
                                            
                                            if eh_cliente_cla:
                                                print(f"   🎯 CLIENTE CLA - Prosseguindo com cálculos AUPUS")
                                            else:
                                                print(f"   ⏭️ CLIENTE NÃO-CLA (sigla: {sigla_cliente}) - Apenas extração")
                                            
                                            # Definir nome do arquivo final
                                            if nome_cliente:
                                                # Limpar nome do cliente para evitar caracteres problemáticos
                                                nome_limpo = "".join(c for c in nome_cliente if c.isalnum() or c in (' ', '-', '_')).strip()
                                                novo_nome = f"{uc_pdf}_{nome_limpo}.pdf"
                                            else:
                                                novo_nome = f"{uc_pdf}_{timestamp}.pdf"
                                                print(f"   ⚠️ UC {uc_pdf} não encontrada na planilha")
                                            
                                            novo_caminho = os.path.join(pasta_destino, novo_nome)
                                            
                                            # Verificar se já existe
                                            if os.path.exists(novo_caminho):
                                                self._remover_arquivo_seguro(temp_filepath)
                                                total_ignorados += 1
                                                print(f"   ⏭️ IGNORADO - Arquivo já existe: {novo_nome}")
                                                continue
                                            
                                            # MOVER arquivo com nova função mais robusta
                                            print(f"   📁 Movendo arquivo para: {novo_nome}")
                                            if self._mover_arquivo_seguro(temp_filepath, novo_caminho):
                                                # Arquivo movido com sucesso
                                                dados_pdf["Arquivo"] = novo_nome
                                                
                                                # ========== APLICAR CÁLCULOS AUPUS APENAS PARA CLA ==========
                                                if eh_cliente_cla:
                                                    try:
                                                        print(f"   🧮 Aplicando cálculos AUPUS...")
                                                        dados_pdf = self.calculadora.calcular_valores_aupus(dados_pdf)
                                                        dados_extraidos.append(dados_pdf)  # ← ADICIONAR À LISTA CLA
                                                        total_cla += 1
                                                        print(f"   ✅ PDF CLA processado: {novo_nome}")
                                                    except Exception as calc_err:
                                                        print(f"   ⚠️ Erro nos cálculos AUPUS: {calc_err}")
                                                        # Mesmo com erro, adicionar aos dados CLA
                                                        dados_extraidos.append(dados_pdf)
                                                        total_cla += 1
                                                else:
                                                    # ========== CLIENTE NÃO-CLA: APENAS SALVAR DADOS ==========
                                                    dados_nao_cla.append(dados_pdf)  # ← ADICIONAR À LISTA NÃO-CLA
                                                    total_nao_cla += 1
                                                    print(f"   📋 PDF não-CLA salvo: {novo_nome}")
                                                
                                                total_baixados += 1
                                            else:
                                                print(f"   ❌ Não foi possível mover arquivo final")
                                                # Tentar remover o temporário
                                                self._remover_arquivo_seguro(temp_filepath)
                                        
                                        else:
                                            # Não conseguiu extrair UC
                                            novo_nome = f"sem_uc_{timestamp}.pdf"
                                            novo_caminho = os.path.join(pasta_destino, novo_nome)
                                            
                                            if self._mover_arquivo_seguro(temp_filepath, novo_caminho):
                                                total_baixados += 1
                                                print(f"   ⚠️ Não foi possível extrair UC. Salvo como: {novo_nome}")
                                            else:
                                                self._remover_arquivo_seguro(temp_filepath)
                                            
                                    except Exception as e:
                                        # Erro ao processar
                                        print(f"   ❌ Erro ao processar PDF: {e}")
                                        novo_nome = f"erro_{timestamp}.pdf"
                                        novo_caminho = os.path.join(pasta_destino, novo_nome)
                                        
                                        if self._mover_arquivo_seguro(temp_filepath, novo_caminho):
                                            total_baixados += 1
                                            print(f"   ⚠️ Arquivo salvo com erro: {novo_nome}")
                                        else:
                                            self._remover_arquivo_seguro(temp_filepath)
                                    
            except Exception as e:
                print(f"   ❌ Erro ao processar email: {e}")
                continue
        
        # ========== RELATÓRIO FINAL COM ESTATÍSTICAS ==========
        print(f"\n📊 Resumo Final:")
        print(f"   📥 PDFs processados: {total_baixados}")
        print(f"   ⏭️ PDFs ignorados: {total_ignorados}")
        print(f"   🎯 Clientes CLA (com AUPUS): {total_cla}")
        print(f"   📋 Clientes não-CLA (sem AUPUS): {total_nao_cla}")
        print(f"   📊 Total dados extraídos: {len(dados_extraidos) + len(dados_nao_cla)}")
        
        # ========== RETORNAR APENAS DADOS CLA PARA EXPORTAÇÃO ==========
        return dados_extraidos  # ← SÓ RETORNA CLIENTES CLA

    # ========== NOVOS MÉTODOS PARA PROCESSAMENTO VIA PASTA LOCAL ==========

    def buscar_pdfs_na_pasta(self, caminho_pasta):
        """
        ⭐ NOVO: Busca todos os PDFs em uma pasta local
        """
        try:
            if not os.path.exists(caminho_pasta):
                print(f"❌ Pasta não encontrada: {caminho_pasta}")
                return []
            
            # Buscar todos os arquivos PDF na pasta (incluindo subpastas)
            padroes_pdf = [
                os.path.join(caminho_pasta, "*.pdf"),
                os.path.join(caminho_pasta, "**", "*.pdf")  # Buscar em subpastas também
            ]
            
            arquivos_pdf = []
            for padrao in padroes_pdf:
                arquivos_encontrados = glob.glob(padrao, recursive=True)
                arquivos_pdf.extend(arquivos_encontrados)
            
            # Remover duplicatas e ordenar
            arquivos_pdf = sorted(list(set(arquivos_pdf)))
            
            print(f"📁 Pasta: {caminho_pasta}")
            print(f"📄 Encontrados {len(arquivos_pdf)} arquivos PDF")
            
            return arquivos_pdf
            
        except Exception as e:
            print(f"❌ Erro ao buscar PDFs na pasta: {e}")
            return []

    def processar_pdfs_da_pasta(self, arquivos_pdf, correspondencias):
        """
        ⭐ NOVO: Processa PDFs que já estão baixados em uma pasta
        """
        dados_extraidos = []
        dados_nao_cla = []
        total_processados = 0
        total_cla = 0
        total_nao_cla = 0
        total_erros = 0
        
        print(f"\n📋 Processando {len(arquivos_pdf)} arquivos PDF...")
        
        for i, arquivo_pdf in enumerate(arquivos_pdf, 1):
            try:
                print(f"\n📄 [{i}/{len(arquivos_pdf)}] Processando: {os.path.basename(arquivo_pdf)}")
                
                # EXTRAIR DADOS DO PDF COM NOVO SISTEMA V2
                dados_pdf = self.processar_pdf_seguro(arquivo_pdf)

                # ADICIONAR VERIFICAÇÃO DE SKIP:
                if dados_pdf is None:
                    print(f"   [SKIP] PULANDO: {os.path.basename(arquivo_pdf)}")
                    continue  # Pular para próximo PDF

                if dados_pdf and dados_pdf.get("uc"):
                    uc_pdf = dados_pdf.get("uc")
                    print(f"   🔍 UC encontrada: {uc_pdf}")
                    
                    # ========== BUSCAR DADOS NA PLANILHA ==========
                    nome_cliente = None
                    sigla_cliente = None
                    
                    for id_corresp, info_corresp in correspondencias.items():
                        if info_corresp["uc"] == uc_pdf:
                            nome_cliente = info_corresp["nome"]
                            sigla_cliente = info_corresp.get("sigla", "")
                            
                            # Adicionar dados da planilha
                            dados_pdf["id_planilha"] = info_corresp["id_planilha"]
                            dados_pdf["nome"] = info_corresp["nome"]
                            dados_pdf["sigla"] = sigla_cliente
                            dados_pdf["desconto_fatura"] = float(info_corresp["desconto_fatura"].replace(",", "."))
                            dados_pdf["desconto_bandeira"] = float(info_corresp["desconto_bandeira"].replace(",", "."))
                            dados_pdf["vencimento_consorcio"] = info_corresp["vencimento_consorcio"]
                            dados_pdf["Arquivo"] = os.path.basename(arquivo_pdf)  # Nome do arquivo
                            
                            print(f"   ✅ Cliente: {info_corresp['nome']} | Sigla: {sigla_cliente}")
                            break
                    
                    if not nome_cliente:
                        print(f"   ⚠️ UC {uc_pdf} não encontrada na planilha")
                        dados_pdf["Arquivo"] = os.path.basename(arquivo_pdf)
                        dados_pdf["sigla"] = "N/A"
                    
                    # ========== VERIFICAÇÃO DE SIGLA ==========
                    eh_cliente_cla = (sigla_cliente == "CLA")
                    
                    if eh_cliente_cla:
                        print(f"   🎯 CLIENTE CLA - Aplicando cálculos AUPUS...")
                        try:
                            dados_pdf = self.calculadora.calcular_valores_aupus(dados_pdf)
                            dados_extraidos.append(dados_pdf)
                            total_cla += 1
                            print(f"   ✅ PDF CLA processado com sucesso")
                        except Exception as calc_err:
                            print(f"   ⚠️ Erro nos cálculos AUPUS: {calc_err}")
                            # Mesmo com erro, adicionar aos dados CLA
                            dados_extraidos.append(dados_pdf)
                            total_cla += 1
                    else:
                        print(f"   ⏭️ CLIENTE NÃO-CLA (sigla: {sigla_cliente}) - Sem cálculos AUPUS")
                        dados_nao_cla.append(dados_pdf)
                        total_nao_cla += 1
                    
                    total_processados += 1
                    
                else:
                    print(f"   ❌ Não foi possível extrair UC do PDF")
                    total_erros += 1
                    
            except Exception as e:
                print(f"   ❌ Erro ao processar arquivo: {e}")
                total_erros += 1
                continue
        
        # ========== RELATÓRIO FINAL ==========
        print(f"\n📊 Resumo do Processamento:")
        print(f"   📄 Arquivos processados: {total_processados}")
        print(f"   🎯 Clientes CLA (com AUPUS): {total_cla}")
        print(f"   📋 Clientes não-CLA (sem AUPUS): {total_nao_cla}")
        print(f"   ❌ Erros: {total_erros}")
        print(f"   📊 Total dados extraídos: {len(dados_extraidos) + len(dados_nao_cla)}")
        
        return dados_extraidos  # Retornar apenas dados CLA

    def processar_pdfs_pasta_local(self, caminho_pasta):
        """
        ⭐ NOVO: Função principal para processar faturas de pasta local
        """
        print(f"\n{'#'*60}")
        print(f"# SISTEMA MODULAR V2 - PROCESSAMENTO DE FATURAS PASTA LOCAL")
        print(f"# Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"# Pasta: {caminho_pasta}")
        print(f"{'#'*60}\n")
        
        try:
            # 1. Ler correspondências da planilha
            print(f"📊 Lendo planilha de controle...")
            correspondencias = ler_correspondencias_planilha(self.CAMINHO_PLANILHA)
            
            # 2. Buscar PDFs na pasta
            arquivos_pdf = self.buscar_pdfs_na_pasta(caminho_pasta)
            if not arquivos_pdf:
                print("❌ Nenhum arquivo PDF encontrado na pasta")
                return
            
            # 3. Processar PDFs
            dados_extraidos = self.processar_pdfs_da_pasta(arquivos_pdf, correspondencias)
            
            # 4. Exportar resultados APENAS PARA CLIENTES CLA
            if dados_extraidos:
                print(f"\n📊 Exportando dados de {len(dados_extraidos)} faturas CLA...")
                
                # Verificação adicional de segurança
                dados_cla_confirmados = []
                for dados in dados_extraidos:
                    if dados.get("sigla") == "CLA":
                        dados_cla_confirmados.append(dados)
                    else:
                        print(f"   ⚠️ Dados não-CLA encontrados: {dados.get('nome', 'N/A')} - Removendo")
                
                if dados_cla_confirmados:
                    print(f"   🎯 Confirmados {len(dados_cla_confirmados)} clientes CLA para exportação")
                    
                    try:
                        exportar_para_excel(dados_cla_confirmados)
                        print("✅ Exportação de clientes CLA concluída com sucesso!")
                    except Exception as export_err:
                        print(f"\n❌ ERRO NA EXPORTAÇÃO CLA:")
                        print(f"   Tipo: {type(export_err).__name__}")
                        print(f"   Mensagem: {export_err}")
                        
                        # Tentativa de correção
                        print(f"\n🔧 Tentando correção com conversão Decimal→float...")
                        dados_corrigidos = []
                        for dados in dados_cla_confirmados:
                            dados_float = self._converter_decimals_para_float(dados)
                            dados_corrigidos.append(dados_float)
                        
                        try:
                            exportar_para_excel(dados_corrigidos)
                            print("   ✅ Exportação CLA com correção bem-sucedida!")
                        except Exception as second_err:
                            print(f"   ❌ Erro persistiu: {second_err}")
                else:
                    print("   ⚠️ Nenhum cliente CLA confirmado para exportação")
            else:
                print("\n⚠️ Nenhum cliente CLA foi processado")
                
        except Exception as e:
            print(f"\n❌ Erro geral: {e}")
            
        print(f"\n{'='*60}")
        print("PROCESSAMENTO FINALIZADO")
        print(f"{'='*60}\n")

    # ========== MÉTODO ORIGINAL PARA EMAIL (MODIFICADO) ==========

    def processar_pdfs_email(self, data_inicio):
        """
        Função principal de processamento COM VERIFICAÇÃO DE SIGLA
        """
        print(f"\n{'#'*60}")
        print(f"# SISTEMA MODULAR V2 - PROCESSAMENTO DE FATURAS VIA EMAIL")
        print(f"# Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"# Data inicial busca: {data_inicio}")
        print(f"{'#'*60}\n")
        
        pasta_destino = self.criar_pasta_destino(data_inicio)
        
        try:
            # 1. Ler correspondências da planilha
            print(f"📊 Lendo planilha de controle...")
            correspondencias = ler_correspondencias_planilha(self.CAMINHO_PLANILHA)
            
            # 2. Conectar e buscar emails
            mail, emails_ids = self.buscar_emails_por_data(data_inicio)
            if not mail or not emails_ids:
                print("❌ Nenhum email encontrado ou erro na conexão")
                return
            
            # 3. Baixar e processar PDFs (agora com verificação de sigla)
            dados_extraidos = self.baixar_e_processar_pdfs(mail, emails_ids, pasta_destino, correspondencias)
            mail.logout()
            
            # 4. Exportar resultados APENAS PARA CLIENTES CLA
            if dados_extraidos:
                print(f"\n📊 Exportando dados de {len(dados_extraidos)} faturas CLA...")
                
                # ========== VERIFICAÇÃO ADICIONAL (SEGURANÇA) ==========
                dados_cla_confirmados = []
                for dados in dados_extraidos:
                    if dados.get("sigla") == "CLA":
                        dados_cla_confirmados.append(dados)
                    else:
                        print(f"   ⚠️ Dados não-CLA encontrados na lista de exportação: {dados.get('nome', 'N/A')} - Removendo")
                
                if dados_cla_confirmados:
                    print(f"   🎯 Confirmados {len(dados_cla_confirmados)} clientes CLA para exportação")
                    
                    try:
                        exportar_para_excel(dados_cla_confirmados)
                        print("✅ Exportação de clientes CLA concluída com sucesso!")
                        print(f"\n📁 PDFs salvos em: {pasta_destino}")
                    except Exception as export_err:
                        print(f"\n❌ ERRO NA EXPORTAÇÃO CLA:")
                        print(f"   Tipo: {type(export_err).__name__}")
                        print(f"   Mensagem: {export_err}")
                        
                        # Traceback completo
                        import traceback
                        print(f"\n📍 TRACEBACK:")
                        traceback.print_exc()
                        
                        # Tentativa de correção
                        print(f"\n🔧 Tentando correção com conversão Decimal→float...")
                        dados_corrigidos = []
                        for dados in dados_cla_confirmados:
                            dados_float = self._converter_decimals_para_float(dados)
                            dados_corrigidos.append(dados_float)
                        
                        try:
                            exportar_para_excel(dados_corrigidos)
                            print("   ✅ Exportação CLA com correção bem-sucedida!")
                        except Exception as second_err:
                            print(f"   ❌ Erro persistiu: {second_err}")
                else:
                    print("   ⚠️ Nenhum cliente CLA confirmado para exportação")
            else:
                print("\n⚠️ Nenhum cliente CLA foi processado")
                
        except Exception as e:
            print(f"\n❌ Erro geral: {e}")
            
        print(f"\n{'='*60}")
        print("PROCESSAMENTO FINALIZADO")
        print(f"{'='*60}\n")


def main():
    """
    ⭐ FUNÇÃO PRINCIPAL MODIFICADA: Agora oferece duas opções
    """
    processador = ProcessadorFaturasEmail()
    
    print("\nPROCESSADOR DE FATURAS - AUPUS ENERGIA")
    print("=" * 50)
    print("Escolha o modo de processamento:")
    print("1  Processar faturas do EMAIL")
    print("2  Processar faturas de PASTA LOCAL")
    print("=" * 50)
    
    while True:
        opcao = input("Digite sua opção (1 ou 2): ").strip()
        
        if opcao == "1":
            # ========== MODO EMAIL (ORIGINAL) ==========
            print("\n📧 MODO: Processamento via EMAIL")
            print("Digite a data inicial para buscar faturas")
            
            while True:
                data_inicio = input("Data (DD/MM/YYYY): ").strip()
                
                try:
                    # Validar formato da data
                    datetime.strptime(data_inicio, "%d/%m/%Y")
                    break
                except ValueError:
                    print("❌ Formato inválido! Use DD/MM/YYYY")
            
            # Executar processamento via email
            processador.processar_pdfs_email(data_inicio)
            break
            
        elif opcao == "2":
            # ========== MODO PASTA LOCAL (NOVO - SEM INPUT) ==========
            print("\n📁 MODO: Processamento de PASTA LOCAL")
            print(f"📂 Pasta configurada: {processador.CAMINHO_PASTA_LOCAL}")
            
            # Verificar se a pasta existe
            if os.path.exists(processador.CAMINHO_PASTA_LOCAL):
                if os.path.isdir(processador.CAMINHO_PASTA_LOCAL):
                    print("✅ Pasta encontrada! Iniciando processamento...")
                    # Executar processamento via pasta local
                    processador.processar_pdfs_pasta_local(processador.CAMINHO_PASTA_LOCAL)
                else:
                    print("❌ O caminho configurado não é uma pasta válida!")
            else:
                print("❌ Pasta configurada não encontrada!")
                print(f"💡 Verifique se existe: {processador.CAMINHO_PASTA_LOCAL}")
            break
            
        else:
            print("❌ Opção inválida! Digite 1 ou 2")
    
    input("\nPressione ENTER para finalizar...")


if __name__ == "__main__":
    main()