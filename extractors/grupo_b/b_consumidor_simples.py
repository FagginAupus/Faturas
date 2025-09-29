"""
Group B Simple Consumer Extractor (without SCEE compensation).
Similar to b_consumidor_compensado.py but sets SCEE fields to zero.
CRITICAL: Maintains exact field names for compatibility with Calculadora_AUPUS.py
"""

import re
import fitz
from typing import Dict, Any, List, Optional
from decimal import Decimal
from pathlib import Path

# Import base extractor and utilities
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from core.base_extractor import BaseExtractor, safe_decimal_conversion


class BConsumidorSimplesExtractor(BaseExtractor):
    """
    Extractor for Group B simple consumers (without SCEE compensation).
    Handles both CONVENCIONAL and BRANCA tariff modalities.

    CRITICAL FIELDS EXTRACTED (maintain exact names):
    - consumo
    - rs_consumo, valor_consumo
    - For BRANCA: consumo_p, consumo_fp, consumo_hi
    - Sets SCEE fields to zero: saldo=0, excedente_recebido=0, etc.
    """

    def __init__(self):
        super().__init__()

        # General consumption (CONVENCIONAL)
        self.consumo_geral: Optional[Decimal] = None
        self.rs_consumo_geral: Optional[Decimal] = None
        self.valor_consumo_geral: Optional[Decimal] = None

        # BRANCA consumption by posto
        self.consumo_postos: Dict[str, Decimal] = {}
        self.rs_consumo_postos: Dict[str, Decimal] = {}
        self.valor_consumo_postos: Dict[str, Decimal] = {}

        # Bandeiras
        self.bandeira_codigo = 0  # 0=Verde, 1=Vermelha, 2=Amarela, 3=Vermelha+Amarela

        # Financial totals
        self.juros_total = Decimal('0')
        self.multa_total = Decimal('0')

    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """
        Main extraction method for Group B simple consumers.

        Returns:
            Dictionary with EXACT same field names as Leitor_Faturas_PDF.py
            Sets all SCEE fields to Decimal('0') for compatibility
        """
        try:
            # Open PDF and extract text
            doc = self._open_pdf(pdf_path)

            # Reset accumulators
            self._reset_accumulators()

            # Process all pages
            for page_num in range(doc.page_count):
                page = doc[page_num]
                self._processar_pagina(page, page_num, doc)

            # Finalize and build result
            dados = self._finalizar_extracao()

            # Close PDF safely
            self._close_pdf_safely(doc)

            # Ensure required fields and compatibility
            dados_finais = self._ensure_required_fields(dados)

            if self.debug:
                self._imprimir_relatorio_extracao(pdf_path, dados_finais)

            return dados_finais

        except Exception as e:
            self._error_print(f"Erro na extração B simples: {e}")
            return {"erro": str(e)}

    def _reset_accumulators(self):
        """Reset all accumulators for fresh extraction."""
        self.consumo_postos.clear()
        self.rs_consumo_postos.clear()
        self.valor_consumo_postos.clear()

        self.consumo_geral = None
        self.rs_consumo_geral = None
        self.valor_consumo_geral = None

        self.juros_total = Decimal('0')
        self.multa_total = Decimal('0')
        self.bandeira_codigo = 0

    def _processar_pagina(self, page: fitz.Page, page_num: int, doc: fitz.Document):
        """
        Process a single PDF page.
        Similar to compensado but focuses only on basic consumption.
        """
        try:
            # Extract text blocks with position information
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if text:
                                # Get block position
                                bbox = span["bbox"]
                                block_info = {
                                    'x0': bbox[0], 'y0': bbox[1],
                                    'x1': bbox[2], 'y1': bbox[3]
                                }

                                # Process text block
                                self._processar_bloco_texto(text, block_info)

        except Exception as e:
            if self.debug:
                print(f"AVISO: Erro processando página {page_num}: {e}")

    def _processar_bloco_texto(self, text: str, block_info: Dict):
        """
        Process a text block and extract relevant data.
        Focuses on consumption and financial data only.
        """
        x0, y0 = block_info.get('x0', 0), block_info.get('y0', 0)

        # Check if within main table area (from original system)
        if not (30 <= x0 <= 650 and 350 <= y0 <= 755):
            return

        parts = text.split()
        if not parts:
            return

        # Identify line type and process accordingly
        if self._is_consumption_line(text, parts):
            self._processar_linha_consumo(text, parts)
        elif self._is_bandeira_line(text, parts):
            self._processar_linha_bandeira(text, parts)
        elif self._is_financial_line(text, parts):
            self._processar_linha_financeira(text, parts)

    def _is_consumption_line(self, text: str, parts: List[str]) -> bool:
        """Check if line contains consumption data."""
        # Must have kWh indicator and numeric values
        has_kwh = any(indicator in text.upper() for indicator in ["KWH", "kWh"])
        has_numeric = any(self._is_numeric_value(part) for part in parts)

        # Exclude SCEE-related lines for simple consumers
        scee_terms = ["COMPENSADO", "EXCEDENTE", "SCEE", "CRÉDITO", "CREDITO"]
        has_scee = any(term in text.upper() for term in scee_terms)

        return has_kwh and has_numeric and len(parts) >= 5 and not has_scee

    def _is_bandeira_line(self, text: str, parts: List[str]) -> bool:
        """Check if line contains bandeira tarifária data."""
        bandeira_indicators = ["BANDEIRA", "ADICIONAL"]
        return any(indicator in text.upper() for indicator in bandeira_indicators) and len(parts) >= 4

    def _is_financial_line(self, text: str, parts: List[str]) -> bool:
        """Check if line contains financial data (juros, multa, etc)."""
        financial_indicators = ["JUROS", "MULTA", "ILUMINAÇÃO", "ILUMINACAO"]
        return any(indicator in text.upper() for indicator in financial_indicators)

    def _processar_linha_consumo(self, text: str, parts: List[str]):
        """
        Process consumption line.
        Similar to compensado but without SCEE logic.
        """
        try:
            kwh_index = self._find_correct_kwh_index(parts)
            if kwh_index == -1:
                return

            # Extract basic values
            if kwh_index + 4 >= len(parts):
                return

            quantidade = safe_decimal_conversion(parts[kwh_index + 2].replace('.', ''))
            tarifa = safe_decimal_conversion(parts[kwh_index + 1])
            valor = safe_decimal_conversion(parts[kwh_index + 4])

            # Extract tarifa sem imposto if available
            tarifa_sem_imposto = Decimal('0')
            if kwh_index + 7 < len(parts):
                tarifa_sem_imposto = safe_decimal_conversion(parts[kwh_index + 7])

            # Identify posto (for BRANCA)
            posto = self._identificar_posto(text)

            if self.debug:
                print(f"DEBUG: Consumo simples {posto}: {quantidade} kWh x R$ {tarifa} = R$ {valor}")

            # Store data based on posto
            self._armazenar_dados_consumo(posto, quantidade, tarifa, valor, tarifa_sem_imposto)

        except Exception as e:
            if self.debug:
                print(f"AVISO: Erro processando linha consumo: {e}")

    def _find_correct_kwh_index(self, parts: List[str]) -> int:
        """Find the correct kWh index in parts list."""
        for i, part in enumerate(parts):
            if part.upper() in ['KWH', 'kWh']:
                return i
        return -1

    def _identificar_posto(self, text: str) -> str:
        """
        Identify posto horário for BRANCA tariff.
        Returns: 'p'|'fp'|'hi'|'' where '' means CONVENCIONAL
        """
        text_upper = text.upper()

        # Check for posto horário (BRANCA tariff)
        if "PONTA" in text_upper and "FORA" not in text_upper:
            return "p"
        elif "FORA PONTA" in text_upper or "FORA-PONTA" in text_upper:
            return "fp"
        elif "INTERMEDIÁRIO" in text_upper or "INTERMEDIARIO" in text_upper:
            return "hi"
        else:
            return ""

    def _armazenar_dados_consumo(self, posto: str, quantidade: Decimal,
                                tarifa: Decimal, valor: Decimal, tarifa_si: Decimal):
        """Store consumption data in appropriate accumulators."""
        if posto:
            # BRANCA tariff - store by posto
            campo_consumo = f"consumo_{posto}"
            campo_tarifa = f"rs_consumo_{posto}"
            campo_valor = f"valor_consumo_{posto}"

            self.consumo_postos[campo_consumo] = quantidade
            self.rs_consumo_postos[campo_tarifa] = tarifa
            self.valor_consumo_postos[campo_valor] = valor

            # Store tarifa sem imposto if available
            if tarifa_si > 0:
                self.rs_consumo_postos[f"{campo_tarifa}_si"] = tarifa_si
        else:
            # CONVENCIONAL tariff - general consumption
            self.consumo_geral = quantidade
            self.rs_consumo_geral = tarifa
            self.valor_consumo_geral = valor

    def _processar_linha_bandeira(self, text: str, parts: List[str]):
        """Process bandeira tarifária line."""
        try:
            if "AMARELA" in text.upper():
                self._extrair_bandeira("amarela", text, parts)
            elif "VERMELHA" in text.upper():
                self._extrair_bandeira("vermelha", text, parts)
        except Exception as e:
            if self.debug:
                print(f"AVISO: Erro processando bandeira: {e}")

    def _extrair_bandeira(self, tipo: str, text: str, parts: List[str]):
        """Extract bandeira data."""
        try:
            # Find numeric value in parts for bandeira cost
            for part in parts:
                if self._is_monetary_value(part):
                    valor = safe_decimal_conversion(part)

                    # Store bandeira data based on type
                    if tipo == "amarela":
                        self.bandeira_codigo = 2
                        if self.debug:
                            print(f"   OK: Bandeira Amarela detectada: R$ {valor}")
                    elif tipo == "vermelha":
                        if self.bandeira_codigo == 2:
                            self.bandeira_codigo = 3  # Vermelha + Amarela
                        else:
                            self.bandeira_codigo = 1
                        if self.debug:
                            print(f"   OK: Bandeira Vermelha detectada: R$ {valor}")
                    break
        except Exception as e:
            if self.debug:
                print(f"AVISO: Erro extraindo bandeira: {e}")

    def _processar_linha_financeira(self, text: str, parts: List[str]):
        """Process financial line (juros, multa, iluminação)."""
        if "JUROS" in text.upper():
            self._extrair_juros(text, parts)
        elif "MULTA" in text.upper():
            self._extrair_multa(text, parts)

    def _extrair_juros(self, text: str, parts: List[str]):
        """Extract juros data."""
        for part in parts:
            if self._is_monetary_value(part):
                valor = safe_decimal_conversion(part)
                self.juros_total += valor
                if self.debug:
                    print(f"   OK: Juros detectado: R$ {valor}")
                break

    def _extrair_multa(self, text: str, parts: List[str]):
        """Extract multa data."""
        for part in parts:
            if self._is_monetary_value(part):
                valor = safe_decimal_conversion(part)
                self.multa_total += valor
                if self.debug:
                    print(f"   OK: Multa detectada: R$ {valor}")
                break

    def _is_numeric_value(self, text: str) -> bool:
        """Check if text represents a numeric value."""
        try:
            cleaned = text.replace('.', '').replace(',', '.').replace(' ', '')
            float(cleaned)
            return True
        except:
            return False

    def _is_monetary_value(self, text: str) -> bool:
        """Check if text represents a monetary value."""
        return self._is_numeric_value(text) and (',' in text or len(text.replace('.', '')) > 2)

    def _finalizar_extracao(self) -> Dict[str, Any]:
        """
        Finalize extraction and build result dictionary.
        Maintains EXACT field names and sets SCEE fields to zero.
        """
        result = {}

        # Add consumption data
        result.update(self.consumo_postos)
        result.update(self.rs_consumo_postos)
        result.update(self.valor_consumo_postos)

        # Add general consumption
        if self.consumo_geral:
            result['consumo'] = self.consumo_geral
            result['rs_consumo'] = self.rs_consumo_geral
            result['valor_consumo'] = self.valor_consumo_geral

        # Add financial data
        if self.juros_total > 0:
            result['valor_juros'] = self.juros_total
        if self.multa_total > 0:
            result['valor_multa'] = self.multa_total

        # Apply totalization logic
        self._finalizar_totalizacoes(result)

        # Set SCEE fields to zero for compatibility
        self._definir_campos_scee_zero(result)

        return result

    def _finalizar_totalizacoes(self, result: Dict[str, Any]):
        """
        Apply totalization logic for BRANCA tariff.
        Similar to compensado but simpler.
        """
        def to_decimal(value):
            if isinstance(value, Decimal):
                return value
            try:
                return Decimal(str(value)) if value else Decimal('0')
            except:
                return Decimal('0')

        # GRUPO B - TARIFA BRANCA totalization
        postos_b = ['p', 'fp', 'hi']

        # Calculate total consumption from postos if needed
        if 'consumo' not in result or result.get('consumo', Decimal('0')) == Decimal('0'):
            consumo_p = to_decimal(result.get('consumo_p', 0))
            consumo_fp = to_decimal(result.get('consumo_fp', 0))
            consumo_hi = to_decimal(result.get('consumo_hi', 0))

            if consumo_p > 0 or consumo_fp > 0 or consumo_hi > 0:
                result['consumo'] = consumo_p + consumo_fp + consumo_hi
                if self.debug:
                    print(f"OK: Consumo total B Branca: {result['consumo']}")

    def _definir_campos_scee_zero(self, result: Dict[str, Any]):
        """
        Set all SCEE fields to zero for simple consumers.
        CRITICAL for compatibility with Calculadora_AUPUS.py
        """
        scee_fields = [
            'saldo', 'excedente_recebido', 'credito_recebido',
            'energia_injetada', 'geracao_ciclo',
            'consumo_comp', 'consumo_n_comp',
            'rs_consumo_comp', 'rs_consumo_n_comp',
            'valor_consumo_comp', 'valor_consumo_n_comp',
            'uc_geradora_1', 'uc_geradora_2'
        ]

        for field in scee_fields:
            if field.endswith('_1') or field.endswith('_2'):
                result[field] = ""  # String fields
            else:
                result[field] = Decimal('0')  # Numeric fields

        # BRANCA specific SCEE fields
        postos = ['p', 'fp', 'hi']
        for posto in postos:
            for prefix in ['consumo_comp', 'consumo_n_comp', 'rs_consumo_comp', 'rs_consumo_n_comp', 'valor_consumo_comp', 'valor_consumo_n_comp']:
                field = f"{prefix}_{posto}"
                result[field] = Decimal('0')

        if self.debug:
            print(f"OK: Campos SCEE definidos como zero para consumidor simples")

    def _imprimir_relatorio_extracao(self, pdf_path: str, dados: Dict[str, Any]):
        """Print extraction report for debugging."""
        if not self.debug:
            return

        print(f"\n{'='*60}")
        print(f"RELATORIO EXTRACÃO B SIMPLES - {Path(pdf_path).name}")
        print(f"{'='*60}")

        # Basic consumption
        print("CONSUMO:")
        consumo_fields = [k for k in dados.keys() if 'consumo' in k.lower() and 'rs_' not in k.lower() and 'valor_' not in k.lower()]
        for field in sorted(consumo_fields):
            print(f"   {field}: {dados[field]}")

        # Verify SCEE fields are zero
        print("\nCRÍTICO - SCEE (devem ser zero):")
        scee_check = ['saldo', 'excedente_recebido', 'consumo_comp', 'consumo_n_comp']
        for field in scee_check:
            if field in dados:
                print(f"   {field}: {dados[field]}")

        print(f"{'='*60}")

    def extract_basic_data(self, texto_completo: str) -> Dict[str, Any]:
        """Extract basic invoice data using Common Extractor."""
        from extractors.common.dados_basicos_extractor import DadosBasicosExtractor
        extractor = DadosBasicosExtractor()
        return extractor.extract_basic_data(texto_completo)

    def extract_tax_data(self, texto_completo: str) -> Dict[str, Any]:
        """Extract tax data using Common Extractor."""
        from extractors.common.impostos_extractor import ImpostosExtractor
        extractor = ImpostosExtractor()
        return extractor.extract_tax_data(texto_completo)

    def extract_financial_data(self, texto_completo: str) -> Dict[str, Any]:
        """Extract financial data using Common Extractor."""
        from extractors.common.financeiro_extractor import FinanceiroExtractor
        extractor = FinanceiroExtractor()
        return extractor.extract_financial_data(texto_completo)

    def extract_complete(self, pdf_path: str) -> Dict[str, Any]:
        """
        Complete extraction using all Common Extractors + Group B simple logic.
        This method combines data from all extractors for complete compatibility.
        """
        try:
            # Extract full text from PDF
            doc = self._open_pdf(pdf_path)
            texto_completo = ""

            for page_num in range(doc.page_count):
                page = doc[page_num]
                texto_completo += page.get_text()

            self._close_pdf_safely(doc)

            # Use Common Extractors for shared data
            dados_basicos = self.extract_basic_data(texto_completo)
            dados_impostos = self.extract_tax_data(texto_completo)
            dados_financeiros = self.extract_financial_data(texto_completo)

            # Extract Group B specific consumption data
            dados_consumo = self.extract(pdf_path)

            # Merge all data
            resultado_final = {}
            resultado_final.update(dados_basicos)
            resultado_final.update(dados_impostos)
            resultado_final.update(dados_financeiros)
            resultado_final.update(dados_consumo)

            # Ensure bandeira code
            resultado_final['bandeira_codigo'] = self.bandeira_codigo

            if self.debug:
                print(f"[B_SIMPLES] Extração completa: {len(resultado_final)} campos")

            return resultado_final

        except Exception as e:
            self._error_print(f"Erro na extração completa B simples: {e}")
            return {"erro": str(e)}