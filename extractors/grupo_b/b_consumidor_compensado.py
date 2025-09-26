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

    def _processar_pagina(self, page: fitz.Page, page_num: int, doc: fitz.Document):
        """
        Process a single PDF page.
        Migrated from original system's page processing logic.
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

    def _is_consumption_line(self, text: str, parts: List[str]) -> bool:
        """Check if line contains consumption data."""
        consumption_indicators = [
            "CONSUMO", "ENERGIA ELÉTRICA", "kWh", "KWH"
        ]

        # Must have kWh indicator and numeric values
        has_kwh = any(indicator in text.upper() for indicator in ["KWH", "kWh"])
        has_numeric = any(self._is_numeric_value(part) for part in parts)

        return has_kwh and has_numeric and len(parts) >= 5

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
        Migrated from _processar_consumo_grupo_b in original system.
        """
        try:
            kwh_index = self._find_correct_kwh_index(parts)
            if kwh_index == -1:
                return

            # Extract basic values (maintain original logic)
            if kwh_index + 4 >= len(parts):
                return

            quantidade = safe_decimal_conversion(parts[kwh_index + 2].replace('.', ''))
            tarifa = safe_decimal_conversion(parts[kwh_index + 1])
            valor = safe_decimal_conversion(parts[kwh_index + 4])

            # Extract tarifa sem imposto if available
            tarifa_sem_imposto = Decimal('0')
            if kwh_index + 7 < len(parts):
                tarifa_sem_imposto = safe_decimal_conversion(parts[kwh_index + 7])

            # Identify consumption type and posto (for BRANCA)
            tipo_consumo, posto = self._identificar_tipo_consumo(text)

            if self.debug:
                print(f"DEBUG: Consumo {tipo_consumo} {posto}: {quantidade} kWh x R$ {tarifa} = R$ {valor}")

            # Store data based on type
            self._armazenar_dados_consumo(tipo_consumo, posto, quantidade, tarifa, valor, tarifa_sem_imposto)

        except Exception as e:
            if self.debug:
                print(f"AVISO: Erro processando linha consumo: {e}")

    def _find_correct_kwh_index(self, parts: List[str]) -> int:
        """
        Find the correct kWh index in parts list.
        Migrated from original system.
        """
        for i, part in enumerate(parts):
            if part.upper() in ['KWH', 'kWh']:
                return i
        return -1

    def _identificar_tipo_consumo(self, text: str) -> tuple:
        """
        Identify consumption type and posto.
        Returns: (tipo, posto) where tipo = 'comp'|'n_comp'|'geral' and posto = 'p'|'fp'|'hi'|''
        """
        text_upper = text.upper()

        # Check for compensated/non-compensated
        if "COMPENSADO" in text_upper and "NÃO" not in text_upper:
            tipo = "comp"
        elif "NÃO COMPENSADO" in text_upper or "NAO COMPENSADO" in text_upper:
            tipo = "n_comp"
        else:
            tipo = "geral"

        # Check for posto horário (BRANCA tariff)
        if "PONTA" in text_upper and "FORA" not in text_upper:
            posto = "p"
        elif "FORA PONTA" in text_upper or "FORA-PONTA" in text_upper:
            posto = "fp"
        elif "INTERMEDIÁRIO" in text_upper or "INTERMEDIARIO" in text_upper:
            posto = "hi"
        else:
            posto = ""

        return tipo, posto

    def _armazenar_dados_consumo(self, tipo: str, posto: str, quantidade: Decimal,
                                tarifa: Decimal, valor: Decimal, tarifa_si: Decimal):
        """Store consumption data in appropriate accumulators."""
        # Build field suffix
        sufixo = f"_{posto}" if posto else ""

        if tipo == "comp":
            campo_consumo = f"consumo_comp{sufixo}"
            campo_tarifa = f"rs_consumo_comp{sufixo}"
            campo_valor = f"valor_consumo_comp{sufixo}"

            self.consumo_comp[campo_consumo] = quantidade
            self.rs_consumo_comp[campo_tarifa] = tarifa
            self.valor_consumo_comp[campo_valor] = valor

            # Store tarifa sem imposto if available
            if tarifa_si > 0:
                self.rs_consumo_comp[f"{campo_tarifa}_si"] = tarifa_si

        elif tipo == "n_comp":
            campo_consumo = f"consumo_n_comp{sufixo}"
            campo_tarifa = f"rs_consumo_n_comp{sufixo}"
            campo_valor = f"valor_consumo_n_comp{sufixo}"

            self.consumo_n_comp[campo_consumo] = quantidade
            self.rs_consumo_n_comp[campo_tarifa] = tarifa
            self.valor_consumo_n_comp[campo_valor] = valor

            # Store tarifa sem imposto if available
            if tarifa_si > 0:
                self.rs_consumo_n_comp[f"{campo_tarifa}_si"] = tarifa_si

        else:  # geral
            if not posto:  # Only for general consumption
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

    def _processar_linha_bandeira(self, text: str, parts: List[str]):
        """Process bandeira tarifária line."""
        try:
            if "AMARELA" in text.upper():
                # Extract bandeira amarela data
                self._extrair_bandeira("amarela", text, parts)
            elif "VERMELHA" in text.upper():
                # Extract bandeira vermelha data
                self._extrair_bandeira("vermelha", text, parts)
        except Exception as e:
            if self.debug:
                print(f"AVISO: Erro processando bandeira: {e}")

    def _extrair_bandeira(self, tipo: str, text: str, parts: List[str]):
        """Extract bandeira data."""
        # Implementation would be similar to original BandeiraExtractor
        # For now, placeholder to maintain structure
        pass

    def _processar_linha_financeira(self, text: str, parts: List[str]):
        """Process financial line (juros, multa, iluminação)."""
        if "JUROS" in text.upper():
            self._extrair_juros(text, parts)
        elif "MULTA" in text.upper():
            self._extrair_multa(text, parts)
        elif "ILUMINAÇÃO" in text.upper() or "ILUMINACAO" in text.upper():
            self._extrair_iluminacao(text, parts)

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
        # Implementation placeholder
        pass

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
