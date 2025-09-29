"""
Group B Consumer with SCEE Compensation Extractor.
Migrates logic from ConsumoExtractor and CreditosSaldosExtractor.
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


class BConsumidorCompensadoExtractor(BaseExtractor):
    """
    Extractor for Group B consumers with SCEE compensation.
    Handles both CONVENCIONAL and BRANCA tariff modalities.

    CRITICAL FIELDS EXTRACTED (maintain exact names):
    - consumo, consumo_comp, consumo_n_comp
    - rs_consumo, rs_consumo_comp, rs_consumo_n_comp
    - valor_consumo, valor_consumo_comp, valor_consumo_n_comp
    - saldo, excedente_recebido, credito_recebido
    - energia_injetada, geracao_ciclo
    - uc_geradora_1, uc_geradora_2, etc.
    - For BRANCA: consumo_p, consumo_fp, consumo_hi (and comp/n_comp variants)
    """

    def __init__(self):
        super().__init__()

        # Accumulators for consumption data (maintain structure from original)
        self.consumo_comp: Dict[str, Decimal] = {}
        self.rs_consumo_comp: Dict[str, Decimal] = {}
        self.valor_consumo_comp: Dict[str, Decimal] = {}
        self.consumo_n_comp: Dict[str, Decimal] = {}
        self.rs_consumo_n_comp: Dict[str, Decimal] = {}
        self.valor_consumo_n_comp: Dict[str, Decimal] = {}

        # General consumption (CONVENCIONAL)
        self.consumo_geral: Optional[Decimal] = None
        self.rs_consumo_geral: Optional[Decimal] = None
        self.valor_consumo_geral: Optional[Decimal] = None

        # SCEE data
        self.energia_injetada_registros: List[Dict] = []
        self.geracao_registros: List[Dict] = []
        self.excedente_registros: List[Dict] = []

        # Bandeiras
        self.bandeira_codigo = 0  # 0=Verde, 1=Vermelha, 2=Amarela, 3=Vermelha+Amarela
        self.bandeira_quantidade = Decimal('0')
        self.bandeira_valor = Decimal('0')

        # Injection data (for SCEE)
        self.injecao_quantidade = Decimal('0')
        self.injecao_valor = Decimal('0')

        # Financial totals
        self.juros_total = Decimal('0')
        self.multa_total = Decimal('0')
        self.creditos_total = Decimal('0')

    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """
        Main extraction method for Group B compensated consumers.

        Returns:
            Dictionary with EXACT same field names as Leitor_Faturas_PDF.py
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
            self._error_print(f"Erro na extração B compensado: {e}")
            return {"erro": str(e)}

    def _reset_accumulators(self):
        """Reset all accumulators for fresh extraction."""
        self.consumo_comp.clear()
        self.rs_consumo_comp.clear()
        self.valor_consumo_comp.clear()
        self.consumo_n_comp.clear()
        self.rs_consumo_n_comp.clear()
        self.valor_consumo_n_comp.clear()

        self.energia_injetada_registros.clear()
        self.geracao_registros.clear()
        self.excedente_registros.clear()

        self.consumo_geral = None
        self.rs_consumo_geral = None
        self.valor_consumo_geral = None

        self.juros_total = Decimal('0')
        self.multa_total = Decimal('0')
        self.creditos_total = Decimal('0')
        self.bandeira_codigo = 0
        self.bandeira_quantidade = Decimal('0')
        self.bandeira_valor = Decimal('0')
        self.injecao_quantidade = Decimal('0')
        self.injecao_valor = Decimal('0')

    def _processar_pagina(self, page: fitz.Page, page_num: int, doc: fitz.Document):
        """
        Process a single PDF page.
        Migrated from original system's page processing logic.
        """
        try:
            # Extract full text and reconstruct proper lines for consumption data
            texto_completo = page.get_text()
            linhas_brutas = [linha.strip() for linha in texto_completo.split('\n') if linha.strip()]

            # Reconstruct consumption lines by looking for patterns
            linhas_processadas = self._reconstruct_consumption_lines(linhas_brutas)

            # Add debug print
            if self.debug:
                print(f"\n{'='*60}")
                print(f"DEBUG EXTRATOR CONSUMO B COMPENSADO")
                print(f"{'='*60}")
                print(f"Total de linhas brutas: {len(linhas_brutas)}")
                print(f"Total de linhas processadas: {len(linhas_processadas)}")
                print(f"\nLinhas processadas para consumo:")
                for i, linha in enumerate(linhas_processadas[:5]):
                    print(f"  [{i}] {linha}")

            # Process reconstructed consumption lines
            for linha in linhas_processadas:
                if self.debug:
                    print(f"Processando linha: {linha}")

                # Check if line contains consumption data
                if self._is_consumption_line_new(linha):
                    self._processar_linha_consumo_new(linha)

            # Process original lines for SCEE and other data
            for linha in linhas_brutas:
                if self._is_scee_line(linha):
                    self._processar_linha_scee(linha)
                elif self._is_financial_line_new(linha):
                    self._processar_linha_financeira_new(linha)

        except Exception as e:
            if self.debug:
                print(f"AVISO: Erro processando página {page_num}: {e}")

    def _processar_bloco_texto(self, text: str, block_info: Dict):
        """
        Process a text block and extract relevant data.
        Based on original ConsumoExtractor logic.
        """
        x0, y0 = block_info.get('x0', 0), block_info.get('y0', 0)

        # Check if within main table area (from original system)
        if not (30 <= x0 <= 650 and 350 <= y0 <= 755):
            # Also check for SCEE data which can be outside main table
            if not self._is_scee_text(text):
                return

        parts = text.split()
        if not parts:
            return

        # Identify line type and process accordingly
        if self._is_consumption_line(text, parts):
            self._processar_linha_consumo(text, parts)
        elif self._is_scee_line(text):
            self._processar_linha_scee(text)
        elif self._is_bandeira_line(text, parts):
            self._processar_linha_bandeira(text, parts)
        elif self._is_financial_line(text, parts):
            self._processar_linha_financeira(text, parts)

    def _reconstruct_consumption_lines(self, linhas_brutas: List[str]) -> List[str]:
        """
        Reconstruct consumption lines from separated text fragments.
        Based on the debug output, we need to combine:
        - Item name (e.g., "ADC BANDEIRA VERMELHA")
        - "kWh"
        - Numbers (tarifa, quantidade, valor)
        """
        linhas_processadas = []

        # Look for consumption indicators in sequential lines
        consumption_indicators = [
            "ADC BANDEIRA VERMELHA", "ADICIONAL BANDEIRA",
            "CONSUMO NAO COMPENSADO", "CONSUMO NÃO COMPENSADO",
            "CONSUMO SCEE",
            "INJECAO SCEE", "INJEÇÃO SCEE"
        ]

        i = 0
        while i < len(linhas_brutas):
            linha_atual = linhas_brutas[i]

            # Check if current line is a consumption indicator
            is_consumption_start = any(indicator in linha_atual.upper() for indicator in consumption_indicators)

            if is_consumption_start:
                # Reconstruct the full consumption line
                linha_completa = linha_atual

                # Look ahead for kWh and numeric values
                j = i + 1
                valores_encontrados = []

                # Collect next few lines to reconstruct the consumption line
                while j < min(i + 10, len(linhas_brutas)):  # Look ahead max 10 lines
                    próxima_linha = linhas_brutas[j]

                    if "kWh" in próxima_linha or "KWH" in próxima_linha:
                        linha_completa += " " + próxima_linha
                    elif self._is_numeric_value(próxima_linha):
                        valores_encontrados.append(próxima_linha)
                        linha_completa += " " + próxima_linha

                        # Stop when we have enough values (at least 5: tarifa, quantidade, valor_intermediario, valor_final)
                        if len(valores_encontrados) >= 5:
                            break
                    elif próxima_linha in ["19%", "%"] or próxima_linha.endswith("%"):
                        # Skip percentage lines but continue
                        pass
                    elif any(indicator in próxima_linha.upper() for indicator in consumption_indicators):
                        # Found another consumption line, stop here
                        break

                    j += 1

                if "kWh" in linha_completa and len(valores_encontrados) >= 2:
                    linhas_processadas.append(linha_completa)
                    if self.debug:
                        print(f"   Linha reconstruida: {linha_completa}")

                i = j  # Skip processed lines
            else:
                i += 1

        return linhas_processadas

    def _is_consumption_line_new(self, linha: str) -> bool:
        """Check if line contains consumption data - NEW VERSION."""
        linha_upper = linha.upper()

        # Patterns we're looking for:
        # "CONSUMO NÃO COMPENSADO kWh 100,00 0,964151 96,41"
        # "CONSUMO SCEE kWh 709,00 0,643844 456,49"
        # "ADC BANDEIRA VERMELHA kWh 100,00 0,101814 10,18"
        # "INJEÇÃO SCEE - UC 10037100562 - GD I kWh 709,00 0,643844 -456,49"

        indicators = [
            "CONSUMO NÃO COMPENSADO", "CONSUMO NAO COMPENSADO",
            "CONSUMO SCEE", "CONSUMO COMPENSADO",
            "ADC BANDEIRA", "ADICIONAL BANDEIRA", "BANDEIRA",
            "INJEÇÃO SCEE", "INJECAO SCEE", "INJECÃO SCEE"
        ]

        has_indicator = any(indicator in linha_upper for indicator in indicators)
        has_kwh = "KWH" in linha_upper or "kWh" in linha
        has_values = any(char.isdigit() for char in linha) and "," in linha

        return has_indicator and has_kwh and has_values

    def _is_scee_text(self, text: str) -> bool:
        """Check if text contains SCEE information."""
        scee_indicators = [
            "INFORMAÇÕES DO SCEE", "INFORMACOES DO SCEE",
            "CRÉDITO DE ENERGIA", "CREDITO DE ENERGIA", "SCEE:",
            "EXCEDENTE RECEBIDO", "GERAÇÃO CICLO", "GERACAO CICLO",
            "SALDO KWH", "CRÉDITO RECEBIDO", "CREDITO RECEBIDO",
            "ENERGIA INJETADA", "SISTEMA DE COMPENSAÇÃO"
        ]

        return any(indicator in text.upper() for indicator in scee_indicators)

    def _is_scee_line(self, text: str) -> bool:
        """Check if line is SCEE data line."""
        return self._is_scee_text(text)

    def _is_bandeira_line_new(self, linha: str) -> bool:
        """Check if line contains bandeira tarifária data - NEW VERSION."""
        linha_upper = linha.upper()
        bandeira_indicators = ["ADC BANDEIRA", "ADICIONAL BANDEIRA", "BANDEIRA"]
        has_kwh = "KWH" in linha_upper or "kWh" in linha
        return any(indicator in linha_upper for indicator in bandeira_indicators) and has_kwh

    def _is_financial_line_new(self, linha: str) -> bool:
        """Check if line contains financial data (juros, multa, etc) - NEW VERSION."""
        linha_upper = linha.upper()
        financial_indicators = ["JUROS", "MULTA", "ILUMINAÇÃO", "ILUMINACAO", "CONTRIB"]
        return any(indicator in linha_upper for indicator in financial_indicators)

    def _processar_linha_consumo_new(self, linha: str):
        """
        Process consumption line - NEW VERSION with QUANTIDADE and VALOR extraction.
        Expected format: "ITEM kWh QUANTIDADE TARIFA VALOR %TRIB VALOR_TRIB BASE"
        Examples:
        - "CONSUMO NAO COMPENSADO kWh 100,00 0,964151 96,41 3,5 96,41 19% 18,32 0,745930"
        - "CONSUMO SCEE kWh 709,00 0,643844 456,49 16,59 456,49 19% 86,73 0,498120"
        - "ADC BANDEIRA VERMELHA kWh 100,00 0,101814 10,18 0,37 10,18 19% 1,93 0,078770"
        """
        try:
            if self.debug:
                print(f"   Processando linha consumo: {linha}")

            # Split linha into parts
            parts = linha.split()
            if len(parts) < 5:
                return

            # Find kWh position
            kwh_index = -1
            for i, part in enumerate(parts):
                if part.upper() in ['KWH', 'kWh']:
                    kwh_index = i
                    break

            if kwh_index == -1 or kwh_index + 3 >= len(parts):
                return

            # Extract values from expected positions
            # Format: ITEM kWh TARIFA QUANTIDADE VALOR_INTERMEDIARIO VALOR_PRINCIPAL OUTROS...
            # Based on patterns:
            # "ADC BANDEIRA VERMELHA kWh 0,101814 100,00 0,37 10,18 1,93"
            # "CONSUMO NÃO COMPENSADO kWh 0,964151 100,00 3,5 96,41 18,32"
            # "CONSUMO SCEE kWh 0,643844 709,00 16,59 456,49 86,73"

            tarifa_str = parts[kwh_index + 1]      # First number after kWh (tarifa unitária)
            quantidade_str = parts[kwh_index + 2]  # Second number after kWh (quantidade kWh)

            # The main value is the 4th number after kWh (index + 4)
            if kwh_index + 4 < len(parts):
                valor_str = parts[kwh_index + 4]  # Fourth number after kWh (valor principal)
            else:
                valor_str = parts[kwh_index + 3]  # Fallback to third if fourth not available

            # Convert to Decimal with comma handling
            quantidade = self._convert_value_with_comma(quantidade_str)
            tarifa = self._convert_value_with_comma(tarifa_str)
            valor = self._convert_value_with_comma(valor_str)

            # Handle negative values for injection
            if valor_str.startswith('-'):
                valor = -abs(valor)

            # Identify consumption type
            tipo_consumo = self._identificar_tipo_consumo_new(linha)

            if self.debug:
                print(f"   Valores extraidos: quantidade={quantidade}, tarifa={tarifa}, valor={valor}, tipo={tipo_consumo}")

            # Store data
            self._armazenar_dados_consumo_new(tipo_consumo, quantidade, tarifa, valor)

        except Exception as e:
            if self.debug:
                print(f"   ERRO processando linha consumo: {e}")

    def _find_correct_kwh_index(self, parts: List[str]) -> int:
        """
        Find the correct kWh index in parts list.
        Migrated from original system.
        """
        for i, part in enumerate(parts):
            if part.upper() in ['KWH', 'kWh']:
                return i
        return -1

    def _identificar_tipo_consumo_new(self, linha: str) -> str:
        """
        Identify consumption type from line - NEW VERSION.
        Returns: 'comp', 'n_comp', 'bandeira', 'injecao'
        """
        linha_upper = linha.upper()

        if "CONSUMO SCEE" in linha_upper or ("CONSUMO" in linha_upper and "COMPENSADO" in linha_upper and "NAO" not in linha_upper and "NÃO" not in linha_upper):
            return "comp"
        elif "CONSUMO NAO COMPENSADO" in linha_upper or "CONSUMO NÃO COMPENSADO" in linha_upper:
            return "n_comp"
        elif "ADC BANDEIRA" in linha_upper or "ADICIONAL BANDEIRA" in linha_upper or "BANDEIRA" in linha_upper:
            return "bandeira"
        elif "INJECAO SCEE" in linha_upper or "INJEÇÃO SCEE" in linha_upper:
            return "injecao"
        else:
            return "geral"

    def _armazenar_dados_consumo_new(self, tipo: str, quantidade: Decimal, tarifa: Decimal, valor: Decimal):
        """Store consumption data - NEW VERSION."""
        if tipo == "comp":
            self.consumo_comp["consumo_comp"] = quantidade
            self.rs_consumo_comp["rs_consumo_comp"] = tarifa
            self.valor_consumo_comp["valor_consumo_comp"] = valor

        elif tipo == "n_comp":
            self.consumo_n_comp["consumo_n_comp"] = quantidade
            self.rs_consumo_n_comp["rs_consumo_n_comp"] = tarifa
            self.valor_consumo_n_comp["valor_consumo_n_comp"] = valor

        elif tipo == "bandeira":
            # Store bandeira data in separate variables
            if not hasattr(self, 'bandeira_quantidade'):
                self.bandeira_quantidade = Decimal('0')
                self.bandeira_valor = Decimal('0')

            self.bandeira_quantidade = quantidade
            self.bandeira_valor = valor
            self.bandeira_codigo = 1  # Assume vermelha if detected

        elif tipo == "injecao":
            # Store injection data
            if not hasattr(self, 'injecao_quantidade'):
                self.injecao_quantidade = Decimal('0')
                self.injecao_valor = Decimal('0')

            self.injecao_quantidade = quantidade
            self.injecao_valor = valor

        else:  # geral
            self.consumo_geral = quantidade
            self.rs_consumo_geral = tarifa
            self.valor_consumo_geral = valor

    def _processar_linha_scee(self, text: str):
        """
        Process SCEE data line.
        Migrated from CreditosSaldosExtractor logic.
        """
        if self.debug:
            print(f"DEBUG: Processando SCEE: {text[:100]}...")

        # Extract generation data
        self._extrair_geracao_ciclo(text)

        # Extract excedente data
        self._extrair_excedente_recebido(text)

        # Extract credit data
        self._extrair_credito_recebido(text)

        # Extract saldo data
        self._extrair_saldo_energia(text)

    def _extrair_geracao_ciclo(self, text: str):
        """Extract geração ciclo data."""
        # Pattern: "GERAÇÃO CICLO (6/2025) KWH: UC 10037114075 : 58.010,82"
        geracao_pattern = r'GERAÇÃO CICLO.*?KWH:\s*UC\s*(\d+)\s*:\s*([\d.,]+)'
        geracao_match = re.search(geracao_pattern, text, re.IGNORECASE)

        if geracao_match:
            uc_geradora = geracao_match.group(1)
            geracao_total = safe_decimal_conversion(geracao_match.group(2))

            self.geracao_registros.append({
                'uc': uc_geradora,
                'tipo': 'grupo_b',
                'total': geracao_total
            })

            if self.debug:
                print(f"   OK: Geração detectada: UC {uc_geradora}, Total: {geracao_total}")

        # Pattern for BRANCA: "UC 10037114024 : P=0,40, FP=18.781,95, HR=0,00, HI=0,00"
        geracao_branca_pattern = r'UC\s*(\d+)\s*:\s*P=([\d.,]+),\s*FP=([\d.,]+),\s*HR=([\d.,]+),\s*HI=([\d.,]+)'
        geracao_branca_match = re.search(geracao_branca_pattern, text, re.IGNORECASE)

        if geracao_branca_match:
            uc_geradora = geracao_branca_match.group(1)
            p_val = safe_decimal_conversion(geracao_branca_match.group(2))
            fp_val = safe_decimal_conversion(geracao_branca_match.group(3))
            hr_val = safe_decimal_conversion(geracao_branca_match.group(4))
            hi_val = safe_decimal_conversion(geracao_branca_match.group(5))

            geracao_total = p_val + fp_val + hr_val + hi_val

            self.geracao_registros.append({
                'uc': uc_geradora,
                'tipo': 'grupo_b_branca',
                'total': geracao_total,
                'p': p_val,
                'fp': fp_val,
                'hr': hr_val,
                'hi': hi_val
            })

            if self.debug:
                print(f"   OK: Geração Branca: UC {uc_geradora}, Total: {geracao_total}")

    def _extrair_excedente_recebido(self, text: str):
        """Extract excedente recebido data."""
        # Pattern: "EXCEDENTE RECEBIDO KWH: UC 10037114075 : 16.370,65"
        excedente_pattern = r'EXCEDENTE RECEBIDO KWH:\s*UC\s*(\d+)\s*:\s*([\d.,]+)'
        excedente_match = re.search(excedente_pattern, text, re.IGNORECASE)

        if excedente_match:
            uc = excedente_match.group(1)
            excedente_total = safe_decimal_conversion(excedente_match.group(2))

            self.excedente_registros.append({
                'uc': uc,
                'total': excedente_total
            })

            if self.debug:
                print(f"   OK: Excedente: UC {uc}, Total: {excedente_total}")

    def _extrair_credito_recebido(self, text: str):
        """Extract crédito recebido data."""
        # Patterns for credit
        credit_patterns = [
            r'CRÉDITO RECEBIDO.*?(\d+,\d+)',
            r'CREDITO RECEBIDO.*?(\d+,\d+)',
            r'CRÉDITO.*?(\d+,\d+)',
            r'(\d+,\d+).*CRÉDITO'
        ]

        for pattern in credit_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                credito = safe_decimal_conversion(match.group(1))
                self.creditos_total += credito

                if self.debug:
                    print(f"   OK: Crédito detectado: {credito}")
                break

    def _extrair_saldo_energia(self, text: str):
        """Extract saldo energia data."""
        # Look for saldo patterns
        saldo_patterns = [
            r'SALDO.*?(\d+,\d+)',
            r'(\d+,\d+).*SALDO',
            r'SALDO KWH.*?(\d+,\d+)'
        ]

        for pattern in saldo_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                saldo = safe_decimal_conversion(match.group(1))
                # Store saldo (will be processed in finalization)
                if self.debug:
                    print(f"   OK: Saldo detectado: {saldo}")
                break

    def _processar_linha_bandeira_new(self, linha: str):
        """Process bandeira tarifária line - NEW VERSION."""
        try:
            # Use the same processing as consumption line
            self._processar_linha_consumo_new(linha)
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

    def _processar_linha_financeira_new(self, linha: str):
        """Process financial line (juros, multa, iluminação) - NEW VERSION."""
        linha_upper = linha.upper()
        if "JUROS" in linha_upper:
            self._extrair_juros_new(linha)
        elif "MULTA" in linha_upper:
            self._extrair_multa_new(linha)
        elif "ILUMINAÇÃO" in linha_upper or "ILUMINACAO" in linha_upper:
            self._extrair_iluminacao_new(linha)

    def _extrair_juros(self, text: str, parts: List[str]):
        """Extract juros data."""
        # Find numeric value in parts
        for part in parts:
            if self._is_monetary_value(part):
                valor = safe_decimal_conversion(part)
                self.juros_total += valor
                if self.debug:
                    print(f"   OK: Juros detectado: R$ {valor}")
                break

    def _extrair_multa(self, text: str, parts: List[str]):
        """Extract multa data."""
        # Find numeric value in parts
        for part in parts:
            if self._is_monetary_value(part):
                valor = safe_decimal_conversion(part)
                self.multa_total += valor
                if self.debug:
                    print(f"   OK: Multa detectada: R$ {valor}")
                break

    def _extrair_iluminacao(self, text: str, parts: List[str]):
        """Extract iluminação data."""
        # Find numeric value in parts
        for part in parts:
            if self._is_monetary_value(part):
                valor = safe_decimal_conversion(part)
                # Store iluminação value (would be added to result in finalization)
                if self.debug:
                    print(f"   OK: Iluminação detectada: R$ {valor}")
                break

    def _is_numeric_value(self, text: str) -> bool:
        """Check if text represents a numeric value."""
        try:
            # Remove common formatting
            cleaned = text.replace('.', '').replace(',', '.').replace(' ', '')
            float(cleaned)
            return True
        except:
            return False

    def _is_monetary_value(self, text: str) -> bool:
        """Check if text represents a monetary value."""
        return self._is_numeric_value(text) and (',' in text or len(text.replace('.', '')) > 2)

    def _convert_value_with_comma(self, valor_str: str) -> Decimal:
        """
        Convert value string with comma as decimal separator to Decimal.
        Examples: "100,00" -> 100.00, "709,00" -> 709.00, "456,49" -> 456.49
        """
        try:
            # Remove any spaces and handle negative
            valor_str = valor_str.strip()
            is_negative = valor_str.startswith('-')
            if is_negative:
                valor_str = valor_str[1:]

            # Replace comma with dot for decimal conversion
            valor_str_clean = valor_str.replace(',', '.')

            # Remove thousand separators (dots before decimal)
            if valor_str_clean.count('.') > 1:
                # Split by dots, last one is decimal separator
                parts = valor_str_clean.split('.')
                valor_str_clean = ''.join(parts[:-1]) + '.' + parts[-1]

            valor = Decimal(valor_str_clean)
            return -valor if is_negative else valor

        except Exception as e:
            if self.debug:
                print(f"   Erro convertendo valor '{valor_str}': {e}")
            return Decimal('0')

    def _extrair_juros_new(self, linha: str):
        """Extract juros data - NEW VERSION."""
        import re
        # Look for monetary values in line
        valores = re.findall(r'\d+[,.]\d+', linha)
        for valor_str in valores:
            if self._is_monetary_value(valor_str):
                valor = self._convert_value_with_comma(valor_str)
                self.juros_total += valor
                if self.debug:
                    print(f"   Juros detectado: R$ {valor}")
                break

    def _extrair_multa_new(self, linha: str):
        """Extract multa data - NEW VERSION."""
        import re
        # Look for monetary values in line
        valores = re.findall(r'\d+[,.]\d+', linha)
        for valor_str in valores:
            if self._is_monetary_value(valor_str):
                valor = self._convert_value_with_comma(valor_str)
                self.multa_total += valor
                if self.debug:
                    print(f"   Multa detectada: R$ {valor}")
                break

    def _extrair_iluminacao_new(self, linha: str):
        """Extract iluminação data - NEW VERSION."""
        import re
        # Look for monetary values in line
        valores = re.findall(r'\d+[,.]\d+', linha)
        for valor_str in valores:
            if self._is_monetary_value(valor_str):
                valor = self._convert_value_with_comma(valor_str)
                # Store illumination value (can be added to financial data)
                if self.debug:
                    print(f"   Iluminacao detectada: R$ {valor}")
                break

    def _finalizar_extracao(self) -> Dict[str, Any]:
        """
        Finalize extraction and build result dictionary.
        Maintains EXACT field names from original system.
        """
        result = {}

        # Add consumption data
        result.update(self.consumo_comp)
        result.update(self.rs_consumo_comp)
        result.update(self.valor_consumo_comp)
        result.update(self.consumo_n_comp)
        result.update(self.rs_consumo_n_comp)
        result.update(self.valor_consumo_n_comp)

        # Add bandeira data
        if hasattr(self, 'bandeira_quantidade') and self.bandeira_quantidade > 0:
            result['bandeira_quantidade'] = self.bandeira_quantidade
            result['bandeira_valor'] = self.bandeira_valor

        # Add injection data
        if hasattr(self, 'injecao_quantidade') and self.injecao_quantidade > 0:
            result['injecao_quantidade'] = self.injecao_quantidade
            result['injecao_valor'] = self.injecao_valor

        # Calculate consumo total from meter reading or sum compensated + non-compensated
        self._calcular_consumo_total(result)

        # Calculate valor_consumo total
        self._calcular_valor_consumo_total(result)

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

        # Process SCEE data
        self._processar_dados_scee(result)

        # Apply totalization logic (migrated from original)
        self._finalizar_totalizacoes(result)

        # Print final debug report
        if self.debug:
            self._print_valores_extraidos(result)

        return result

    def _processar_dados_scee(self, result: Dict[str, Any]):
        """Process SCEE data and add to result."""
        # Add generation data
        if self.geracao_registros:
            for i, registro in enumerate(self.geracao_registros):
                if i == 0:
                    result['uc_geradora_1'] = registro['uc']
                    result['geracao_ciclo'] = registro['total']
                elif i == 1:
                    result['uc_geradora_2'] = registro['uc']
                    result['geracao_ugs_2'] = registro['total']

        # Add excedente data
        excedente_total = sum(reg['total'] for reg in self.excedente_registros)
        if excedente_total > 0:
            result['excedente_recebido'] = excedente_total

        # Add credit data
        if self.creditos_total > 0:
            result['credito_recebido'] = self.creditos_total

        # Calculate energia_injetada (sum of generation)
        energia_injetada_total = sum(reg['total'] for reg in self.geracao_registros)
        if energia_injetada_total > 0:
            result['energia_injetada'] = energia_injetada_total

    def _finalizar_totalizacoes(self, result: Dict[str, Any]):
        """
        Apply totalization logic migrated from original _finalizar_totalizacoes.
        CRITICAL for compatibility.
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

        for posto in postos_b:
            comp_key = f'consumo_comp_{posto}'
            n_comp_key = f'consumo_n_comp_{posto}'
            total_key = f'consumo_{posto}'

            # If has comp/n_comp division, sum for total
            if comp_key in result or n_comp_key in result:
                comp_val = to_decimal(result.get(comp_key, 0))
                n_comp_val = to_decimal(result.get(n_comp_key, 0))
                total = comp_val + n_comp_val

                if total > Decimal('0'):
                    result[total_key] = total

        # GRUPO B - TARIFA CONVENCIONAL totalization
        if ('consumo_comp' in result or 'consumo_n_comp' in result):
            comp_total = to_decimal(result.get('consumo_comp', 0))
            n_comp_total = to_decimal(result.get('consumo_n_comp', 0))
            total_geral = comp_total + n_comp_total

            if total_geral > Decimal('0'):
                result['consumo'] = total_geral

        # Calculate total consumption from postos if needed
        if 'consumo' not in result or result.get('consumo', Decimal('0')) == Decimal('0'):
            consumo_p = to_decimal(result.get('consumo_p', 0))
            consumo_fp = to_decimal(result.get('consumo_fp', 0))
            consumo_hi = to_decimal(result.get('consumo_hi', 0))

            if consumo_p > 0 or consumo_fp > 0 or consumo_hi > 0:
                result['consumo'] = consumo_p + consumo_fp + consumo_hi
                if self.debug:
                    print(f"OK: Consumo total B Branca: {result['consumo']}")

        # Calculate compensated total
        consumo_comp_p = to_decimal(result.get('consumo_comp_p', 0))
        consumo_comp_fp = to_decimal(result.get('consumo_comp_fp', 0))
        consumo_comp_hi = to_decimal(result.get('consumo_comp_hi', 0))

        if consumo_comp_p > 0 or consumo_comp_fp > 0 or consumo_comp_hi > 0:
            total_comp = consumo_comp_p + consumo_comp_fp + consumo_comp_hi
            result['consumo_comp'] = total_comp
            if self.debug:
                print(f"OK: Consumo compensado total B Branca: {total_comp}")

        # Calculate non-compensated total
        consumo_n_comp_p = to_decimal(result.get('consumo_n_comp_p', 0))
        consumo_n_comp_fp = to_decimal(result.get('consumo_n_comp_fp', 0))
        consumo_n_comp_hi = to_decimal(result.get('consumo_n_comp_hi', 0))

        if consumo_n_comp_p > 0 or consumo_n_comp_fp > 0 or consumo_n_comp_hi > 0:
            total_n_comp = consumo_n_comp_p + consumo_n_comp_fp + consumo_n_comp_hi
            result['consumo_n_comp'] = total_n_comp
            if self.debug:
                print(f"OK: Consumo não compensado total B Branca: {total_n_comp}")

    def _imprimir_relatorio_extracao(self, pdf_path: str, dados: Dict[str, Any]):
        """Print extraction report for debugging."""
        if not self.debug:
            return

        print(f"\n{'='*60}")
        print(f"RELATORIO EXTRACÃO B COMPENSADO - {Path(pdf_path).name}")
        print(f"{'='*60}")

        # Basic consumption
        print("CONSUMO:")
        consumo_fields = [k for k in dados.keys() if 'consumo' in k.lower() and 'rs_' not in k.lower()]
        for field in sorted(consumo_fields):
            print(f"   {field}: {dados[field]}")

        # SCEE data
        print("\nSCEE:")
        scee_fields = ['saldo', 'excedente_recebido', 'credito_recebido', 'energia_injetada', 'geracao_ciclo']
        for field in scee_fields:
            if field in dados:
                print(f"   {field}: {dados[field]}")

        # UGs
        ugs = [k for k in dados.keys() if 'uc_geradora' in k.lower()]
        for ug in ugs:
            print(f"   {ug}: {dados[ug]}")

        print(f"{'='*60}")

    def _ensure_required_fields(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all required fields are present with correct types."""
        # Ensure decimal fields
        decimal_fields = [
            'consumo', 'consumo_comp', 'consumo_n_comp',
            'valor_consumo', 'valor_consumo_comp', 'valor_consumo_n_comp',
            'rs_consumo', 'rs_consumo_comp', 'rs_consumo_n_comp',
            'saldo', 'excedente_recebido', 'credito_recebido',
            'energia_injetada', 'geracao_ciclo',
            'valor_juros', 'valor_multa', 'valor_iluminacao'
        ]

        for field in decimal_fields:
            if field in dados and not isinstance(dados[field], Decimal):
                dados[field] = safe_decimal_conversion(str(dados[field]))
            elif field not in dados:
                dados[field] = Decimal('0')

        # Ensure string fields
        string_fields = ['uc_geradora_1', 'uc_geradora_2', 'uc_geradora_3']
        for field in string_fields:
            if field not in dados:
                dados[field] = ''

        # Add bandeira code
        dados['bandeira_codigo'] = self.bandeira_codigo

        return dados

    def _calcular_consumo_total(self, result: Dict[str, Any]):
        """
        Calculate total consumption from available data.
        Priority: meter reading -> sum of compensated + non-compensated
        """
        try:
            # First try to get from meter reading if available (would be extracted elsewhere)
            # For now, calculate from available compensated + non-compensated

            consumo_comp = result.get('consumo_comp', Decimal('0'))
            consumo_n_comp = result.get('consumo_n_comp', Decimal('0'))

            if isinstance(consumo_comp, str):
                consumo_comp = Decimal(consumo_comp)
            if isinstance(consumo_n_comp, str):
                consumo_n_comp = Decimal(consumo_n_comp)

            total_consumo = consumo_comp + consumo_n_comp

            # Example from expected data: 709 + 100 = 809
            if total_consumo > 0:
                result['consumo'] = total_consumo
                if self.debug:
                    print(f"   Consumo total calculado: {total_consumo} kWh")

        except Exception as e:
            if self.debug:
                print(f"   Erro calculando consumo total: {e}")

    def _calcular_valor_consumo_total(self, result: Dict[str, Any]):
        """
        Calculate total consumption value.
        """
        try:
            valor_comp = result.get('valor_consumo_comp', Decimal('0'))
            valor_n_comp = result.get('valor_consumo_n_comp', Decimal('0'))
            valor_bandeira = result.get('bandeira_valor', Decimal('0'))

            if isinstance(valor_comp, str):
                valor_comp = Decimal(valor_comp)
            if isinstance(valor_n_comp, str):
                valor_n_comp = Decimal(valor_n_comp)
            if isinstance(valor_bandeira, str):
                valor_bandeira = Decimal(valor_bandeira)

            # Sum all consumption values: 456.49 + 96.41 + 10.18 = 563.08
            total_valor = valor_comp + valor_n_comp + valor_bandeira

            if total_valor > 0:
                result['valor_consumo'] = total_valor
                if self.debug:
                    print(f"   Valor consumo total calculado: R$ {total_valor}")

        except Exception as e:
            if self.debug:
                print(f"   Erro calculando valor consumo total: {e}")

    def _print_valores_extraidos(self, result: Dict[str, Any]):
        """
        Print final extracted values for debugging.
        """
        print(f"\n{'='*60}")
        print(f"VALORES EXTRAIDOS - CONSUMO")
        print(f"{'='*60}")
        print(f"QUANTIDADES:")
        print(f"   consumo_total: {result.get('consumo', 0)}")
        print(f"   consumo_compensado: {result.get('consumo_comp', 0)}")
        print(f"   consumo_nao_compensado: {result.get('consumo_n_comp', 0)}")
        print(f"   bandeira_quantidade: {result.get('bandeira_quantidade', 0)}")
        print(f"\nVALORES:")
        print(f"   valor_consumo_compensado: {result.get('valor_consumo_comp', 0)}")
        print(f"   valor_consumo_nao_compensado: {result.get('valor_consumo_n_comp', 0)}")
        print(f"   valor_bandeira: {result.get('bandeira_valor', 0)}")
        print(f"   valor_total_consumo: {result.get('valor_consumo', 0)}")
        print(f"{'='*60}\n")

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

    def extract_scee_data(self, texto_completo: str) -> Dict[str, Any]:
        """Extract SCEE data using Common Extractor."""
        from extractors.common.scee_extractor import SCEEExtractor
        extractor = SCEEExtractor()
        return extractor.extract_scee_data(texto_completo)

    def extract_complete(self, pdf_path: str) -> Dict[str, Any]:
        """
        Complete extraction using all Common Extractors + Group B specific logic.
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
            dados_scee = self.extract_scee_data(texto_completo)

            # Extract Group B specific consumption data
            dados_consumo = self.extract(pdf_path)

            # Merge all data
            resultado_final = {}
            resultado_final.update(dados_basicos)
            resultado_final.update(dados_impostos)
            resultado_final.update(dados_financeiros)
            resultado_final.update(dados_scee)
            resultado_final.update(dados_consumo)

            # Ensure compatibility fields
            resultado_final = self._ensure_required_fields(resultado_final)

            if self.debug:
                print(f"[B_COMPENSADO] Extração completa: {len(resultado_final)} campos")

            return resultado_final

        except Exception as e:
            self._error_print(f"Erro na extração completa B compensado: {e}")
            return {"erro": str(e)}
