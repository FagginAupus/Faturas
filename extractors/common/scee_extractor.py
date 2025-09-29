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
            # Add comprehensive debug at start
            if self.debug:
                print(f"\n{'='*60}")
                print(f"DEBUG EXTRATOR SCEE")
                print(f"{'='*60}")
                print(f"Texto total: {len(texto_completo)} caracteres")

            # Check if this invoice has SCEE information
            if not self._tem_informacoes_scee(texto_completo):
                if self.debug:
                    print("Nenhuma informacao SCEE encontrada.")
                return self._default_scee_values()

            # Debug: Show SCEE block if found
            if "INFORMAÇÕES DO SCEE" in texto_completo or "INFORMACOES DO SCEE" in texto_completo:
                inicio = texto_completo.find("INFORMAÇÕES DO SCEE")
                if inicio == -1:
                    inicio = texto_completo.find("INFORMACOES DO SCEE")

                if inicio != -1:
                    bloco = texto_completo[inicio:inicio+500]
                    if self.debug:
                        print(f"\nBLOCO SCEE ENCONTRADO:")
                        print(bloco)
                        print()
                else:
                    if self.debug:
                        print("Bloco INFORMACOES DO SCEE nao encontrado!")

            # Check for INJECAO SCEE line in table
            if self.debug:
                linhas = texto_completo.split('\n')
                for linha in linhas:
                    if "INJEÇÃO SCEE" in linha or "INJECAO SCEE" in linha:
                        print(f"Linha INJECAO encontrada: {linha}")
                        break

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

            # Extract injection data from table (INJECAO SCEE line)
            injecao_data = self._extrair_injecao_scee(texto_completo)
            dados.update(injecao_data)

            # Try to get injection data from external source (B extractor results) if available
            # This addresses cases where the line reconstruction didn't capture the right values
            self._tentar_injecao_externa(dados, texto_completo)

            # Print final debug summary
            if self.debug:
                self._print_valores_extraidos(dados)

            if self.debug and dados:
                print(f"[SCEE] Extraidos {len(dados)} campos SCEE")

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

        # PADRÕES MÚLTIPLOS para maior robustez - formato brasileiro
        geracao_patterns = [
            r'GERAÇÃO CICLO.*?KWH:\s*UC\s*(\d+)\s*:\s*([\d.,]+)',
            r'GERACAO CICLO.*?KWH:\s*UC\s*(\d+)\s*:\s*([\d.,]+)',
            r'GERAÇÃO CICLO.*?UC\s*(\d+).*?:\s*([\d.,]+)',
            r'GERACAO CICLO.*?UC\s*(\d+).*?:\s*([\d.,]+)'
        ]

        geracao_match = None
        for pattern in geracao_patterns:
            geracao_match = re.search(pattern, texto, re.IGNORECASE)
            if geracao_match:
                if self.debug:
                    print(f"   Padrão geração encontrado: {pattern}")
                    print(f"   Match: {geracao_match.group(0)}")
                break

        if geracao_match:
            uc_geradora = geracao_match.group(1)
            geracao_valor_str = geracao_match.group(2)
            geracao_total = self._converter_valor_brasileiro(geracao_valor_str)

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

        # PADRÕES MÚLTIPLOS para maior robustez - formato brasileiro
        excedente_patterns = [
            r'EXCEDENTE RECEBIDO KWH:\s*UC\s*(\d+)\s*:\s*([\d.,]+)',
            r'EXCEDENTE RECEBIDO.*?UC\s*(\d+).*?:\s*([\d.,]+)',
            r'ENERGIA EXCEDENTE.*?UC\s*(\d+).*?:\s*([\d.,]+)'
        ]

        excedente_match = None
        for pattern in excedente_patterns:
            excedente_match = re.search(pattern, texto, re.IGNORECASE)
            if excedente_match:
                if self.debug:
                    print(f"   Padrão excedente encontrado: {pattern}")
                    print(f"   Match: {excedente_match.group(0)}")
                break

        if excedente_match:
            uc = excedente_match.group(1)
            excedente_valor_str = excedente_match.group(2)
            excedente_total = self._converter_valor_brasileiro(excedente_valor_str)

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

        # MÚLTIPLOS PADRÕES para maior robustez - formato brasileiro
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
                credito_valor_str = match.group(1)
                valor_credito = self._converter_valor_brasileiro(credito_valor_str)
                resultado['credito_recebido'] = valor_credito

                if self.debug:
                    print(f"   OK: Crédito detectado: {valor_credito} (string: {credito_valor_str})")
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
            # PADRÕES CONVENCIONAL MÚLTIPLOS - formato brasileiro
            saldo_conv_patterns = [
                r'SALDO KWH:\s*([\d.,]+)(?=,|\s|$)',
                r'SALDO DO CICLO.*?KWH.*?([\d.,]+)',
                r'SALDO.*?([\d.,]+)\s*KWH'
            ]

            for pattern in saldo_conv_patterns:
                saldo_conv_match = re.search(pattern, texto, re.IGNORECASE)
                if saldo_conv_match:
                    saldo_valor_str = saldo_conv_match.group(1)
                    saldo_total = self._converter_valor_brasileiro(saldo_valor_str)
                    resultado['saldo'] = saldo_total

                    if self.debug:
                        print(f"   OK: Saldo Convencional detectado: {saldo_total} (string: {saldo_valor_str})")
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

    def _extrair_injecao_scee(self, texto: str) -> Dict[str, Any]:
        """
        Extract data from INJECAO SCEE line in consumption table.
        Format: "INJEÇÃO SCEE - UC 10037100562 - GD I kWh 709,00 0,643844 -456,49"
        Returns quantidade (709,00) and valor (456,49 positive)
        """
        resultado = {}

        if self.debug:
            print(f"[SCEE] Extraindo dados de injeção...")

        # Look for INJECAO SCEE line and extract values
        # First try to find a fully reconstructed line with all values
        pattern_completo = r'INJE[ÇC][ÃA]O SCEE.*?kWh\s+([\d.,]+)\s+([\d.,]+)\s+([-]?[\d.,]+)'
        match_completo = re.search(pattern_completo, texto, re.IGNORECASE)

        if match_completo:
            quantidade_str = match_completo.group(1)  # 709,00
            tarifa_str = match_completo.group(2)      # 0,643844
            valor_str = match_completo.group(3)       # -456,49

            # Convert values
            quantidade = self._converter_valor_brasileiro(quantidade_str)
            valor = abs(self._converter_valor_brasileiro(valor_str))  # Always positive

            resultado['energia_injetada'] = quantidade
            resultado['valor_energia_injetada'] = valor

            if self.debug:
                print(f"   Linha INJECAO completa encontrada:")
                print(f"   Match: {match_completo.group(0)}")
                print(f"   Quantidade injetada: {quantidade} kWh")
                print(f"   Valor energia injetada: R$ {valor}")
        else:
            # Fallback: process line by line if full pattern not found
            linhas = texto.split('\n')
            for i, linha in enumerate(linhas):
                if "INJEÇÃO SCEE" in linha or "INJECAO SCEE" in linha:
                    if self.debug:
                        print(f"   Linha INJECAO encontrada: {linha}")

                    # Extract UC number
                    uc_match = re.search(r'UC\s*(\d+)', linha)
                    if uc_match:
                        uc_number = uc_match.group(1)
                        if self.debug:
                            print(f"   UC extraida: {uc_number}")

                    # Try to find values in next few lines after INJECAO line
                    valores_numericos = []
                    for j in range(i + 1, min(i + 10, len(linhas))):
                        linha_seguinte = linhas[j].strip()

                        # Look for numeric values that could be quantidade/valor
                        numeric_matches = re.findall(r'([-]?[\d.,]+)', linha_seguinte)
                        for match in numeric_matches:
                            if re.match(r'^[-]?[\d.,]+$', match):  # Pure numeric value
                                valores_numericos.append(match)

                        # Stop if we have enough values or found next item
                        if len(valores_numericos) >= 3:
                            break
                        if any(word in linha_seguinte.upper() for word in ['CONTRIB', 'ITENS', 'TOTAL']):
                            break

                    if len(valores_numericos) >= 3:
                        # Based on pattern from B extractor: [tarifa, quantidade, valor_intermediario, valor_principal]
                        # From debug: 0,643844 709,00 -16,59 -456,49
                        # We want: quantidade = 709,00, valor = 456,49

                        # Try to identify which is quantidade (should be larger integer-like) and valor (larger absolute)
                        valores_convertidos = []
                        for val in valores_numericos[:5]:  # Check first 5 values
                            try:
                                converted = self._converter_valor_brasileiro(val)
                                valores_convertidos.append((val, abs(converted)))
                            except:
                                continue

                        if len(valores_convertidos) >= 2:
                            # Sort by absolute value to find the largest ones
                            valores_ordenados = sorted(valores_convertidos, key=lambda x: x[1], reverse=True)

                            # Find quantidade: should be the largest value, typically hundreds (709.0)
                            quantidade_str = valores_ordenados[0][0]
                            quantidade = self._converter_valor_brasileiro(quantidade_str)

                            # Find valor: should be the largest VALUE among those > 100
                            # Expected pattern: 709.00 (quantidade), 456.49 (valor), smaller values (tarifa, etc)
                            valor_str = None
                            for val_str, val_abs in valores_ordenados[1:]:  # Skip the quantidade
                                if val_abs > 100:  # Value should be > 100 for meaningful energy cost
                                    valor_str = val_str
                                    break

                            # Fallback to second largest if no good valor found
                            if not valor_str:
                                valor_str = valores_ordenados[1][0] if len(valores_ordenados) > 1 else valores_ordenados[0][0]

                            valor = abs(self._converter_valor_brasileiro(valor_str))

                            resultado['energia_injetada'] = quantidade
                            resultado['valor_energia_injetada'] = valor

                            if self.debug:
                                print(f"   Valores reconstruidos das linhas seguintes:")
                                print(f"   Valores encontrados: {valores_numericos}")
                                print(f"   Valores convertidos e ordenados: {valores_ordenados}")
                                print(f"   Quantidade injetada: {quantidade} kWh (de {quantidade_str})")
                                print(f"   Valor energia injetada: R$ {valor} (de {valor_str})")
                            break
                    else:
                        if self.debug:
                            print(f"   Valores insuficientes nas linhas seguintes: {valores_numericos}")

        return resultado

    def _tentar_injecao_externa(self, dados: Dict[str, Any], texto_completo: str):
        """
        Try to get injection data from reconstructed lines (like from B extractor).
        This is a fallback when the basic line-by-line extraction fails.
        """
        if self.debug:
            print(f"[SCEE] Tentando capturar injeção de fonte externa...")

        # Look for patterns that indicate already processed data
        # Pattern from B extractor: "INJEÇÃO SCEE - UC 10037100562 - GD I kWh 709,00 0,643844 -456,49"
        pattern_completo = r'INJE[ÇC][ÃA]O SCEE.*?kWh\s+([\d.,]+)\s+([\d.,]+)\s+([-]?[\d.,]+)\s+([-]?[\d.,]+)'
        match = re.search(pattern_completo, texto_completo, re.IGNORECASE)

        if match:
            # Expected: kWh QUANTIDADE TARIFA VALOR_INTERMEDIARIO VALOR_PRINCIPAL
            quantidade_str = match.group(1)  # 709,00
            valor_principal_str = match.group(4)  # -456,49

            quantidade = self._converter_valor_brasileiro(quantidade_str)
            valor_principal = abs(self._converter_valor_brasileiro(valor_principal_str))

            # Only override if we got better values
            if quantidade > 0 and valor_principal > 100:  # Reasonable thresholds
                dados['energia_injetada'] = quantidade
                dados['valor_energia_injetada'] = valor_principal

                if self.debug:
                    print(f"   Valores de injeção capturados de fonte externa:")
                    print(f"   Match completo: {match.group(0)}")
                    print(f"   energia_injetada: {quantidade} kWh")
                    print(f"   valor_energia_injetada: R$ {valor_principal}")
            else:
                if self.debug:
                    print(f"   Valores externos não passaram na validação: qtd={quantidade}, val={valor_principal}")
        else:
            # Final fallback: use credito_recebido as energia_injetada (common pattern)
            if dados.get('credito_recebido', 0) > 0 and dados.get('energia_injetada', 0) == 0:
                dados['energia_injetada'] = dados['credito_recebido']
                if self.debug:
                    print(f"   Fallback: energia_injetada = credito_recebido = {dados['energia_injetada']}")

    def _converter_valor_brasileiro(self, valor_str: str) -> Decimal:
        """
        Convert Brazilian number format to Decimal.
        Examples: "5.128,26" -> 5128.26, "959,50" -> 959.50, "709,00" -> 709.00
        Also handles trailing commas: "5.128,26," -> 5128.26
        """
        try:
            # Clean the string - remove trailing commas, spaces, and unwanted characters
            valor_str = valor_str.strip().rstrip(',').rstrip()

            # Handle negative values
            is_negative = valor_str.startswith('-')
            if is_negative:
                valor_str = valor_str[1:]

            # Remove thousand separators (dots) and replace comma with dot
            if ',' in valor_str:
                # Split by comma to get integer and decimal parts
                parts = valor_str.split(',')
                if len(parts) == 2:
                    integer_part = parts[0].replace('.', '')  # Remove dots from integer part
                    decimal_part = parts[1]
                    valor_clean = f"{integer_part}.{decimal_part}"
                else:
                    valor_clean = valor_str.replace('.', '').replace(',', '.')
            else:
                valor_clean = valor_str.replace('.', '')  # Only thousand separators

            result = Decimal(valor_clean)
            return -result if is_negative else result

        except Exception as e:
            if self.debug:
                print(f"   Erro convertendo valor '{valor_str}': {e}")
            return Decimal('0')

    def _print_valores_extraidos(self, dados: Dict[str, Any]):
        """
        Print final extracted SCEE values for debugging.
        """
        print(f"\n{'='*60}")
        print(f"VALORES EXTRAIDOS - SCEE")
        print(f"{'='*60}")
        print(f"QUANTIDADES (kWh):")
        print(f"   geracao_ciclo: {dados.get('geracao_ciclo', 0)}")
        print(f"   excedente_recebido: {dados.get('excedente_recebido', 0)}")
        print(f"   credito_recebido: {dados.get('credito_recebido', 0)}")
        print(f"   saldo: {dados.get('saldo', 0)}")
        print(f"   energia_injetada: {dados.get('energia_injetada', 0)}")
        print(f"\nVALORES (R$):")
        print(f"   valor_energia_injetada: {dados.get('valor_energia_injetada', 0)}")
        print(f"\nUCs GERADORAS:")
        print(f"   uc_geradora_1: {dados.get('uc_geradora_1', '')}")
        print(f"   uc_geradora_2: {dados.get('uc_geradora_2', '')}")
        print(f"   uc_geradora_3: {dados.get('uc_geradora_3', '')}")
        print(f"{'='*60}\n")

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