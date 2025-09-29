"""
Common extractor for financial data (juros, multa, iluminação).
Migrates logic from ConsumoExtractor financial processing.
CRITICAL: Maintains exact field names for compatibility.
"""

import re
from typing import Dict, Any, Optional
from decimal import Decimal
from pathlib import Path

# Import utilities
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from core.base_extractor import safe_decimal_conversion


class FinanceiroExtractor:
    """
    Extractor for financial data common to all invoice types.
    Migrated from original ConsumoExtractor financial logic.

    CRITICAL FIELDS EXTRACTED (maintain exact names):
    - valor_juros, valor_multa, valor_iluminacao
    - valor_beneficio_bruto, valor_beneficio_liquido
    """

    def __init__(self):
        self.debug = True
        # Accumulators for financial values
        self.juros_total = Decimal('0')
        self.multa_total = Decimal('0')
        self.iluminacao_total = Decimal('0')

    def extract_financial_data(self, texto_completo: str) -> Dict[str, Any]:
        """
        Extract financial data (fees, fines, etc.) from complete text.
        Migrated from original ConsumoExtractor financial methods.

        Args:
            texto_completo: Full text from all PDF pages

        Returns:
            Dictionary with financial data using exact field names
        """
        result = {}

        # Reset accumulators
        self._reset_accumulators()

        # Process text by lines to simulate coordinate-based processing
        lines = texto_completo.split('\n')

        for line_num, text in enumerate(lines):
            if not text.strip():
                continue

            # Simulate coordinate-based filtering from original
            x0, y0 = self._simulate_coordinates(line_num, len(lines))
            block_info = {'x0': x0, 'y0': y0}

            # Verificar área da tabela principal - COPIED FROM ORIGINAL
            if not (30 <= x0 <= 650 and 350 <= y0 <= 755):
                continue

            parts = text.split()

            # JUROS - COPIED FROM ORIGINAL LOGIC
            if "JUROS" in text.upper():
                try:
                    # PADRÃO NOVO: "JUROS MORATÓRIA. 0,21"
                    juros_pattern = r'JUROS\s*MORAT[\u00d3O]RIA\.?\s*([\d,]+)'
                    juros_match = re.search(juros_pattern, text)
                    if juros_match:
                        valor = safe_decimal_conversion(juros_match.group(1), "juros")
                        if valor > Decimal('0'):
                            self.juros_total += valor
                            result['valor_juros'] = self.juros_total
                            continue

                    valor_match = re.search(r'JUROS.*?([\d,]+)', text)
                    if valor_match:
                        valor = safe_decimal_conversion(valor_match.group(1), "juros")
                        if valor > Decimal('0'):
                            self.juros_total += valor
                            result['valor_juros'] = self.juros_total
                            continue

                    # PADRÃO ANTIGO: Buscar após palavra JUROS
                    for i, part in enumerate(parts):
                        if "JUROS" in part.upper():
                            for j in range(i+1, len(parts)):
                                current_part = parts[j]

                                if re.search(r'\d', current_part):
                                    try:
                                        valor = safe_decimal_conversion(current_part, "juros")
                                        if valor > Decimal('0'):
                                            self.juros_total += valor
                                            result['valor_juros'] = self.juros_total
                                            break
                                    except Exception:
                                        continue
                            break
                except Exception as e:
                    if self.debug:
                        print(f"ERRO: ERRO juros: {e}")

            # MULTA - COPIED FROM ORIGINAL LOGIC
            if "MULTA" in text.upper() and any(char.isdigit() for char in text):
                try:
                    # PADRÃO NOVO: "MULTA - 06/2025. 2,06"
                    multa_pattern = r'MULTA\s*(?:-\s*\d{2}/\d{4})?\.*\s*([\d,]+)'
                    multa_match = re.search(multa_pattern, text)
                    if multa_match:
                        valor = safe_decimal_conversion(multa_match.group(1), "multa")
                        if valor > Decimal('0'):
                            self.multa_total += valor
                            result['valor_multa'] = self.multa_total
                            continue

                    valor_match = re.search(r'MULTA.*?([\d,]+)', text)
                    if valor_match:
                        valor = safe_decimal_conversion(valor_match.group(1), "multa")
                        if valor > Decimal('0'):
                            self.multa_total += valor
                            result['valor_multa'] = self.multa_total
                            continue

                    # PADRÃO ANTIGO: Buscar após palavra MULTA
                    for i, part in enumerate(parts):
                        if "MULTA" in part.upper():
                            for j in range(i+1, len(parts)):
                                current_part = parts[j]

                                if re.search(r'\d', current_part):
                                    try:
                                        valor = safe_decimal_conversion(current_part, "multa")
                                        if valor > Decimal('0'):
                                            self.multa_total += valor
                                            result['valor_multa'] = self.multa_total
                                            break
                                    except Exception:
                                        continue
                            break
                except Exception as e:
                    if self.debug:
                        print(f"ERRO: ERRO multa: {e}")

            # ILUMINAÇÃO - COPIED FROM ORIGINAL LOGIC
            if any(termo in text.upper() for termo in [
                "ILUM",
                "ILUMINAÇÃO PÚBLICA",
                "CONTRIB. ILUM"
            ]):
                try:
                    for part in reversed(parts):
                        # Verificar se a parte parece um número antes de tentar converter
                        if re.search(r'\d', part):  # Tem pelo menos um dígito
                            try:
                                valor = safe_decimal_conversion(part, "iluminacao")
                                if valor > Decimal('0'):  # Só aceitar valores positivos
                                    result['valor_iluminacao'] = result.get('valor_iluminacao', Decimal('0')) + valor
                                    break
                            except Exception:
                                continue
                except Exception as e:
                    if self.debug:
                        print(f"ERRO: ERRO iluminação: {e}")

        if self.debug and result:
            print(f"[FINANCEIRO] Extraídos {len(result)} campos financeiros")

        return result

    def _reset_accumulators(self):
        """Reset financial accumulators."""
        self.juros_total = Decimal('0')
        self.multa_total = Decimal('0')
        self.iluminacao_total = Decimal('0')

    def _simulate_coordinates(self, line_num: int, total_lines: int) -> tuple:
        """Simulate coordinates based on line position for coordinate-based logic."""
        # Distribute lines to simulate the main table area (30-650, 350-755)
        x0 = 30 + (line_num % 20) * 31  # Within table x range
        y0 = 350 + (line_num / total_lines) * 405  # Within table y range
        return (x0, y0)

    def _extrair_juros_fallback(self, texto: str) -> Dict[str, Any]:
        """Extract juros data - improved to handle multiple lines and sum all values."""
        resultado = {}

        if self.debug:
            print(f"[FINANCEIRO] Extraindo juros...")

        try:
            # ESTRATÉGIA MULTI-PADRÃO: Encontrar TODOS os juros e somar
            linhas = texto.split('\n')
            valores_encontrados = []

            # PADRÃO 1: "JUROS DE MORA R$ 12,34" ou "JUROS R$ 12,34"
            juros_pattern_rs = r'JUROS.*?R\$\s*([\d.,]+)'
            for match in re.finditer(juros_pattern_rs, texto, re.IGNORECASE):
                valor = safe_decimal_conversion(match.group(1))
                if valor > Decimal('0'):
                    valores_encontrados.append(valor)
                    if self.debug:
                        print(f"   Juros padrão R$: {valor}")

            # PADRÃO 2: "JUROS" seguido de valor na mesma linha
            for linha in linhas:
                if 'JUROS' in linha.upper():
                    # Buscar valores numéricos na linha após JUROS
                    parts = linha.split()
                    for i, part in enumerate(parts):
                        if "JUROS" in part.upper():
                            # Verificar próximas partes na mesma linha
                            for j in range(i + 1, len(parts)):
                                current_part = parts[j]
                                if re.match(r'^[\d.,]+$', current_part):
                                    try:
                                        valor = safe_decimal_conversion(current_part)
                                        if valor > Decimal('0'):
                                            valores_encontrados.append(valor)
                                            if self.debug:
                                                print(f"   Juros mesma linha: {valor}")
                                            break
                                    except Exception:
                                        continue

            # PADRÃO 3: "JUROS" em uma linha e valor na linha seguinte
            for i, linha in enumerate(linhas):
                if 'JUROS' in linha.upper() and 'MORATÓRIA' in linha.upper():
                    # Verificar se a próxima linha tem apenas um valor numérico
                    if i + 1 < len(linhas):
                        proxima_linha = linhas[i + 1].strip()
                        if re.match(r'^[\d.,]+$', proxima_linha):
                            try:
                                valor = safe_decimal_conversion(proxima_linha)
                                if valor > Decimal('0'):
                                    valores_encontrados.append(valor)
                                    if self.debug:
                                        print(f"   Juros linha seguinte: {valor}")
                            except Exception:
                                continue

            # PADRÃO 4: Busca genérica por "JUROS" e valores próximos
            juros_generic_pattern = r'JUROS[^R\d]*?([\d.,]+)'
            for match in re.finditer(juros_generic_pattern, texto, re.IGNORECASE):
                valor = safe_decimal_conversion(match.group(1))
                if valor > Decimal('0'):
                    # Evitar duplicatas verificando se já foi encontrado
                    if valor not in valores_encontrados:
                        valores_encontrados.append(valor)
                        if self.debug:
                            print(f"   Juros genérico: {valor}")

            # SOMAR TODOS OS VALORES ENCONTRADOS
            if valores_encontrados:
                self.juros_total = sum(valores_encontrados)
                resultado['valor_juros'] = self.juros_total

                if self.debug:
                    print(f"   TOTAL JUROS: {len(valores_encontrados)} valores encontrados")
                    for i, valor in enumerate(valores_encontrados):
                        print(f"     Juros {i+1}: R$ {valor}")
                    print(f"   SOMA FINAL: R$ {self.juros_total}")

        except Exception as e:
            if self.debug:
                print(f"[ERRO] Erro extraindo juros: {e}")

        return resultado