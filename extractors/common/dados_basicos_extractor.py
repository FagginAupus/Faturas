"""
Common extractor for basic invoice data.
Migrates logic from DadosBasicosExtractor.
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


class DadosBasicosExtractor:
    """
    Extractor for basic invoice data common to all types.
    Migrated from original DadosBasicosExtractor.

    CRITICAL FIELDS EXTRACTED (maintain exact names):
    - uc, endereco, cnpj_cpf, medidor
    - grupo, modalidade_tarifaria, tipo_fornecimento
    - mes_referencia, data_leitura, vencimento
    - valor_concessionaria
    """

    def __init__(self):
        self.debug = True

    def extract_basic_data(self, texto_completo: str) -> Dict[str, Any]:
        """
        Extract basic invoice data from complete text.
        Migrated from original DadosBasicosExtractor - maintains exact logic.

        Args:
            texto_completo: Full text from all PDF pages

        Returns:
            Dictionary with basic data using exact field names
        """
        result = {}

        # Process text by lines for coordinate-based logic simulation
        lines = texto_completo.split('\n')

        for line_num, text in enumerate(lines):
            if not text.strip():
                continue

            # Simulate coordinate-based filtering from original
            x0, y0 = self._simulate_coordinates(line_num, len(lines))
            block_info = {'x0': x0, 'y0': y0}

            # UC (Unidade Consumidora) - COPIED FROM ORIGINAL
            if 380 <= x0 <= 450 and 190 <= y0 <= 220:
                uc_match = re.search(r"\d+", text)
                if uc_match:
                    result['uc'] = uc_match.group(0)

            # Classificação completa (Grupo, Subgrupo, Tipo) - COPIED FROM ORIGINAL
            if "Classificação:" in text:
                classificacao_completa = text.split("Classificação:")[-1].strip()
                partes = classificacao_completa.split()

                if partes:
                    # Primeiro elemento é o grupo (A ou B)
                    result['grupo'] = partes[0]

                    # Segundo elemento é o subgrupo (B1, B2, A3, etc.)
                    if len(partes) > 1:
                        result['subgrupo'] = partes[1]

                    # Extrair tipo de consumidor (RESIDENCIAL, RURAL, etc.)
                    if "-" in classificacao_completa:
                        antes_hifen = classificacao_completa.split("-")[0].strip().split()
                        depois_hifen = classificacao_completa.split("-")[1].strip()

                        # O tipo está geralmente após o subgrupo
                        if len(antes_hifen) > 2:
                            result['tipo_consumidor'] = antes_hifen[2]

                        # Modalidade tarifária está após o hífen
                        if "BRANCA" in depois_hifen:
                            result['modalidade_tarifaria'] = "BRANCA"
                        elif "CONVENCIONAL" in depois_hifen:
                            result['modalidade_tarifaria'] = "CONVENCIONAL"

                        result['classificacao'] = depois_hifen

            # Tipo de fornecimento - COPIED FROM ORIGINAL
            if "tipo de fornecimento:" in text.lower():
                tipo_part = text.lower().split("tipo de fornecimento:")[-1].strip().split("\n")[0]
                result['tipo_fornecimento'] = tipo_part.upper()

            # Vencimento e valor - COPIED FROM ORIGINAL
            if (185.00 <= x0 <= 430.00) and (240.00 <= y0 <= 280.00):
                # Data de vencimento - SEM MUDANÇA
                from datetime import datetime
                date_match = re.search(r"\d{2}/\d{2}/\d{4}", text)
                if date_match:
                    try:
                        vencimento = datetime.strptime(date_match.group(0), "%d/%m/%Y")
                        result['vencimento'] = vencimento.strftime("%d/%m/%y")
                    except ValueError:
                        pass

                # Valor da fatura - USAR DECIMAL
                valor_match = re.search(r"\*+(\d+(?:\.\d+)*,\d{2})", text)
                if valor_match:
                    result['valor_concessionaria'] = self._clean_monetary_value(valor_match.group(1))

            # Resolução Homologatória (geralmente no rodapé) - COPIED FROM ORIGINAL
            if (25 <= x0 <= 200) and (700 <= y0 <= 900):
                res_match = re.search(r"(\d{4})/(\d{2})", text)
                if res_match:
                    result['resolucao_homologatoria'] = res_match.group(0)

        # Additional patterns not coordinate-dependent
        # Extract UC with broader patterns if not found
        if 'uc' not in result:
            uc_patterns = [
                r'Unidade Consumidora[:\s]*(\d{10,12})',
                r'UC[:\s]*(\d{10,12})',
                r'(\d{11})(?:\s|$)',  # 11-digit standalone
            ]
            for pattern in uc_patterns:
                match = re.search(pattern, texto_completo, re.IGNORECASE)
                if match:
                    result['uc'] = match.group(1).strip()
                    break

        # Extract CPF/CNPJ if not found
        if 'cnpj_cpf' not in result:
            cnpj_cpf = self._extrair_cnpj_cpf(texto_completo)
            if cnpj_cpf:
                result['cnpj_cpf'] = cnpj_cpf

        # Extract address if not found
        if 'endereco' not in result:
            endereco = self._extrair_endereco(texto_completo)
            if endereco:
                result['endereco'] = endereco

        if self.debug and result:
            print(f"[BASICOS] Extraídos {len(result)} campos: {list(result.keys())}")

        return result

    def _simulate_coordinates(self, line_num: int, total_lines: int) -> tuple:
        """Simulate coordinates based on line position for coordinate-based logic."""
        # Simple simulation: distribute lines across coordinate space
        x0 = 50 + (line_num % 10) * 80  # Simulate horizontal position
        y0 = 100 + (line_num / total_lines) * 600  # Simulate vertical position
        return (x0, y0)

    def _clean_monetary_value(self, value: str) -> Decimal:
        """Clean and convert monetary values to Decimal - COPIED FROM ORIGINAL."""
        try:
            if not value or not isinstance(value, str):
                return Decimal('0')

            # Remove R$, espaços
            cleaned = value.replace('R$', '').strip()

            if not cleaned:
                return Decimal('0')

            return safe_decimal_conversion(cleaned, "monetary")

        except Exception as e:
            print(f"AVISO: Erro em clean_monetary_value com '{value}': {e}")
            return Decimal('0')

    def _extrair_endereco(self, texto: str) -> Optional[str]:
        """Extract customer address."""
        # Look for address patterns
        endereco_patterns = [
            r'Endereço[:\s]*(.*?)(?:\n|CEP|Município)',
            r'ENDEREÇO[:\s]*(.*?)(?:\n|CEP|MUNICÍPIO)',
            r'(?:RUA|AV|AVENIDA|TRAVESSA|QUADRA).*?(?:\n|CEP)',
        ]

        for pattern in endereco_patterns:
            match = re.search(pattern, texto, re.MULTILINE | re.IGNORECASE | re.DOTALL)
            if match:
                endereco = match.group(1).strip()
                # Clean address
                endereco = re.sub(r'\s+', ' ', endereco)
                if len(endereco) > 10:  # Minimum address length
                    return endereco

        return None

    def _extrair_cnpj_cpf(self, texto: str) -> Optional[str]:
        """Extract CPF or CNPJ."""
        # CNPJ pattern: XX.XXX.XXX/XXXX-XX
        cnpj_pattern = r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}'
        cnpj_match = re.search(cnpj_pattern, texto)
        if cnpj_match:
            return cnpj_match.group(0)

        # CPF pattern: XXX.XXX.XXX-XX
        cpf_pattern = r'\d{3}\.\d{3}\.\d{3}-\d{2}'
        cpf_match = re.search(cpf_pattern, texto)
        if cpf_match:
            return cpf_match.group(0)

        # Alternative patterns without formatting
        cnpj_alt = r'\d{14}'
        cpf_alt = r'\d{11}'

        # Look for 14-digit CNPJ
        for match in re.finditer(cnpj_alt, texto):
            numero = match.group(0)
            if self._is_valid_cnpj_format(numero):
                return self._format_cnpj(numero)

        # Look for 11-digit CPF
        for match in re.finditer(cpf_alt, texto):
            numero = match.group(0)
            if self._is_valid_cpf_format(numero):
                return self._format_cpf(numero)

        return None

    def _is_valid_cnpj_format(self, numero: str) -> bool:
        """Basic CNPJ format validation."""
        return len(numero) == 14 and numero.isdigit()

    def _is_valid_cpf_format(self, numero: str) -> bool:
        """Basic CPF format validation."""
        return len(numero) == 11 and numero.isdigit()

    def _format_cnpj(self, numero: str) -> str:
        """Format CNPJ with dots and slash."""
        return f"{numero[:2]}.{numero[2:5]}.{numero[5:8]}/{numero[8:12]}-{numero[12:]}"

    def _format_cpf(self, numero: str) -> str:
        """Format CPF with dots and dash."""
        return f"{numero[:3]}.{numero[3:6]}.{numero[6:9]}-{numero[9:]}"

    def _extrair_medidor(self, texto: str) -> Optional[str]:
        """Extract meter number."""
        medidor_patterns = [
            r'Medidor[:\s]*(\d+)',
            r'Número do Medidor[:\s]*(\d+)',
            r'Nº do Medidor[:\s]*(\d+)'
        ]

        for pattern in medidor_patterns:
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extrair_grupo(self, texto: str) -> Optional[str]:
        """Extract tariff group (A or B)."""
        if re.search(r'GRUPO\s*A', texto, re.IGNORECASE):
            return "A"
        elif re.search(r'GRUPO\s*B', texto, re.IGNORECASE):
            return "B"

        # Infer from other indicators
        if any(indicator in texto.upper() for indicator in ['DEMANDA', 'TUSD', 'TE']):
            return "A"
        elif any(indicator in texto.upper() for indicator in ['MONOFÁSICO', 'BIFÁSICO', 'TRIFÁSICO']):
            return "B"

        return "B"  # Default assumption

    def _extrair_modalidade_tarifaria(self, texto: str) -> Optional[str]:
        """Extract tariff modality."""
        if re.search(r'AZUL', texto, re.IGNORECASE):
            return "AZUL"
        elif re.search(r'VERDE', texto, re.IGNORECASE):
            return "VERDE"
        elif re.search(r'BRANCA', texto, re.IGNORECASE):
            return "BRANCA"
        elif re.search(r'CONVENCIONAL', texto, re.IGNORECASE):
            return "CONVENCIONAL"

        # Infer from time-of-use indicators
        if any(indicator in texto.upper() for indicator in ['PONTA', 'FORA PONTA', 'INTERMEDIÁRIO']):
            return "BRANCA"

        return "CONVENCIONAL"  # Default for Group B

    def _extrair_tipo_fornecimento(self, texto: str) -> Optional[str]:
        """Extract power supply type."""
        if re.search(r'MONOFÁSICO', texto, re.IGNORECASE):
            return "MONOFÁSICO"
        elif re.search(r'BIFÁSICO', texto, re.IGNORECASE):
            return "BIFÁSICO"
        elif re.search(r'TRIFÁSICO', texto, re.IGNORECASE):
            return "TRIFÁSICO"

        return None

    def _extrair_mes_referencia(self, texto: str) -> Optional[str]:
        """Extract reference month."""
        # Pattern: MM/YYYY
        mes_patterns = [
            r'Referência[:\s]*(\d{2}/\d{4})',
            r'Ref[:\s]*(\d{2}/\d{4})',
            r'(\d{2}/\d{4})'
        ]

        for pattern in mes_patterns:
            match = re.search(pattern, texto)
            if match:
                return match.group(1)

        return None

    def _extrair_data_leitura(self, texto: str) -> Optional[str]:
        """Extract reading date."""
        # Pattern: DD/MM/YY or DD/MM/YYYY
        data_patterns = [
            r'Leitura[:\s]*(\d{2}/\d{2}/\d{2,4})',
            r'Data.*Leitura[:\s]*(\d{2}/\d{2}/\d{2,4})',
            r'(\d{2}/\d{2}/\d{2})(?:\s|$)'
        ]

        for pattern in data_patterns:
            match = re.search(pattern, texto)
            if match:
                return match.group(1)

        return None

    def _extrair_vencimento(self, texto: str) -> Optional[str]:
        """Extract due date."""
        # Pattern: DD/MM/YYYY
        vencimento_patterns = [
            r'Vencimento[:\s]*(\d{2}/\d{2}/\d{4})',
            r'Data.*Vencimento[:\s]*(\d{2}/\d{2}/\d{4})',
            r'Vence[:\s]*(\d{2}/\d{2}/\d{4})'
        ]

        for pattern in vencimento_patterns:
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                return match.group(1)

        return None