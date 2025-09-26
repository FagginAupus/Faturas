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

    def extract_financial_data(self, texto_completo: str, blocks_info: list = None) -> Dict[str, Any]:
        """
        Extract financial data from complete invoice text.

        Args:
            texto_completo: Full text from all PDF pages
            blocks_info: Optional list of text blocks with position info

        Returns:
            Dictionary with financial data using exact field names
        """
        dados = {}

        try:
            # Reset accumulators
            self._reset_accumulators()

            # Extract juros data
            juros_data = self._extrair_juros(texto_completo)
            dados.update(juros_data)

            # Extract multa data
            multa_data = self._extrair_multa(texto_completo)
            dados.update(multa_data)

            # Extract iluminação data
            iluminacao_data = self._extrair_iluminacao(texto_completo)
            dados.update(iluminacao_data)

            # Extract benefit data
            beneficios_data = self._extrair_beneficios(texto_completo)
            dados.update(beneficios_data)

            # If blocks info available, try position-based extraction
            if blocks_info:
                positioned_data = self._extract_positioned_financial(blocks_info)
                dados.update(positioned_data)

            if self.debug and dados:
                print(f"[FINANCEIRO] Extraídos {len(dados)} campos financeiros")

        except Exception as e:
            if self.debug:
                print(f"[ERRO] Erro extraindo dados financeiros: {e}")

        return dados

    def _reset_accumulators(self):
        """Reset financial accumulators."""
        self.juros_total = Decimal('0')
        self.multa_total = Decimal('0')
        self.iluminacao_total = Decimal('0')

    def _extrair_juros(self, texto: str) -> Dict[str, Any]:
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

    def _extrair_multa(self, texto: str) -> Dict[str, Any]:
        """Extract multa data - improved to handle multiple lines and sum all values."""
        resultado = {}

        if self.debug:
            print(f"[FINANCEIRO] Extraindo multa...")

        try:
            # ESTRATÉGIA MULTI-PADRÃO: Encontrar TODAS as multas e somar
            linhas = texto.split('\n')
            valores_encontrados = []

            # PADRÃO 1: "MULTA POR ATRASO R$ 12,34" ou "MULTA R$ 12,34"
            multa_pattern_rs = r'MULTA.*?R\$\s*([\d.,]+)'
            for match in re.finditer(multa_pattern_rs, texto, re.IGNORECASE):
                valor = safe_decimal_conversion(match.group(1))
                if valor > Decimal('0'):
                    valores_encontrados.append(valor)
                    if self.debug:
                        print(f"   Multa padrão R$: {valor}")

            # PADRÃO 2: "MULTA" seguido de valor na mesma linha
            for linha in linhas:
                if 'MULTA' in linha.upper():
                    # Buscar valores numéricos na linha após MULTA
                    parts = linha.split()
                    for i, part in enumerate(parts):
                        if "MULTA" in part.upper():
                            # Verificar próximas partes na mesma linha
                            for j in range(i + 1, len(parts)):
                                current_part = parts[j]
                                # Procurar por valores numéricos, ignorando datas/códigos
                                if re.match(r'^[\d.,]+$', current_part) and '/' not in current_part:
                                    try:
                                        valor = safe_decimal_conversion(current_part)
                                        if valor > Decimal('0'):
                                            valores_encontrados.append(valor)
                                            if self.debug:
                                                print(f"   Multa mesma linha: {valor}")
                                            break
                                    except Exception:
                                        continue

            # PADRÃO 3: "MULTA - MM/YYYY" em uma linha e valor na linha seguinte
            for i, linha in enumerate(linhas):
                if 'MULTA' in linha.upper() and re.search(r'\d{2}/\d{4}', linha):
                    # Verificar se a próxima linha tem apenas um valor numérico
                    if i + 1 < len(linhas):
                        proxima_linha = linhas[i + 1].strip()
                        if re.match(r'^[\d.,]+$', proxima_linha):
                            try:
                                valor = safe_decimal_conversion(proxima_linha)
                                if valor > Decimal('0'):
                                    valores_encontrados.append(valor)
                                    if self.debug:
                                        print(f"   Multa linha seguinte: {valor}")
                            except Exception:
                                continue

            # PADRÃO 4: Busca genérica por "MULTA" e valores próximos (mais restritiva)
            multa_generic_pattern = r'MULTA[^R\d]*?([\d.,]+)'
            for match in re.finditer(multa_generic_pattern, texto, re.IGNORECASE):
                valor_str = match.group(1)
                # Ignorar datas (formato MM/YYYY) e valores muito pequenos que podem ser meses
                if '/' not in valor_str:
                    valor = safe_decimal_conversion(valor_str)
                    if valor > Decimal('0.50'):  # Só valores acima de R$ 0,50 para evitar números de mês
                        # Evitar duplicatas verificando se já foi encontrado
                        if valor not in valores_encontrados:
                            # Verificar se não é um número de mês isolado (1-12)
                            if not (valor >= Decimal('1') and valor <= Decimal('12') and valor == valor.to_integral_value()):
                                valores_encontrados.append(valor)
                                if self.debug:
                                    print(f"   Multa genérica: {valor}")
                            elif self.debug:
                                print(f"   Multa ignorada (possivelmente mês): {valor}")

            # SOMAR TODOS OS VALORES ENCONTRADOS
            if valores_encontrados:
                self.multa_total = sum(valores_encontrados)
                resultado['valor_multa'] = self.multa_total

                if self.debug:
                    print(f"   TOTAL MULTA: {len(valores_encontrados)} valores encontrados")
                    for i, valor in enumerate(valores_encontrados):
                        print(f"     Multa {i+1}: R$ {valor}")
                    print(f"   SOMA FINAL: R$ {self.multa_total}")

        except Exception as e:
            if self.debug:
                print(f"[ERRO] Erro extraindo multa: {e}")

        return resultado

    def _extrair_iluminacao(self, texto: str) -> Dict[str, Any]:
        """Extract iluminação data."""
        resultado = {}

        if self.debug:
            print(f"[FINANCEIRO] Extraindo iluminação...")

        try:
            # PADRÕES ILUMINAÇÃO
            iluminacao_patterns = [
                r'ILUMINAÇÃO.*?R\$\s*([\d.,]+)',
                r'ILUMINACAO.*?R\$\s*([\d.,]+)',
                r'CONTRIB.*ILUM.*?R\$\s*([\d.,]+)',
                r'COSIP.*?R\$\s*([\d.,]+)',
                r'ILUMINAÇÃO.*?([\d.,]+)',
                r'ILUMINACAO.*?([\d.,]+)'
            ]

            for pattern in iluminacao_patterns:
                match = re.search(pattern, texto, re.IGNORECASE)
                if match:
                    valor = safe_decimal_conversion(match.group(1))
                    if valor > Decimal('0'):
                        self.iluminacao_total += valor
                        resultado['valor_iluminacao'] = self.iluminacao_total
                        if self.debug:
                            print(f"   OK: Iluminação detectada: R$ {valor}")
                        return resultado

            # PADRÃO LINHA: Buscar em linhas que contenham iluminação
            linhas = texto.split('\n')
            for linha in linhas:
                if any(termo in linha.upper() for termo in ['ILUMINAÇÃO', 'ILUMINACAO', 'COSIP']):
                    parts = linha.split()
                    for part in parts:
                        # Verificar se a parte parece um número antes de tentar converter
                        if re.search(r'\d', part):  # Tem pelo menos um dígito
                            try:
                                valor = safe_decimal_conversion(part)
                                if valor > Decimal('0'):  # Só aceitar valores positivos
                                    self.iluminacao_total += valor
                                    resultado['valor_iluminacao'] = self.iluminacao_total
                                    if self.debug:
                                        print(f"   OK: Iluminação detectada (busca linha): R$ {valor}")
                                    return resultado
                            except Exception:
                                continue

        except Exception as e:
            if self.debug:
                print(f"[ERRO] Erro extraindo iluminação: {e}")

        return resultado

    def _extrair_beneficios(self, texto: str) -> Dict[str, Any]:
        """Extract benefit data."""
        resultado = {}

        if self.debug:
            print(f"[FINANCEIRO] Extraindo benefícios...")

        try:
            # PADRÃO BENEFÍCIO BRUTO
            beneficio_bruto_patterns = [
                r'BENEFÍCIO BRUTO.*?R\$\s*([\d.,]+)',
                r'BENEFICIO BRUTO.*?R\$\s*([\d.,]+)',
                r'VALOR BRUTO.*?R\$\s*([\d.,]+)'
            ]

            for pattern in beneficio_bruto_patterns:
                match = re.search(pattern, texto, re.IGNORECASE)
                if match:
                    valor = safe_decimal_conversion(match.group(1))
                    if valor > Decimal('0'):
                        resultado['valor_beneficio_bruto'] = valor
                        if self.debug:
                            print(f"   OK: Benefício bruto detectado: R$ {valor}")
                        break

            # PADRÃO BENEFÍCIO LÍQUIDO
            beneficio_liquido_patterns = [
                r'BENEFÍCIO LÍQUIDO.*?R\$\s*([\d.,]+)',
                r'BENEFICIO LIQUIDO.*?R\$\s*([\d.,]+)',
                r'VALOR LÍQUIDO.*?R\$\s*([\d.,]+)',
                r'VALOR LIQUIDO.*?R\$\s*([\d.,]+)'
            ]

            for pattern in beneficio_liquido_patterns:
                match = re.search(pattern, texto, re.IGNORECASE)
                if match:
                    valor = safe_decimal_conversion(match.group(1))
                    if valor > Decimal('0'):
                        resultado['valor_beneficio_liquido'] = valor
                        if self.debug:
                            print(f"   OK: Benefício líquido detectado: R$ {valor}")
                        break

        except Exception as e:
            if self.debug:
                print(f"[ERRO] Erro extraindo benefícios: {e}")

        return resultado

    def _extract_positioned_financial(self, blocks_info: list) -> Dict[str, Any]:
        """
        Extract financial data using position information.
        Based on original coordinate-based logic if needed.
        """
        resultado = {}

        # For now, this is a placeholder for position-based extraction
        # The text-based extraction above should be sufficient for most cases
        # But this can be expanded if specific coordinate-based logic is needed

        return resultado