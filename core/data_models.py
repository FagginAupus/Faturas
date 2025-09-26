"""
Data models and enums for the modular invoice processing system.
Maintains compatibility with existing field names and types.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional
from decimal import Decimal


class GrupoTarifario(Enum):
    """Tariff groups according to Brazilian electricity regulation."""
    A = "A"  # High voltage consumers (industrial)
    B = "B"  # Low voltage consumers (residential/commercial)


class ModalidadeTarifaria(Enum):
    """Tariff modalities for different consumer types."""
    # Group B
    CONVENCIONAL = "CONVENCIONAL"
    BRANCA = "BRANCA"

    # Group A
    AZUL = "AZUL"
    VERDE = "VERDE"


class TipoConsumidor(Enum):
    """Consumer types for classification."""
    # Group B focus (initial implementation)
    B_CONSUMIDOR_COMPENSADO = "B_CONSUMIDOR_COMPENSADO"    # With SCEE compensation
    B_CONSUMIDOR_SIMPLES = "B_CONSUMIDOR_SIMPLES"          # Without compensation

    # Group A (ignore for now)
    A_CONSUMIDOR = "A_CONSUMIDOR"
    A_GERADOR = "A_GERADOR"

    # Unsupported types
    UNSUPPORTED = "UNSUPPORTED"


class TipoFornecimento(Enum):
    """Power supply types."""
    MONOFASICO = "MONOFÁSICO"
    BIFASICO = "BIFÁSICO"
    TRIFASICO = "TRIFÁSICO"


@dataclass
class ClassificacaoFatura:
    """
    Invoice classification result.
    Used by the classifier to determine processing strategy.
    """
    tipo_consumidor: TipoConsumidor
    grupo: GrupoTarifario
    modalidade: ModalidadeTarifaria
    tipo_fornecimento: Optional[TipoFornecimento] = None
    tem_compensacao_scee: bool = False
    tem_multiplas_ugs: bool = False
    confianca: str = "baixa"  # baixa, media, alta
    detalhes: Dict[str, Any] = None

    def __post_init__(self):
        if self.detalhes is None:
            self.detalhes = {}

    @property
    def is_supported(self) -> bool:
        """Check if this invoice type is supported in current implementation."""
        return self.tipo_consumidor in [
            TipoConsumidor.B_CONSUMIDOR_COMPENSADO,
            TipoConsumidor.B_CONSUMIDOR_SIMPLES
        ]

    @property
    def extractor_class(self) -> str:
        """Get the appropriate extractor class name for this classification."""
        if self.tipo_consumidor == TipoConsumidor.B_CONSUMIDOR_COMPENSADO:
            return "BConsumidorCompensadoExtractor"
        elif self.tipo_consumidor == TipoConsumidor.B_CONSUMIDOR_SIMPLES:
            return "BConsumidorSimplesExtractor"
        else:
            return "UnsupportedExtractor"


# Required fields mapping for compatibility validation
CAMPOS_OBRIGATORIOS = {
    "basicos": [
        "uc", "grupo", "modalidade_tarifaria", "tipo_fornecimento",
        "endereco", "cnpj_cpf", "medidor", "mes_referencia",
        "data_leitura", "vencimento"
    ],
    "consumo": [
        "consumo"  # Always required, comp/n_comp optional
    ],
    "financeiro": [
        "valor_concessionaria"
    ],
    "impostos": [
        "aliquota_icms", "aliquota_pis", "aliquota_cofins"
    ],
    "scee_opcional": [
        "saldo", "excedente_recebido", "credito_recebido"
    ]
}

# Fields used by Calculadora_AUPUS.py (critical for compatibility)
CAMPOS_CALCULADORA_AUPUS = [
    "uc", "grupo", "modalidade_tarifaria", "consumo_comp", "consumo_n_comp",
    "energia_injetada", "desconto_fatura", "desconto_bandeira",
    "aliquota_icms", "aliquota_pis", "aliquota_cofins",
    "valor_concessionaria", "valor_bandeira"
]

# Fields used by Exportar_Planilha.py (critical for compatibility)
CAMPOS_EXPORTAR_PLANILHA = [
    "uc", "nome", "consumo", "saldo", "excedente_recebido",
    "valor_economia", "valor_consorcio", "aliquota_icms",
    "aliquota_pis", "aliquota_cofins"
]

# Default values for optional fields (maintain type consistency)
VALORES_PADRAO = {
    # SCEE fields (Decimal zero, not None)
    "saldo": Decimal('0'),
    "excedente_recebido": Decimal('0'),
    "credito_recebido": Decimal('0'),
    "energia_injetada": Decimal('0'),
    "geracao_ciclo": Decimal('0'),
    "consumo_comp": Decimal('0'),
    "consumo_n_comp": Decimal('0'),

    # Financial fields
    "valor_juros": Decimal('0'),
    "valor_multa": Decimal('0'),
    "valor_iluminacao": Decimal('0'),
    "valor_bandeira": Decimal('0'),

    # Tariff fields
    "rs_consumo": Decimal('0'),
    "rs_consumo_comp": Decimal('0'),
    "rs_consumo_n_comp": Decimal('0'),

    # String fields
    "uc_geradora_1": "",
    "uc_geradora_2": "",

    # Tax aliquotes (maintain as Decimal, not percentage)
    "aliquota_icms": Decimal('0'),
    "aliquota_pis": Decimal('0'),
    "aliquota_cofins": Decimal('0')
}