"""
Base abstract extractor class for invoice processing.
Maintains compatibility with existing safe_decimal_conversion function.
"""

import re
import fitz  # PyMuPDF
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from decimal import Decimal, InvalidOperation
from pathlib import Path


def safe_decimal_conversion(value: str, campo: str = "") -> Decimal:
    """
    Safe Decimal conversion with robust error handling.
    COPIED from Leitor_Faturas_PDF.py to maintain compatibility.
    """
    try:
        if not value:
            return Decimal('0')

        # Convert to string if not already
        cleaned = str(value).strip()

        # If empty after cleaning
        if not cleaned:
            return Decimal('0')

        # Handle percentages - extract only the number
        if '%' in cleaned:
            cleaned = re.sub(r'[^\d.,-]', '', cleaned)
            if cleaned:
                # Convert to decimal (19% -> 0.19)
                decimal_val = Decimal(cleaned.replace(',', '.')) / Decimal('100')
                return decimal_val
            return Decimal('0')

        # Remove characters that are not digits, comma, dot or negative sign
        cleaned = re.sub(r'[^\d.,-]', '', cleaned)

        # If empty after cleaning
        if not cleaned:
            return Decimal('0')

        # Handle special cases
        if cleaned in ['-', '.', ',', '-.', '-,']:
            return Decimal('0')

        # If has comma and dot, comma is decimal
        if ',' in cleaned and '.' in cleaned:
            cleaned = cleaned.replace('.', '').replace(',', '.')
        # If only has comma, it's decimal
        elif ',' in cleaned:
            cleaned = cleaned.replace(',', '.')

        # Remove extra dots/commas at the end
        cleaned = cleaned.rstrip('.,')

        # If still empty
        if not cleaned:
            return Decimal('0')

        # Validate if it's a valid number before converting
        if not re.match(r'^-?\d*\.?\d*$', cleaned):
            return Decimal('0')

        return Decimal(cleaned)

    except (ValueError, TypeError, InvalidOperation) as e:
        print(f"AVISO: Erro convertendo '{value}' para Decimal no campo '{campo}': {e}")
        return Decimal('0')


class BaseExtractor(ABC):
    """
    Abstract base class for all invoice extractors.
    Ensures consistent interface and compatibility with existing system.
    """

    def __init__(self):
        self.debug = True  # Match existing system behavior
        self.dados = {}    # Match existing data structure

    @abstractmethod
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract data from PDF invoice.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary with extracted data using EXACT same field names
            as the current Leitor_Faturas_PDF.py system
        """
        pass

    def _open_pdf(self, pdf_path: str) -> fitz.Document:
        """Open PDF document safely."""
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
            if doc.page_count == 0:
                raise ValueError("PDF has no pages")
            return doc
        except Exception as e:
            raise ValueError(f"Cannot open PDF: {e}")

    def _extract_text_from_page(self, page: fitz.Page) -> str:
        """Extract text from a PDF page."""
        try:
            return page.get_text()
        except Exception as e:
            if self.debug:
                print(f"AVISO: Erro ao extrair texto da página: {e}")
            return ""

    def _extract_all_text(self, doc: fitz.Document) -> str:
        """Extract text from all pages."""
        all_text = ""
        for page_num in range(doc.page_count):
            page = doc[page_num]
            page_text = self._extract_text_from_page(page)
            all_text += f"\n{page_text}"
        return all_text

    def _search_pattern(self, text: str, pattern: str, grupo: int = 1) -> Optional[str]:
        """
        Search for a regex pattern in text.

        Args:
            text: Text to search in
            pattern: Regex pattern
            grupo: Capture group to return (default 1)

        Returns:
            Matched string or None
        """
        try:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match and len(match.groups()) >= grupo:
                return match.group(grupo).strip()
        except Exception as e:
            if self.debug:
                print(f"AVISO: Erro na busca do padrão '{pattern}': {e}")
        return None

    def _search_multiple_patterns(self, text: str, patterns: List[str]) -> Optional[str]:
        """Search for multiple patterns, return first match."""
        for pattern in patterns:
            result = self._search_pattern(text, pattern)
            if result:
                return result
        return None

    def _extract_monetary_value(self, text: str, campo: str = "") -> Decimal:
        """
        Extract and convert monetary value using safe conversion.
        Maintains compatibility with existing behavior.
        """
        if not text:
            return Decimal('0')

        # Clean and convert using the same function as existing system
        return safe_decimal_conversion(text, campo)

    def _extract_uc(self, text: str) -> Optional[str]:
        """
        Extract UC (Unidade Consumidora) using patterns from existing system.
        CRITICAL: Must match existing UC extraction logic exactly.
        """
        # Common UC patterns (from existing system)
        uc_patterns = [
            r'(?:UC|Unidade Consumidora)[:\s]*(\d{10,12})',
            r'(?:^|\s)(\d{11})(?:\s|$)',  # 11-digit number
            r'Código[:\s]*(\d{10,12})',
            r'(\d{10,12})\s*-\s*[A-Z]'
        ]

        for pattern in uc_patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                uc = match.group(1).strip()
                if len(uc) >= 10:  # Minimum UC length
                    return uc

        return None

    def _ensure_required_fields(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure all required fields exist with proper default values.
        CRITICAL for compatibility with Calculadora_AUPUS and Exportar_Planilha.
        """
        from .data_models import VALORES_PADRAO

        # Ensure all default values exist
        for campo, valor_padrao in VALORES_PADRAO.items():
            if campo not in dados:
                dados[campo] = valor_padrao

        # Ensure critical string fields are not None
        string_fields = ["uc", "grupo", "modalidade_tarifaria", "endereco", "cnpj_cpf"]
        for field in string_fields:
            if field not in dados or dados[field] is None:
                dados[field] = ""

        return dados

    def _validate_extraction_result(self, dados: Dict[str, Any]) -> bool:
        """
        Validate that extracted data meets minimum requirements.
        """
        # Must have UC
        if not dados.get("uc"):
            if self.debug:
                print("ERRO: UC não encontrada")
            return False

        # Must have grupo
        if not dados.get("grupo"):
            if self.debug:
                print("ERRO: Grupo tarifário não identificado")
            return False

        return True

    def _debug_print(self, message: str):
        """Print debug message if debug mode is enabled."""
        if self.debug:
            print(f"[DEBUG] {message}")

    def _info_print(self, message: str):
        """Print info message."""
        if self.debug:
            print(f"[INFO] {message}")

    def _error_print(self, message: str):
        """Print error message."""
        print(f"[ERRO] {message}")

    def _success_print(self, message: str):
        """Print success message."""
        if self.debug:
            print(f"[OK] {message}")

    def _close_pdf_safely(self, doc: fitz.Document):
        """Close PDF document safely."""
        try:
            if doc:
                doc.close()
        except Exception as e:
            if self.debug:
                print(f"AVISO: Erro ao fechar PDF: {e}")

    def _extract_basic_data(self, text: str) -> Dict[str, Any]:
        """
        Extract basic data common to all invoice types.
        This method will be implemented by common extractors.
        """
        # This will be implemented by common/dados_basicos_extractor.py
        return {}

    def _extract_tax_data(self, text: str) -> Dict[str, Any]:
        """
        Extract tax data (ICMS, PIS, COFINS).
        This method will be implemented by common extractors.
        """
        # This will be implemented by common/impostos_extractor.py
        return {}

    def _extract_financial_data(self, text: str) -> Dict[str, Any]:
        """
        Extract financial data (values, fees, etc.).
        This method will be implemented by common extractors.
        """
        # This will be implemented by common/financeiro_extractor.py
        return {}