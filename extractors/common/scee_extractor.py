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

        # PADRÕES MÚLTIPLOS para maior robustez
        geracao_patterns = [
            r'GERAÇÃO CICLO.*?KWH:\s*UC\s*(\d+)\s*:\s*([\d.,]+)',
            r'GERACAO CICLO.*?KWH:\s*UC\s*(\d+)\s*:\s*([\d.,]+)',
            r'GERAÇÃO CICLO.*?UC\s*(\d+).*?([\d.,]+)',
            r'GERACAO CICLO.*?UC\s*(\d+).*?([\d.,]+)'
        ]

        geracao_match = None
        for pattern in geracao_patterns:
            geracao_match = re.search(pattern, texto, re.IGNORECASE)
            if geracao_match:
                break

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

        # PADRÕES MÚLTIPLOS para maior robustez
        excedente_patterns = [
            r'EXCEDENTE RECEBIDO KWH:\s*UC\s*(\d+)\s*:\s*([\d.,]+)',
            r'EXCEDENTE RECEBIDO.*?UC\s*(\d+).*?([\d.,]+)',
            r'ENERGIA EXCEDENTE.*?UC\s*(\d+).*?([\d.,]+)'
        ]

        excedente_match = None
        for pattern in excedente_patterns:
            excedente_match = re.search(pattern, texto, re.IGNORECASE)
            if excedente_match:
                break

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

        # MÚLTIPLOS PADRÕES para maior robustez
        credito_patterns = [
            r'CRÉDITO RECEBIDO KWH\s+([\d.,]+)',
            r'CREDITO RECEBIDO KWH\s+([\d.,]+)',
            r'CRÉDITO RECEBIDO.*?([\d.,]+)',
            r'CREDITO RECEBIDO.*?([\d.,]+)',
            r'CRÉDITO DE ENERGIA.*?([\d.,]+)',
            r'CREDITO DE ENERGIA.*?([\d.,]+)'
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
            # PADRÕES CONVENCIONAL MÚLTIPLOS
            saldo_conv_patterns = [
                r'SALDO KWH:\s*([\d.,]+)(?=,|\s|$)',
                r'SALDO DO CICLO.*?KWH.*?([\d.,]+)',
                r'SALDO.*?([\d.,]+)\s*KWH'
            ]

            for pattern in saldo_conv_patterns:
                saldo_conv_match = re.search(pattern, texto, re.IGNORECASE)
                if saldo_conv_match:
                    saldo_total = safe_decimal_conversion(saldo_conv_match.group(1))
                    resultado['saldo'] = saldo_total

                    if self.debug:
                        print(f"   OK: Saldo Convencional detectado: {saldo_total}")
                    break

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
            # PADRÕES CONVENCIONAL MÚLTIPLOS para 30 dias
            saldo_30_conv_patterns = [
                r'SALDO A EXPIRAR EM 30 DIAS KWH:\s*([\d.,]+)(?=,|\s|$)',
                r'A EXPIRAR EM 30 DIAS.*?([\d.,]+)',
                r'EXPIRAR.*?30.*?DIAS.*?([\d.,]+)'
            ]

            for pattern in saldo_30_conv_patterns:
                saldo_30_conv_match = re.search(pattern, texto, re.IGNORECASE)
                if saldo_30_conv_match:
                    resultado['saldo_30'] = safe_decimal_conversion(saldo_30_conv_match.group(1))
                    if self.debug:
                        print(f"   OK: Saldo 30 dias: {resultado['saldo_30']}")
                    break

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
            # PADRÕES CONVENCIONAL MÚLTIPLOS para 60 dias
            saldo_60_conv_patterns = [
                r'SALDO A EXPIRAR EM 60 DIAS KWH:\s*([\d.,]+)(?=,|\s|$)',
                r'A EXPIRAR EM 60 DIAS.*?([\d.,]+)',
                r'EXPIRAR.*?60.*?DIAS.*?([\d.,]+)'
            ]

            for pattern in saldo_60_conv_patterns:
                saldo_60_conv_match = re.search(pattern, texto, re.IGNORECASE)
                if saldo_60_conv_match:
                    resultado['saldo_60'] = safe_decimal_conversion(saldo_60_conv_match.group(1))
                    if self.debug:
                        print(f"   OK: Saldo 60 dias: {resultado['saldo_60']}")
                    break

        return resultado

    def _extrair_rateio_geracao(self, texto: str) -> Dict[str, Any]:
        """
        Extract generation rateio (distribution) data.
        Based on original CreditosSaldosExtractor logic.
        """
        resultado = {}

        if self.debug:
            print(f"[SCEE] Extraindo rateio de geração...")

        # PADRÃO PRINCIPAL: "CADASTRO RATEIO GERAÇÃO: UC 12345 = 100%"
        rateio_pattern = r'CADASTRO RATEIO GERAÇÃO:\s*UC\s*(\d+)\s*=\s*([\d.,]+%?)'
        rateio_match = re.search(rateio_pattern, texto, re.IGNORECASE)

        if rateio_match:
            resultado['rateio_fatura'] = rateio_match.group(2)
            if self.debug:
                print(f"   OK: Rateio: UC {rateio_match.group(1)} = {rateio_match.group(2)}")

        # PADRÃO ALTERNATIVO: Múltiplas UCs com percentuais
        # "RATEIO DA GERAÇÃO: UC 10037114075 (45%), UC 10037114024 (55%)"
        rateio_multiplo_pattern = r'RATEIO.*?UC\s*(\d+).*?([\d,]+)%'
        rateios_multiplos = re.findall(rateio_multiplo_pattern, texto, re.IGNORECASE)

        if rateios_multiplos:
            for idx, (uc, percentual) in enumerate(rateios_multiplos, 1):
                if idx <= 3:  # Máximo 3 UGs
                    resultado[f'uc_geradora_{idx}'] = uc
                    resultado[f'rateio_{idx}'] = safe_decimal_conversion(percentual) / Decimal('100')  # Converter para decimal

                    if self.debug:
                        print(f"   OK: Rateio {idx}: UC {uc} = {percentual}%")

        return resultado

    def _processar_dados_ugs(self, dados: Dict[str, Any]):
        """
        Process multiple UG data and set energia_injetada.
        CRITICAL: energia_injetada is used by Calculadora_AUPUS.py
        Based on original logic from CreditosSaldosExtractor.
        """
        if self.debug:
            print(f"[SCEE] Processando dados de UGs...")

        # Coletar todas as geracoes e excedentes
        geracoes = []
        excedentes = []

        # Extrair de registros brutos de geração
        if '_geracao_ugs_raw' in dados:
            for item in dados['_geracao_ugs_raw']:
                total_geracao = item.get('total', Decimal('0'))
                if total_geracao > 0:
                    geracoes.append(total_geracao)

                # Armazenar UCs geradoras (máximo 3)
                if len(geracoes) <= 3:
                    dados[f'uc_geradora_{len(geracoes)}'] = item.get('uc', '')

            if self.debug and geracoes:
                print(f"   Geracoes encontradas: {len(geracoes)} UGs")
                for i, geracao in enumerate(geracoes, 1):
                    print(f"     UG {i}: {geracao} kWh")

        # Extrair de registros brutos de excedente
        if '_excedente_ugs_raw' in dados:
            for item in dados['_excedente_ugs_raw']:
                total_excedente = item.get('total', Decimal('0'))
                if total_excedente > 0:
                    excedentes.append(total_excedente)

            if self.debug and excedentes:
                print(f"   Excedentes encontrados: {len(excedentes)} UGs")

        # CRITICAL LOGIC: energia_injetada priority - COPIED FROM ORIGINAL
        # 1. Preferir excedente_recebido (já calculado)
        # 2. Fallback para geracao_ciclo
        # 3. Fallback para soma das geracoes
        # 4. Fallback para soma dos excedentes

        energia_injetada_calculada = Decimal('0')

        if dados.get('excedente_recebido', Decimal('0')) > 0:
            energia_injetada_calculada = dados['excedente_recebido']
            if self.debug:
                print(f"   energia_injetada = excedente_recebido: {energia_injetada_calculada}")
        elif dados.get('geracao_ciclo', Decimal('0')) > 0:
            energia_injetada_calculada = dados['geracao_ciclo']
            if self.debug:
                print(f"   energia_injetada = geracao_ciclo: {energia_injetada_calculada}")
        elif geracoes:
            energia_injetada_calculada = sum(geracoes)
            if self.debug:
                print(f"   energia_injetada = soma geracoes: {energia_injetada_calculada}")
        elif excedentes:
            energia_injetada_calculada = sum(excedentes)
            if self.debug:
                print(f"   energia_injetada = soma excedentes: {energia_injetada_calculada}")
        else:
            energia_injetada_calculada = Decimal('0')
            if self.debug:
                print(f"   energia_injetada = 0 (nenhum dado encontrado)")

        # CRITICAL: Set energia_injetada (usado pela Calculadora_AUPUS.py)
        dados['energia_injetada'] = energia_injetada_calculada

        # Garantir que UCs geradoras existam mesmo que vazias
        for i in range(1, 4):  # uc_geradora_1, uc_geradora_2, uc_geradora_3
            uc_key = f'uc_geradora_{i}'
            if uc_key not in dados:
                dados[uc_key] = ''

        # Limpar campos internos temporarios
        dados.pop('_geracao_ugs_raw', None)
        dados.pop('_excedente_ugs_raw', None)

        if self.debug:
            print(f"[SCEE] Processamento UGs concluído:")
            print(f"   energia_injetada FINAL: {dados['energia_injetada']}")
            print(f"   UCs geradoras: {dados.get('uc_geradora_1', '')}, {dados.get('uc_geradora_2', '')}, {dados.get('uc_geradora_3', '')}")

    def _default_scee_values(self) -> Dict[str, Any]:
        """
        Return default SCEE values when invoice has no SCEE.
        Based on original CreditosSaldosExtractor behavior.
        """
        if self.debug:
            print(f"[SCEE] Aplicando valores padrão (sem SCEE)")

        return {
            # Saldos principais
            'saldo': Decimal('0'),
            'saldo_30': Decimal('0'),
            'saldo_60': Decimal('0'),

            # Energias
            'excedente_recebido': Decimal('0'),
            'credito_recebido': Decimal('0'),
            'energia_injetada': Decimal('0'),  # CRITICAL para Calculadora_AUPUS
            'geracao_ciclo': Decimal('0'),

            # UCs geradoras
            'uc_geradora_1': '',
            'uc_geradora_2': '',
            'uc_geradora_3': '',

            # Rateios
            'rateio_1': Decimal('0'),
            'rateio_2': Decimal('0'),
            'rateio_3': Decimal('0')
        }