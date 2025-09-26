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

    def extract_tax_data(self, texto_completo: str, blocks_info: list = None) -> Dict[str, Any]:
        """
        Extract tax data from complete invoice text.

        Args:
            texto_completo: Full text from all PDF pages
            blocks_info: Optional list of text blocks with position info

        Returns:
            Dictionary with tax data using exact field names
        """
        dados = {}

        try:
            # Extract ICMS data
            icms_data = self._extrair_icms(texto_completo)
            dados.update(icms_data)

            # Extract PIS data
            pis_data = self._extrair_pis(texto_completo)
            dados.update(pis_data)

            # Extract COFINS data
            cofins_data = self._extrair_cofins(texto_completo)
            dados.update(cofins_data)

            # If blocks info available, try position-based extraction
            if blocks_info:
                positioned_data = self._extract_positioned_taxes(blocks_info)
                dados.update(positioned_data)

            if self.debug and dados:
                print(f"[IMPOSTOS] Extraídos {len(dados)} campos de impostos")

        except Exception as e:
            if self.debug:
                print(f"[ERRO] Erro extraindo impostos: {e}")

        return dados

    def _extrair_icms(self, texto: str) -> Dict[str, Any]:
        """Extract ICMS data."""
        resultado = {}

        # ICMS patterns - based on original system logic
        icms_patterns = [
            # Pattern: "ICMS base aliquota valor"
            r'ICMS\s+([\d.,]+)\s+([\d.,]+)%?\s+([\d.,]+)',
            # Pattern with multiple spaces
            r'ICMS\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,2},\d{2,4})%?\s+(\d{1,3}(?:\.\d{3})*,\d{2})',
            # Pattern in table format
            r'ICMS.*?\n.*?([\d.,]+)\s+([\d.,]+)%?\s+([\d.,]+)'
        ]

        for pattern in icms_patterns:
            match = re.search(pattern, texto, re.IGNORECASE | re.MULTILINE)
            if match:
                try:
                    base_str = match.group(1)
                    aliquota_str = match.group(2).replace('%', '')
                    valor_str = match.group(3)

                    # Convert to Decimal
                    base = safe_decimal_conversion(base_str)
                    aliquota = safe_decimal_conversion(aliquota_str)
                    valor = safe_decimal_conversion(valor_str)

                    # Convert aliquota to decimal percentage
                    if aliquota > Decimal('1'):
                        aliquota = aliquota / Decimal('100')

                    resultado['base_icms'] = base
                    resultado['aliquota_icms'] = aliquota
                    resultado['valor_icms'] = valor

                    if self.debug:
                        print(f"[ICMS] Base: {base}, Alíquota: {float(aliquota)*100:.4f}%, Valor: {valor}")
                    break

                except Exception as e:
                    if self.debug:
                        print(f"[AVISO] Erro processando ICMS: {e}")

        return resultado

    def _extrair_pis(self, texto: str) -> Dict[str, Any]:
        """Extract PIS data."""
        resultado = {}

        # PIS patterns
        pis_patterns = [
            # Pattern: "PIS/PASEP base aliquota valor"
            r'PIS/PASEP\s+([\d.,]+)\s+([\d.,]+)%?\s+([\d.,]+)',
            r'PIS\s+([\d.,]+)\s+([\d.,]+)%?\s+([\d.,]+)',
            # Pattern with multiple spaces
            r'PIS/PASEP\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,2},\d{2,4})%?\s+(\d{1,3}(?:\.\d{3})*,\d{2})',
            # Pattern in table format
            r'PIS.*?\n.*?([\d.,]+)\s+([\d.,]+)%?\s+([\d.,]+)'
        ]

        for pattern in pis_patterns:
            match = re.search(pattern, texto, re.IGNORECASE | re.MULTILINE)
            if match:
                try:
                    base_str = match.group(1)
                    aliquota_str = match.group(2).replace('%', '')
                    valor_str = match.group(3)

                    # Convert to Decimal
                    base = safe_decimal_conversion(base_str)
                    aliquota = safe_decimal_conversion(aliquota_str)
                    valor = safe_decimal_conversion(valor_str)

                    # Convert aliquota to decimal percentage
                    if aliquota > Decimal('1'):
                        aliquota = aliquota / Decimal('100')

                    resultado['base_pis'] = base
                    resultado['aliquota_pis'] = aliquota
                    resultado['valor_pis'] = valor

                    if self.debug:
                        print(f"[PIS] Base: {base}, Alíquota: {float(aliquota)*100:.4f}%, Valor: {valor}")
                    break

                except Exception as e:
                    if self.debug:
                        print(f"[AVISO] Erro processando PIS: {e}")

        return resultado

    def _extrair_cofins(self, texto: str) -> Dict[str, Any]:
        """Extract COFINS data."""
        resultado = {}

        # COFINS patterns
        cofins_patterns = [
            # Pattern: "COFINS base aliquota valor"
            r'COFINS\s+([\d.,]+)\s+([\d.,]+)%?\s+([\d.,]+)',
            # Pattern with multiple spaces
            r'COFINS\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s+(\d{1,2},\d{2,4})%?\s+(\d{1,3}(?:\.\d{3})*,\d{2})',
            # Pattern in table format
            r'COFINS.*?\n.*?([\d.,]+)\s+([\d.,]+)%?\s+([\d.,]+)'
        ]

        for pattern in cofins_patterns:
            match = re.search(pattern, texto, re.IGNORECASE | re.MULTILINE)
            if match:
                try:
                    base_str = match.group(1)
                    aliquota_str = match.group(2).replace('%', '')
                    valor_str = match.group(3)

                    # Convert to Decimal
                    base = safe_decimal_conversion(base_str)
                    aliquota = safe_decimal_conversion(aliquota_str)
                    valor = safe_decimal_conversion(valor_str)

                    # Convert aliquota to decimal percentage
                    if aliquota > Decimal('1'):
                        aliquota = aliquota / Decimal('100')

                    resultado['base_cofins'] = base
                    resultado['aliquota_cofins'] = aliquota
                    resultado['valor_cofins'] = valor

                    if self.debug:
                        print(f"[COFINS] Base: {base}, Alíquota: {float(aliquota)*100:.4f}%, Valor: {valor}")
                    break

                except Exception as e:
                    if self.debug:
                        print(f"[AVISO] Erro processando COFINS: {e}")

        return resultado

    def _extract_positioned_taxes(self, blocks_info: list) -> Dict[str, Any]:
        """
        Extract tax data using position information.
        Based on original coordinate-based logic.
        """
        resultado = {}

        for block in blocks_info:
            text = block.get('text', '').strip()
            if not text:
                continue

            x0 = block.get('x0', 0)
            y0 = block.get('y0', 0)

            # Tax area coordinates (from original system)
            if not (660 <= x0 <= 880 and 390 <= y0 <= 450):
                continue

            parts = text.split()

            try:
                if "PIS/PASEP" in text:
                    # Base de cálculo do PIS (primeiro valor após "PIS/PASEP")
                    if len(parts) >= 2:
                        base = safe_decimal_conversion(parts[1])
                        resultado['base_pis'] = base

                    # Alíquota do PIS (segundo valor)
                    if len(parts) >= 3:
                        aliquota_str = parts[2].replace('%', '')
                        aliquota = safe_decimal_conversion(aliquota_str)
                        if aliquota > Decimal('1'):
                            aliquota = aliquota / Decimal('100')
                        resultado['aliquota_pis'] = aliquota

                    # Valor do PIS (terceiro valor)
                    if len(parts) >= 4:
                        valor = safe_decimal_conversion(parts[3])
                        resultado['valor_pis'] = valor

                elif "ICMS" in text and "COFINS" not in text:
                    # Base de cálculo do ICMS
                    if len(parts) >= 2:
                        base = safe_decimal_conversion(parts[1])
                        resultado['base_icms'] = base

                    # Alíquota do ICMS
                    if len(parts) >= 3:
                        aliquota_str = parts[2].replace('%', '')
                        aliquota = safe_decimal_conversion(aliquota_str)
                        if aliquota > Decimal('1'):
                            aliquota = aliquota / Decimal('100')
                        resultado['aliquota_icms'] = aliquota

                    # Valor do ICMS
                    if len(parts) >= 4:
                        valor = safe_decimal_conversion(parts[3])
                        resultado['valor_icms'] = valor

                elif "COFINS" in text:
                    # Base de cálculo do COFINS
                    if len(parts) >= 2:
                        base = safe_decimal_conversion(parts[1])
                        resultado['base_cofins'] = base

                    # Alíquota do COFINS
                    if len(parts) >= 3:
                        aliquota_str = parts[2].replace('%', '')
                        aliquota = safe_decimal_conversion(aliquota_str)
                        if aliquota > Decimal('1'):
                            aliquota = aliquota / Decimal('100')
                        resultado['aliquota_cofins'] = aliquota

                    # Valor do COFINS
                    if len(parts) >= 4:
                        valor = safe_decimal_conversion(parts[3])
                        resultado['valor_cofins'] = valor

            except Exception as e:
                if self.debug:
                    print(f"[AVISO] Erro processando bloco positioned: {e}")

        return resultado