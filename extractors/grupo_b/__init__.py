"""
Group B invoice extractors.
Focused on residential and small commercial consumers.
"""

from .b_consumidor_compensado import BConsumidorCompensadoExtractor
from .b_consumidor_simples import BConsumidorSimplesExtractor

__all__ = [
    'BConsumidorCompensadoExtractor',
    'BConsumidorSimplesExtractor'
]