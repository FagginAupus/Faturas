"""
Invoice classifier for modular PDF processing system.
Identifies invoice types to determine appropriate extraction strategy.
"""

import re
import fitz
from typing import Dict, Any, List, Optional
from pathlib import Path

from .data_models import (
    ClassificacaoFatura, TipoConsumidor, GrupoTarifario,
    ModalidadeTarifaria, TipoFornecimento
)


class FaturaClassifier:
    """
    Classifies invoices to determine the appropriate extractor.
    Based on patterns from existing Leitor_Faturas_PDF.py system.
    """

    def __init__(self):
        self.debug = True

    def classify_pdf(self, pdf_path: str) -> ClassificacaoFatura:
        """
        Main classification method.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            ClassificacaoFatura with identified type and characteristics
        """
        try:
            # Open and extract text
            doc = fitz.open(pdf_path)
            texto_completo = ""

            for page_num in range(doc.page_count):
                page = doc[page_num]
                texto_completo += page.get_text() + "\n"

            doc.close()

            # Perform classification
            return self._classify_from_text(texto_completo)

        except Exception as e:
            if self.debug:
                print(f"[ERRO] Erro na classificação: {e}")

            # Return unsupported classification
            return ClassificacaoFatura(
                tipo_consumidor=TipoConsumidor.UNSUPPORTED,
                grupo=GrupoTarifario.B,  # Default assumption
                modalidade=ModalidadeTarifaria.CONVENCIONAL,
                confianca="baixa",
                detalhes={"erro": str(e)}
            )

    def _classify_from_text(self, texto: str) -> ClassificacaoFatura:
        """
        Classify invoice based on text content.
        Uses patterns from existing system to maintain compatibility.
        """
        # 1. Identify tariff group (A or B)
        grupo = self._identificar_grupo(texto)

        # 2. Identify tariff modality
        modalidade = self._identificar_modalidade(texto, grupo)

        # 3. Identify supply type
        tipo_fornecimento = self._identificar_tipo_fornecimento(texto)

        # 4. Check for SCEE compensation
        tem_compensacao = self._tem_compensacao_scee(texto)

        # 5. Check for multiple generating units
        tem_multiplas_ugs = self._tem_multiplas_ugs(texto)

        # 6. Determine consumer type based on identified characteristics
        tipo_consumidor = self._determinar_tipo_consumidor(
            grupo, modalidade, tem_compensacao, texto
        )

        # 7. Calculate confidence level
        confianca = self._calcular_confianca(grupo, modalidade, tipo_consumidor, texto)

        # 8. Collect additional details
        detalhes = self._coletar_detalhes(texto, grupo, modalidade, tem_compensacao)

        return ClassificacaoFatura(
            tipo_consumidor=tipo_consumidor,
            grupo=grupo,
            modalidade=modalidade,
            tipo_fornecimento=tipo_fornecimento,
            tem_compensacao_scee=tem_compensacao,
            tem_multiplas_ugs=tem_multiplas_ugs,
            confianca=confianca,
            detalhes=detalhes
        )

    def _identificar_grupo(self, texto: str) -> GrupoTarifario:
        """
        Identify tariff group (A or B).
        Based on existing patterns from Leitor_Faturas_PDF.py.
        """
        # Group A indicators
        grupo_a_patterns = [
            r'GRUPO\s*A',
            r'TARIFA\s*(?:AZUL|VERDE)',
            r'DEMANDA\s*(?:CONTRATADA|REGISTRADA)',
            r'TUSD.*TE',  # TUSD and TE components
            r'kW\s*(?:CONTRATADA|REGISTRADA)',
            r'(?:PONTA|FORA\s*PONTA).*(?:TUSD|TE)'
        ]

        # Group B indicators
        grupo_b_patterns = [
            r'GRUPO\s*B',
            r'TARIFA\s*(?:CONVENCIONAL|BRANCA)',
            r'(?:MONOFÁSICO|BIFÁSICO|TRIFÁSICO)',
            r'CONSUMO\s*(?:kWh|KWH)',
            r'ENERGIA\s*ELÉTRICA.*kWh'
        ]

        # Check Group A first (more specific)
        for pattern in grupo_a_patterns:
            if re.search(pattern, texto, re.IGNORECASE):
                if self.debug:
                    print(f"[CLASSIFY] Grupo A identificado: {pattern}")
                return GrupoTarifario.A

        # Check Group B
        for pattern in grupo_b_patterns:
            if re.search(pattern, texto, re.IGNORECASE):
                if self.debug:
                    print(f"[CLASSIFY] Grupo B identificado: {pattern}")
                return GrupoTarifario.B

        # Default to B if uncertain (most common)
        if self.debug:
            print("[CLASSIFY] Grupo não identificado, assumindo B")
        return GrupoTarifario.B

    def _identificar_modalidade(self, texto: str, grupo: GrupoTarifario) -> ModalidadeTarifaria:
        """
        Identify tariff modality based on group and text patterns.
        """
        if grupo == GrupoTarifario.A:
            # Group A modalities
            if re.search(r'AZUL', texto, re.IGNORECASE):
                return ModalidadeTarifaria.AZUL
            elif re.search(r'VERDE', texto, re.IGNORECASE):
                return ModalidadeTarifaria.VERDE
            else:
                return ModalidadeTarifaria.VERDE  # Default for A

        else:  # Group B
            # Check for Tarifa Branca indicators
            branca_patterns = [
                r'BRANCA',
                r'(?:PONTA|FORA\s*PONTA|INTERMEDIÁRIO).*kWh',
                r'HORÁRIO.*(?:PONTA|INTERMEDIÁRIO)',
                r'POSTO\s*TARIFÁRIO'
            ]

            for pattern in branca_patterns:
                if re.search(pattern, texto, re.IGNORECASE):
                    if self.debug:
                        print(f"[CLASSIFY] Tarifa Branca identificada: {pattern}")
                    return ModalidadeTarifaria.BRANCA

            # Default to CONVENCIONAL for Group B
            return ModalidadeTarifaria.CONVENCIONAL

    def _identificar_tipo_fornecimento(self, texto: str) -> Optional[TipoFornecimento]:
        """Identify power supply type."""
        if re.search(r'MONOFÁSICO', texto, re.IGNORECASE):
            return TipoFornecimento.MONOFASICO
        elif re.search(r'BIFÁSICO', texto, re.IGNORECASE):
            return TipoFornecimento.BIFASICO
        elif re.search(r'TRIFÁSICO', texto, re.IGNORECASE):
            return TipoFornecimento.TRIFASICO

        return None

    def _tem_compensacao_scee(self, texto: str) -> bool:
        """
        Check if invoice has SCEE compensation.
        Based on patterns from existing CreditosSaldosExtractor.
        """
        compensacao_patterns = [
            r'SCEE',
            r'SISTEMA.*COMPENSAÇÃO',
            r'ENERGIA.*COMPENSADA',
            r'CONSUMO.*COMPENSADO',
            r'ENERGIA.*INJETADA',
            r'CRÉDITO.*ENERGIA',
            r'SALDO.*ENERGIA',
            r'EXCEDENTE.*ENERGIA',
            r'GERAÇÃO.*DISTRIBUÍDA',
            r'MICRO.*GERAÇÃO',
            r'MINI.*GERAÇÃO'
        ]

        for pattern in compensacao_patterns:
            if re.search(pattern, texto, re.IGNORECASE):
                if self.debug:
                    print(f"[CLASSIFY] Compensação SCEE detectada: {pattern}")
                return True

        return False

    def _tem_multiplas_ugs(self, texto: str) -> bool:
        """Check if there are multiple generating units."""
        # Look for multiple UC patterns
        uc_matches = re.findall(r'UC\s*\d{10,12}', texto, re.IGNORECASE)
        if len(uc_matches) > 1:
            return True

        # Look for multiple injection entries
        injection_matches = re.findall(r'INJEÇÃO.*UC.*\d{10,12}', texto, re.IGNORECASE)
        return len(injection_matches) > 1

    def _determinar_tipo_consumidor(self, grupo: GrupoTarifario, modalidade: ModalidadeTarifaria,
                                   tem_compensacao: bool, texto: str) -> TipoConsumidor:
        """
        Determine specific consumer type based on identified characteristics.
        """
        # For now, focus only on Group B (as per requirements)
        if grupo == GrupoTarifario.B:
            if tem_compensacao:
                return TipoConsumidor.B_CONSUMIDOR_COMPENSADO
            else:
                return TipoConsumidor.B_CONSUMIDOR_SIMPLES

        # Group A is not supported in initial implementation
        else:
            if self.debug:
                print("[CLASSIFY] Grupo A detectado - não suportado na implementação inicial")
            return TipoConsumidor.UNSUPPORTED

    def _calcular_confianca(self, grupo: GrupoTarifario, modalidade: ModalidadeTarifaria,
                           tipo_consumidor: TipoConsumidor, texto: str) -> str:
        """
        Calculate confidence level of the classification.
        """
        confidence_score = 0

        # Group identification confidence
        if grupo == GrupoTarifario.B:
            # Look for strong Group B indicators
            strong_b_patterns = [
                r'GRUPO\s*B',
                r'(?:MONOFÁSICO|BIFÁSICO|TRIFÁSICO)',
                r'CONSUMO.*kWh'
            ]
            for pattern in strong_b_patterns:
                if re.search(pattern, texto, re.IGNORECASE):
                    confidence_score += 25

        # Modality identification confidence
        if modalidade == ModalidadeTarifaria.BRANCA:
            if re.search(r'BRANCA', texto, re.IGNORECASE):
                confidence_score += 30
            elif re.search(r'PONTA.*FORA.*PONTA', texto, re.IGNORECASE):
                confidence_score += 20

        elif modalidade == ModalidadeTarifaria.CONVENCIONAL:
            confidence_score += 15  # Less specific, but common

        # Consumer type confidence
        if tipo_consumidor == TipoConsumidor.B_CONSUMIDOR_COMPENSADO:
            scee_patterns = [r'SCEE', r'COMPENSAÇÃO', r'INJETADA']
            for pattern in scee_patterns:
                if re.search(pattern, texto, re.IGNORECASE):
                    confidence_score += 15

        # Return confidence level
        if confidence_score >= 70:
            return "alta"
        elif confidence_score >= 40:
            return "media"
        else:
            return "baixa"

    def _coletar_detalhes(self, texto: str, grupo: GrupoTarifario,
                         modalidade: ModalidadeTarifaria, tem_compensacao: bool) -> Dict[str, Any]:
        """
        Collect additional details for debugging and validation.
        """
        detalhes = {
            "patterns_found": [],
            "uc_count": len(re.findall(r'\d{10,12}', texto)),
            "has_tusd_te": bool(re.search(r'TUSD.*TE', texto, re.IGNORECASE)),
            "has_demand": bool(re.search(r'DEMANDA', texto, re.IGNORECASE)),
            "compensation_patterns": []
        }

        # Collect found compensation patterns
        if tem_compensacao:
            comp_patterns = ['SCEE', 'COMPENSAÇÃO', 'INJETADA', 'CRÉDITO', 'SALDO']
            for pattern in comp_patterns:
                if re.search(pattern, texto, re.IGNORECASE):
                    detalhes["compensation_patterns"].append(pattern)

        return detalhes

    def classify_multiple_pdfs(self, pdf_paths: List[str]) -> Dict[str, ClassificacaoFatura]:
        """
        Classify multiple PDFs at once.

        Args:
            pdf_paths: List of PDF file paths

        Returns:
            Dictionary mapping file paths to classifications
        """
        results = {}

        for pdf_path in pdf_paths:
            try:
                classification = self.classify_pdf(pdf_path)
                results[pdf_path] = classification

                if self.debug:
                    print(f"[CLASSIFY] {Path(pdf_path).name}: {classification.tipo_consumidor.value}")

            except Exception as e:
                if self.debug:
                    print(f"[ERRO] Erro classificando {pdf_path}: {e}")

                results[pdf_path] = ClassificacaoFatura(
                    tipo_consumidor=TipoConsumidor.UNSUPPORTED,
                    grupo=GrupoTarifario.B,
                    modalidade=ModalidadeTarifaria.CONVENCIONAL,
                    confianca="baixa",
                    detalhes={"erro": str(e)}
                )

        return results

    def get_supported_types(self) -> List[TipoConsumidor]:
        """Return list of supported consumer types."""
        return [
            TipoConsumidor.B_CONSUMIDOR_COMPENSADO,
            TipoConsumidor.B_CONSUMIDOR_SIMPLES
        ]

    def is_supported_type(self, classificacao: ClassificacaoFatura) -> bool:
        """Check if the classified type is supported."""
        return classificacao.is_supported