"""
Main invoice processor V2 - Modular Architecture.
CRITICAL: Maintains 100% compatibility with existing system.
Interface identical to Leitor_Faturas_PDF.py
"""

import fitz
import sys
from typing import Dict, Any, Optional
from decimal import Decimal
from pathlib import Path

# Core imports
sys.path.append(str(Path(__file__).parent.parent))
from core.fatura_classifier import FaturaClassifier
from core.data_models import (
    ClassificacaoFatura, TipoConsumidor, GrupoTarifario,
    VALORES_PADRAO, CAMPOS_CALCULADORA_AUPUS
)

# Common extractors
from extractors.common.dados_basicos_extractor import DadosBasicosExtractor
from extractors.common.impostos_extractor import ImpostosExtractor
from extractors.common.scee_extractor import SCEEExtractor
from extractors.common.financeiro_extractor import FinanceiroExtractor

# Group B extractors
from extractors.grupo_b.b_consumidor_compensado import BConsumidorCompensadoExtractor
from extractors.grupo_b.b_consumidor_simples import BConsumidorSimplesExtractor


class FaturaProcessorV2:
    """
    Main processor for invoice V2 - modular architecture.

    INTERFACE IDENTICAL to Leitor_Faturas_PDF.py
    Must return exactly the same fields with same names and types.
    """

    def __init__(self):
        self.classifier = FaturaClassifier()
        self.debug = True

        # Initialize common extractors
        self.dados_basicos_extractor = DadosBasicosExtractor()
        self.impostos_extractor = ImpostosExtractor()
        self.scee_extractor = SCEEExtractor()
        self.financeiro_extractor = FinanceiroExtractor()

    def processar_fatura(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process invoice PDF and return extracted data.

        INTERFACE IDENTICAL to Leitor_Faturas_PDF.py
        Must return exactly the same fields.

        Args:
            pdf_path: Path to PDF file to process

        Returns:
            Dictionary with extracted data using exact field names
        """
        try:
            if self.debug:
                print(f"\n{'='*60}")
                print(f"PROCESSADOR V2 - {Path(pdf_path).name}")
                print(f"{'='*60}")

            # Step 1: Classify invoice type
            classificacao = self._classify_invoice(pdf_path)

            if self.debug:
                print(f"Classificação: {classificacao.tipo_consumidor.value}")
                print(f"Grupo: {classificacao.grupo.value}")
                print(f"Modalidade: {classificacao.modalidade.value}")
                print(f"Confiança: {classificacao.confianca}")

            # Step 2: Check if supported type
            if not self._is_supported_type(classificacao):
                return self._create_skip_result(classificacao)

            # Step 3: Extract data with specific extractor
            dados = self._extract_with_specific_extractor(pdf_path, classificacao)

            # Step 4: CRITICAL - ensure compatibility
            dados_validados = self._ensure_compatibility(dados)

            # Step 5: Debug log if necessary
            if self.debug:
                self._log_extraction_summary(dados_validados, pdf_path)

            return dados_validados

        except Exception as e:
            error_msg = f"Erro processando fatura V2: {e}"
            if self.debug:
                print(f"ERRO: {error_msg}")
            return {"erro": error_msg}

    def _classify_invoice(self, pdf_path: str) -> ClassificacaoFatura:
        """Classify invoice type."""
        try:
            return self.classifier.classify_pdf(pdf_path)
        except Exception as e:
            if self.debug:
                print(f"ERRO na classificação: {e}")
            # Return default unsupported classification
            from core.data_models import ModalidadeTarifaria
            return ClassificacaoFatura(
                tipo_consumidor=TipoConsumidor.UNSUPPORTED,
                grupo=GrupoTarifario.B,
                modalidade=ModalidadeTarifaria.CONVENCIONAL,
                confianca="baixa"
            )

    def _is_supported_type(self, classificacao: ClassificacaoFatura) -> bool:
        """Check if invoice type is supported in current implementation."""
        return classificacao.tipo_consumidor in [
            TipoConsumidor.B_CONSUMIDOR_COMPENSADO,
            TipoConsumidor.B_CONSUMIDOR_SIMPLES
        ]

    def _create_skip_result(self, classificacao: ClassificacaoFatura) -> Dict[str, Any]:
        """Create result for unsupported invoice types."""
        return {
            'skip_processing': True,
            'skip_reason': f"Tipo não suportado: {classificacao.tipo_consumidor.value}",
            'uc': None  # For compatibility
        }

    def _extract_with_specific_extractor(self, pdf_path: str, classificacao: ClassificacaoFatura) -> Dict[str, Any]:
        """Extract data using specific extractor for invoice type."""
        dados = {}

        try:
            # Extract common data first
            dados.update(self._extract_common_data(pdf_path))

            # Extract with specific extractor
            if classificacao.tipo_consumidor == TipoConsumidor.B_CONSUMIDOR_COMPENSADO:
                extractor = BConsumidorCompensadoExtractor()
                dados_especificos = extractor.extract(pdf_path)
                dados.update(dados_especificos)

            elif classificacao.tipo_consumidor == TipoConsumidor.B_CONSUMIDOR_SIMPLES:
                extractor = BConsumidorSimplesExtractor()
                dados_especificos = extractor.extract(pdf_path)
                dados.update(dados_especificos)

            # Store classification info
            dados['_classificacao'] = classificacao
            dados['grupo'] = classificacao.grupo.value
            dados['modalidade_tarifaria'] = classificacao.modalidade.value

        except Exception as e:
            if self.debug:
                print(f"ERRO na extração específica: {e}")
            dados['erro_extracao'] = str(e)

        return dados

    def _extract_common_data(self, pdf_path: str) -> Dict[str, Any]:
        """Extract common data using common extractors."""
        dados = {}

        try:
            # Read full PDF text for common extractors
            texto_completo = self._extract_full_text(pdf_path)

            if self.debug:
                print(f"Texto extraído: {len(texto_completo)} caracteres")

            # Extract basic data
            dados_basicos = self.dados_basicos_extractor.extract_basic_data(texto_completo)
            dados.update(dados_basicos)

            # Extract tax data
            dados_impostos = self.impostos_extractor.extract_tax_data(texto_completo)
            dados.update(dados_impostos)

            # Extract SCEE data
            dados_scee = self.scee_extractor.extract_scee_data(texto_completo)
            dados.update(dados_scee)

            # Extract financial data
            dados_financeiros = self.financeiro_extractor.extract_financial_data(texto_completo)
            dados.update(dados_financeiros)

        except Exception as e:
            if self.debug:
                print(f"ERRO na extração comum: {e}")
            dados['erro_comum'] = str(e)

        return dados

    def _extract_full_text(self, pdf_path: str) -> str:
        """Extract full text from PDF for text-based extractors."""
        try:
            doc = fitz.open(pdf_path)
            texto_completo = ""

            for page_num in range(doc.page_count):
                page = doc[page_num]
                texto_completo += page.get_text()
                texto_completo += "\n"

            doc.close()
            return texto_completo

        except Exception as e:
            if self.debug:
                print(f"ERRO extraindo texto: {e}")
            return ""

    def _ensure_compatibility(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """
        CRITICAL FUNCTION: Ensure compatibility with existing system.

        Must guarantee that all expected fields exist with correct types.
        Consultar CAMPOS_OBRIGATORIOS em data_models.py
        """
        dados_finais = dados.copy()

        try:
            # Apply default values for missing fields
            for field, default_value in VALORES_PADRAO.items():
                if field not in dados_finais:
                    dados_finais[field] = default_value

            # Ensure critical fields for Calculadora_AUPUS.py
            self._ensure_calculadora_fields(dados_finais)

            # Ensure numeric fields are Decimal type
            self._ensure_decimal_types(dados_finais)

            # Clean up internal fields
            self._cleanup_internal_fields(dados_finais)

            # Final validation
            self._validate_final_data(dados_finais)

        except Exception as e:
            if self.debug:
                print(f"ERRO garantindo compatibilidade: {e}")
            dados_finais['erro_compatibilidade'] = str(e)

        return dados_finais

    def _ensure_calculadora_fields(self, dados: Dict[str, Any]):
        """Ensure all fields required by Calculadora_AUPUS.py exist."""
        for campo in CAMPOS_CALCULADORA_AUPUS:
            if campo not in dados:
                if campo in VALORES_PADRAO:
                    dados[campo] = VALORES_PADRAO[campo]
                elif 'aliquota' in campo.lower():
                    dados[campo] = Decimal('0')
                elif 'valor' in campo.lower() or 'consumo' in campo.lower():
                    dados[campo] = Decimal('0')
                else:
                    dados[campo] = ""

    def _ensure_decimal_types(self, dados: Dict[str, Any]):
        """Ensure numeric fields are Decimal type."""
        numeric_fields = [
            'consumo', 'consumo_comp', 'consumo_n_comp',
            'valor_concessionaria', 'valor_consumo', 'valor_bandeira',
            'saldo', 'excedente_recebido', 'credito_recebido',
            'energia_injetada', 'geracao_ciclo',
            'aliquota_icms', 'aliquota_pis', 'aliquota_cofins',
            'valor_icms', 'valor_pis', 'valor_cofins',
            'valor_juros', 'valor_multa', 'valor_iluminacao'
        ]

        for field in numeric_fields:
            if field in dados and dados[field] is not None:
                if not isinstance(dados[field], Decimal):
                    try:
                        dados[field] = Decimal(str(dados[field]))
                    except:
                        dados[field] = Decimal('0')

    def _cleanup_internal_fields(self, dados: Dict[str, Any]):
        """Remove internal fields that should not be in final result."""
        internal_fields = [
            '_classificacao', '_geracao_ugs_raw', '_excedente_ugs_raw',
            'erro_extracao', 'erro_comum', 'erro_compatibilidade'
        ]

        for field in internal_fields:
            dados.pop(field, None)

    def _validate_final_data(self, dados: Dict[str, Any]):
        """Final validation of extracted data."""
        # Ensure UC exists (critical for system)
        if 'uc' not in dados or not dados['uc']:
            if self.debug:
                print("AVISO: UC não encontrada!")
            dados['uc'] = None

        # Ensure consumption data makes sense
        if 'consumo' in dados and dados['consumo'] is not None:
            if dados['consumo'] < Decimal('0'):
                if self.debug:
                    print("AVISO: Consumo negativo detectado")
                dados['consumo'] = Decimal('0')

    def _log_extraction_summary(self, dados: Dict[str, Any], pdf_path: str):
        """Log extraction summary for debugging."""
        if not self.debug:
            return

        print(f"\n{'='*60}")
        print(f"RESUMO EXTRAÇÃO V2 - {Path(pdf_path).name}")
        print(f"{'='*60}")

        # Basic info
        print(f"UC: {dados.get('uc', 'NÃO ENCONTRADA')}")
        print(f"Grupo: {dados.get('grupo', 'N/A')}")
        print(f"Modalidade: {dados.get('modalidade_tarifaria', 'N/A')}")

        # Consumption
        consumo = dados.get('consumo', 0)
        consumo_comp = dados.get('consumo_comp', 0)
        consumo_n_comp = dados.get('consumo_n_comp', 0)
        print(f"Consumo Total: {consumo} kWh")
        print(f"Compensado: {consumo_comp} kWh")
        print(f"Não Compensado: {consumo_n_comp} kWh")

        # SCEE
        saldo = dados.get('saldo', 0)
        excedente = dados.get('excedente_recebido', 0)
        print(f"Saldo SCEE: {saldo} kWh")
        print(f"Excedente: {excedente} kWh")

        # Taxes
        icms = dados.get('aliquota_icms', 0)
        pis = dados.get('aliquota_pis', 0)
        cofins = dados.get('aliquota_cofins', 0)
        if isinstance(icms, Decimal):
            print(f"ICMS: {float(icms)*100:.2f}%")
        if isinstance(pis, Decimal):
            print(f"PIS: {float(pis)*100:.2f}%")
        if isinstance(cofins, Decimal):
            print(f"COFINS: {float(cofins)*100:.2f}%")

        # Count extracted fields
        non_empty_fields = [k for k, v in dados.items()
                           if v is not None and v != "" and v != Decimal('0')]
        print(f"\nTotal de campos extraídos: {len(non_empty_fields)}")

        print(f"{'='*60}")

    # Compatibility methods (maintain interface)
    def processar_fatura_email(self, pdf_path: str) -> Dict[str, Any]:
        """Alias for compatibility with email processing."""
        return self.processar_fatura(pdf_path)

    def extrair_dados_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Alias for compatibility with direct PDF processing."""
        return self.processar_fatura(pdf_path)