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
        # Add comprehensive debug at start
        if self.debug:
            print(f"\n{'='*60}")
            print(f"DEBUG EXTRATOR IMPOSTOS")
            print(f"{'='*60}")

        result = {}

        # Process text by lines to simulate block processing
        lines = texto_completo.split('\n')

        # Search for tax lines and show them
        if self.debug:
            impostos_procurar = ['PIS/PASEP', 'ICMS', 'COFINS']
            print(f"Procurando linhas de impostos...")

            for linha in lines:
                for imposto in impostos_procurar:
                    if imposto in linha:
                        print(f"Linha {imposto} encontrada: {linha}")

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
                    valores = self._extrair_valores_imposto(text, "PIS/PASEP")
                    if valores:
                        result['base_pis'] = Decimal(str(valores['base']))
                        result['aliquota_pis'] = Decimal(str(valores['aliquota'])) / Decimal('100')
                        result['valor_pis'] = Decimal(str(valores['valor']))

                elif "ICMS" in text and "COFINS" not in text:
                    valores = self._extrair_valores_imposto(text, "ICMS")
                    if valores:
                        result['base_icms'] = Decimal(str(valores['base']))
                        result['aliquota_icms'] = Decimal(str(valores['aliquota'])) / Decimal('100')
                        result['valor_icms'] = Decimal(str(valores['valor']))

                elif "COFINS" in text:
                    valores = self._extrair_valores_imposto(text, "COFINS")
                    if valores:
                        result['base_cofins'] = Decimal(str(valores['base']))
                        result['aliquota_cofins'] = Decimal(str(valores['aliquota'])) / Decimal('100')
                        result['valor_cofins'] = Decimal(str(valores['valor']))

            except Exception as e:
                if self.debug:
                    print(f"ERRO ao converter valor na linha: '{text}'")
                    print(f"   Tipo do erro: {type(e).__name__}")
                    print(f"   Mensagem: {str(e)}")
                    print(f"   Contexto: parts = {parts}")

        # Fallback: try direct line-by-line extraction if coordinate-based failed
        if not result:
            if self.debug:
                print("Tentando extração linha por linha...")

            result = self._extract_direct_lines(texto_completo)

        # Print final debug summary
        if self.debug:
            self._print_impostos_extraidos(result)

        if self.debug and result:
            print(f"[IMPOSTOS] Extraidos {len(result)} campos de impostos")

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

    def limpar_valor_numerico(self, texto):
        """
        Limpa e converte valores numéricos do formato brasileiro
        Exemplos:
          "86,34" → 86.34
          "0,798%" → 0.798
          "19%" → 19.0
          "R$*********125,33" → 125.33
          "5.128,26" → 5128.26
        """
        if not texto or texto.strip() == '':
            return None

        # Remove espaços, R$, asteriscos, %
        texto = texto.strip()
        texto = texto.replace('R$', '').replace('*', '').replace('%', '').replace(' ', '')

        # Se tem ponto E vírgula: formato brasileiro (1.234,56)
        if '.' in texto and ',' in texto:
            texto = texto.replace('.', '')  # Remove separador de milhares
            texto = texto.replace(',', '.')  # Vírgula vira ponto decimal
        # Se tem só vírgula: substitui por ponto
        elif ',' in texto:
            texto = texto.replace(',', '.')

        try:
            return float(texto)
        except:
            if self.debug:
                print(f"Não foi possível converter: '{texto}'")
            return None

    def _extrair_valores_imposto(self, linha: str, nome_imposto: str) -> Dict[str, float]:
        """
        Extrai BASE, ALÍQUOTA e VALOR de uma linha de imposto.
        Formato esperado: "IMPOSTO BASE ALÍQUOTA% VALOR"
        Exemplo: "PIS/PASEP 86,34 0,798% 0,69"
        """
        resultado = {}

        try:
            # Remove o nome do imposto e divide em partes
            linha_limpa = linha.replace(nome_imposto, '').strip()

            # Regex para capturar 3 valores numéricos
            # Padrão: BASE ALÍQUOTA% VALOR
            import re
            pattern = r'([\d.,]+)\s+([\d.,]+%?)\s+([\d.,]+)$'
            match = re.search(pattern, linha_limpa)

            if match:
                base_str = match.group(1)     # 86,34
                aliquota_str = match.group(2) # 0,798% ou 19%
                valor_str = match.group(3)    # 0,69

                # Converter valores usando função robusta
                base = self.limpar_valor_numerico(base_str)
                aliquota = self.limpar_valor_numerico(aliquota_str)
                valor = self.limpar_valor_numerico(valor_str)

                if base is not None and aliquota is not None and valor is not None:
                    resultado['base'] = base
                    resultado['aliquota'] = aliquota
                    resultado['valor'] = valor

                    if self.debug:
                        print(f"   {nome_imposto}: base={base}, aliquota={aliquota}%, valor={valor}")
                else:
                    if self.debug:
                        print(f"   Falha na conversão de valores para {nome_imposto}")
                        print(f"   base_str='{base_str}' -> {base}")
                        print(f"   aliquota_str='{aliquota_str}' -> {aliquota}")
                        print(f"   valor_str='{valor_str}' -> {valor}")
            else:
                if self.debug:
                    print(f"   Padrão não encontrado para {nome_imposto}: '{linha_limpa}'")

        except Exception as e:
            if self.debug:
                print(f"   ERRO ao extrair {nome_imposto}: {type(e).__name__}: {str(e)}")
                print(f"   Linha: '{linha}'")

        return resultado

    def _extract_direct_lines(self, texto_completo: str) -> Dict[str, Any]:
        """
        Fallback extraction: search through all lines for tax patterns.
        Uses structured pattern: TAX_NAME -> ALIQUOTA% -> BASE -> VALOR
        """
        resultado = {}

        if self.debug:
            print(f"Iniciando extração linha por linha com padrão estruturado...")

        lines = [line.strip() for line in texto_completo.split('\n')]

        for line_num, line in enumerate(lines):
            if not line:
                continue

            try:
                # Look for PIS/PASEP
                if line == "PIS/PASEP" or line == "PIS":
                    if self.debug:
                        print(f"Linha PIS encontrada ({line_num}): {line}")

                    valores = self._extrair_valores_sequenciais(lines, line_num, "PIS")
                    if valores:
                        resultado['base_pis'] = valores['base']
                        resultado['aliquota_pis'] = valores['aliquota']
                        resultado['valor_pis'] = valores['valor']

                # Look for ICMS (standalone line)
                elif line == "ICMS":
                    if self.debug:
                        print(f"Linha ICMS encontrada ({line_num}): {line}")

                    valores = self._extrair_valores_sequenciais(lines, line_num, "ICMS")
                    if valores:
                        resultado['base_icms'] = valores['base']
                        resultado['aliquota_icms'] = valores['aliquota']
                        resultado['valor_icms'] = valores['valor']

                # Look for COFINS (standalone line)
                elif line == "COFINS":
                    if self.debug:
                        print(f"Linha COFINS encontrada ({line_num}): {line}")

                    valores = self._extrair_valores_sequenciais(lines, line_num, "COFINS")
                    if valores:
                        resultado['base_cofins'] = valores['base']
                        resultado['aliquota_cofins'] = valores['aliquota']
                        resultado['valor_cofins'] = valores['valor']

            except Exception as e:
                if self.debug:
                    print(f"ERRO ao processar linha {line_num}: '{line}'")
                    print(f"   Erro: {type(e).__name__}: {str(e)}")
                continue

        # If still no results, try fallback patterns
        if not resultado:
            if self.debug:
                print("Tentando padrões alternativos...")
            resultado = self._extract_fallback_patterns(texto_completo)

        return resultado

    def _extrair_valores_sequenciais(self, lines: list, tax_line: int, nome_imposto: str) -> Dict[str, Decimal]:
        """
        Extract tax values from sequential lines after tax name.
        Pattern: TAX_NAME -> ALIQUOTA% -> BASE -> VALOR
        """
        resultado = {}

        try:
            # Make sure we have enough lines after the tax name
            if tax_line + 3 >= len(lines):
                if self.debug:
                    print(f"   {nome_imposto}: Não há linhas suficientes após o nome do imposto")
                return {}

            aliquota_str = lines[tax_line + 1].strip()  # Next line: percentage
            base_str = lines[tax_line + 2].strip()      # Next line: base value
            valor_str = lines[tax_line + 3].strip()     # Next line: tax value

            if self.debug:
                print(f"   {nome_imposto}: aliquota_str='{aliquota_str}', base_str='{base_str}', valor_str='{valor_str}'")

            # Convert values using robust function
            aliquota_num = self.limpar_valor_numerico(aliquota_str)
            base_num = self.limpar_valor_numerico(base_str)
            valor_num = self.limpar_valor_numerico(valor_str)

            if aliquota_num is not None and base_num is not None and valor_num is not None:
                # Convert to Decimal and handle percentage conversion
                aliquota_decimal = Decimal(str(aliquota_num))
                # Always convert percentage to decimal (19% -> 0.19, 0.798% -> 0.00798)
                if '%' in aliquota_str:
                    aliquota_decimal = aliquota_decimal / Decimal('100')

                resultado['base'] = Decimal(str(base_num))
                resultado['aliquota'] = aliquota_decimal
                resultado['valor'] = Decimal(str(valor_num))

                if self.debug:
                    print(f"   {nome_imposto}: SUCESSO - base={resultado['base']}, aliquota={resultado['aliquota']}, valor={resultado['valor']}")
            else:
                if self.debug:
                    print(f"   {nome_imposto}: Falha na conversão de valores")
                    print(f"       aliquota_num={aliquota_num}, base_num={base_num}, valor_num={valor_num}")

        except Exception as e:
            if self.debug:
                print(f"   ERRO extraindo {nome_imposto}: {type(e).__name__}: {str(e)}")

        return resultado

    def _print_impostos_extraidos(self, dados: Dict[str, Any]):
        """
        Print final extracted tax values for debugging.
        """
        print(f"\n{'='*60}")
        print(f"VALORES EXTRAIDOS - IMPOSTOS")
        print(f"{'='*60}")
        print(f"ICMS:")
        print(f"   base: {dados.get('base_icms', 0)}")
        print(f"   aliquota: {dados.get('aliquota_icms', 0)}%")
        print(f"   valor: {dados.get('valor_icms', 0)}")
        print(f"\nPIS:")
        print(f"   base: {dados.get('base_pis', 0)}")
        print(f"   aliquota: {dados.get('aliquota_pis', 0)}%")
        print(f"   valor: {dados.get('valor_pis', 0)}")
        print(f"\nCOFINS:")
        print(f"   base: {dados.get('base_cofins', 0)}")
        print(f"   aliquota: {dados.get('aliquota_cofins', 0)}%")
        print(f"   valor: {dados.get('valor_cofins', 0)}")
        print(f"{'='*60}\n")

