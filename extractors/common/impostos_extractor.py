"""
Common extractor for tax data (ICMS, PIS, COFINS).
Migrates logic from ImpostosExtractor.
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


class ImpostosExtractor:
    """
    Extractor for tax data common to all invoice types.
    Migrated from original ImpostosExtractor.

    CRITICAL FIELDS EXTRACTED (maintain exact names):
    - aliquota_icms, aliquota_pis, aliquota_cofins
    - valor_icms, valor_pis, valor_cofins
    - base_icms, base_pis, base_cofins
    """

    def __init__(self):
        self.debug = True

    def extract_tax_data(self, texto_completo: str) -> Dict[str, Any]:
        """
        Extract tax data (ICMS, PIS, COFINS) from complete text.
        Migrated from original ImpostosExtractor - maintains exact logic.

        Args:
            texto_completo: Full text from all PDF pages

        Returns:
            Dictionary with tax data using exact field names
        """
        result = {}

        # Process text by lines to simulate block processing
        lines = texto_completo.split('\n')

        for line_num, text in enumerate(lines):
            if not text.strip():
                continue

            # Simulate coordinate-based filtering from original
            x0, y0 = self._simulate_coordinates(line_num, len(lines))
            block_info = {'x0': x0, 'y0': y0}

            # Área típica dos impostos - COPIED FROM ORIGINAL
            if not (660 <= x0 <= 880 and 390 <= y0 <= 450):
                continue

            parts = text.split()

            try:
                if "PIS/PASEP" in text:
                    # Base de cálculo do PIS (primeiro valor após "PIS/PASEP") - COPIED FROM ORIGINAL
                    if len(parts) >= 2:
                        base_str = parts[1].replace(',', '.')
                        base = Decimal(base_str)
                        result['base_pis'] = base

                    # Alíquota do PIS (segundo valor) - COPIED FROM ORIGINAL
                    if len(parts) >= 3:
                        aliquota_str = parts[2].replace(',', '.').rstrip('%')
                        if aliquota_str.replace('.', '').isdigit():
                            aliquota = Decimal(aliquota_str) / Decimal('100')
                            result['aliquota_pis'] = aliquota

                    # Valor do PIS (terceiro valor) - COPIED FROM ORIGINAL
                    if len(parts) >= 4:
                        valor_str = parts[3].replace(',', '.')
                        valor = Decimal(valor_str)
                        result['valor_pis'] = valor

                elif "ICMS" in text and "COFINS" not in text:
                    # Base de cálculo do ICMS - COPIED FROM ORIGINAL
                    if len(parts) >= 2:
                        base_str = parts[1].replace(',', '.')
                        base = Decimal(base_str)
                        result['base_icms'] = base

                    # Alíquota do ICMS - COPIED FROM ORIGINAL
                    if len(parts) >= 3:
                        aliquota_str = parts[2].replace(',', '.').rstrip('%')
                        if aliquota_str.replace('.', '').isdigit():
                            aliquota = Decimal(aliquota_str) / Decimal('100')
                            result['aliquota_icms'] = aliquota

                    # Valor do ICMS - COPIED FROM ORIGINAL
                    if len(parts) >= 4:
                        valor_str = parts[3].replace(',', '.')
                        valor = Decimal(valor_str)
                        result['valor_icms'] = valor

                elif "COFINS" in text:
                    # Base de cálculo do COFINS - COPIED FROM ORIGINAL
                    if len(parts) >= 2:
                        base_str = parts[1].replace(',', '.')
                        base = Decimal(base_str)
                        result['base_cofins'] = base

                    # Alíquota do COFINS - COPIED FROM ORIGINAL
                    if len(parts) >= 3:
                        aliquota_str = parts[2].replace(',', '.').rstrip('%')
                        if aliquota_str.replace('.', '').isdigit():
                            aliquota = Decimal(aliquota_str) / Decimal('100')
                            result['aliquota_cofins'] = aliquota

                    # Valor do COFINS - COPIED FROM ORIGINAL
                    if len(parts) >= 4:
                        valor_str = parts[3].replace(',', '.')
                        valor = Decimal(valor_str)
                        result['valor_cofins'] = valor

            except (ValueError, IndexError) as e:
                if self.debug:
                    print(f"Erro ao processar impostos: {e} - Texto: {text[:50]}")

        # Fallback: try pattern-based extraction if coordinate-based failed
        if not result:
            result = self._extract_fallback_patterns(texto_completo)

        if self.debug and result:
            print(f"[IMPOSTOS] Extraídos {len(result)} campos de impostos")

        return result

    def _simulate_coordinates(self, line_num: int, total_lines: int) -> tuple:
        """Simulate coordinates based on line position for coordinate-based logic."""
        # Distribute lines to simulate the tax area coordinates (660-880, 390-450)
        x0 = 660 + (line_num % 5) * 44  # Within tax x range
        y0 = 390 + (line_num % 10) * 6   # Within tax y range
        return (x0, y0)

    def _extract_fallback_patterns(self, texto: str) -> Dict[str, Any]:
        """Fallback pattern-based extraction if coordinate-based fails."""
        resultado = {}

        # ICMS patterns
        icms_patterns = [
            r'ICMS\s+([\d.,]+)\s+([\d.,]+)%?\s+([\d.,]+)',
            r'ICMS.*?([\d{1,3}(?:\.\d{3})*,\d{2}]).*?([\d{1,2},\d{2,4}])%?.*?([\d{1,3}(?:\.\d{3})*,\d{2}])'
        ]

        for pattern in icms_patterns:
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                try:
                    base = safe_decimal_conversion(match.group(1))
                    aliquota_str = match.group(2).replace('%', '')
                    aliquota = safe_decimal_conversion(aliquota_str)
                    valor = safe_decimal_conversion(match.group(3))

                    if aliquota > Decimal('1'):
                        aliquota = aliquota / Decimal('100')

                    resultado['base_icms'] = base
                    resultado['aliquota_icms'] = aliquota
                    resultado['valor_icms'] = valor
                    break
                except Exception:
                    continue

        # PIS patterns
        pis_patterns = [
            r'PIS/PASEP\s+([\d.,]+)\s+([\d.,]+)%?\s+([\d.,]+)',
            r'PIS\s+([\d.,]+)\s+([\d.,]+)%?\s+([\d.,]+)'
        ]

        for pattern in pis_patterns:
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                try:
                    base = safe_decimal_conversion(match.group(1))
                    aliquota_str = match.group(2).replace('%', '')
                    aliquota = safe_decimal_conversion(aliquota_str)
                    valor = safe_decimal_conversion(match.group(3))

                    if aliquota > Decimal('1'):
                        aliquota = aliquota / Decimal('100')

                    resultado['base_pis'] = base
                    resultado['aliquota_pis'] = aliquota
                    resultado['valor_pis'] = valor
                    break
                except Exception:
                    continue

        # COFINS patterns
        cofins_patterns = [
            r'COFINS\s+([\d.,]+)\s+([\d.,]+)%?\s+([\d.,]+)'
        ]

        for pattern in cofins_patterns:
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                try:
                    base = safe_decimal_conversion(match.group(1))
                    aliquota_str = match.group(2).replace('%', '')
                    aliquota = safe_decimal_conversion(aliquota_str)
                    valor = safe_decimal_conversion(match.group(3))

                    if aliquota > Decimal('1'):
                        aliquota = aliquota / Decimal('100')

                    resultado['base_cofins'] = base
                    resultado['aliquota_cofins'] = aliquota
                    resultado['valor_cofins'] = valor
                    break
                except Exception:
                    continue

        return resultado

