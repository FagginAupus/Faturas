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
        Extract basic data from complete invoice text.

        Args:
            texto_completo: Full text from all PDF pages

        Returns:
            Dictionary with basic invoice data using exact field names
        """
        dados = {}

        try:
            # Extract UC (Unidade Consumidora)
            uc = self._extrair_uc(texto_completo)
            if uc:
                dados['uc'] = uc

            # Extract address
            endereco = self._extrair_endereco(texto_completo)
            if endereco:
                dados['endereco'] = endereco

            # Extract CPF/CNPJ
            cnpj_cpf = self._extrair_cnpj_cpf(texto_completo)
            if cnpj_cpf:
                dados['cnpj_cpf'] = cnpj_cpf

            # Extract meter number
            medidor = self._extrair_medidor(texto_completo)
            if medidor:
                dados['medidor'] = medidor

            # Extract tariff group
            grupo = self._extrair_grupo(texto_completo)
            if grupo:
                dados['grupo'] = grupo

            # Extract tariff modality
            modalidade = self._extrair_modalidade_tarifaria(texto_completo)
            if modalidade:
                dados['modalidade_tarifaria'] = modalidade

            # Extract supply type
            tipo_fornecimento = self._extrair_tipo_fornecimento(texto_completo)
            if tipo_fornecimento:
                dados['tipo_fornecimento'] = tipo_fornecimento

            # Extract reference month
            mes_referencia = self._extrair_mes_referencia(texto_completo)
            if mes_referencia:
                dados['mes_referencia'] = mes_referencia

            # Extract reading date
            data_leitura = self._extrair_data_leitura(texto_completo)
            if data_leitura:
                dados['data_leitura'] = data_leitura

            # Extract due date
            vencimento = self._extrair_vencimento(texto_completo)
            if vencimento:
                dados['vencimento'] = vencimento

            # Extract total invoice value
            valor_concessionaria = self._extrair_valor_concessionaria(texto_completo)
            if valor_concessionaria:
                dados['valor_concessionaria'] = valor_concessionaria

            if self.debug and dados:
                print(f"[BASICOS] Extraídos {len(dados)} campos básicos")

        except Exception as e:
            if self.debug:
                print(f"[ERRO] Erro extraindo dados básicos: {e}")

        return dados

    def _extrair_uc(self, texto: str) -> Optional[str]:
        """Extract UC (Unidade Consumidora)."""
        # Patterns for UC extraction (from original system)
        uc_patterns = [
            r'Unidade Consumidora[:\s]*(\d{10,12})',
            r'UC[:\s]*(\d{10,12})',
            r'Código[:\s]*(\d{10,12})',
            r'(\d{11})(?:\s|$)',  # 11-digit standalone number
            r'(\d{10,12})\s*-\s*[A-Z]'
        ]

        for pattern in uc_patterns:
            match = re.search(pattern, texto, re.MULTILINE | re.IGNORECASE)
            if match:
                uc = match.group(1).strip()
                if len(uc) >= 10:  # Minimum UC length
                    if self.debug:
                        print(f"[UC] Encontrada: {uc}")
                    return uc

        return None

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

    def _extrair_valor_concessionaria(self, texto: str) -> Optional[Decimal]:
        """Extract total invoice value."""
        # Look for total value patterns
        valor_patterns = [
            r'Total.*?R\$\s*([\d.,]+)',
            r'Valor Total.*?R\$\s*([\d.,]+)',
            r'TOTAL.*?([\d.,]+)',
            r'R\$\s*([\d.,]+)(?:\s|$)'
        ]

        for pattern in valor_patterns:
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                valor_str = match.group(1)
                valor = safe_decimal_conversion(valor_str)
                if valor > Decimal('0'):
                    return valor

        return None