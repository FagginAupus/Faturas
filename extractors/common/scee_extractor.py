"""
Common extractor for SCEE (Energy Compensation System) data.
Migrates logic from CreditosSaldosExtractor.
CRITICAL: Maintains exact field names for compatibility.
"""

import re
from typing import Dict, Any, List, Optional
from decimal import Decimal
from pathlib import Path

# Import utilities
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from core.base_extractor import safe_decimal_conversion


class SCEEExtractor:
    """
    Extractor for SCEE data common to all invoice types.
    Migrated from original CreditosSaldosExtractor.

    CRITICAL FIELDS EXTRACTED (maintain exact names):
    - saldo, excedente_recebido, credito_recebido
    - energia_injetada, geracao_ciclo
    - uc_geradora_1, uc_geradora_2
    - For BRANCA: saldo_p, saldo_fp, saldo_hr, saldo_hi
    - saldo_30, saldo_60 (with posto variants if applicable)
    """

    def __init__(self):
        self.debug = True

    def extract_scee_data(self, texto_completo: str) -> Dict[str, Any]:
        """
        Extract SCEE data from complete invoice text.

        Args:
            texto_completo: Full text from all PDF pages

        Returns:
            Dictionary with SCEE data using exact field names
        """
        dados = {}

        try:
            # Check if this invoice has SCEE information
            if not self._tem_informacoes_scee(texto_completo):
                return self._default_scee_values()

            # Extract generation data
            geracao_data = self._extrair_geracao_ciclo(texto_completo)
            dados.update(geracao_data)

            # Extract excedente data
            excedente_data = self._extrair_excedente_recebido(texto_completo)
            dados.update(excedente_data)

            # Extract credit data
            credito_data = self._extrair_credito_recebido(texto_completo)
            dados.update(credito_data)

            # Extract saldo data
            saldo_data = self._extrair_saldo_energia(texto_completo)
            dados.update(saldo_data)

            # Extract saldos a expirar
            saldos_expirar = self._extrair_saldos_a_expirar(texto_completo)
            dados.update(saldos_expirar)

            # Extract rateio data
            rateio_data = self._extrair_rateio_geracao(texto_completo)
            dados.update(rateio_data)

            # Process UG data and set energia_injetada
            self._processar_dados_ugs(dados)

            if self.debug and dados:
                print(f"[SCEE] Extraídos {len(dados)} campos SCEE")

        except Exception as e:
            if self.debug:
                print(f"[ERRO] Erro extraindo SCEE: {e}")
            dados = self._default_scee_values()

        return dados

    def _tem_informacoes_scee(self, texto: str) -> bool:
        """Check if invoice contains SCEE information."""
        scee_indicators = [
            "INFORMAÇÕES DO SCEE:", "INFORMACOES DO SCEE:",
            "CRÉDITO DE ENERGIA:", "CREDITO DE ENERGIA:", "SCEE:",
            "EXCEDENTE RECEBIDO", "GERAÇÃO CICLO", "GERACAO CICLO",
            "SALDO KWH", "CRÉDITO RECEBIDO", "CREDITO RECEBIDO",
            "ENERGIA INJETADA", "SISTEMA DE COMPENSAÇÃO"
        ]

        return any(indicator in texto.upper() for indicator in scee_indicators)

    def _extrair_geracao_ciclo(self, texto: str) -> Dict[str, Any]:
        """Extract geração ciclo data."""
        resultado = {}
        geracao_matches = []

        if self.debug:
            print(f"[SCEE] Extraindo geração ciclo...")

        # PADRÃO PRINCIPAL: "GERAÇÃO CICLO (6/2025) KWH: UC 10037114075 : 58.010,82"
        geracao_pattern = r'GERAÇÃO CICLO.*?KWH:\s*UC\s*(\d+)\s*:\s*([\d.,]+)'
        geracao_match = re.search(geracao_pattern, texto, re.IGNORECASE)

        if geracao_match:
            uc_geradora = geracao_match.group(1)
            geracao_total = safe_decimal_conversion(geracao_match.group(2))

            geracao_matches.append({
                'uc': uc_geradora,
                'tipo': 'grupo_b',
                'total': geracao_total
            })

            if self.debug:
                print(f"   OK: Geração detectada: UC {uc_geradora}, Total: {geracao_total}")

        # PADRÃO TARIFA BRANCA: "UC 10037114024 : P=0,40, FP=18.781,95, HR=0,00, HI=0,00"
        geracao_branca_pattern = r'UC\s*(\d+)\s*:\s*P=([\d.,]+),\s*FP=([\d.,]+),\s*HR=([\d.,]+),\s*HI=([\d.,]+)'
        geracao_branca_match = re.search(geracao_branca_pattern, texto, re.IGNORECASE)

        if geracao_branca_match:
            uc_geradora = geracao_branca_match.group(1)
            p_val = safe_decimal_conversion(geracao_branca_match.group(2))
            fp_val = safe_decimal_conversion(geracao_branca_match.group(3))
            hr_val = safe_decimal_conversion(geracao_branca_match.group(4))
            hi_val = safe_decimal_conversion(geracao_branca_match.group(5))

            geracao_total = p_val + fp_val + hr_val + hi_val

            geracao_matches.append({
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
                print(f"       P={p_val}, FP={fp_val}, HR={hr_val}, HI={hi_val}")

        # Store generation data
        if geracao_matches:
            resultado['_geracao_ugs_raw'] = geracao_matches

            # Set first UG as primary
            resultado['uc_geradora_1'] = geracao_matches[0]['uc']
            resultado['geracao_ciclo'] = geracao_matches[0]['total']

            # Set second UG if available
            if len(geracao_matches) > 1:
                resultado['uc_geradora_2'] = geracao_matches[1]['uc']
                resultado['geracao_ugs_2'] = geracao_matches[1]['total']

        return resultado

    def _extrair_excedente_recebido(self, texto: str) -> Dict[str, Any]:
        """Extract excedente recebido data."""
        resultado = {}
        excedente_matches = []

        if self.debug:
            print(f"[SCEE] Extraindo excedente recebido...")

        # PADRÃO CONVENCIONAL: "EXCEDENTE RECEBIDO KWH: UC 10037114075 : 16.370,65"
        excedente_pattern = r'EXCEDENTE RECEBIDO KWH:\s*UC\s*(\d+)\s*:\s*([\d.,]+)'
        excedente_match = re.search(excedente_pattern, texto, re.IGNORECASE)

        if excedente_match:
            uc = excedente_match.group(1)
            excedente_total = safe_decimal_conversion(excedente_match.group(2))

            excedente_matches.append({
                'uc': uc,
                'tipo': 'grupo_b',
                'total': excedente_total
            })

            if self.debug:
                print(f"   OK: Excedente detectado: UC {uc}, Total: {excedente_total}")

        # PADRÃO TARIFA BRANCA: "EXCEDENTE RECEBIDO KWH: UC 10037114024 : P=0,11, FP=5.258,95, HR=0,00, HI=0,00"
        excedente_branca_pattern = r'EXCEDENTE RECEBIDO KWH:\s*UC\s*(\d+)\s*:\s*P=([\d.,]+),\s*FP=([\d.,]+),\s*HR=([\d.,]+),\s*HI=([\d.,]+)'
        excedente_branca_match = re.search(excedente_branca_pattern, texto, re.IGNORECASE)

        if excedente_branca_match:
            uc = excedente_branca_match.group(1)
            p_val = safe_decimal_conversion(excedente_branca_match.group(2))
            fp_val = safe_decimal_conversion(excedente_branca_match.group(3))
            hr_val = safe_decimal_conversion(excedente_branca_match.group(4))
            hi_val = safe_decimal_conversion(excedente_branca_match.group(5))

            excedente_total = p_val + fp_val + hr_val + hi_val

            excedente_matches.append({
                'uc': uc,
                'tipo': 'grupo_b_branca',
                'total': excedente_total,
                'p': p_val,
                'fp': fp_val,
                'hr': hr_val,
                'hi': hi_val
            })

            if self.debug:
                print(f"   OK: Excedente Branca: UC {uc}, Total: {excedente_total}")
                print(f"       P={p_val}, FP={fp_val}, HR={hr_val}, HI={hi_val}")

        # Store excedente data
        if excedente_matches:
            resultado['_excedente_ugs_raw'] = excedente_matches

            # Calculate total excedente
            total_excedente = sum(item['total'] for item in excedente_matches)
            resultado['excedente_recebido'] = total_excedente
        else:
            resultado['excedente_recebido'] = Decimal('0')

        return resultado

    def _extrair_credito_recebido(self, texto: str) -> Dict[str, Any]:
        """Extract crédito recebido data."""
        resultado = {}

        if self.debug:
            print(f"[SCEE] Extraindo crédito recebido...")

        # PADRÃO: "CRÉDITO RECEBIDO KWH 1.234,56"
        credito_patterns = [
            r'CRÉDITO RECEBIDO KWH\s+([\d.,]+)',
            r'CREDITO RECEBIDO KWH\s+([\d.,]+)',
            r'CRÉDITO RECEBIDO.*?([\d.,]+)',
            r'CREDITO RECEBIDO.*?([\d.,]+)'
        ]

        for pattern in credito_patterns:
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                valor_credito = safe_decimal_conversion(match.group(1))
                resultado['credito_recebido'] = valor_credito

                if self.debug:
                    print(f"   OK: Crédito detectado: {valor_credito}")
                break

        if 'credito_recebido' not in resultado:
            resultado['credito_recebido'] = Decimal('0')

        return resultado

    def _extrair_saldo_energia(self, texto: str) -> Dict[str, Any]:
        """Extract saldo energia data."""
        resultado = {}

        if self.debug:
            print(f"[SCEE] Extraindo saldo energia...")

        # PADRÃO TARIFA BRANCA: "SALDO KWH: P=1.234,56, FP=5.678,90, HR=0,00, HI=0,00"
        saldo_branca_pattern = r'SALDO KWH:\s*P=([\d.,]+),\s*FP=([\d.,]+),\s*HR=([\d.,]+),\s*HI=([\d.,]+)'
        saldo_branca_match = re.search(saldo_branca_pattern, texto, re.IGNORECASE)

        if saldo_branca_match:
            # TARIFA BRANCA - saldos separados por posto
            saldo_p = safe_decimal_conversion(saldo_branca_match.group(1))
            saldo_fp = safe_decimal_conversion(saldo_branca_match.group(2))
            saldo_hr = safe_decimal_conversion(saldo_branca_match.group(3))
            saldo_hi = safe_decimal_conversion(saldo_branca_match.group(4))

            saldo_total = saldo_p + saldo_fp + saldo_hr + saldo_hi

            # Save saldos por posto
            resultado['saldo_p'] = saldo_p
            resultado['saldo_fp'] = saldo_fp
            resultado['saldo_hr'] = saldo_hr
            resultado['saldo_hi'] = saldo_hi
            resultado['saldo'] = saldo_total

            if self.debug:
                print(f"   OK: Saldo Branca detectado:")
                print(f"       P={saldo_p}, FP={saldo_fp}, HR={saldo_hr}, HI={saldo_hi}")
                print(f"       Total: {saldo_total}")
        else:
            # PADRÃO CONVENCIONAL: "SALDO KWH: 1.234,56"
            saldo_conv_pattern = r'SALDO KWH:\s*([\d.,]+)(?=,|\s|$)'
            saldo_conv_match = re.search(saldo_conv_pattern, texto, re.IGNORECASE)

            if saldo_conv_match:
                saldo_total = safe_decimal_conversion(saldo_conv_match.group(1))
                resultado['saldo'] = saldo_total

                if self.debug:
                    print(f"   OK: Saldo Convencional detectado: {saldo_total}")

        # Default saldo if not found
        if 'saldo' not in resultado:
            resultado['saldo'] = Decimal('0')
            if self.debug:
                print(f"   Saldo definido como 0 (não encontrado)")

        return resultado

    def _extrair_saldos_a_expirar(self, texto: str) -> Dict[str, Any]:
        """Extract saldos a expirar data."""
        resultado = {}

        if self.debug:
            print(f"[SCEE] Extraindo saldos a expirar...")

        # SALDO A EXPIRAR EM 30 DIAS
        # PADRÃO TARIFA BRANCA
        saldo_30_branca_pattern = r'SALDO A EXPIRAR EM 30 DIAS KWH:\s*P=([\d.,]+),\s*FP=([\d.,]+),\s*HR=([\d.,]+),\s*HI=([\d.,]+)'
        saldo_30_branca_match = re.search(saldo_30_branca_pattern, texto, re.IGNORECASE)

        if saldo_30_branca_match:
            saldo_30_p = safe_decimal_conversion(saldo_30_branca_match.group(1))
            saldo_30_fp = safe_decimal_conversion(saldo_30_branca_match.group(2))
            saldo_30_hr = safe_decimal_conversion(saldo_30_branca_match.group(3))
            saldo_30_hi = safe_decimal_conversion(saldo_30_branca_match.group(4))

            resultado['saldo_30_p'] = saldo_30_p
            resultado['saldo_30_fp'] = saldo_30_fp
            resultado['saldo_30_hr'] = saldo_30_hr
            resultado['saldo_30_hi'] = saldo_30_hi
            resultado['saldo_30'] = saldo_30_p + saldo_30_fp + saldo_30_hr + saldo_30_hi

            if self.debug:
                print(f"   OK: Saldo 30 dias Branca: P={saldo_30_p}, FP={saldo_30_fp}, HR={saldo_30_hr}, HI={saldo_30_hi}")
        else:
            # PADRÃO CONVENCIONAL
            saldo_30_conv_pattern = r'SALDO A EXPIRAR EM 30 DIAS KWH:\s*([\d.,]+)(?=,|\s|$)'
            saldo_30_conv_match = re.search(saldo_30_conv_pattern, texto, re.IGNORECASE)

            if saldo_30_conv_match:
                resultado['saldo_30'] = safe_decimal_conversion(saldo_30_conv_match.group(1))
                if self.debug:
                    print(f"   OK: Saldo 30 dias: {resultado['saldo_30']}")

        # SALDO A EXPIRAR EM 60 DIAS
        # PADRÃO TARIFA BRANCA
        saldo_60_branca_pattern = r'SALDO A EXPIRAR EM 60 DIAS KWH:\s*P=([\d.,]+),\s*FP=([\d.,]+),\s*HR=([\d.,]+),\s*HI=([\d.,]+)'
        saldo_60_branca_match = re.search(saldo_60_branca_pattern, texto, re.IGNORECASE)

        if saldo_60_branca_match:
            saldo_60_p = safe_decimal_conversion(saldo_60_branca_match.group(1))
            saldo_60_fp = safe_decimal_conversion(saldo_60_branca_match.group(2))
            saldo_60_hr = safe_decimal_conversion(saldo_60_branca_match.group(3))
            saldo_60_hi = safe_decimal_conversion(saldo_60_branca_match.group(4))

            resultado['saldo_60_p'] = saldo_60_p
            resultado['saldo_60_fp'] = saldo_60_fp
            resultado['saldo_60_hr'] = saldo_60_hr
            resultado['saldo_60_hi'] = saldo_60_hi
            resultado['saldo_60'] = saldo_60_p + saldo_60_fp + saldo_60_hr + saldo_60_hi

            if self.debug:
                print(f"   OK: Saldo 60 dias Branca: P={saldo_60_p}, FP={saldo_60_fp}, HR={saldo_60_hr}, HI={saldo_60_hi}")
        else:
            # PADRÃO CONVENCIONAL
            saldo_60_conv_pattern = r'SALDO A EXPIRAR EM 60 DIAS KWH:\s*([\d.,]+)(?=,|\s|$)'
            saldo_60_conv_match = re.search(saldo_60_conv_pattern, texto, re.IGNORECASE)

            if saldo_60_conv_match:
                resultado['saldo_60'] = safe_decimal_conversion(saldo_60_conv_match.group(1))
                if self.debug:
                    print(f"   OK: Saldo 60 dias: {resultado['saldo_60']}")

        return resultado

    def _extrair_rateio_geracao(self, texto: str) -> Dict[str, Any]:
        """Extract rateio geração data."""
        resultado = {}

        # PADRÃO: "CADASTRO RATEIO GERAÇÃO: UC 12345 = 100%"
        rateio_pattern = r'CADASTRO RATEIO GERAÇÃO:\s*UC\s*(\d+)\s*=\s*([\d.,]+%?)'
        rateio_match = re.search(rateio_pattern, texto, re.IGNORECASE)

        if rateio_match:
            resultado['rateio_fatura'] = rateio_match.group(2)
            if self.debug:
                print(f"   OK: Rateio: UC {rateio_match.group(1)} = {rateio_match.group(2)}")

        return resultado

    def _processar_dados_ugs(self, dados: Dict[str, Any]):
        """Process UG data and calculate energia_injetada."""
        # Calculate energia_injetada from generation data
        geracao_raw = dados.get('_geracao_ugs_raw', [])
        if geracao_raw:
            energia_injetada_total = sum(ug['total'] for ug in geracao_raw)
            dados['energia_injetada'] = energia_injetada_total

            if self.debug:
                print(f"[SCEE] Energia injetada total calculada: {energia_injetada_total}")
        else:
            dados['energia_injetada'] = Decimal('0')

        # Clean up raw data (not needed in final result)
        dados.pop('_geracao_ugs_raw', None)
        dados.pop('_excedente_ugs_raw', None)

    def _default_scee_values(self) -> Dict[str, Any]:
        """Return default SCEE values for invoices without SCEE."""
        return {
            'saldo': Decimal('0'),
            'excedente_recebido': Decimal('0'),
            'credito_recebido': Decimal('0'),
            'energia_injetada': Decimal('0'),
            'geracao_ciclo': Decimal('0'),
            'uc_geradora_1': '',
            'uc_geradora_2': ''
        }