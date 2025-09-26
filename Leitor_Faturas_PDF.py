import fitz  # PyMuPDF
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json
import os
from enum import Enum
from decimal import Decimal, InvalidOperation

# ================== FUNÇÃO GLOBAL PARA CONVERSÃO SEGURA ==================

def safe_decimal_conversion(value: str, campo: str = "") -> Decimal:
    """
    Conversão segura para Decimal com tratamento robusto de erros
    """
    try:
        if not value:
            return Decimal('0')

        # Converter para string se não for
        cleaned = str(value).strip()

        # Se está vazio após limpeza
        if not cleaned:
            return Decimal('0')

        # Tratar percentuais - extrair apenas o número
        if '%' in cleaned:
            cleaned = re.sub(r'[^\d.,-]', '', cleaned)
            if cleaned:
                # Converter para decimal (19% -> 0.19)
                decimal_val = Decimal(cleaned.replace(',', '.')) / Decimal('100')
                return decimal_val
            return Decimal('0')

        # Remove caracteres que não são dígitos, vírgula, ponto ou sinal negativo
        cleaned = re.sub(r'[^\d.,-]', '', cleaned)

        # Se ficou vazio após limpeza
        if not cleaned:
            return Decimal('0')

        # Tratar casos especiais
        if cleaned in ['-', '.', ',', '-.', '-,']:
            return Decimal('0')

        # Se tem vírgula e ponto, vírgula é decimal
        if ',' in cleaned and '.' in cleaned:
            cleaned = cleaned.replace('.', '').replace(',', '.')
        # Se só tem vírgula, é decimal
        elif ',' in cleaned:
            cleaned = cleaned.replace(',', '.')

        # Remove pontos/vírgulas extras no final
        cleaned = cleaned.rstrip('.,')

        # Se ainda está vazio
        if not cleaned:
            return Decimal('0')

        # Validar se é um número válido antes de converter
        if not re.match(r'^-?\d*\.?\d*$', cleaned):
            return Decimal('0')

        return Decimal(cleaned)

    except (ValueError, TypeError, InvalidOperation) as e:
        print(f"AVISO: Erro convertendo '{value}' para Decimal no campo '{campo}': {e}")
        return Decimal('0')
    
# ================== ENUMS ==================

class GrupoTarifario(Enum):
    A = "A"
    B = "B"

class ModalidadeTarifaria(Enum):
    CONVENCIONAL = "CONVENCIONAL"
    BRANCA = "BRANCA"
    AZUL = "AZUL"
    VERDE = "VERDE"

class TipoFornecimento(Enum):
    MONOFASICO = "MONOFÁSICO"
    BIFASICO = "BIFÁSICO"
    TRIFASICO = "TRIFÁSICO"

# ================== ESTRUTURAS DE DADOS ==================
@dataclass
class DadosBasicosFatura:
    """Dados básicos presentes em todas as faturas"""
    uc: Optional[str] = None
    mes_referencia: Optional[str] = None
    vencimento: Optional[str] = None
    valor_concessionaria: Optional[Decimal] = None
    grupo: Optional[str] = None
    subgrupo: Optional[str] = None
    classificacao: Optional[str] = None
    modalidade_tarifaria: Optional[str] = None
    tipo_fornecimento: Optional[str] = None
    tipo_consumidor: Optional[str] = None
    endereco: Optional[str] = None
    cnpj_cpf: Optional[str] = None
    medidor: Optional[str] = None
    data_leitura: Optional[str] = None
    resolucao_homologatoria: Optional[str] = None
    ug: Optional[str] = None
    modalidade_tarifaria_validacao: Optional[Dict[str, Any]] = None
    
    #  NOVAS LINHAS PARA IRRIGAÇÃO
    irrigante: Optional[str] = None  # "Sim" ou "Não"
    desconto_irrigacao: Optional[str] = None  # Ex: "80%"

@dataclass
class DadosImpostos:
    """Dados de impostos - EXPANDIDO"""
    # Bases de cálculo (NOVO)
    base_icms: Optional[Decimal] = None
    base_pis: Optional[Decimal] = None
    base_cofins: Optional[Decimal] = None
    
    # Alíquotas
    aliquota_icms: Optional[Decimal] = None
    aliquota_pis: Optional[Decimal] = None
    aliquota_cofins: Optional[Decimal] = None
    
    # Valores
    valor_icms: Optional[Decimal] = None
    valor_pis: Optional[Decimal] = None
    valor_cofins: Optional[Decimal] = None

@dataclass
class DadosConsumoB:
    """Dados específicos de consumo para Grupo B - EXPANDIDO"""
    # Consumo geral (convencional)
    consumo: Optional[Decimal] = None
    rs_consumo: Optional[Decimal] = None
    valor_consumo: Optional[Decimal] = None
    
    # Consumo por posto horário (tarifa branca)
    consumo_p: Optional[Decimal] = None
    consumo_fp: Optional[Decimal] = None
    consumo_hi: Optional[Decimal] = None
    rs_consumo_p: Optional[Decimal] = None
    rs_consumo_fp: Optional[Decimal] = None
    rs_consumo_hi: Optional[Decimal] = None
    valor_consumo_p: Optional[Decimal] = None
    valor_consumo_fp: Optional[Decimal] = None
    valor_consumo_hi: Optional[Decimal] = None
    
    # Consumo compensado (SCEE)
    consumo_comp: Optional[Decimal] = None
    rs_consumo_comp: Optional[Decimal] = None
    valor_consumo_comp: Optional[Decimal] = None
    consumo_comp_p: Optional[Decimal] = None
    consumo_comp_fp: Optional[Decimal] = None
    consumo_comp_hi: Optional[Decimal] = None
    rs_consumo_comp_p: Optional[Decimal] = None
    rs_consumo_comp_fp: Optional[Decimal] = None
    rs_consumo_comp_hi: Optional[Decimal] = None
    valor_consumo_comp_p: Optional[Decimal] = None
    valor_consumo_comp_fp: Optional[Decimal] = None
    valor_consumo_comp_hi: Optional[Decimal] = None
    
    # Consumo não compensado
    consumo_n_comp: Optional[Decimal] = None
    rs_consumo_n_comp: Optional[Decimal] = None
    valor_consumo_n_comp: Optional[Decimal] = None
    consumo_n_comp_p: Optional[Decimal] = None
    consumo_n_comp_fp: Optional[Decimal] = None
    consumo_n_comp_hi: Optional[Decimal] = None
    rs_consumo_n_comp_p: Optional[Decimal] = None
    rs_consumo_n_comp_fp: Optional[Decimal] = None
    rs_consumo_n_comp_hi: Optional[Decimal] = None
    valor_consumo_n_comp_p: Optional[Decimal] = None
    valor_consumo_n_comp_fp: Optional[Decimal] = None
    valor_consumo_n_comp_hi: Optional[Decimal] = None
    
    # Bandeiras tarifárias
    adc_bandeira_amarela: Optional[Decimal] = None
    rs_adc_bandeira_amarela: Optional[Decimal] = None
    valor_adc_bandeira_amarela: Optional[Decimal] = None
    adc_bandeira_vermelha: Optional[Decimal] = None
    rs_adc_bandeira_vermelha: Optional[Decimal] = None
    valor_adc_bandeira_vermelha: Optional[Decimal] = None
    
    # Bandeiras por posto horário
    adc_bandeira_amarela_p: Optional[Decimal] = None
    adc_bandeira_amarela_fp: Optional[Decimal] = None
    adc_bandeira_amarela_hi: Optional[Decimal] = None
    rs_adc_bandeira_amarela_p: Optional[Decimal] = None
    rs_adc_bandeira_amarela_fp: Optional[Decimal] = None
    rs_adc_bandeira_amarela_hi: Optional[Decimal] = None
    valor_adc_bandeira_amarela_p: Optional[Decimal] = None
    valor_adc_bandeira_amarela_fp: Optional[Decimal] = None
    valor_adc_bandeira_amarela_hi: Optional[Decimal] = None
    
    adc_bandeira_vermelha_p: Optional[Decimal] = None
    adc_bandeira_vermelha_fp: Optional[Decimal] = None
    adc_bandeira_vermelha_hi: Optional[Decimal] = None
    rs_adc_bandeira_vermelha_p: Optional[Decimal] = None
    rs_adc_bandeira_vermelha_fp: Optional[Decimal] = None
    rs_adc_bandeira_vermelha_hi: Optional[Decimal] = None
    valor_adc_bandeira_vermelha_p: Optional[Decimal] = None
    valor_adc_bandeira_vermelha_fp: Optional[Decimal] = None
    valor_adc_bandeira_vermelha_hi: Optional[Decimal] = None

@dataclass
class DadosConsumoA:
    """Dados específicos de consumo para Grupo A - EXPANDIDO"""
    # Consumo por tipo (p=ponta, fp=fora ponta, hr=hora reservada)
    consumo_p: Optional[Decimal] = None
    consumo_fp: Optional[Decimal] = None
    consumo_hr: Optional[Decimal] = None
    
    # Valores tarifários básicos
    rs_consumo_p: Optional[Decimal] = None
    rs_consumo_fp: Optional[Decimal] = None
    rs_consumo_hr: Optional[Decimal] = None
    valor_consumo_p: Optional[Decimal] = None
    valor_consumo_fp: Optional[Decimal] = None
    valor_consumo_hr: Optional[Decimal] = None
    
    # TUSD por posto
    consumo_p_tusd: Optional[Decimal] = None
    consumo_fp_tusd: Optional[Decimal] = None
    consumo_hr_tusd: Optional[Decimal] = None
    rs_consumo_p_tusd: Optional[Decimal] = None
    rs_consumo_fp_tusd: Optional[Decimal] = None
    rs_consumo_hr_tusd: Optional[Decimal] = None
    valor_consumo_p_tusd: Optional[Decimal] = None
    valor_consumo_fp_tusd: Optional[Decimal] = None
    valor_consumo_hr_tusd: Optional[Decimal] = None
    
    # TE por posto  
    consumo_p_te: Optional[Decimal] = None
    consumo_fp_te: Optional[Decimal] = None
    consumo_hr_te: Optional[Decimal] = None
    rs_consumo_p_te: Optional[Decimal] = None
    rs_consumo_fp_te: Optional[Decimal] = None
    rs_consumo_hr_te: Optional[Decimal] = None
    valor_consumo_p_te: Optional[Decimal] = None
    valor_consumo_fp_te: Optional[Decimal] = None
    valor_consumo_hr_te: Optional[Decimal] = None
    
    # Consumo compensado (SCEE)
    consumo_comp_p_tusd: Optional[Decimal] = None
    consumo_comp_fp_tusd: Optional[Decimal] = None
    consumo_comp_hr_tusd: Optional[Decimal] = None
    rs_consumo_comp_p_tusd: Optional[Decimal] = None
    rs_consumo_comp_fp_tusd: Optional[Decimal] = None
    rs_consumo_comp_hr_tusd: Optional[Decimal] = None
    valor_consumo_comp_p_tusd: Optional[Decimal] = None
    valor_consumo_comp_fp_tusd: Optional[Decimal] = None
    valor_consumo_comp_hr_tusd: Optional[Decimal] = None
    
    consumo_comp_p_te: Optional[Decimal] = None
    consumo_comp_fp_te: Optional[Decimal] = None
    consumo_comp_hr_te: Optional[Decimal] = None
    rs_consumo_comp_p_te: Optional[Decimal] = None
    rs_consumo_comp_fp_te: Optional[Decimal] = None
    rs_consumo_comp_hr_te: Optional[Decimal] = None
    valor_consumo_comp_p_te: Optional[Decimal] = None
    valor_consumo_comp_fp_te: Optional[Decimal] = None
    valor_consumo_comp_hr_te: Optional[Decimal] = None
    
    # Consumo não compensado
    consumo_n_comp_p_tusd: Optional[Decimal] = None
    consumo_n_comp_fp_tusd: Optional[Decimal] = None
    consumo_n_comp_hr_tusd: Optional[Decimal] = None
    rs_consumo_n_comp_p_tusd: Optional[Decimal] = None
    rs_consumo_n_comp_fp_tusd: Optional[Decimal] = None
    rs_consumo_n_comp_hr_tusd: Optional[Decimal] = None
    valor_consumo_n_comp_p_tusd: Optional[Decimal] = None
    valor_consumo_n_comp_fp_tusd: Optional[Decimal] = None
    valor_consumo_n_comp_hr_tusd: Optional[Decimal] = None
    
    consumo_n_comp_p_te: Optional[Decimal] = None
    consumo_n_comp_fp_te: Optional[Decimal] = None
    consumo_n_comp_hr_te: Optional[Decimal] = None
    rs_consumo_n_comp_p_te: Optional[Decimal] = None
    rs_consumo_n_comp_fp_te: Optional[Decimal] = None
    rs_consumo_n_comp_hr_te: Optional[Decimal] = None
    valor_consumo_n_comp_p_te: Optional[Decimal] = None
    valor_consumo_n_comp_fp_te: Optional[Decimal] = None
    valor_consumo_n_comp_hr_te: Optional[Decimal] = None
    
    # Demanda básica
    demanda_contratada: Optional[Decimal] = None
    demanda_faturada: Optional[Decimal] = None
    rs_demanda_faturada: Optional[Decimal] = None
    valor_demanda: Optional[Decimal] = None
    
    # NOVO: Tipos adicionais de demanda
    rs_demanda_isento_faturada: Optional[Decimal] = None
    demanda_isento_faturada: Optional[Decimal] = None
    valor_demanda_isento: Optional[Decimal] = None
    
    rs_demanda_geracao: Optional[Decimal] = None
    demanda_geracao: Optional[Decimal] = None
    valor_demanda_geracao: Optional[Decimal] = None
    
    rs_demanda_ultrapassagem: Optional[Decimal] = None
    demanda_ultrapassagem: Optional[Decimal] = None
    valor_demanda_ultrapassagem: Optional[Decimal] = None
    
    rs_demanda_ultrapassagem_geracao: Optional[Decimal] = None
    demanda_ultrapassagem_geracao: Optional[Decimal] = None
    valor_demanda_ultra_geracao: Optional[Decimal] = None
    
    # NOVO: UFER por posto
    rs_ufer_p: Optional[Decimal] = None
    ufer_p: Optional[Decimal] = None
    valor_ufer_p: Optional[Decimal] = None
    
    rs_ufer_fp: Optional[Decimal] = None
    ufer_fp: Optional[Decimal] = None
    valor_ufer_fp: Optional[Decimal] = None
    
    rs_ufer_hr: Optional[Decimal] = None
    ufer_hr: Optional[Decimal] = None
    valor_ufer_hr: Optional[Decimal] = None
    
    # UFER geral (sem posto)
    rs_ufer: Optional[Decimal] = None
    ufer: Optional[Decimal] = None
    valor_ufer: Optional[Decimal] = None
    
    # NOVO: DMCR
    rs_dmcr: Optional[Decimal] = None
    dmcr: Optional[Decimal] = None
    valor_dmcr: Optional[Decimal] = None
    
    # NOVO: Bandeiras tarifárias por posto (Grupo A)
    rs_adc_bandeira_amarela_p: Optional[Decimal] = None
    adc_bandeira_amarela_p: Optional[Decimal] = None
    valor_adc_bandeira_amarela_p: Optional[Decimal] = None
    
    rs_adc_bandeira_amarela_fp: Optional[Decimal] = None
    adc_bandeira_amarela_fp: Optional[Decimal] = None
    valor_adc_bandeira_amarela_fp: Optional[Decimal] = None
    
    rs_adc_bandeira_amarela_hr: Optional[Decimal] = None
    adc_bandeira_amarela_hr: Optional[Decimal] = None
    valor_adc_bandeira_amarela_hr: Optional[Decimal] = None
    
    rs_adc_bandeira_vermelha_p: Optional[Decimal] = None
    adc_bandeira_vermelha_p: Optional[Decimal] = None
    valor_adc_bandeira_vermelha_p: Optional[Decimal] = None
    
    rs_adc_bandeira_vermelha_fp: Optional[Decimal] = None
    adc_bandeira_vermelha_fp: Optional[Decimal] = None
    valor_adc_bandeira_vermelha_fp: Optional[Decimal] = None
    
    rs_adc_bandeira_vermelha_hr: Optional[Decimal] = None
    adc_bandeira_vermelha_hr: Optional[Decimal] = None
    valor_adc_bandeira_vermelha_hr: Optional[Decimal] = None

@dataclass
class DadosGeracao:
    """Dados de geração de energia - NOVA ESTRUTURA"""
    # ========= TOTAIS GERAIS (mantém compatibilidade) =========
    geracao_ciclo: Optional[Decimal] = None  # TOTAL de todas as UGs
    geracao_ciclo_p: Optional[Decimal] = None  # TOTAL ponta
    geracao_ciclo_fp: Optional[Decimal] = None  # TOTAL fora ponta
    geracao_ciclo_hr: Optional[Decimal] = None  # TOTAL hora reservada
    
    # ========= NOVA ESTRUTURA: Lista de UGs =========
    ugs_geradoras: List[Dict[str, Any]] = field(default_factory=list)
    
    # ========= COMPATIBILIDADE: Campos individuais (temporário) =========
    uc_geradora: Optional[str] = None  # UG principal (SCEE)
    uc_geradora_1: Optional[str] = None
    uc_geradora_2: Optional[str] = None
    geracao_ciclo_1: Optional[Decimal] = None
    geracao_ciclo_2: Optional[Decimal] = None
    geracao_ciclo_p_1: Optional[Decimal] = None
    geracao_ciclo_fp_1: Optional[Decimal] = None
    geracao_ciclo_hr_1: Optional[Decimal] = None
    geracao_ciclo_p_2: Optional[Decimal] = None
    geracao_ciclo_fp_2: Optional[Decimal] = None
    geracao_ciclo_hr_2: Optional[Decimal] = None
    
    # Informações das UGs (legado)
    ugs_geradoras_db: Optional[str] = None  # String para banco (separada por vírgula)

@dataclass
class DadosCreditos:
    """Dados de créditos e saldos - NOVA ESTRUTURA"""
    # ========= TOTAIS GERAIS =========
    excedente_recebido: Optional[Decimal] = None  # TOTAL
    excedente_recebido_p: Optional[Decimal] = None  # TOTAL ponta
    excedente_recebido_fp: Optional[Decimal] = None  # TOTAL fora ponta
    excedente_recebido_hr: Optional[Decimal] = None  # TOTAL hora reservada
    
    # ========= NOVA ESTRUTURA: Lista de UGs =========
    ugs_excedentes: List[Dict[str, Any]] = field(default_factory=list)
    
    # ========= COMPATIBILIDADE: Campos individuais (temporário) =========
    excedente_recebido_1: Optional[Decimal] = None
    excedente_recebido_2: Optional[Decimal] = None
    excedente_recebido_p_1: Optional[Decimal] = None
    excedente_recebido_fp_1: Optional[Decimal] = None
    excedente_recebido_hr_1: Optional[Decimal] = None
    excedente_recebido_p_2: Optional[Decimal] = None
    excedente_recebido_fp_2: Optional[Decimal] = None
    excedente_recebido_hr_2: Optional[Decimal] = None
    
    # Saldos básicos (sem mudança)
    saldo: Optional[Decimal] = None
    saldo_30: Optional[Decimal] = None
    saldo_60: Optional[Decimal] = None
    
    # Saldos por posto horário
    saldo_p: Optional[Decimal] = None
    saldo_fp: Optional[Decimal] = None
    saldo_hr: Optional[Decimal] = None
    saldo_hi: Optional[Decimal] = None
    
    # Saldos a expirar por posto (Grupo A)
    saldo_30_p: Optional[Decimal] = None
    saldo_30_fp: Optional[Decimal] = None
    saldo_30_hr: Optional[Decimal] = None
    saldo_60_p: Optional[Decimal] = None
    saldo_60_fp: Optional[Decimal] = None
    saldo_60_hr: Optional[Decimal] = None
    
    # Créditos
    credito_recebido: Optional[Decimal] = None
    valor_credito_consumo: Optional[Decimal] = None
    credito_recebido_p: Optional[Decimal] = None
    credito_recebido_fp: Optional[Decimal] = None
    credito_recebido_hr: Optional[Decimal] = None
    credito_recebido_total: Optional[Decimal] = None
    
    # Rateio
    rateio_fatura: Optional[str] = None

@dataclass
class DadosEnergiaInjetada:
    """Dados de energia injetada - NOVA ESTRUTURA"""
    # ========= TOTAIS GERAIS =========
    energia_injetada: Optional[Decimal] = None  # TOTAL
    valor_energia_injetada: Optional[Decimal] = None  # VALOR TOTAL
    
    # Totais por posto (Grupo A)
    energia_injetada_p: Optional[Decimal] = None
    energia_injetada_fp: Optional[Decimal] = None
    energia_injetada_hr: Optional[Decimal] = None
    valor_energia_injetada_p: Optional[Decimal] = None
    valor_energia_injetada_fp: Optional[Decimal] = None
    valor_energia_injetada_hr: Optional[Decimal] = None
    
    # Totais por posto (Grupo B Branca)
    energia_injetada_hi: Optional[Decimal] = None
    valor_energia_injetada_hi: Optional[Decimal] = None
    
    # Totais por componente (Grupo A)
    energia_injetada_tusd_p: Optional[Decimal] = None
    energia_injetada_tusd_fp: Optional[Decimal] = None
    energia_injetada_tusd_hr: Optional[Decimal] = None
    energia_injetada_te_p: Optional[Decimal] = None
    energia_injetada_te_fp: Optional[Decimal] = None
    energia_injetada_te_hr: Optional[Decimal] = None
    valor_energia_injetada_tusd_p: Optional[Decimal] = None
    valor_energia_injetada_tusd_fp: Optional[Decimal] = None
    valor_energia_injetada_tusd_hr: Optional[Decimal] = None
    valor_energia_injetada_te_p: Optional[Decimal] = None
    valor_energia_injetada_te_fp: Optional[Decimal] = None
    valor_energia_injetada_te_hr: Optional[Decimal] = None
    
    # ========= NOVA ESTRUTURA: Lista de UGs =========
    ugs_injecao: List[Dict[str, Any]] = field(default_factory=list)
    
    # ========= COMPATIBILIDADE: Campos individuais (temporário) =========
    energia_injetada_1: Optional[Decimal] = None
    energia_injetada_2: Optional[Decimal] = None
    valor_energia_injetada_1: Optional[Decimal] = None
    valor_energia_injetada_2: Optional[Decimal] = None

@dataclass
class DadosFinanceiros:
    """Dados financeiros adicionais - EXPANDIDO"""
    # Encargos
    valor_iluminacao: Optional[Decimal] = None
    valor_juros: Optional[Decimal] = None
    valor_multa: Optional[Decimal] = None
    
    # Benefícios
    valor_beneficio_bruto: Optional[Decimal] = None
    valor_beneficio_liquido: Optional[Decimal] = None
    
    # Créditos diversos
    valor_dic: Optional[Decimal] = None  # Compensação DIC
    valor_bonus_itaipu: Optional[Decimal] = None
    
    # NOVO: Outros valores financeiros
    valor_concessionaria_duplicada: Optional[Decimal] = None  # Duplicidade de pagamento
    valor_dif_demanda: Optional[Decimal] = None  # Diferença de demanda
    rs_dif_demanda: Optional[Decimal] = None
    dif_demanda: Optional[Decimal] = None
    
    valor_parc_injet: Optional[Decimal] = None  # Parcela injeção s/desc
    valor_correcao_ipca: Optional[Decimal] = None  # Correção IPCA
    
    # NOVO: Dados da tabela de leitura
    # Leituras de energia ativa
    leitura_atual_energia_ativa: Optional[Decimal] = None
    leitura_anterior_energia_ativa: Optional[Decimal] = None
    const_medidor_energia_ativa: Optional[Decimal] = None
    
    # Leituras de energia geração
    leitura_atual_energia_geracao: Optional[Decimal] = None
    leitura_anterior_energia_geracao: Optional[Decimal] = None
    const_medidor_energia_geracao: Optional[Decimal] = None
    
    # Leituras por posto (Grupo A)
    leitura_atual_energia_ativa_p: Optional[Decimal] = None
    leitura_anterior_energia_ativa_p: Optional[Decimal] = None
    const_medidor_energia_ativa_p: Optional[Decimal] = None
    
    leitura_atual_energia_ativa_fp: Optional[Decimal] = None
    leitura_anterior_energia_ativa_fp: Optional[Decimal] = None
    const_medidor_energia_ativa_fp: Optional[Decimal] = None
    
    leitura_atual_energia_ativa_hr: Optional[Decimal] = None
    leitura_anterior_energia_ativa_hr: Optional[Decimal] = None
    const_medidor_energia_ativa_hr: Optional[Decimal] = None
    
    # Leituras de geração por posto (Grupo A)
    leitura_atual_energia_geracao_p: Optional[Decimal] = None
    leitura_anterior_energia_geracao_p: Optional[Decimal] = None
    const_medidor_energia_geracao_p: Optional[Decimal] = None
    
    leitura_atual_energia_geracao_fp: Optional[Decimal] = None
    leitura_anterior_energia_geracao_fp: Optional[Decimal] = None
    const_medidor_energia_geracao_fp: Optional[Decimal] = None
    
    leitura_atual_energia_geracao_hr: Optional[Decimal] = None
    leitura_anterior_energia_geracao_hr: Optional[Decimal] = None
    const_medidor_energia_geracao_hr: Optional[Decimal] = None
    
    # Leituras de demanda por posto (Grupo A)
    leitura_atual_demanda_p: Optional[Decimal] = None
    leitura_anterior_demanda_p: Optional[Decimal] = None
    const_medidor_demanda_p: Optional[Decimal] = None
    
    leitura_atual_demanda_fp: Optional[Decimal] = None
    leitura_anterior_demanda_fp: Optional[Decimal] = None
    const_medidor_demanda_fp: Optional[Decimal] = None
    
    leitura_atual_demanda_hr: Optional[Decimal] = None
    leitura_anterior_demanda_hr: Optional[Decimal] = None
    const_medidor_demanda_hr: Optional[Decimal] = None
    
    # Leituras de demanda geração por posto (Grupo A)
    leitura_atual_demanda_geracao_p: Optional[Decimal] = None
    leitura_anterior_demanda_geracao_p: Optional[Decimal] = None
    const_medidor_demanda_geracao_p: Optional[Decimal] = None
    
    leitura_atual_demanda_geracao_fp: Optional[Decimal] = None
    leitura_anterior_demanda_geracao_fp: Optional[Decimal] = None
    const_medidor_demanda_geracao_fp: Optional[Decimal] = None
    
    leitura_atual_demanda_geracao_hr: Optional[Decimal] = None
    leitura_anterior_demanda_geracao_hr: Optional[Decimal] = None
    const_medidor_demanda_geracao_hr: Optional[Decimal] = None
    
    # Leituras de UFER por posto (Grupo A)
    leitura_atual_ufer_p: Optional[Decimal] = None
    leitura_anterior_ufer_p: Optional[Decimal] = None
    const_medidor_ufer_p: Optional[Decimal] = None
    
    leitura_atual_ufer_fp: Optional[Decimal] = None
    leitura_anterior_ufer_fp: Optional[Decimal] = None
    const_medidor_ufer_fp: Optional[Decimal] = None
    
    leitura_atual_ufer_hr: Optional[Decimal] = None
    leitura_anterior_ufer_hr: Optional[Decimal] = None
    const_medidor_ufer_hr: Optional[Decimal] = None
    
    # Leituras de DMCR por posto (Grupo A)
    leitura_atual_dmcr_p: Optional[Decimal] = None
    leitura_anterior_dmcr_p: Optional[Decimal] = None
    const_medidor_dmcr_p: Optional[Decimal] = None
    
    leitura_atual_dmcr_fp: Optional[Decimal] = None
    leitura_anterior_dmcr_fp: Optional[Decimal] = None
    const_medidor_dmcr_fp: Optional[Decimal] = None
    
    leitura_atual_dmcr_hr: Optional[Decimal] = None
    leitura_anterior_dmcr_hr: Optional[Decimal] = None
    const_medidor_dmcr_hr: Optional[Decimal] = None

@dataclass
class FaturaCompleta:
    """Estrutura completa da fatura - NOVA ESTRUTURA"""
    dados_basicos: DadosBasicosFatura = field(default_factory=DadosBasicosFatura)
    impostos: DadosImpostos = field(default_factory=DadosImpostos)
    consumo_b: DadosConsumoB = field(default_factory=DadosConsumoB)
    consumo_a: DadosConsumoA = field(default_factory=DadosConsumoA)
    geracao: DadosGeracao = field(default_factory=DadosGeracao)
    creditos: DadosCreditos = field(default_factory=DadosCreditos)
    energia_injetada: DadosEnergiaInjetada = field(default_factory=DadosEnergiaInjetada)
    financeiros: DadosFinanceiros = field(default_factory=DadosFinanceiros)
    
    # Dados brutos originais
    dados_brutos: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte toda a estrutura para dicionário"""
        from dataclasses import asdict
        return asdict(self)

    
        
# ================== EXTRACTORS (ESTRATÉGIAS) ==================

class BaseExtractor(ABC):
    """Classe base para todos os extractors"""
    
    def __init__(self):
        self.patterns = {}
        
    @abstractmethod
    def extract(self, text: str, block_info: Dict) -> Dict[str, Any]:
        """Extrai informações do texto"""
        pass
    

        
    def clean_monetary_value(self, value: str) -> Decimal:
        """Limpa e converte valores monetários para Decimal - VERSÃO SEGURA"""
        try:
            if not value or not isinstance(value, str):
                return Decimal('0')
            
            # Remove R$, espaços
            cleaned = value.replace('R$', '').strip()
            
            if not cleaned:
                return Decimal('0')
            
            # CORREÇÃO: chamar função global
            return safe_decimal_conversion(cleaned, "monetary")
            
        except Exception as e:
            print(f"AVISO: Erro em clean_monetary_value com '{value}': {e}")
            return Decimal('0')
    
    def clean_numeric_value(self, value: str) -> Decimal:
        """Limpa e converte valores numéricos para Decimal - VERSÃO CORRIGIDA"""
        try:
            if not value or not isinstance(value, str):
                return Decimal('0')
            
            # Remove espaços e caracteres especiais
            cleaned = value.strip()
            
            # Se tem mais de um ponto, assume que pontos são separadores de milhar
            if cleaned.count('.') > 1:
                # Remove todos os pontos exceto o último (se for decimal)
                parts = cleaned.split('.')
                if len(parts[-1]) <= 2:  # Último segmento tem 2 dígitos ou menos = decimal
                    cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
                else:  # Todos são separadores de milhar
                    cleaned = ''.join(parts)
            
            # Se tem ponto e vírgula, ponto é milhar e vírgula é decimal
            if '.' in cleaned and ',' in cleaned:
                cleaned = cleaned.replace('.', '').replace(',', '.')
            # Se só tem vírgula, é decimal
            elif ',' in cleaned:
                cleaned = cleaned.replace(',', '.')
            
            # Remove pontos/vírgulas extras no final
            cleaned = cleaned.rstrip('.,')
            
            # Se ainda tem pontos no meio, remove (separadores de milhar)
            if '.' in cleaned and len(cleaned.split('.')[-1]) > 2:
                cleaned = cleaned.replace('.', '')
            
            return Decimal(cleaned) if cleaned else Decimal('0')
            
        except (ValueError, AttributeError, TypeError):
            return Decimal('0')

class DadosBasicosExtractor(BaseExtractor):
    """Extrator para dados básicos da fatura"""
    
    def extract(self, text: str, block_info: Dict) -> Dict[str, Any]:
        result = {}
        x0, y0 = block_info.get('x0', 0), block_info.get('y0', 0)
        
        # UC (Unidade Consumidora) - SEM MUDANÇA
        if 380 <= x0 <= 450 and 190 <= y0 <= 220:
            uc_match = re.search(r"\d+", text)
            if uc_match:
                result['uc'] = uc_match.group(0)
        
        # Classificação completa (Grupo, Subgrupo, Tipo)
        if "Classificação:" in text:
            # Exemplo: "Classificação: B B1 RESIDENCIAL - RESIDENCIAL NORMAL CONVENCIONAL"
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
        
        # Tipo de fornecimento
        if "tipo de fornecimento:" in text.lower():
            tipo_part = text.lower().split("tipo de fornecimento:")[-1].strip().split("\n")[0]
            result['tipo_fornecimento'] = tipo_part.upper()
        
        # Vencimento e valor
        if (185.00 <= x0 <= 430.00) and (240.00 <= y0 <= 280.00):
            # Data de vencimento - SEM MUDANÇA
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
                result['valor_concessionaria'] = self.clean_monetary_value(valor_match.group(1))
        
        # Resolução Homologatória (geralmente no rodapé)
        if (25 <= x0 <= 200) and (700 <= y0 <= 900):
            res_match = re.search(r"(\d{4})/(\d{2})", text)
            if res_match:
                result['resolucao_homologatoria'] = res_match.group(0)
        
        return result

class MesReferenciaExtractor(BaseExtractor):
    """Extrator específico para mês de referência"""
    
    def __init__(self):
        super().__init__()
        self.meses_dict = {
            'JAN': '01', 'FEV': '02', 'MAR': '03', 'ABR': '04',
            'MAI': '05', 'JUN': '06', 'JUL': '07', 'AGO': '08',
            'SET': '09', 'OUT': '10', 'NOV': '11', 'DEZ': '12'
        }
    
    def extract(self, text: str, block_info: Dict = None) -> Dict[str, Any]:
        patterns = [
            r'([A-Z]{3})/(\d{4})',
            r'(\d{2})/(\d{4})',
            r'([A-Z]+)/(\d{4})'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                for match in matches:
                    mes, ano = match
                    
                    if mes in self.meses_dict:
                        mes_numero = self.meses_dict[mes]
                        return {'mes_referencia': f"{mes_numero}/{ano}"}
                    elif mes.isdigit() and 1 <= int(mes) <= 12:
                        return {'mes_referencia': f"{mes.zfill(2)}/{ano}"}
        
        return {}

class ModalidadeTarifariaExtractor(BaseExtractor):
    """Extrator para identificar modalidade tarifária baseado no conteúdo da fatura"""
    
    def __init__(self):
        super().__init__()
        self.modalidade_detectada = None
        self.confianca = 0  # 0 = baixa, 1 = média, 2 = alta
    
    def extract(self, text: str, block_info: Dict) -> Dict[str, Any]:
        result = {}
        
        # PRIORIDADE 1: Tabela de leitura/medição (mais confiável)
        if "ENERGIA ATIVA" in text and "KWH" in text:
            # Se encontrar medição com ÚNICO, é definitivamente CONVENCIONAL
            if "ÚNICO" in text and not any(posto in text for posto in ["PONTA", "FORA PONTA", "INTERMEDIÁRIO"]):
                self.modalidade_detectada = "CONVENCIONAL"
                self.confianca = 2
                result['modalidade_tarifaria'] = "CONVENCIONAL"
                return result
            
            # Se encontrar medição com postos horários, é definitivamente BRANCA
            if any(posto in text for posto in ["PONTA", "FORA PONTA", "INTERMEDIÁRIO"]):
                self.modalidade_detectada = "BRANCA"
                self.confianca = 2
                result['modalidade_tarifaria'] = "BRANCA"
                return result
        
        # PRIORIDADE 2: Tabela de fornecimento/consumo
        if "CONSUMO" in text or "ADC BANDEIRA" in text:
            linha = text.upper()
            
            # Verifica consumo com especificação de posto horário
            # Padrões: "CONSUMO P", "CONSUMO FP", "CONSUMO HI", "ADC BANDEIRA AMARELA P"
            if re.search(r'(CONSUMO|ADC BANDEIRA \w+)\s+(P|FP|HI|INT)\s+kWh', linha):
                if self.confianca < 2:  # Só atualiza se não tiver certeza ainda
                    self.modalidade_detectada = "BRANCA"
                    self.confianca = 2
                    result['modalidade_tarifaria'] = "BRANCA"
                return result
            
            # Se tem consumo mas sem posto horário específico
            elif "KWH" in linha and not re.search(r'\s+(P|FP|HI|INT|PONTA|FORA)\s+', linha):
                if self.confianca == 0:  # Só considera se não tiver nenhuma evidência
                    self.modalidade_detectada = "CONVENCIONAL"
                    self.confianca = 1
                    result['modalidade_tarifaria'] = "CONVENCIONAL"
        
        # PRIORIDADE 3: Classificação textual (menos confiável para Grupo B)
        # Nota: A classificação pode dizer "CONVENCIONAL" mas a fatura ser BRANCA
        if self.confianca == 0 and "Classificação:" in text:
            if "BRANCA" in text.upper():
                self.modalidade_detectada = "BRANCA"
                self.confianca = 1
                result['modalidade_tarifaria'] = "BRANCA"
        
        # Para Grupo A, verificar modalidades AZUL ou VERDE
        if "AZUL" in text.upper() and ("MODALIDADE" in text.upper() or "Classificação:" in text):
            result['modalidade_tarifaria'] = "AZUL"
        elif "VERDE" in text.upper() and ("MODALIDADE" in text.upper() or "Classificação:" in text):
            result['modalidade_tarifaria'] = "VERDE"
        
        return result

# ================== PROCESSADOR PRINCIPAL ==================

class ImpostosExtractor(BaseExtractor):
    """Extrator para dados de impostos - VERSÃO DECIMAL"""
    
    def extract(self, text: str, block_info: Dict) -> Dict[str, Any]:
        result = {}
        x0, y0 = block_info.get('x0', 0), block_info.get('y0', 0)
        
        # Área típica dos impostos
        if not (660 <= x0 <= 880 and 390 <= y0 <= 450):
            return result
        
        parts = text.split()
        
        try:
            if "PIS/PASEP" in text:
                # Base de cálculo do PIS (primeiro valor após "PIS/PASEP")
                if len(parts) >= 2:
                    base_str = parts[1].replace(',', '.')
                    base = Decimal(base_str)
                    result['base_pis'] = base
                
                # Alíquota do PIS (segundo valor)
                if len(parts) >= 3:
                    aliquota_str = parts[2].replace(',', '.').rstrip('%')
                    if aliquota_str.replace('.', '').isdigit():
                        aliquota = Decimal(aliquota_str) / Decimal('100')
                        result['aliquota_pis'] = aliquota
                
                # Valor do PIS (terceiro valor)
                if len(parts) >= 4:
                    valor_str = parts[3].replace(',', '.')
                    valor = Decimal(valor_str)
                    result['valor_pis'] = valor
                        
            elif "ICMS" in text and "COFINS" not in text:
                # Base de cálculo do ICMS
                if len(parts) >= 2:
                    base_str = parts[1].replace(',', '.')
                    base = Decimal(base_str)
                    result['base_icms'] = base
                
                # Alíquota do ICMS
                if len(parts) >= 3:
                    aliquota_str = parts[2].replace(',', '.').rstrip('%')
                    if aliquota_str.replace('.', '').isdigit():
                        aliquota = Decimal(aliquota_str) / Decimal('100')
                        result['aliquota_icms'] = aliquota
                
                # Valor do ICMS
                if len(parts) >= 4:
                    valor_str = parts[3].replace(',', '.')
                    valor = Decimal(valor_str)
                    result['valor_icms'] = valor
                        
            elif "COFINS" in text:
                # Base de cálculo do COFINS
                if len(parts) >= 2:
                    base_str = parts[1].replace(',', '.')
                    base = Decimal(base_str)
                    result['base_cofins'] = base
                
                # Alíquota do COFINS
                if len(parts) >= 3:
                    aliquota_str = parts[2].replace(',', '.').rstrip('%')
                    if aliquota_str.replace('.', '').isdigit():
                        aliquota = Decimal(aliquota_str) / Decimal('100')
                        result['aliquota_cofins'] = aliquota
                
                # Valor do COFINS
                if len(parts) >= 4:
                    valor_str = parts[3].replace(',', '.')
                    valor = Decimal(valor_str)
                    result['valor_cofins'] = valor
                        
        except (ValueError, IndexError) as e:
            print(f"Erro ao processar impostos: {e} - Texto: {text[:50]}")
        
        return result



class CreditosSaldosExtractor(BaseExtractor):
    """Extrator para dados de créditos e saldos SCEE - VERSÃO CORRIGIDA PARA TARIFA BRANCA"""
    
    def extract(self, text: str, block_info: Dict) -> Dict[str, Any]:
        """Extrai dados do SCEE - VERSÃO MELHORADA para Tarifa Branca"""
        result = {}

        # VERSÃO MAIS FLEXÍVEL: Verificar múltiplas variações possíveis
        tem_scee = any(termo in text.upper() for termo in [
            "INFORMAÇÕES DO SCEE:",
            "INFORMACOES DO SCEE:",
            "CRÉDITO DE ENERGIA:",
            "CREDITO DE ENERGIA:",
            "SCEE:",
            "EXCEDENTE RECEBIDO",
            "GERAÇÃO CICLO",
            "GERACAO CICLO",
            "SALDO KWH",
            "CRÉDITO RECEBIDO",
            "CREDITO RECEBIDO"
        ])
        
        if not tem_scee:
            return result
        
        print(f"DEBUG: Processando SCEE (texto detectado)...")
        print(f" Texto completo: {text[:300]}...")
        
        # ========= GERAÇÃO CICLO =========
        geracao_matches = []
        
        # PADRÃO PRINCIPAL: "GERAÇÃO CICLO (6/2025) KWH: UC 10037114075 : 58.010,82"
        geracao_pattern = r'GERAÇÃO CICLO.*?KWH:\s*UC\s*(\d+)\s*:\s*([\d.,]+)'
        geracao_match = re.search(geracao_pattern, text)
        if geracao_match:
            uc_geradora = geracao_match.group(1)
            geracao_total = self.clean_numeric_value(geracao_match.group(2))
            
            print(f"   OK: Geração detectada: UC {uc_geradora}, Total: {geracao_total}")
            
            geracao_matches.append({
                'uc': uc_geradora,
                'tipo': 'grupo_b',
                'total': geracao_total
            })

        # PADRÃO TARIFA BRANCA: "UC 10037114024 : P=0,40, FP=18.781,95, HR=0,00, HI=0,00"
        geracao_branca_pattern = r'UC\s*(\d+)\s*:\s*P=([\d.,]+),\s*FP=([\d.,]+),\s*HR=([\d.,]+),\s*HI=([\d.,]+)'
        geracao_branca_match = re.search(geracao_branca_pattern, text)
        if geracao_branca_match:
            uc_geradora = geracao_branca_match.group(1)
            p_val = self.clean_numeric_value(geracao_branca_match.group(2))
            fp_val = self.clean_numeric_value(geracao_branca_match.group(3))
            hr_val = self.clean_numeric_value(geracao_branca_match.group(4))
            hi_val = self.clean_numeric_value(geracao_branca_match.group(5))
            
            geracao_total = p_val + fp_val + hr_val + hi_val
            
            print(f"   OK: Geração Branca detectada: UC {uc_geradora}")
            print(f"       P={p_val}, FP={fp_val}, HR={hr_val}, HI={hi_val}, Total={geracao_total}")
            
            geracao_matches.append({
                'uc': uc_geradora,
                'tipo': 'grupo_b_branca',
                'total': geracao_total,
                'p': p_val,
                'fp': fp_val,
                'hr': hr_val,
                'hi': hi_val
            })
        
        # ========= EXCEDENTE RECEBIDO =========
        excedente_matches = []
        
        # PADRÃO CONVENCIONAL: "EXCEDENTE RECEBIDO KWH: UC 10037114075 : 16.370,65"
        excedente_pattern = r'EXCEDENTE RECEBIDO KWH:\s*UC\s*(\d+)\s*:\s*([\d.,]+)'
        excedente_match = re.search(excedente_pattern, text)
        if excedente_match:
            uc = excedente_match.group(1)
            excedente_total = self.clean_numeric_value(excedente_match.group(2))
            
            print(f"   OK: Excedente detectado: UC {uc}, Total: {excedente_total}")
            
            excedente_matches.append({
                'uc': uc,
                'tipo': 'grupo_b',
                'total': excedente_total
            })

        # PADRÃO TARIFA BRANCA: "EXCEDENTE RECEBIDO KWH: UC 10037114024 : P=0,11, FP=5.258,95, HR=0,00, HI=0,00"
        excedente_branca_pattern = r'EXCEDENTE RECEBIDO KWH:\s*UC\s*(\d+)\s*:\s*P=([\d.,]+),\s*FP=([\d.,]+),\s*HR=([\d.,]+),\s*HI=([\d.,]+)'
        excedente_branca_match = re.search(excedente_branca_pattern, text)
        if excedente_branca_match:
            uc = excedente_branca_match.group(1)
            p_val = self.clean_numeric_value(excedente_branca_match.group(2))
            fp_val = self.clean_numeric_value(excedente_branca_match.group(3))
            hr_val = self.clean_numeric_value(excedente_branca_match.group(4))
            hi_val = self.clean_numeric_value(excedente_branca_match.group(5))
            
            excedente_total = p_val + fp_val + hr_val + hi_val
            
            print(f"   OK: Excedente Branca detectado: UC {uc}")
            print(f"       P={p_val}, FP={fp_val}, HR={hr_val}, HI={hi_val}, Total={excedente_total}")
            
            excedente_matches.append({
                'uc': uc,
                'tipo': 'grupo_b_branca',
                'total': excedente_total,
                'p': p_val,
                'fp': fp_val,
                'hr': hr_val,
                'hi': hi_val
            })
        
        # ========= CRÉDITO RECEBIDO =========
        credito_pattern = r'CRÉDITO RECEBIDO KWH\s+([\d.,]+)'
        credito_match = re.search(credito_pattern, text)
        if credito_match:
            valor_credito = self.clean_numeric_value(credito_match.group(1))
            result['credito_recebido'] = valor_credito
            print(f"   OK: Crédito detectado: {valor_credito}")
        
        # ========= SALDO ATUAL - VERSÃO CORRIGIDA PARA TARIFA BRANCA =========
        
        # PADRÃO 1: SALDO CONVENCIONAL (funcionando)
        saldo_conv_pattern = r'SALDO KWH:\s*([\d.,]+)(?=,|\s|$)'
        saldo_conv_match = re.search(saldo_conv_pattern, text)
        
        # PADRÃO 2: SALDO TARIFA BRANCA (NOVO)
        saldo_branca_pattern = r'SALDO KWH:\s*P=([\d.,]+),\s*FP=([\d.,]+),\s*HR=([\d.,]+),\s*HI=([\d.,]+)'
        saldo_branca_match = re.search(saldo_branca_pattern, text)
        
        if saldo_branca_match:
            # TARIFA BRANCA - saldos separados por posto
            saldo_p = self.clean_numeric_value(saldo_branca_match.group(1))
            saldo_fp = self.clean_numeric_value(saldo_branca_match.group(2))
            saldo_hr = self.clean_numeric_value(saldo_branca_match.group(3))
            saldo_hi = self.clean_numeric_value(saldo_branca_match.group(4))
            
            saldo_total = saldo_p + saldo_fp + saldo_hr + saldo_hi
            
            # Salvar saldos por posto
            result['saldo_p'] = saldo_p
            result['saldo_fp'] = saldo_fp  
            result['saldo_hr'] = saldo_hr
            result['saldo_hi'] = saldo_hi
            result['saldo'] = saldo_total
            
            print(f"   OK: Saldo Branca detectado:")
            print(f"       P={saldo_p}, FP={saldo_fp}, HR={saldo_hr}, HI={saldo_hi}")
            print(f"       Total: {saldo_total}")
            
        elif saldo_conv_match:
            # TARIFA CONVENCIONAL - saldo único
            saldo_total = self.clean_numeric_value(saldo_conv_match.group(1))
            result['saldo'] = saldo_total
            print(f"   OK: Saldo Convencional detectado: {saldo_total}")
        
        # ========= SALDOS A EXPIRAR - VERSÃO CORRIGIDA =========
        
        # PADRÃO CONVENCIONAL
        saldo_30_conv_pattern = r'SALDO A EXPIRAR EM 30 DIAS KWH:\s*([\d.,]+)(?=,|\s|$)'
        saldo_30_conv_match = re.search(saldo_30_conv_pattern, text)
        
        # PADRÃO TARIFA BRANCA (se existir no futuro)
        saldo_30_branca_pattern = r'SALDO A EXPIRAR EM 30 DIAS KWH:\s*P=([\d.,]+),\s*FP=([\d.,]+),\s*HR=([\d.,]+),\s*HI=([\d.,]+)'
        saldo_30_branca_match = re.search(saldo_30_branca_pattern, text)
        
        if saldo_30_branca_match:
            # TARIFA BRANCA
            saldo_30_p = self.clean_numeric_value(saldo_30_branca_match.group(1))
            saldo_30_fp = self.clean_numeric_value(saldo_30_branca_match.group(2))
            saldo_30_hr = self.clean_numeric_value(saldo_30_branca_match.group(3))
            saldo_30_hi = self.clean_numeric_value(saldo_30_branca_match.group(4))
            
            result['saldo_30_p'] = saldo_30_p
            result['saldo_30_fp'] = saldo_30_fp
            result['saldo_30_hr'] = saldo_30_hr
            result['saldo_30_hi'] = saldo_30_hi
            result['saldo_30'] = saldo_30_p + saldo_30_fp + saldo_30_hr + saldo_30_hi
            print(f"   OK: Saldo 30 dias Branca: P={saldo_30_p}, FP={saldo_30_fp}, HR={saldo_30_hr}, HI={saldo_30_hi}")
            
        elif saldo_30_conv_match:
            # TARIFA CONVENCIONAL
            result['saldo_30'] = self.clean_numeric_value(saldo_30_conv_match.group(1))
            print(f"   OK: Saldo 30 dias: {result['saldo_30']}")
        
        # Mesmo padrão para 60 dias
        saldo_60_conv_pattern = r'SALDO A EXPIRAR EM 60 DIAS KWH:\s*([\d.,]+)(?=,|\s|$)'
        saldo_60_conv_match = re.search(saldo_60_conv_pattern, text)
        
        saldo_60_branca_pattern = r'SALDO A EXPIRAR EM 60 DIAS KWH:\s*P=([\d.,]+),\s*FP=([\d.,]+),\s*HR=([\d.,]+),\s*HI=([\d.,]+)'
        saldo_60_branca_match = re.search(saldo_60_branca_pattern, text)
        
        if saldo_60_branca_match:
            saldo_60_p = self.clean_numeric_value(saldo_60_branca_match.group(1))
            saldo_60_fp = self.clean_numeric_value(saldo_60_branca_match.group(2))
            saldo_60_hr = self.clean_numeric_value(saldo_60_branca_match.group(3))
            saldo_60_hi = self.clean_numeric_value(saldo_60_branca_match.group(4))
            
            result['saldo_60_p'] = saldo_60_p
            result['saldo_60_fp'] = saldo_60_fp
            result['saldo_60_hr'] = saldo_60_hr
            result['saldo_60_hi'] = saldo_60_hi
            result['saldo_60'] = saldo_60_p + saldo_60_fp + saldo_60_hr + saldo_60_hi
            print(f"   OK: Saldo 60 dias Branca: P={saldo_60_p}, FP={saldo_60_fp}, HR={saldo_60_hr}, HI={saldo_60_hi}")
            
        elif saldo_60_conv_match:
            result['saldo_60'] = self.clean_numeric_value(saldo_60_conv_match.group(1))
            print(f"   OK: Saldo 60 dias: {result['saldo_60']}")
        
        # ========= RATEIO GERAÇÃO =========
        rateio_pattern = r'CADASTRO RATEIO GERAÇÃO:\s*UC\s*(\d+)\s*=\s*([\d.,]+%?)'
        rateio_match = re.search(rateio_pattern, text)
        if rateio_match:
            result['rateio_fatura'] = rateio_match.group(2)
            print(f"   OK: Rateio: UC {rateio_match.group(1)} = {rateio_match.group(2)}")
        
        # ========= SALVAR DADOS BRUTOS =========
        if geracao_matches:
            result['_geracao_ugs_raw'] = geracao_matches
            print(f"   DATA: {len(geracao_matches)} registros de geração salvos")
        
        if excedente_matches:
            result['_excedente_ugs_raw'] = excedente_matches
            print(f"   DATA: {len(excedente_matches)} registros de excedente salvos")
        
        # ========= GARANTIR VALORES MÍNIMOS =========
        if 'saldo' not in result:
            result['saldo'] = Decimal('0')
            print(f"   LISTA: Saldo definido como 0 (não encontrado)")
        
        if 'excedente_recebido' not in result and excedente_matches:
            total_excedente = sum(item['total'] for item in excedente_matches)
            result['excedente_recebido'] = total_excedente
            print(f"   LISTA: Excedente recebido calculado: {total_excedente}")
        elif 'excedente_recebido' not in result:
            result['excedente_recebido'] = Decimal('0')
            print(f"   LISTA: Excedente recebido definido como 0 (não encontrado)")
        
        print(f"TARGET: Resultado final:")
        print(f"    Saldo total: {result.get('saldo')}")
        if 'saldo_p' in result:
            print(f"    Saldos por posto: P={result.get('saldo_p')}, FP={result.get('saldo_fp')}, HR={result.get('saldo_hr')}, HI={result.get('saldo_hi')}")
        print(f"    Excedente: {result.get('excedente_recebido')}")
        
        return result
    
class EnderecoExtractor(BaseExtractor):
    """Extrator para endereço e CNPJ/CPF"""
    
    def extract(self, text: str, block_info: Dict) -> Dict[str, Any]:
        result = {}
        x0, y0 = block_info.get('x0', 0), block_info.get('y0', 0)
        
        # Coordenadas do endereço (do código antigo)
        if (28.0 <= x0 <= 200.00) and (110.00 <= y0 <= 200.00):
            text = text.strip().replace("\n", " ")
            match = re.search(r"(.*?)(?=\bPERDAS)", text, re.DOTALL)
            if match:
                endereco = match.group(1).strip()
                endereco_array = endereco.split(" ")

                if "CNPJ/CPF:" in endereco_array:
                    index_cnpj = endereco_array.index("CNPJ/CPF:")
                    cnpj_cpf = endereco_array[index_cnpj + 1] if index_cnpj + 1 < len(endereco_array) else ""
                else:
                    cnpj_cpf = ""

                result["endereco"] = endereco
                result["cnpj_cpf"] = cnpj_cpf
        
        return result

class DataLeituraExtractor(BaseExtractor):
    """Extrator para data de leitura"""
    
    def extract(self, text: str, block_info: Dict) -> Dict[str, Any]:
        result = {}
        x0, y0 = block_info.get('x0', 0), block_info.get('y0', 0)
        
        # Coordenadas da data de leitura (do código antigo)
        if (560.00 <= x0 <= 700.00) and (135.0 <= y0 <= 150.0):
            all_dates = re.findall(r"\d{2}/\d{2}/\d{4}", text)
            if len(all_dates) >= 2:
                try:
                    leitura_atual_date = all_dates[1]
                    leitura_atual_date = datetime.strptime(leitura_atual_date, "%d/%m/%Y")
                    leitura_atual_date = leitura_atual_date.strftime("%d/%m/%y")
                    result["data_leitura"] = leitura_atual_date
                except ValueError:
                    pass
        
        return result


class TabelaLeituraExtractor(BaseExtractor):
    """Extrator para dados da tabela de leitura (medidores) - IMPLEMENTAÇÃO COMPLETA"""
    
    def extract(self, text: str, block_info: Dict, grupo: Optional[str] = None) -> Dict[str, Any]:
        result = {}
        x0, y0 = block_info.get('x0', 0), block_info.get('y0', 0)
        
        # Coordenadas da tabela de leitura (do código antigo)
        if (25 <= x0 <= 510) and (670 <= y0 <= 870):
            if grupo == "A":
                self._processar_grupo_a(text, result)
            elif grupo == "B":
                self._processar_grupo_b(text, result)
        
        return result
    
    def _processar_grupo_a(self, text: str, result: Dict[str, Any]) -> None:
        """Processa tabela de leitura para Grupo A"""
        parts = re.split(r"\s+", text)

        energia_geracao = []
        energia_ativa = []
        demanda = []
        demanda_geracao = []
        ufer = []
        dmcr = []

        # Iterar pela lista e classificar os dados
        current_group = None
        current_data = []

        for item in parts:
            # Detectar o início de um novo grupo
            if item == 'ENERGIA':
                if "GERAÇÃO" in parts[parts.index(item) + 1:]:
                    if current_group:
                        locals()[current_group].append(current_data)
                    current_group = 'energia_geracao'
                    current_data = ['ENERGIA']
                else:
                    if current_group:
                        locals()[current_group].append(current_data)
                    current_group = 'energia_ativa'
                    current_data = ['ENERGIA']
            elif item == 'DEMANDA':
                # Verificar se a palavra "GERAÇÃO" aparece logo após "DEMANDA"
                if "GERAÇÃO" in parts[parts.index(item) + 1:]:
                    if current_group:
                        locals()[current_group].append(current_data)
                    current_group = 'demanda_geracao'
                    current_data = ['DEMANDA']
                else:
                    if current_group:
                        locals()[current_group].append(current_data)
                    current_group = 'demanda'
                    current_data = ['DEMANDA']
            elif item == 'UFER':
                if current_group:
                    locals()[current_group].append(current_data)
                current_group = 'ufer'
                current_data = ['UFER']
            elif item == 'DMCR':
                if current_group:
                    locals()[current_group].append(current_data)
                current_group = 'dmcr'
                current_data = ['DMCR']
            else:
                current_data.append(item)

        # Adicionar o último grupo
        if current_group:
            locals()[current_group].append(current_data)

        # Lista com os grupos de dados
        all_data = [
            ('energia_geracao', energia_geracao),
            ('energia_ativa', energia_ativa),
            ('demanda', demanda),
            ('demanda_geracao', demanda_geracao),
            ('ufer', ufer),
            ('dmcr', dmcr)
        ]

        # Processar cada grupo de dados
        for group_name, group_data in all_data:
            for row in group_data:
                # Encontrar o índice do tipo (PONTA, FORA PONTA, RESERVADO)
                index = next(
                    (i for i, val in enumerate(row) if val in ["PONTA", "FORA", "RESERVADO", "INTERME"]),
                    -1,
                )

                if index >= 0:
                    # Reconstruir o tipo correto
                    if row[index] == "FORA" and index + 1 < len(row) and row[index + 1] == "PONTA":
                        tipo = "fp"
                    elif row[index] == "RESERVADO":
                        tipo = "hr"
                    elif row[index] == "PONTA":
                        tipo = "p"
                    elif row[index] == "INTERME":
                        tipo = "intermed"
                    else:
                        continue

                    # Calcular os índices relativos ao tipo
                    info_data = row[max(0, index - 4): index]
                    for i, value in enumerate(info_data, start=1):
                        # CORREÇÃO: Validar antes de converter
                        if value and re.search(r'\d', str(value)):
                            formatted_value = safe_decimal_conversion(str(value), f"tabela_leitura_{group_name}_{tipo}")
                        else:
                            formatted_value = Decimal('0')

                        if i == 1:
                            key = f"leitura_atual_{group_name}_{tipo}"
                            result[key] = formatted_value
                        elif i == 3:
                            key = f"leitura_anterior_{group_name}_{tipo}"
                            result[key] = formatted_value
                        elif i == 4:
                            key = f"const_medidor_{group_name}_{tipo}"
                            result[key] = formatted_value

    def _processar_grupo_b(self, text: str, result: Dict[str, Any]) -> None:
        """Processa tabela de leitura para Grupo B - VERSÃO CORRIGIDA"""
        parts = re.split(r"\s+", text)
        
        groups = [['ENERGIA', 'ATIVA'], ['ENERGIA', 'GERAÇÃO']]

        for group_words in groups:
            group_name = group_words[1].lower()
            
            indices = []
            for i in range(len(parts) - 1):
                if parts[i] == group_words[0] and parts[i + 1] == group_words[1]:
                    indices.append(i)

            for idx, start_index in enumerate(indices):
                end_index = indices[idx + 1] if idx + 1 < len(indices) else len(parts)
                group_data = parts[start_index:end_index]

                if len(group_data) > 4:
                    info_data = group_data[4:]
                    for i, value in enumerate(info_data, start=1):
                        # CORREÇÃO: Validar antes de converter
                        if value and re.search(r'\d', str(value)):
                            formatted_value = safe_decimal_conversion(str(value), f"tabela_leitura_{group_name}")
                        else:
                            formatted_value = Decimal('0')

                        if i == 1:
                            key = f"leitura_atual_energia_{group_name}"
                            result[key] = formatted_value
                        elif i == 4:
                            key = f"leitura_anterior_energia_{group_name}"
                            result[key] = formatted_value
                        elif i == 5:
                            key = f"const_medidor_energia_{group_name}"
                            result[key] = formatted_value


    def validar_conversoes_decimal(dados: Dict[str, Any]) -> Dict[str, Any]:
        """Valida e corrige todos os valores Decimal nos dados extraídos"""
        dados_corrigidos = {}
        
        for key, value in dados.items():
            if isinstance(value, str) and re.search(r'\d', value):
                # Se é uma string que parece numérica, tentar converter
                if any(campo in key.lower() for campo in ['valor', 'rs_', 'aliquota', 'consumo', 'demanda', 'saldo']):
                    try:
                        dados_corrigidos[key] = safe_decimal_conversion(value, key)
                    except:
                        dados_corrigidos[key] = value  # Manter original se não conseguir converter
                else:
                    dados_corrigidos[key] = value
            else:
                dados_corrigidos[key] = value
        
        return dados_corrigidos


class MedidorExtractor(BaseExtractor):
    """Extrator específico para números de medidores usando coordenadas precisas"""
    
    def __init__(self):
        super().__init__()
        self.grupo = None
        
    def set_grupo(self, grupo: str):
        """Define o grupo para usar coordenadas corretas"""
        self.grupo = grupo
    
    def extract(self, text: str, block_info: Dict) -> Dict[str, Any]:
        result = {}
        
        # Esta função precisa da função extrair_coluna do código antigo
        # Por enquanto, vou implementar uma versão simplificada
        
        if self.grupo == "A":
            # Coordenadas para Grupo A - Coluna do medidor
            # (440, 683, 505, 840) conforme código antigo
            result = self._extrair_medidor_grupo_a(text, block_info)
        elif self.grupo == "B":
            # Coordenadas para Grupo B - Coluna do medidor  
            # (30, 683, 95, 740) conforme código antigo
            result = self._extrair_medidor_grupo_b(text, block_info)
            
        return result
    
    def _extrair_medidor_grupo_a(self, text: str, block_info: Dict) -> Dict[str, Any]:
        """Extrai medidor para Grupo A"""
        x0, y0 = block_info.get('x0', 0), block_info.get('y0', 0)
        
        # Coordenadas da coluna do medidor para Grupo A
        if (440 <= x0 <= 505) and (683 <= y0 <= 840):
            # Pegar o primeiro número encontrado (medidor)
            medidor_match = re.search(r'\d+', text)
            if medidor_match:
                return {'medidor': medidor_match.group(0)}
        
        return {}
    
    def _extrair_medidor_grupo_b(self, text: str, block_info: Dict) -> Dict[str, Any]:
        """Extrai medidor para Grupo B"""
        x0, y0 = block_info.get('x0', 0), block_info.get('y0', 0)
        
        # Coordenadas da coluna do medidor para Grupo B
        if (30 <= x0 <= 95) and (683 <= y0 <= 740):
            # Pegar o primeiro número encontrado (medidor)
            medidor_match = re.search(r'\d+', text)
            if medidor_match:
                return {'medidor': medidor_match.group(0)}
        
        return {}

def extrair_coluna(page, rect):
    """
    Função migrada do código antigo para extrair texto e coordenadas de uma coluna
    Esta função é necessária para o MedidorExtractor funcionar corretamente
    """
    # Obter todas as palavras com coordenadas
    palavras_com_coords = page.get_text("words")  # [(x0, y0, x1, y1, texto, bloco, linha, palavra), ...]

    # Filtrar palavras que estão dentro do retângulo especificado
    palavras_filtradas = [
        (x0, y0, x1, y1, texto)
        for x0, y0, x1, y1, texto, *_ in palavras_com_coords
        if rect.contains(fitz.Rect(x0, y0, x1, y1))
    ]

    # Ordenar palavras por `y0` (posição vertical) e, em seguida, por `x0` (posição horizontal)
    palavras_filtradas.sort(key=lambda w: (round(w[1]), w[0]))

    # Agrupar palavras por linhas baseadas na coordenada `y0`
    linhas = {}
    for x0, y0, x1, y1, texto in palavras_filtradas:
        linha_chave = round(y0)  # Arredondar `y0` para agrupar palavras que pertencem à mesma linha
        if linha_chave not in linhas:
            linhas[linha_chave] = {
                "y0": y0,
                "y1": y1,
                "texto": texto  # Adicionar a primeira palavra
            }
        else:
            linhas[linha_chave]["texto"] += f" {texto}"  # Concatenar palavras da mesma linha

    # Retornar uma lista com as coordenadas `y0`, `y1` da primeira palavra e o texto completo da linha
    return [{"y0": v["y0"], "y1": v["y1"], "texto": v["texto"]} for v in linhas.values()]


# Versão melhorada do MedidorExtractor que usa a função extrair_coluna
class MedidorExtractorAvancado(BaseExtractor):
    """Extrator avançado para medidores usando a função extrair_coluna"""
    
    def __init__(self):
        super().__init__()
        self.grupo = None
        self.page = None  # Precisa receber a página do PDF
        
    def set_contexto(self, grupo: str, page):
        """Define o grupo e a página para extração precisa"""
        self.grupo = grupo
        self.page = page
    
    def extract(self, text: str, block_info: Dict) -> Dict[str, Any]:
        result = {}
        
        if not self.page:
            return result
            
        try:
            if self.grupo == "A":
                # Coordenadas para Grupo A - Coluna do medidor
                rect_medidor_a = fitz.Rect(440, 683, 505, 840)
                itens_medidor = extrair_coluna(self.page, rect_medidor_a)
                if itens_medidor:
                    medidor = itens_medidor[0]['texto']
                    result['medidor'] = medidor
                    
            elif self.grupo == "B":
                # Coordenadas para Grupo B - Coluna do medidor  
                rect_medidor_b = fitz.Rect(30, 683, 95, 740)
                itens_medidor = extrair_coluna(self.page, rect_medidor_b)
                if itens_medidor:
                    medidor = itens_medidor[0]['texto']
                    result['medidor'] = medidor
                    
        except (IndexError, KeyError, AttributeError):
            pass
            
        return result
    
    # ATUALIZAÇÃO DO FATURAPROCESSOR PARA INCLUIR OS NOVOS EXTRACTORS

class FaturaProcessor:
    def __init__(self):
        self.debug = True
        self.extractors = {
            'dados_basicos': DadosBasicosExtractor(),
            'mes_referencia': MesReferenciaExtractor(),
            'modalidade_tarifaria': ModalidadeTarifariaExtractor(),
            'consumo': ConsumoExtractor(),
            'impostos': ImpostosExtractor(),
            'creditos_saldos': CreditosSaldosExtractor(),
            'endereco': EnderecoExtractor(),
            'data_leitura': DataLeituraExtractor(),
            'tabela_leitura': TabelaLeituraExtractor(),
            'medidor': MedidorExtractor(),
            'demanda': DemandaExtractor(),
            'geracao': GeracaoExtractor(),
            'irrigacao': IrrigacaoExtractor(),  #  NOVA LINHA AQUI
        }
        self.dados = {}
            
    def processar_fatura(self, pdf_path: str) -> Dict[str, Any]:
        """Processa uma fatura PDF e retorna os dados extraídos - VERSÃO CORRIGIDA"""
        doc = fitz.open(pdf_path)

        # Resetar acumuladores dos extractors
        self._resetar_extractors()
        
        # Processar todas as páginas
        for page_num in range(len(doc)):
            page = doc[page_num]
            self._processar_pagina(page, page_num, doc)
        
        # Pós-processamento CORRIGIDO
        self._pos_processamento()

        # NOVO: RELATÓRIO DETALHADO DOS DADOS EXTRAÍDOS
        self._imprimir_relatorio_extracao(pdf_path)
        
        doc.close()
        return self.dados
    
    def _imprimir_relatorio_extracao(self, pdf_path: str):
        """Imprime relatório detalhado dos dados extraídos"""
        print(f"\n{'='*80}")
        print(f"LISTA: RELATÓRIO DE EXTRAÇÃO - {os.path.basename(pdf_path)}")
        print(f"{'='*80}")
        
        # Dados básicos
        print(f"  DADOS BÁSICOS:")
        dados_basicos = ['uc', 'grupo', 'subgrupo', 'modalidade_tarifaria', 'tipo_fornecimento', 
                        'mes_referencia', 'vencimento', 'valor_concessionaria', 'data_leitura', 'medidor']
        for campo in dados_basicos:
            if campo in self.dados:
                valor = self.dados[campo]
                print(f"   {campo}: {valor}")
        
        # Consumo
        print(f"\n CONSUMO:")
        campos_consumo = [k for k in self.dados.keys() if 'consumo' in k.lower() and 'rs_' not in k.lower()]
        for campo in sorted(campos_consumo):
            print(f"   {campo}: {self.dados[campo]}")
        
        # Tarifas
        print(f"\n TARIFAS:")
        campos_tarifas = [k for k in self.dados.keys() if 'rs_' in k.lower()]
        for campo in sorted(campos_tarifas):
            print(f"   {campo}: {self.dados[campo]}")
        
        # Valores monetários
        print(f"\n VALORES:")
        campos_valores = [k for k in self.dados.keys() if 'valor_' in k.lower()]
        for campo in sorted(campos_valores):
            print(f"   {campo}: {self.dados[campo]}")
        
        # Geração e SCEE
        print(f"\n GERAÇÃO/SCEE:")
        campos_geracao = [k for k in self.dados.keys() if any(termo in k.lower() for termo in ['geracao', 'injetada', 'saldo', 'credito', 'excedente'])]
        for campo in sorted(campos_geracao):
            print(f"   {campo}: {self.dados[campo]}")
        
        # Impostos
        print(f"\n  IMPOSTOS:")
        campos_impostos = [k for k in self.dados.keys() if any(termo in k.lower() for termo in ['icms', 'pis', 'cofins', 'aliquota'])]
        for campo in sorted(campos_impostos):
            valor = self.dados[campo]
            if 'aliquota' in campo and isinstance(valor, Decimal):
                print(f"   {campo}: {float(valor)*100:.4f}%")
            else:
                print(f"   {campo}: {valor}")
        
        # Bandeiras
        print(f"\n BANDEIRAS:")
        campos_bandeiras = [k for k in self.dados.keys() if 'bandeira' in k.lower()]
        for campo in sorted(campos_bandeiras):
            print(f"   {campo}: {self.dados[campo]}")
        
        # Outros
        print(f"\nDATA: OUTROS:")
        campos_outros = [k for k in self.dados.keys() if k not in dados_basicos and 
                        not any(termo in k.lower() for termo in ['consumo', 'rs_', 'valor_', 'geracao', 'injetada', 
                                                            'saldo', 'credito', 'excedente', 'icms', 'pis', 
                                                            'cofins', 'aliquota', 'bandeira'])]
        for campo in sorted(campos_outros):
            print(f"   {campo}: {self.dados[campo]}")
        
        print(f"\nGRAFICO: TOTAL DE CAMPOS EXTRAÍDOS: {len(self.dados)}")
        print(f"{'='*80}\n")

    # Adicionar estas funções à classe FaturaProcessor:

    def _resetar_extractors(self):
        self.dados.clear()
        """Reseta todos os acumuladores dos extractors"""
        for extractor in self.extractors.values():
            if hasattr(extractor, 'juros_total'): extractor.juros_total = 0.0
            if hasattr(extractor, 'multa_total'): extractor.multa_total = 0.0
            if hasattr(extractor, 'creditos_total'): extractor.creditos_total = 0.0
            if hasattr(extractor, 'consumo_tusd'): extractor.consumo_tusd = {}
            if hasattr(extractor, 'consumo_te'): extractor.consumo_te = {}
            if hasattr(extractor, 'rs_tusd'): extractor.rs_tusd = {}
            if hasattr(extractor, 'rs_te'): extractor.rs_te = {}
            if hasattr(extractor, 'valor_tusd'): extractor.valor_tusd = {}
            if hasattr(extractor, 'valor_te'): extractor.valor_te = {}
            if hasattr(extractor, 'consumo_comp'): extractor.consumo_comp = {}
            if hasattr(extractor, 'consumo_n_comp'): extractor.consumo_n_comp = {}
            if hasattr(extractor, 'valor_consumo_n_comp'): extractor.valor_consumo_n_comp = {}
            if hasattr(extractor, 'consumo_geral'): extractor.consumo_geral = None
            if hasattr(extractor, 'rs_consumo_geral'): extractor.rs_consumo_geral = None
            if hasattr(extractor, 'valor_consumo_geral'): extractor.valor_consumo_geral = None
            if hasattr(extractor, 'modalidade_detectada'): extractor.modalidade_detectada = None
            if hasattr(extractor, 'confianca'): extractor.confianca = 0
            if hasattr(extractor, 'bandeira_codigo'): extractor.bandeira_codigo = 0
            # CORREÇÃO: Resetar o novo acumulador
            if hasattr(extractor, 'energia_injetada_registros'): extractor.energia_injetada_registros = []  

    def _calcular_totais_por_posto(self, ugs_agrupadas: Dict) -> None:
        """Calcula totais de energia injetada por posto para Grupo A e Grupo B Branca"""
        
        # Verificar se é Grupo A ou Grupo B
        primeira_ug = next(iter(ugs_agrupadas.values()))
        tem_grupo_a = any(item.get('tipo') == 'grupo_a' for item in primeira_ug['detalhes'])
        tem_postos_b = any(item.get('posto') and item.get('posto') != 'unico' for item in primeira_ug['detalhes'])
        
        if tem_grupo_a:
            # GRUPO A: Calcular totais por posto e componente
            totais_grupo_a = {}
            
            for uc, ug_data in ugs_agrupadas.items():
                for item in ug_data['detalhes']:
                    if item.get('tipo') == 'grupo_a':
                        posto = item.get('posto', '')
                        componente = item.get('componente', '')
                        
                        if posto and componente:
                            # Chaves para totais: energia_injetada_tusd_p, energia_injetada_te_fp, etc.
                            if componente in ['tusd', 'te']:
                                chave_quant = f"energia_injetada_{componente}_{posto}"
                                chave_valor = f"valor_energia_injetada_{componente}_{posto}"
                            else:
                                chave_quant = f"energia_injetada_{posto}"
                                chave_valor = f"valor_energia_injetada_{posto}"
                            
                            if chave_quant not in totais_grupo_a:
                                totais_grupo_a[chave_quant] = Decimal('0')
                                totais_grupo_a[chave_valor] = Decimal('0')
                            
                            totais_grupo_a[chave_quant] += item['quantidade']
                            totais_grupo_a[chave_valor] += abs(item['valor'])
            
            # Salvar totais do Grupo A
            for chave, valor in totais_grupo_a.items():
                self.dados[chave] = valor
        
        elif tem_postos_b:
            # GRUPO B BRANCA: Calcular totais por posto
            totais_grupo_b = {}
            
            for uc, ug_data in ugs_agrupadas.items():
                for item in ug_data['detalhes']:
                    if item.get('tipo') == 'grupo_b':
                        posto = item.get('posto', '')
                        
                        if posto and posto != 'unico':
                            chave_quant = f"energia_injetada_{posto}"
                            chave_valor = f"valor_energia_injetada_{posto}"
                            
                            if chave_quant not in totais_grupo_b:
                                totais_grupo_b[chave_quant] = Decimal('0')
                                totais_grupo_b[chave_valor] = Decimal('0')
                            
                            totais_grupo_b[chave_quant] += item['quantidade']
                            totais_grupo_b[chave_valor] += abs(item['valor'])
            
            # Salvar totais do Grupo B Branca
            for chave, valor in totais_grupo_b.items():
                self.dados[chave] = valor

    def _processar_pagina(self, page, page_num: int, doc):
        """Processa uma página do PDF"""
        text_blocks = page.get_text("blocks")
        page_text = page.get_text()

        # PRIMEIRA PASSADA: Extrair dados básicos para obter o grupo
        for block in text_blocks:
            x0, y0, x1, y1, text = block[:5]
            text = text.strip()
            block_info = {'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1, 'page_num': page_num}

            # Extrair dados básicos primeiro
            if 'dados_basicos' in self.extractors:
                extracted_basicos = self.extractors['dados_basicos'].extract(text, block_info)
                self.dados.update(extracted_basicos)

        # Obter grupo atual
        current_group = self.dados.get('grupo')
        
        # SEGUNDA PASSADA: Processar todos os outros extractors
        for block in text_blocks:
            x0, y0, x1, y1, text = block[:5]
            text = text.strip()
            block_info = {'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1, 'page_num': page_num, 'page': page}

            for extractor_name, extractor in self.extractors.items():
                if extractor_name == 'dados_basicos': 
                    continue
                    
                try:
                    #  ADICIONAR PROCESSAMENTO DE IRRIGAÇÃO
                    if extractor_name == 'irrigacao':
                        extracted = extractor.extract(text, block_info)
                    # Extractors que precisam do grupo como parâmetro
                    elif extractor_name in ['consumo', 'tabela_leitura']:
                        extracted = extractor.extract(text, block_info, grupo=current_group)
                    elif extractor_name == 'mes_referencia' and page_num == 0:
                        extracted = extractor.extract(page_text)
                    # CORREÇÃO PRINCIPAL: creditos_saldos usa texto completo
                    elif extractor_name == 'creditos_saldos':
                        extracted = extractor.extract(page_text, block_info)
                    else:
                        extracted = extractor.extract(text, block_info)
                    
                    self.dados.update(extracted)
                    
                except Exception as e:
                    print(f"Erro no extractor {extractor_name}: {e}")
                    continue
    
    def _processar_segunda_pagina(self, page):
        """Processa a segunda página se existir (para dados adicionais)"""
        text_blocks = page.get_text("blocks")
        current_group = self.dados.get('grupo')
        
        for block in text_blocks:
            x0, y0, x1, y1, text = block[:5]
            text = text.strip()
            block_info = {'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1, 'page_num': 1, 'page': page}
            
            # Processar apenas extractors relevantes para segunda página
            extractors_segunda_pagina = ['consumo', 'tabela_leitura', 'impostos', 'creditos_saldos']
            
            for extractor_name in extractors_segunda_pagina:
                if extractor_name in self.extractors:
                    try:
                        extractor = self.extractors[extractor_name]
                        if extractor_name == 'consumo':
                            extracted = extractor.extract(text, block_info, grupo=current_group)
                        else:
                            extracted = extractor.extract(text, block_info)
                        self.dados.update(extracted)
                    except Exception as e:
                        print(f"Erro no extractor {extractor_name} (página 2): {e}")
                        continue
    
    def _pos_processamento(self):
        """Executa pós-processamento dos dados extraídos"""
        # 1. Inferir modalidade se não foi identificada
        self._inferir_modalidade_tarifaria()
        
        # 2. Finalizar totalizações de consumo
        if 'consumo' in self.extractors:
            try:
                self.extractors['consumo']._finalizar_totalizacoes(self.dados)
            except Exception as e:
                print(f"Erro na finalização de totalizações: {e}")
        
        # 3. Validar modalidade tarifária
        self._validar_modalidade_tarifaria()
        
        #  NOVA VALIDAÇÃO DE IRRIGAÇÃO
        # 4. Validar dados de irrigação
        self._validar_irrigacao()
        
        # 5. Processar múltiplas UGs (SCEE + Energia Injetada)
        try:
            self._processar_multiplas_ugs()
        except Exception as e:
            print(f"ERRO: Erro no processamento de múltiplas UGs: {e}")
            import traceback
            traceback.print_exc()
        
        self._aplicar_fallback_energia_injetada_scee()
        
        # 6. Limpar dados inconsistentes (por último)
        self._limpar_dados_inconsistentes()
    
    def _aplicar_fallback_energia_injetada_scee(self):
        """Versão simplificada - apenas garantir que consumo existe"""
        try:
            if not self.dados.get('consumo'):
                consumo_comp = self._to_decimal(self.dados.get('consumo_comp', 0))
                consumo_n_comp = self._to_decimal(self.dados.get('consumo_n_comp', 0))
                
                if consumo_comp > 0 or consumo_n_comp > 0:
                    self.dados['consumo'] = consumo_comp + consumo_n_comp
                    
        except Exception as e:
            print(f"AVISO: Erro no fallback: {e}")

    def _obter_consumo_comp_total(self) -> Decimal:
        """Obtém consumo compensado total já calculado"""
        # Por postos (Tarifa Branca)
        comp_p = self._to_decimal(self.dados.get("consumo_comp_p", 0))
        comp_fp = self._to_decimal(self.dados.get("consumo_comp_fp", 0))
        comp_hi = self._to_decimal(self.dados.get("consumo_comp_hi", 0))
        
        if comp_p > 0 or comp_fp > 0 or comp_hi > 0:
            return comp_p + comp_fp + comp_hi
        
        # Único (Tarifa Convencional)
        return self._to_decimal(self.dados.get("consumo_comp", 0))

    def _calcular_consumo_total_final(self):
        """Garante que consumo total está calculado corretamente"""
        consumo_comp = self._to_decimal(self.dados.get("consumo_comp", 0))
        consumo_n_comp = self._to_decimal(self.dados.get("consumo_n_comp", 0))
        
        if consumo_comp > 0 or consumo_n_comp > 0:
            total = consumo_comp + consumo_n_comp
            if total > 0:
                self.dados["consumo"] = total
                if getattr(self, 'debug', False):
                    print(f"OK: Consumo total calculado: {total} kWh (comp: {consumo_comp} + n_comp: {consumo_n_comp})")

    def _validar_irrigacao(self):
        """Valida e consolida dados de irrigação"""
        try:
            # Se não foi detectado automaticamente, verificar manualmente
            if not self.dados.get('irrigante'):
                # Verificar no texto completo se há menção de irrigação
                texto_completo = str(self.dados)
                
                # Padrões adicionais de detecção
                if any(termo in texto_completo.upper() for termo in [
                    'DESC. 80%', 'DESC. 60%', 'DESC. 70%', 'DESC. 90%',
                    'C/ DESC.', 'DESCONTO', 'IRRIGAÇÃO', 'IRRIGACAO'
                ]):
                    # Tentar extrair o percentual
                    desconto_match = re.search(r'(\d+)%', texto_completo)
                    if desconto_match and int(desconto_match.group(1)) > 50:
                        self.dados['irrigante'] = "Sim"
                        self.dados['desconto_irrigacao'] = f"{desconto_match.group(1)}%"
                    else:
                        self.dados['irrigante'] = "Não"
                        self.dados['desconto_irrigacao'] = "0%"
                else:
                    self.dados['irrigante'] = "Não"
                    self.dados['desconto_irrigacao'] = "0%"
                
        except Exception as e:
            print(f"AVISO: Erro na validação de irrigação: {e}")
            # Valores padrão
            self.dados['irrigante'] = "Não"
            self.dados['desconto_irrigacao'] = "0%"

    def _to_decimal(self, value) -> Decimal:
        """Converte qualquer valor para Decimal de forma segura"""
        if isinstance(value, Decimal):
            return value
        
        try:
            if value is None or value == "":
                return Decimal('0')
            
            if isinstance(value, str):
                cleaned = value.replace(',', '.').strip()
                return Decimal(cleaned) if cleaned else Decimal('0')
            
            return Decimal(str(value))
            
        except (ValueError, TypeError):
            return Decimal('0')
    
    def _finalizar_energia_injetada(self, result: Dict[str, Any]) -> None:
        """NOVO: Finaliza processamento de energia injetada com estratégia de fallback para UC"""
        
        if not self.energia_injetada_registros:
            return
        
        # ESTRATÉGIA DE FALLBACK PARA UCs GERADORAS
        registros_sem_uc = [r for r in self.energia_injetada_registros if not r.get('uc')]
        
        if registros_sem_uc:
            
            # FALLBACK 1: Buscar UC nos dados do SCEE (excedente/geração)
            ucs_do_scee = self._extrair_ucs_do_scee(result)
            
            if ucs_do_scee:
                
                # Se tem apenas 1 UC no SCEE, usar para todos os registros
                if len(ucs_do_scee) == 1:
                    uc_geradora = ucs_do_scee[0]
                    for registro in registros_sem_uc:
                        registro['uc'] = uc_geradora

                # Se tem múltiplas UCs, usar a primeira (pode ser refinado depois)
                else:
                    for registro in registros_sem_uc:
                        registro['uc'] = ucs_do_scee[0]
            
            # FALLBACK 2: Se não encontrou no SCEE, usar UC da própria fatura
            else:
                uc_fatura = result.get('uc')
                if uc_fatura:
                    for registro in registros_sem_uc:
                        registro['uc'] = uc_fatura
                else:
                    print(f"ERRO: Não foi possível identificar UC geradora")
        
        # Preparar dados para pós-processamento
        result['_energia_injetada_ugs_raw'] = self.energia_injetada_registros.copy()

    def _extrair_ucs_do_scee(self, result: Dict[str, Any]) -> List[str]:
        """Extrai UCs geradoras dos dados do SCEE (excedente/geração)"""
        ucs_encontradas = []
        
        # MÉTODO 1: Buscar em dados brutos do SCEE
        for key in ['_geracao_ugs_raw', '_excedente_ugs_raw']:
            if key in result:
                dados_scee = result[key]
                if isinstance(dados_scee, list):
                    for item in dados_scee:
                        if isinstance(item, dict) and 'uc' in item:
                            uc = item['uc']
                            if uc and str(uc) not in ucs_encontradas:
                                ucs_encontradas.append(str(uc))
        
        # MÉTODO 2: Buscar em campos individuais já processados
        for key in ['uc_geradora', 'uc_geradora_1', 'uc_geradora_2']:
            if key in result and result[key]:
                uc = str(result[key])
                if uc not in ucs_encontradas:
                    ucs_encontradas.append(uc)
        
        # MÉTODO 3: Buscar campo 'rateio_fatura' que às vezes tem UC
        rateio = result.get('rateio_fatura', '')
        if rateio and 'UC' in str(rateio):
            uc_match = re.search(r'UC\s*(\d{10,})', str(rateio))
            if uc_match:
                uc = uc_match.group(1)
                if uc not in ucs_encontradas:
                    ucs_encontradas.append(uc)
        
        return ucs_encontradas
    
    def _processar_multiplas_ugs(self):
        """Processa dados de múltiplas UGs geradoras - NOVA ESTRUTURA COM LISTAS"""
        
        # OK: DEBUG: Verificar se os dados brutos existem
        debug_keys = ['_geracao_ugs_raw', '_excedente_ugs_raw', '_energia_injetada_ugs_raw']
        for key in debug_keys:
            if key not in self.dados:
                print(f"ERRO: {key}: NÃO ENCONTRADO")
                
        # Se não tem nenhum dado bruto, sair
        if not any(key in self.dados for key in debug_keys):
            print("AVISO: Nenhum dado bruto de UGs encontrado, pulando processamento...")
            return
        
        # ========= ESTRUTURAS PARA NOVA ARQUITETURA =========
        ugs_geracao = []      # Lista de UGs com dados de geração
        ugs_excedentes = []   # Lista de UGs com dados de excedentes  
        ugs_injecao = []      # Lista de UGs com dados de injeção
        
        # Coletar todas as UCs geradoras encontradas
        todas_ucs = set()
        
        # =========================================================================
        # 1. PROCESSAR GERAÇÃO CICLO - NOVA ESTRUTURA
        # =========================================================================
        if '_geracao_ugs_raw' in self.dados:
            geracao_ugs = self.dados['_geracao_ugs_raw']
            
            # Ordenar por maior total de geração
            geracao_ugs_ordenadas = sorted(
                geracao_ugs,
                key=lambda ug: ug['total'],
                reverse=True  # Maior geração primeiro
            )
            
            total_geracao = Decimal('0')
            total_p = Decimal('0')
            total_fp = Decimal('0')
            total_hr = Decimal('0')
            
            # Processar cada UG
            for i, ug_data in enumerate(geracao_ugs_ordenadas):
                uc = ug_data['uc']
                ordem = i + 1
                todas_ucs.add(uc)
                
                # ========= NOVA ESTRUTURA: Adicionar à lista =========
                ug_geracao = {
                    'uc_geradora': uc,
                    'ordem': ordem,
                    'geracao_ciclo_ug': ug_data['total'],
                    'tipo': ug_data['tipo']
                }
                
                # Se Grupo A, adicionar dados por postos
                if ug_data['tipo'] == 'grupo_a':
                    ug_geracao.update({
                        'geracao_ciclo_p_ug': ug_data['p'],
                        'geracao_ciclo_fp_ug': ug_data['fp'], 
                        'geracao_ciclo_hr_ug': ug_data['hr']
                    })
                    total_p += ug_data['p']
                    total_fp += ug_data['fp']
                    total_hr += ug_data['hr']
                
                ugs_geracao.append(ug_geracao)
                total_geracao += ug_data['total']
                
                # ========= COMPATIBILIDADE: Manter campos _1 e _2 temporariamente =========
                if ordem <= 2:
                    self.dados[f'uc_geradora_{ordem}'] = uc
                    self.dados[f'geracao_ciclo_{ordem}'] = ug_data['total']
                    
                    if ug_data['tipo'] == 'grupo_a':
                        self.dados[f'geracao_ciclo_p_{ordem}'] = ug_data['p']
                        self.dados[f'geracao_ciclo_fp_{ordem}'] = ug_data['fp'] 
                        self.dados[f'geracao_ciclo_hr_{ordem}'] = ug_data['hr']
            
            # ========= TOTAIS GERAIS =========
            self.dados['geracao_ciclo'] = total_geracao
            if total_p > 0 or total_fp > 0 or total_hr > 0:
                self.dados['geracao_ciclo_p'] = total_p
                self.dados['geracao_ciclo_fp'] = total_fp
                self.dados['geracao_ciclo_hr'] = total_hr
            
            # ========= Salvar lista de UGs =========
            self.dados['_ugs_geracao_lista'] = ugs_geracao
            
            # Remover dados temporários
            del self.dados['_geracao_ugs_raw']
        
        # =========================================================================
        # 2. PROCESSAR EXCEDENTE RECEBIDO 
        # =========================================================================
        if '_excedente_ugs_raw' in self.dados:
            excedente_ugs = self.dados['_excedente_ugs_raw']
            
            for ug_data in excedente_ugs:
                uc = ug_data.get('uc')
                if uc:
                    todas_ucs.add(str(uc))
            
            # Ordenar por maior total de excedente
            excedente_ugs_ordenadas = sorted(
                excedente_ugs,
                key=lambda ug: ug['total'],
                reverse=True  # Maior excedente primeiro
            )
            
            # Manter consistência com UGs já definidas na geração
            ucs_ja_definidas = []
            for ug_num in [1, 2]:
                uc_existente = self.dados.get(f'uc_geradora_{ug_num}')
                if uc_existente:
                    ucs_ja_definidas.append(uc_existente)
            
            total_excedente = Decimal('0')
            total_p = Decimal('0')
            total_fp = Decimal('0')
            total_hr = Decimal('0')
            
            # Reordenar excedente para manter consistência com geração
            if ucs_ja_definidas:

                # Primeiro, processar UGs que já estão definidas
                for ug_num, uc_definida in enumerate(ucs_ja_definidas, 1):
                    # Encontrar dados dessa UC no excedente
                    ug_data = next((ug for ug in excedente_ugs if ug['uc'] == uc_definida), None)
                    if ug_data:
                        ordem = ug_num
                        
                        # ========= NOVA ESTRUTURA: Adicionar à lista =========
                        ug_excedente = {
                            'uc_geradora': uc_definida,
                            'ordem': ordem,
                            'excedente_recebido_ug': ug_data['total'],
                            'tipo': ug_data['tipo']
                        }
                        
                        if ug_data['tipo'] == 'grupo_a':
                            ug_excedente.update({
                                'excedente_recebido_p_ug': ug_data['p'],
                                'excedente_recebido_fp_ug': ug_data['fp'],
                                'excedente_recebido_hr_ug': ug_data['hr']
                            })
                            total_p += ug_data['p']
                            total_fp += ug_data['fp']
                            total_hr += ug_data['hr']
                        
                        ugs_excedentes.append(ug_excedente)
                        total_excedente += ug_data['total']
                        
                        # ========= COMPATIBILIDADE =========
                        self.dados[f'excedente_recebido_{ug_num}'] = ug_data['total']
                        
                        if ug_data['tipo'] == 'grupo_a':
                            self.dados[f'excedente_recebido_p_{ug_num}'] = ug_data['p']
                            self.dados[f'excedente_recebido_fp_{ug_num}'] = ug_data['fp']
                            self.dados[f'excedente_recebido_hr_{ug_num}'] = ug_data['hr']
                        
                
                # Depois, processar UGs novas (se houver espaço)
                ucs_processadas = set(ucs_ja_definidas)
                ug_num = len(ucs_ja_definidas) + 1
                
                for ug_data in excedente_ugs_ordenadas:
                    if ug_data['uc'] not in ucs_processadas and ug_num <= 2:
                        uc = ug_data['uc']
                        todas_ucs.add(uc)
                        self.dados[f'uc_geradora_{ug_num}'] = uc
                        
                        # ========= NOVA ESTRUTURA =========
                        ug_excedente = {
                            'uc_geradora': uc,
                            'ordem': ug_num,
                            'excedente_recebido_ug': ug_data['total'],
                            'tipo': ug_data['tipo']
                        }
                        
                        if ug_data['tipo'] == 'grupo_a':
                            ug_excedente.update({
                                'excedente_recebido_p_ug': ug_data['p'],
                                'excedente_recebido_fp_ug': ug_data['fp'],
                                'excedente_recebido_hr_ug': ug_data['hr']
                            })
                            total_p += ug_data['p']
                            total_fp += ug_data['fp']
                            total_hr += ug_data['hr']
                        
                        ugs_excedentes.append(ug_excedente)
                        total_excedente += ug_data['total']
                        
                        # ========= COMPATIBILIDADE =========
                        self.dados[f'excedente_recebido_{ug_num}'] = ug_data['total']
                        ug_num += 1
            else:
                # Se não há UGs definidas ainda, usar ordem por maior excedente
                for i, ug_data in enumerate(excedente_ugs_ordenadas[:2]):
                    uc = ug_data['uc']
                    ordem = i + 1
                    todas_ucs.add(uc)
                    
                    # ========= NOVA ESTRUTURA =========
                    ug_excedente = {
                        'uc_geradora': uc,
                        'ordem': ordem,
                        'excedente_recebido_ug': ug_data['total'],
                        'tipo': ug_data['tipo']
                    }
                    
                    if ug_data['tipo'] == 'grupo_a':
                        ug_excedente.update({
                            'excedente_recebido_p_ug': ug_data['p'],
                            'excedente_recebido_fp_ug': ug_data['fp'],
                            'excedente_recebido_hr_ug': ug_data['hr']
                        })
                        total_p += ug_data['p']
                        total_fp += ug_data['fp']
                        total_hr += ug_data['hr']
                    
                    ugs_excedentes.append(ug_excedente)
                    total_excedente += ug_data['total']
                    
                    # ========= COMPATIBILIDADE =========
                    self.dados[f'uc_geradora_{ordem}'] = uc
                    self.dados[f'excedente_recebido_{ordem}'] = ug_data['total']

            
            # ========= TOTAIS GERAIS =========
            self.dados['excedente_recebido'] = total_excedente
            if total_p > 0 or total_fp > 0 or total_hr > 0:
                self.dados['excedente_recebido_p'] = total_p
                self.dados['excedente_recebido_fp'] = total_fp
                self.dados['excedente_recebido_hr'] = total_hr
            
            # ========= NOVA ESTRUTURA: Salvar lista de UGs =========
            self.dados['_ugs_excedentes_lista'] = ugs_excedentes
            
            # Remover dados temporários
            del self.dados['_excedente_ugs_raw']
        
        # =========================================================================
        # 3. PROCESSAR ENERGIA INJETADA - NOVA ESTRUTURA
        # =========================================================================
        if '_energia_injetada_ugs_raw' in self.dados:
            injecao_ugs = self.dados['_energia_injetada_ugs_raw']
            
            # Debug: Verificar se as UCs foram corrigidas pelo fallback
            ucs_injecao = set()
            for item in injecao_ugs:
                uc = item.get('uc')
                if uc:
                    ucs_injecao.add(str(uc))
        
            
            # Agrupar por UC
            ugs_agrupadas = {}
            for item in injecao_ugs:
                uc = item['uc']
                if not uc:  # Se não tem UC, pular
                    continue
                    
                todas_ucs.add(uc)
                
                # Inicializar estrutura por UC
                if uc not in ugs_agrupadas:
                    ugs_agrupadas[uc] = {
                        'total_quantidade': Decimal('0'),
                        'total_valor': Decimal('0'),
                        'detalhes': []
                    }
                
                # Acumular valores por UC
                quantidade_item = item.get('quantidade', Decimal('0'))
                valor_item = abs(item.get('valor', Decimal('0')))  # Usar valor absoluto
                
                ugs_agrupadas[uc]['total_quantidade'] += quantidade_item
                ugs_agrupadas[uc]['total_valor'] += valor_item
                ugs_agrupadas[uc]['detalhes'].append(item)
            
            # Ordenar por MAIOR VALOR de injeção
            ucs_ordenadas = sorted(
                ugs_agrupadas.keys(), 
                key=lambda uc: ugs_agrupadas[uc]['total_valor'], 
                reverse=True  # Maior valor primeiro
            )

            total_quantidade_geral = Decimal('0')
            total_valor_geral = Decimal('0')
            
            # Processar cada UG ordenada
            for i, uc in enumerate(ucs_ordenadas):
                ordem = i + 1
                ug_data = ugs_agrupadas[uc]
                
                # ========= NOVA ESTRUTURA: Adicionar à lista =========
                ug_injecao = {
                    'uc_geradora': uc,
                    'ordem': ordem,
                    'energia_injetada_ug': ug_data['total_quantidade'],
                    'valor_energia_injetada_ug': ug_data['total_valor'],
                    'detalhes': ug_data['detalhes']  # Manter detalhes para análise
                }
                
                # Processar detalhes por grupo/posto
                detalhes_processados = {}
                for item in ug_data['detalhes']:
                    tipo_grupo = item.get('tipo', 'grupo_b')
                    posto = item.get('posto', 'unico')
                    componente = item.get('componente', 'geral')
                    
                    if tipo_grupo == 'grupo_a':
                        if componente and posto and componente in ['tusd', 'te']:
                            chave = f"energia_injetada_{componente}_{posto}_ug"
                            chave_valor = f"valor_energia_injetada_{componente}_{posto}_ug"
                        elif posto:
                            chave = f"energia_injetada_{posto}_ug"
                            chave_valor = f"valor_energia_injetada_{posto}_ug"
                        else:
                            continue
                    elif tipo_grupo == 'grupo_b':
                        if posto and posto != 'unico':
                            chave = f"energia_injetada_{posto}_ug"
                            chave_valor = f"valor_energia_injetada_{posto}_ug"
                        else:
                            continue  # Já contabilizado no total da UG
                    else:
                        continue
                    
                    # Acumular nos detalhes processados
                    if chave not in detalhes_processados:
                        detalhes_processados[chave] = Decimal('0')
                        detalhes_processados[chave_valor] = Decimal('0')
                    
                    detalhes_processados[chave] += item['quantidade']
                    detalhes_processados[chave_valor] += abs(item['valor'])
                
                # Adicionar detalhes processados à estrutura da UG
                ug_injecao.update(detalhes_processados)
                ugs_injecao.append(ug_injecao)
                
                total_quantidade_geral += ug_data['total_quantidade']
                total_valor_geral += ug_data['total_valor']
                
                # ========= COMPATIBILIDADE: Campos individuais =========
                if ordem <= 2:
                    self.dados[f'uc_geradora_{ordem}'] = uc
                    self.dados[f'energia_injetada_{ordem}'] = ug_data['total_quantidade']
                    self.dados[f'valor_energia_injetada_{ordem}'] = ug_data['total_valor']

                # Processar detalhes individuais para compatibilidade
                for item in ug_data['detalhes']:
                    tipo_grupo = item.get('tipo', 'grupo_b')
                    posto = item.get('posto', 'unico')
                    componente = item.get('componente', 'geral')
                    
                    if tipo_grupo == 'grupo_a':
                        if componente and posto and componente in ['tusd', 'te']:
                            campo_quant = f"energia_injetada_{componente}_{posto}_{ordem}"
                            campo_valor = f"valor_energia_injetada_{componente}_{posto}_{ordem}"
                            
                            current_quant = self.dados.get(campo_quant, Decimal('0'))
                            current_valor = self.dados.get(campo_valor, Decimal('0'))
                            
                            self.dados[campo_quant] = current_quant + item['quantidade']
                            self.dados[campo_valor] = current_valor + abs(item['valor'])
                        
                        elif posto:
                            campo_quant = f"energia_injetada_{posto}_{ordem}"
                            campo_valor = f"valor_energia_injetada_{posto}_{ordem}"
                            
                            current_quant = self.dados.get(campo_quant, Decimal('0'))
                            current_valor = self.dados.get(campo_valor, Decimal('0'))
                            
                            self.dados[campo_quant] = current_quant + item['quantidade']
                            self.dados[campo_valor] = current_valor + abs(item['valor'])
                    
                    elif tipo_grupo == 'grupo_b':
                        if posto and posto != 'unico':
                            campo_quant = f"energia_injetada_{posto}_{ordem}"
                            campo_valor = f"valor_energia_injetada_{posto}_{ordem}"
                            
                            current_quant = self.dados.get(campo_quant, Decimal('0'))
                            current_valor = self.dados.get(campo_valor, Decimal('0'))
                            
                            self.dados[campo_quant] = current_quant + item['quantidade']
                            self.dados[campo_valor] = current_valor + abs(item['valor'])
            
            # ========= TOTAIS GERAIS =========
            self.dados['energia_injetada'] = total_quantidade_geral
            self.dados['valor_energia_injetada'] = total_valor_geral
        
            # Calcular totais por posto para Grupo A e Grupo B Branca
            self._calcular_totais_por_posto(ugs_agrupadas)
            
            # ========= NOVA ESTRUTURA: Salvar lista de UGs =========
            self.dados['_ugs_injecao_lista'] = ugs_injecao

            # Remover dados temporários
            del self.dados['_energia_injetada_ugs_raw']
        
        # Verificar consistência final
        ug1 = self.dados.get('uc_geradora_1')
        ug2 = self.dados.get('uc_geradora_2')

        # ========= SALVAR LISTAS NA ESTRUTURA PRINCIPAL =========
        if ugs_geracao:
            self.dados['_ugs_geracao_lista'] = ugs_geracao
        if ugs_excedentes:
            self.dados['_ugs_excedentes_lista'] = ugs_excedentes
        if ugs_injecao:
            self.dados['_ugs_injecao_lista'] = ugs_injecao
    
    def _calcular_totais_energia_injetada(self, ugs_agrupadas: Dict) -> None:
        """Calcula totais de energia injetada somando todas as UGs"""
        
        # Verificar se é Grupo A ou B
        primeira_ug = next(iter(ugs_agrupadas.values()))
        eh_grupo_a = bool(primeira_ug['grupo_a'])
        
        if eh_grupo_a:
            # Grupo A - somar por componente e posto
            totais = {}
            
            for uc, ug_data in ugs_agrupadas.items():
                for chave, dados in ug_data['grupo_a'].items():
                    if chave not in totais:
                        totais[chave] = Decimal('0')
                    totais[chave] += dados['quantidade']
            
            # Salvar totais
            for chave, total in totais.items():
                posto, componente = chave.split('_')
                campo = f"energia_injetada_{componente}_{posto}"
                self.dados[campo] = total
        
        else:
            # Grupo B - somar por posto
            totais = {}
            
            for uc, ug_data in ugs_agrupadas.items():
                for posto, dados in ug_data['grupo_b'].items():
                    if posto not in totais:
                        totais[posto] = Decimal('0')
                    totais[posto] += dados['quantidade']
            
            # Salvar totais
            for posto, total in totais.items():
                if posto == 'total':
                    self.dados['energia_injetada'] = total
                else:
                    self.dados[f'energia_injetada_{posto}'] = total

    def _inferir_modalidade_tarifaria(self):
        """Infere a modalidade tarifária se não foi identificada diretamente"""
        if 'modalidade_tarifaria' not in self.dados and 'grupo' in self.dados:
            # Se não identificou modalidade mas tem grupo B, assumir convencional como padrão
            if self.dados['grupo'] == 'B':
                self.dados['modalidade_tarifaria'] = 'CONVENCIONAL'
            elif self.dados['grupo'] == 'A':
                # Para grupo A, tentar inferir baseado nos dados encontrados
                if any(key in self.dados for key in ['consumo_p_tusd', 'consumo_fp_tusd']):
                    # Se tem dados de TUSD/TE separados, provavelmente é VERDE
                    self.dados['modalidade_tarifaria'] = 'VERDE'
                else:
                    # Deixar como None se não conseguir determinar
                    pass
    
    def _validar_modalidade_tarifaria(self):
        """Valida a modalidade tarifária usando o TarifaValidator"""
        try:
            validator = TarifaValidator()
            validacao = validator.validar_modalidade(self.dados)
            
            # Atualizar modalidade se necessário
            if validacao['modalidade_validada'] and validacao['confianca'] in ['alta', 'média']:
                self.dados['modalidade_tarifaria'] = validacao['modalidade_validada']
                self.dados['modalidade_tarifaria_validacao'] = validacao
        except Exception as e:
            print(f"Erro na validação de modalidade: {e}")
    
    def _limpar_dados_inconsistentes(self):
        """Remove ou corrige dados inconsistentes - VERSÃO DECIMAL MELHORADA"""
        dados_limpos = {}
        for key, value in self.dados.items():
            if value is not None and value != "" and value != []:
                if isinstance(value, Decimal) and value == Decimal('0'):
                    # SEMPRE manter zeros para estes campos importantes
                    if key in ['saldo', 'saldo_30', 'saldo_60', 'excedente_recebido', 
                            'valor_juros', 'valor_multa', 'credito_recebido',
                            'geracao_ciclo', 'energia_injetada']:
                        dados_limpos[key] = value
                elif isinstance(value, (int, float)) and value == 0.0:
                    if key in ['saldo', 'saldo_30', 'saldo_60', 'excedente_recebido',
                            'valor_juros', 'valor_multa', 'credito_recebido',
                            'geracao_ciclo', 'energia_injetada']:
                        dados_limpos[key] = Decimal(str(value))
                else:
                    dados_limpos[key] = value
            else:
                # NOVO: Para campos críticos, definir Decimal('0') em vez de None
                if key in ['saldo', 'excedente_recebido'] and value is None:
                    dados_limpos[key] = Decimal('0')
                    print(f"    Campo {key} corrigido de None para Decimal('0')")
        
        self.dados = dados_limpos

    def to_json(self) -> str:
        """Converte os dados extraídos para JSON"""
        return json.dumps(self.dados, ensure_ascii=False, indent=2)
    
    def to_structured_data(self) -> FaturaCompleta:
        """Converte os dados extraídos para a estrutura FaturaCompleta - NOVA VERSÃO"""
        try:
            fatura = FaturaCompleta()
            
            # Mapear dados básicos
            for field in fatura.dados_basicos.__dataclass_fields__:
                if field in self.dados:
                    setattr(fatura.dados_basicos, field, self.dados[field])
            
            # Mapear impostos
            for field in fatura.impostos.__dataclass_fields__:
                if field in self.dados:
                    setattr(fatura.impostos, field, self.dados[field])
            
            # Mapear consumo baseado no grupo
            grupo = self.dados.get('grupo')
            if grupo == 'B':
                for field in fatura.consumo_b.__dataclass_fields__:
                    if field in self.dados:
                        setattr(fatura.consumo_b, field, self.dados[field])
            elif grupo == 'A':
                for field in fatura.consumo_a.__dataclass_fields__:
                    if field in self.dados:
                        setattr(fatura.consumo_a, field, self.dados[field])
            
            # ========= NOVA ESTRUTURA: Popular listas de UGs =========
            
            # 1. UGs de Geração
            if '_ugs_geracao_lista' in self.dados:
                fatura.geracao.ugs_geradoras = self.dados['_ugs_geracao_lista']

            # 2. UGs de Excedentes  
            if '_ugs_excedentes_lista' in self.dados:
                fatura.creditos.ugs_excedentes = self.dados['_ugs_excedentes_lista']
 
            # 3. UGs de Injeção
            if '_ugs_injecao_lista' in self.dados:
                fatura.energia_injetada.ugs_injecao = self.dados['_ugs_injecao_lista']
   
            # Mapear campos de geração (excluindo as listas)
            for field in fatura.geracao.__dataclass_fields__:
                if field != 'ugs_geradoras' and field in self.dados:
                    setattr(fatura.geracao, field, self.dados[field])
            
            # Mapear campos de créditos (excluindo as listas)
            for field in fatura.creditos.__dataclass_fields__:
                if field != 'ugs_excedentes' and field in self.dados:
                    setattr(fatura.creditos, field, self.dados[field])
            
            # Mapear campos de energia injetada (excluindo as listas)
            for field in fatura.energia_injetada.__dataclass_fields__:
                if field != 'ugs_injecao' and field in self.dados:
                    setattr(fatura.energia_injetada, field, self.dados[field])
            
            # Mapear financeiros
            for field in fatura.financeiros.__dataclass_fields__:
                if field in self.dados:
                    setattr(fatura.financeiros, field, self.dados[field])
            
            # Salvar dados brutos
            fatura.dados_brutos = self.dados.copy()
            
            return fatura
            
        except Exception as e:
            print(f"Erro ao converter para estrutura: {e}")
            # Retornar estrutura vazia em caso de erro
            fatura = FaturaCompleta()
            fatura.dados_brutos = self.dados.copy()
            return fatura
    
    def get_ugs_data(self) -> Dict[str, List[Dict]]:
        """Retorna dados estruturados das UGs para inserção no banco"""
        return {
            'ugs_geracao': self.dados.get('_ugs_geracao_lista', []),
            'ugs_excedentes': self.dados.get('_ugs_excedentes_lista', []), 
            'ugs_injecao': self.dados.get('_ugs_injecao_lista', [])
        }

    def get_totals_data(self) -> Dict[str, Any]:
        """Retorna apenas os totais para a tabela principal"""
        campos_totais = [
            # Dados básicos
            'uc', 'mes_referencia', 'vencimento', 'valor_concessionaria', 'grupo', 'subgrupo',
            'modalidade_tarifaria', 'tipo_fornecimento', 'classificacao', 'endereco',
            'cnpj_cpf', 'medidor', 'data_leitura', 'resolucao_homologatoria',
            
            # Totais de energia injetada
            'energia_injetada', 'valor_energia_injetada',
            'energia_injetada_p', 'energia_injetada_fp', 'energia_injetada_hr',
            'energia_injetada_hi', 'valor_energia_injetada_p', 'valor_energia_injetada_fp',
            'valor_energia_injetada_hr', 'valor_energia_injetada_hi',
            
            # Totais de excedentes e geração
            'excedente_recebido', 'excedente_recebido_p', 'excedente_recebido_fp', 'excedente_recebido_hr',
            'geracao_ciclo', 'geracao_ciclo_p', 'geracao_ciclo_fp', 'geracao_ciclo_hr',
            
            # Totais de consumo
            'consumo', 'consumo_p', 'consumo_fp', 'consumo_hr', 'consumo_hi',
            'valor_consumo', 'valor_consumo_p', 'valor_consumo_fp', 'valor_consumo_hr',
            
            # Saldos
            'saldo', 'saldo_30', 'saldo_60', 'saldo_p', 'saldo_fp', 'saldo_hr',
            
            # Impostos
            'valor_icms', 'valor_pis', 'valor_cofins', 'aliquota_icms', 'aliquota_pis', 'aliquota_cofins', 'base_icms', 'base_pis' 'base_cofins',
            
            # Financeiros
            'valor_iluminacao', 'valor_juros', 'valor_multa', 'valor_beneficio_bruto', 'valor_beneficio_liquido',
            
            # Irrigação
            'irrigante', 'desconto_irrigacao',
            
            # Bandeiras
            'bandeira'
        ]
        
        # Filtrar apenas campos que existem nos dados
        dados_filtrados = {}
        for campo in campos_totais:
            if campo in self.dados:
                dados_filtrados[campo] = self.dados[campo]
        
        return dados_filtrados

    def get_ugs_count(self) -> int:
        """Retorna o número total de UGs encontradas"""
        ugs_data = self.get_ugs_data()
        
        # Coletar todas as UCs únicas
        ucs_unicas = set()
        
        for categoria, ugs_list in ugs_data.items():
            for ug in ugs_list:
                uc = ug.get('uc_geradora')
                if uc:
                    ucs_unicas.add(uc)
        
        return len(ucs_unicas)

    def get_main_ug(self) -> Optional[str]:
        """Retorna a UC da UG principal (ordem 1)"""
        return self.dados.get('uc_geradora_1')

    def get_ugs_summary(self) -> Dict[str, Any]:
        """Retorna resumo das UGs para debug e relatórios"""
        ugs_data = self.get_ugs_data()
        
        summary = {
            'total_ugs': self.get_ugs_count(),
            'ug_principal': self.get_main_ug(),
            'tem_geracao': len(ugs_data['ugs_geracao']) > 0,
            'tem_excedentes': len(ugs_data['ugs_excedentes']) > 0,
            'tem_injecao': len(ugs_data['ugs_injecao']) > 0,
            'detalhes': {}
        }
        
        # Adicionar detalhes por categoria
        for categoria, ugs_list in ugs_data.items():
            if ugs_list:
                summary['detalhes'][categoria] = []
                for ug in ugs_list:
                    uc = ug.get('uc_geradora')
                    ordem = ug.get('ordem')
                    
                    if categoria == 'ugs_geracao':
                        valor = ug.get('geracao_ciclo_ug', 0)
                        summary['detalhes'][categoria].append(f"UG{ordem}: {uc} = {valor} kWh")
                    elif categoria == 'ugs_excedentes':
                        valor = ug.get('excedente_recebido_ug', 0)
                        summary['detalhes'][categoria].append(f"UG{ordem}: {uc} = {valor} kWh")
                    elif categoria == 'ugs_injecao':
                        valor = ug.get('energia_injetada_ug', 0)
                        summary['detalhes'][categoria].append(f"UG{ordem}: {uc} = {valor} kWh")
        
        return summary
    

class DemandaExtractor(BaseExtractor):
    """Extrator para demanda contratada - VERSÃO DECIMAL"""
    
    def extract(self, text: str, block_info: Dict) -> Dict[str, Any]:
        result = {}
        x0, y0 = block_info.get('x0', 0), block_info.get('y0', 0)
        
        # Demanda contratada
        if (650 <= x0 <= 880) and (450 <= y0 <= 500):
            if "DEMANDA" in text:
                parts = re.split(r"\s+", text)
                try:
                    index = parts.index("kW")
                    result["demanda_contratada"] = Decimal(parts[index + 1])
                except (ValueError, IndexError, TypeError):
                    pass
        
        return result


class GeracaoExtractor(BaseExtractor):
    """Extrator melhorado para geração de energia - VERSÃO DECIMAL"""
    
    def extract(self, text: str, block_info: Dict) -> Dict[str, Any]:
        result = {}
        x0, y0 = block_info.get('x0', 0), block_info.get('y0', 0)
        
        # Detectar se é UG
        if "ENERGIA GERAÇÃO - KWH" in text:
            result["ug"] = "sim"  # String não muda
            
            # Para GRUPO A - extrair por tipo (P, FP, HR)
            if "PONTA" in text and "FORA" not in text:
                parts = re.split(r"\s+", text)
                try:
                    valor_str = parts[-3].replace(',', '.').rstrip('.')
                    if re.match(r'^\d+\.?\d*$', valor_str):
                        # MUDANÇA: usar Decimal em vez de float
                        result["geracao_ciclo_p"] = Decimal(valor_str)
                except (ValueError, IndexError, TypeError):
                    pass
            
            elif "FORA PONTA" in text:
                parts = re.split(r"\s+", text)
                try:
                    valor_str = parts[-3].replace('.', '').replace(',', '.').rstrip('.')
                    if re.match(r'^\d+\.?\d*$', valor_str):
                        # MUDANÇA: usar Decimal em vez de float
                        result["geracao_ciclo_fp"] = Decimal(valor_str)
                except (ValueError, IndexError, TypeError):
                    pass
            
            elif "RESERVADO" in text:
                parts = re.split(r"\s+", text)
                try:
                    valor_str = parts[-3].replace('.', '').replace(',', '.').rstrip('.')
                    if re.match(r'^\d+\.?\d*$', valor_str):
                        # MUDANÇA: usar Decimal em vez de float
                        result["geracao_ciclo_hr"] = Decimal(valor_str)
                except (ValueError, IndexError, TypeError):
                    pass
            
            elif "ÚNICO" in text:
                parts = re.split(r"\s+", text)
                try:
                    valor_str = parts[-3].replace('.', '').replace(',', '.').rstrip('.')
                    if re.match(r'^\d+\.?\d*$', valor_str):
                        # MUDANÇA: usar Decimal em vez de float
                        result["geracao_ciclo"] = Decimal(valor_str)
                except (ValueError, IndexError, TypeError):
                    pass
        
        return result

# ================== CONSUMO EXTRACTOR HÍBRIDO ==================

class TipoLinha(Enum):
    """Tipos de linha identificados nas faturas"""
    CONSUMO = "consumo"
    INJECAO = "injecao"
    BANDEIRA = "bandeira"
    JUROS = "juros"
    MULTA = "multa"
    ILUMINACAO = "iluminacao"
    BENEFICIO = "beneficio"
    DEMANDA = "demanda"
    CREDITO = "credito"
    OUTROS = "outros"
    DESCONHECIDO = "desconhecido"

class ConsumoExtractor(BaseExtractor):
    """Extrator para dados de consumo e fornecimento - VERSÃO DECIMAL"""

    def __init__(self):
        super().__init__()

        # MUDANÇA: usar Decimal('0') em vez de 0.0
        self.juros_total = Decimal('0')
        self.multa_total = Decimal('0')
        self.creditos_total = Decimal('0')

        self.bandeira_codigo = 0  # 0=Verde, 1=Vermelha, 2=Amarela, 3=Vermelha+Amarela

        # MUDANÇA: Acumuladores para TUSD e TE por posto (Grupo A) - usar Decimal
        self.consumo_tusd: Dict[str, Decimal] = {}
        self.consumo_te: Dict[str, Decimal] = {}
        self.rs_tusd: Dict[str, Decimal] = {}
        self.rs_te: Dict[str, Decimal] = {}
        self.valor_tusd: Dict[str, Decimal] = {}
        self.valor_te: Dict[str, Decimal] = {}
        
        # MUDANÇA: Acumuladores para compensado/não compensado - usar Decimal
        self.consumo_comp: Dict[str, Decimal] = {}
        self.rs_consumo_comp: Dict[str, Decimal] = {}
        self.valor_consumo_comp: Dict[str, Decimal] = {}
        self.consumo_n_comp: Dict[str, Decimal] = {}
        self.rs_consumo_n_comp: Dict[str, Decimal] = {}
        self.valor_consumo_n_comp: Dict[str, Decimal] = {}

        # MUDANÇA: Acumuladores para consumo geral (Grupo B) - usar Decimal
        self.consumo_geral: Optional[Decimal] = None
        self.rs_consumo_geral: Optional[Decimal] = None
        self.valor_consumo_geral: Optional[Decimal] = None
        self.energia_injetada_registros: List[Dict] = []

    def extract(self, text: str, block_info: Dict, grupo: Optional[str] = None) -> Dict[str, Any]:
        """Implementa o método abstrato da BaseExtractor - VERSÃO COM DEBUG MELHORADO"""
        result = {}
        x0, y0 = block_info.get('x0', 0), block_info.get('y0', 0)
        
        parts = text.split()
        
        if not parts:
            return result
        
        if "JUROS" in text.upper() or "MULTA" in text.upper():
            print(f"DEBUG: FINANCEIRO detectado ANTES DA DELIMITACAO: x0={x0}, y0={y0}")
            print(f" Texto: {text}")
            print(f"DATA: Parts: {parts[:10]}")

        # Verificar área da tabela principal
        if not (30 <= x0 <= 650 and 350 <= y0 <= 755):
            return result
        
        if "JUROS" in text.upper() or "MULTA" in text.upper():
            print(f"DEBUG: FINANCEIRO detectado DEPOIS DA LIMITCAO: x0={x0}, y0={y0}")
            print(f" Texto: {text}")
            print(f"DATA: Parts: {parts[:10]}")

        parts = text.split()
        if not parts:
            return result
        
        # Identificar tipo de linha
        tipo_linha = self._identificar_tipo_linha(text)
        
        # VERIFICAÇÃO ADICIONAL: Se não identificou como injeção, verificar características
        if tipo_linha != TipoLinha.INJECAO and self._eh_linha_injecao(text, parts):
            tipo_linha = TipoLinha.INJECAO

        try:
            # Direcionar para o processador correto
            if tipo_linha == TipoLinha.CONSUMO:
                if grupo == "A":
                    self._processar_consumo_grupo_a(text, parts, result)
                elif grupo == "B":
                    self._processar_consumo_grupo_b(text, parts, result)
                    
            elif tipo_linha == TipoLinha.INJECAO:
                if grupo == "A":
                    self._processar_injecao_grupo_a(text, parts, result)
                elif grupo == "B":
                    self._processar_injecao_grupo_b(text, parts, result)
                    
            elif tipo_linha == TipoLinha.BANDEIRA:
                self._processar_bandeira(text, parts, result, grupo)
                
            elif tipo_linha == TipoLinha.DEMANDA:
                self._processar_demanda_tabela(text, parts, result, grupo)
                
            elif tipo_linha == TipoLinha.ILUMINACAO:
                self._processar_iluminacao(text, parts, result, grupo)
                
            elif tipo_linha == TipoLinha.JUROS:
                self._processar_juros(text, parts, result, grupo)
                
            elif tipo_linha == TipoLinha.MULTA:
                self._processar_multa(text, parts, result, grupo)
                
            elif tipo_linha == TipoLinha.BENEFICIO:
                self._processar_beneficio(text, parts, result, grupo)
                
            elif tipo_linha == TipoLinha.CREDITO:
                self._processar_creditos(text, parts, result, grupo)
                
            elif tipo_linha == TipoLinha.OUTROS:
                self._processar_outros(text, parts, result, grupo)
            
        except Exception as e:
            print(f"ERRO: ERRO ESPECÍFICO no tipo {tipo_linha}: {e}")
            print(f"ERRO: Texto: {text}")
            print(f"ERRO: Parts: {parts}")
            
        return result
    
    def _identificar_tipo_linha(self, text: str) -> TipoLinha:
        """Identifica o tipo de linha - TODAS AS VARIAÇÕES EQUATORIAL"""
        text_upper = text.upper()
        
        # PRIORIDADE 1: INJEÇÃO (primeiro para evitar confusão) - TODAS AS VARIAÇÕES
        if any(termo in text_upper for termo in [
            # Variações principais
            "ENERGIA INJETADA",
            "INJEÇÃO SCEE", 
            "INJECAO SCEE",
            "INJEÇÃO",
            "INJECAO",
            
            # Variações com GD (Geração Distribuída)
            "- GD I",
            "- GD II", 
            "- GD 1",
            "- GD 2",
            "- GD",
            "GD I",
            "GD II",
            
            # Outras variações possíveis
            "ENERGIA ATIVA INJETADA",
            "ENERGIA INJET",
            "INJECT",
            "COMPENSAÇÃO ATIVA",
            "CRÉDITO ENERGIA",
            "ENERGIA COMPENSADA",
            
            # Variações com sinal negativo (valores negativos)
            "ENERGIA ATIVA FORNECIDA" # quando tem valor negativo
        ]):
            # VERIFICAÇÃO ADICIONAL: Se tem "ENERGIA ATIVA FORNECIDA", verificar se é negativo
            if "ENERGIA ATIVA FORNECIDA" in text_upper:
                # Procurar por valores negativos na linha
                if "-" in text or any(part.startswith('-') for part in text.split()):
                    return TipoLinha.INJECAO
                else:
                    return TipoLinha.CONSUMO  # É consumo normal
            else:
                return TipoLinha.INJECAO
        
        # PRIORIDADE 2: CONSUMO (verificar se não é valor negativo)
        elif any(termo in text_upper for termo in [
            "CONSUMO",
            "ENERGIA ATIVA FORNECIDA", 
            "PARCELA TE",
            "PARC. TE"
        ]) and "kWh" in text:
            # VERIFICAÇÃO ESPECIAL: Se tem valores negativos, pode ser injeção
            if any(part.startswith('-') for part in text.split()) or "- " in text:
                # Verificar se realmente é valor negativo na coluna de valor
                parts = text.split()
                for i, part in enumerate(parts):
                    if part == "kWh" and i + 4 < len(parts):
                        valor_str = parts[i + 4]
                        if valor_str.startswith('-') or any(char in valor_str for char in ['-', '']):
                            return TipoLinha.INJECAO
                # Se chegou até aqui, é consumo normal
                return TipoLinha.CONSUMO
            else:
                return TipoLinha.CONSUMO
        
        # PRIORIDADE 3: BANDEIRAS
        elif "ADC BANDEIRA" in text_upper or "BANDEIRA" in text_upper or "AD. BAND" in text_upper:
            return TipoLinha.BANDEIRA
        
        elif "DEMANDA" in text_upper and "kW" in text:
            return TipoLinha.DEMANDA
        
        elif any(termo in text_upper for termo in [
            "ILUM",
            "ILUMINAÇÃO PÚBLICA",
            "CONTRIB. ILUM"
        ]):
            return TipoLinha.ILUMINACAO
        
        # NOVO: JUROS - múltiplos padrões
        elif any(termo in text_upper for termo in [
            "JUROS MORATÓRIA",
            "JUROS MORAT", 
            "JUROS MORA"
        ]):
            return TipoLinha.JUROS
        
        # NOVO: MULTA - múltiplos padrões
        elif any(termo in text_upper for termo in [
            "MULTA -",
            "MULTA.",
            "MULTA "
        ]) and any(char.isdigit() for char in text):
            return TipoLinha.MULTA
        
        elif any(termo in text_upper for termo in [
            "CRÉDITO DE CONSUMO",
            "COMPENSAÇÃO DE DIC",
            "BONUS ITAIPU",
            "BÔNUS ITAIPU"
        ]):
            return TipoLinha.CREDITO
        
        elif any(termo in text_upper for termo in [
            "UFER",
            "DMCR",
            "CORREÇÃO IPCA",
            "DUPLICIDADE DE PAGAMENTO",
            "DIFERENÇA DE DEMANDA",
            "PARC INJET S/DESC"
        ]):
            return TipoLinha.OUTROS
        
        return TipoLinha.DESCONHECIDO
    
    
    def _identificar_posto(self, text: str) -> Optional[str]:
        """Versão corrigida - verifica abreviações ANTES de termos completos"""
        text_upper = text.upper()
        
        # PRIMEIRO: Verificar abreviações isoladas (mais precisas)
        if re.search(r'\bFP\b', text_upper):
            return "fp"
        elif re.search(r'\bP\b', text_upper) and "PIS" not in text_upper:
            return "p"
        elif re.search(r'\bHI\b', text_upper):
            return "hi"
        elif re.search(r'\bHR\b', text_upper):
            return "hr"
        
        # DEPOIS: Verificar termos completos (fallback)
        elif "FORA PONTA" in text_upper:
            return "fp"
        elif "PONTA" in text_upper:
            return "p"
        elif "INTERMEDIARIO" in text_upper or "INTERMEDIÁRIO" in text_upper:
            return "hi"
        elif "HORA RESERVADA" in text_upper:
            return "hr"
        elif "ÚNICO" in text_upper or "UNICO" in text_upper:
            return "unico"
        
        return None

    def _identificar_componente_energia(self, text: str, parts: List[str] = None, kwh_index: int = None) -> Optional[str]:
        """Identifica se é TUSD ou TE com fallback inteligente."""
        text_upper = text.upper()
        
        # MÉTODO 1: Identificação direta por texto (mais confiável)
        if "TUSD" in text_upper:
            return "tusd"
        elif "TE" in text_upper and "PARC. TE" not in text_upper:  # Evitar confundir com "PARC. TE"
            return "te"
        elif "PARC. TE" in text_upper or "PARC TE" in text_upper:
            return "te"
        
        # MÉTODO 2: Fallback por análise de tarifa (baseado no código anterior)
        if parts and kwh_index is not None:
            try:
                # O código anterior usava índice +7 para a tarifa de referência
                if len(parts) > kwh_index + 7:
                    # MUDANÇA: usar Decimal em vez de float
                    tarifa_ref = Decimal(parts[kwh_index + 7].replace('.', '').replace(',', '.'))
                    
                    # Ranges típicos baseados nas tarifas da Resolução Homologatória
                    # MUDANÇA: usar Decimal para comparações
                    if Decimal('0.09') <= tarifa_ref <= Decimal('2.0'):  # Range típico TUSD (mais alto)
                        return "tusd"
                    elif Decimal('0.02') <= tarifa_ref <= Decimal('0.5'):  # Range típico TE (mais baixo)
                        return "te"
                
                # Fallback adicional: usar a própria tarifa principal (índice +1)
                if len(parts) > kwh_index + 1:
                    # MUDANÇA: usar Decimal em vez de float
                    tarifa_principal = Decimal(parts[kwh_index + 1].replace(',', '.'))
                    
                    # TUSD geralmente tem tarifas mais altas que TE
                    # MUDANÇA: usar Decimal para comparações
                    if tarifa_principal >= Decimal('0.5'):  # Provavelmente TUSD
                        return "tusd"
                    elif tarifa_principal <= Decimal('0.3'):  # Provavelmente TE
                        return "te"
                    
            except (ValueError, IndexError):
                pass
        
        # MÉTODO 3: Fallback por contexto da linha
        # Algumas distribuidoras podem usar termos diferentes
        if any(termo in text_upper for termo in ["DISTRIBUIÇÃO", "DISTRIBUI", "REDE"]):
            return "tusd"  # Relacionado à distribuição/rede
        elif any(termo in text_upper for termo in ["ENERGIA", "GERAÇÃO", "FORNECIMENTO"]):
            return "te"    # Relacionado à energia/geração
        
        # MÉTODO 4: Fallback por posição na fatura (heurística)
        # TUSD geralmente aparece antes de TE nas faturas
        # Este método seria implementado a nível superior, mantendo um contador
        
        return None  # Não conseguiu identificar

    def _find_correct_kwh_index(self, parts: List[str]) -> int:
        """
        Encontra o índice correto do kWh - VERSÃO MAIS ROBUSTA
        """
        kwh_indices = [i for i, part in enumerate(parts) if part == "kWh"]
        
        if len(kwh_indices) == 0:
            return -1
        elif len(kwh_indices) == 1:
            return kwh_indices[0]
        
        # Se há múltiplos kWh, encontrar o que tem valores numéricos após ele
        for kwh_idx in kwh_indices:
            # CORREÇÃO: Verificar se há pelo menos 5 elementos após o kWh (índice +4)
            if kwh_idx + 4 < len(parts):
                try:
                    # Tentar converter os próximos elementos
                    tarifa_str = parts[kwh_idx + 1].replace(',', '.')
                    quantidade_str = parts[kwh_idx + 2].replace('.', '').replace(',', '.')
                    
                    # CORREÇÃO: Usar safe_decimal_conversion
                    safe_decimal_conversion(tarifa_str, "kwh_validation_tarifa")
                    safe_decimal_conversion(quantidade_str, "kwh_validation_quantidade")
                    
                    return kwh_idx
                    
                except Exception:
                    continue
        
        # Fallback: retornar o último kWh encontrado
        return kwh_indices[-1] if kwh_indices else -1


    def _processar_consumo_grupo_a(self, text: str, parts: List[str], result: Dict[str, Any]) -> None:
        """Extrai dados de consumo para o Grupo A (TUSD/TE e postos) - SEM totalizações intermediárias."""
        try:           

            kwh_index = self._find_correct_kwh_index(parts)
            if kwh_index == -1:
                print(f"AVISO: Não encontrou kWh válido em: {text[:50]}...")
                return

            if kwh_index + 7 >= len(parts):
                print(f"AVISO: Índices insuficientes para capturar tarifa sem imposto: {text[:50]}...")
                # Ainda processa, mas sem tarifa sem imposto
                tarifa_sem_imposto = Decimal('0')
            else:
                tarifa_sem_imposto = Decimal(parts[kwh_index + 7].replace(',', '.'))

            componente = self._identificar_componente_energia(text, parts, kwh_index)
            if not componente:
                return

            posto = self._identificar_posto(text)
            if not posto:  # Grupo A geralmente sempre tem posto
                return
            
            # ÍNDICES CORRIGIDOS - MUDANÇA: usar Decimal em vez de float
            tarifa = Decimal(parts[kwh_index + 1].replace(',', '.'))
            tarifa_sem_imposto = Decimal(parts[kwh_index + 7].replace(',', '.'))
            quantidade = Decimal(parts[kwh_index + 2].replace('.', '').replace(',', '.'))
            valor = Decimal(parts[kwh_index + 4].replace(',', '.'))
            
            is_compensado = "SCEE" in text.upper()
            is_not_compensado = "NÃO COMPENSADO" in text.upper()

            # NOMENCLATURA CONFORME CÓDIGO ANTERIOR
            if is_compensado:
                rs_key = f"rs_consumo_comp_{posto}_{componente}"      # ex: rs_consumo_comp_fp_tusd
                quant_key = f"consumo_comp_{posto}_{componente}"      # ex: consumo_comp_fp_tusd
                valor_key = f"valor_consumo_comp_{posto}_{componente}"
            elif is_not_compensado:
                rs_key = f"rs_consumo_n_comp_{posto}_{componente}"    # ex: rs_consumo_n_comp_fp_tusd
                rs_si_key= f"rs_consumo_n_comp_si_{posto}_{componente}"
                quant_key = f"consumo_n_comp_{posto}_{componente}"    # ex: consumo_n_comp_fp_tusd
                valor_key = f"valor_consumo_n_comp_{posto}_{componente}"
                
            else:
                rs_key = f"rs_consumo_{posto}_{componente}"           # ex: rs_consumo_fp_tusd
                quant_key = f"consumo_{posto}_{componente}"           # ex: consumo_fp_tusd
                valor_key = f"valor_consumo_{posto}_{componente}"

            # OK: SALVAR APENAS OS DADOS ORIGINAIS (sem totalizações)
            # MUDANÇA: usar Decimal('0') em vez de 0.0
            result[rs_key] = tarifa
            if is_not_compensado:  # ADICIONAR: só salvar rs_si para não compensado
                result[rs_si_key] = tarifa_sem_imposto
            result[quant_key] = result.get(quant_key, Decimal('0')) + quantidade
            result[valor_key] = result.get(valor_key, Decimal('0')) + valor

            # OK: MANTER ACUMULADORES DA CLASSE (compatibilidade)
            # MUDANÇA: usar Decimal('0') em vez de 0.0
            if componente == "tusd":
                self.consumo_tusd[posto] = self.consumo_tusd.get(posto, Decimal('0')) + quantidade
                self.rs_tusd[posto] = tarifa
                self.valor_tusd[posto] = self.valor_tusd.get(posto, Decimal('0')) + valor
                
                if is_compensado:
                    chave_comp = f'{componente}_{posto}'
                    self.consumo_comp[chave_comp] = self.consumo_comp.get(chave_comp, Decimal('0')) + quantidade
                elif is_not_compensado:
                    chave_n_comp = f'{componente}_{posto}'
                    self.consumo_n_comp[chave_n_comp] = self.consumo_n_comp.get(chave_n_comp, Decimal('0')) + quantidade

            elif componente == "te":
                self.consumo_te[posto] = self.consumo_te.get(posto, Decimal('0')) + quantidade
                self.rs_te[posto] = tarifa
                self.valor_te[posto] = self.valor_te.get(posto, Decimal('0')) + valor
                
                if is_compensado:
                    chave_comp = f'{componente}_{posto}'
                    self.consumo_comp[chave_comp] = self.consumo_comp.get(chave_comp, Decimal('0')) + quantidade
                elif is_not_compensado:
                    chave_n_comp = f'{componente}_{posto}'
                    self.consumo_n_comp[chave_n_comp] = self.consumo_n_comp.get(chave_n_comp, Decimal('0')) + quantidade

            # ERRO: REMOVIDO: Todas as totalizações intermediárias que estavam aqui

        except (ValueError, IndexError) as e:
            print(f"ERRO na extração Grupo A: {e} - Texto: {text[:100]}")

    def _processar_consumo_grupo_b(self, text: str, parts: List[str], result: Dict[str, Any]) -> None:
        """Extrai dados de consumo para o Grupo B com totalização automática - VERSÃO CORRIGIDA"""
        try:
            kwh_index = self._find_correct_kwh_index(parts)
            if kwh_index == -1:
                print(f"AVISO: Não encontrou kWh válido em: {text[:50]}...")
                return
            
            # CORREÇÃO 1: Verificar se há índices suficientes para tarifa sem imposto
            if kwh_index + 7 >= len(parts):
                print(f"AVISO: Índices insuficientes para capturar tarifa sem imposto: {text[:50]}...")
                # Ainda processa, mas sem tarifa sem imposto
                tarifa_sem_imposto = Decimal('0')
            else:
                tarifa_sem_imposto = Decimal(parts[kwh_index + 7].replace(',', '.'))
            
            print("Tarifa sem imposto:",tarifa_sem_imposto)
            # Extrair valores básicos
            quantidade = Decimal(parts[kwh_index + 2].replace('.', '').replace(',', '.'))
            tarifa = Decimal(parts[kwh_index + 1].replace(',', '.'))
            valor = Decimal(parts[kwh_index + 4].replace(',', '.'))

            posto = self._identificar_posto(text)
            text_upper = text.upper()  #  CORREÇÃO: garantir que text_upper está definido
            
            # DEBUG: Imprimir o que foi encontrado
            print(f"DEBUG: CONSUMO B - Texto: {text[:80]}...")
            print(f"   DATA: Posto: {posto} | Quantidade: {quantidade} | Tarifa: {tarifa} | Valor: {valor}")
            
            if "NÃO COMPENSADO" in text_upper:
                # Consumo não compensado
                print(f"   OK: Identificado como NÃO COMPENSADO")
                if posto and posto != "unico":
                    chave_quant = f'consumo_n_comp_{posto}'
                    chave_valor = f'valor_consumo_n_comp_{posto}'
                    chave_rs_si = f'rs_consumo_n_comp_si_{posto}'  # TARIFA SEM IMPOSTO
                    
                    result[chave_quant] = result.get(chave_quant, Decimal('0')) + quantidade
                    result[f'rs_consumo_n_comp_{posto}'] = tarifa
                    result[chave_rs_si] = tarifa_sem_imposto  # ADICIONAR
                    result[chave_valor] = result.get(chave_valor, Decimal('0')) + valor
                else:
                    result['consumo_n_comp'] = result.get('consumo_n_comp', Decimal('0')) + quantidade
                    result['rs_consumo_n_comp'] = tarifa
                    result['rs_consumo_n_comp_si'] = tarifa_sem_imposto  # ADICIONAR
                    result['tarifa_comp'] = tarifa
                    result['valor_consumo_n_comp'] = result.get('valor_consumo_n_comp', Decimal('0')) + valor
                
                chave_acum = posto if posto else 'total'
                self.consumo_n_comp[chave_acum] = self.consumo_n_comp.get(chave_acum, Decimal('0')) + quantidade
                
            elif "SCEE" in text_upper:
                # Consumo SCEE (compensado)
                print(f"   OK: Identificado como SCEE (compensado)")
                if posto and posto != "unico":
                    chave_quant = f'consumo_comp_{posto}'
                    chave_valor = f'valor_consumo_comp_{posto}'
                    
                    result[chave_quant] = result.get(chave_quant, Decimal('0')) + quantidade
                    result[f'rs_consumo_comp_{posto}'] = tarifa
                    result[chave_valor] = result.get(chave_valor, Decimal('0')) + valor
                else:
                    result['consumo_comp'] = result.get('consumo_comp', Decimal('0')) + quantidade
                    result['rs_consumo_comp'] = tarifa
                    result['valor_consumo_comp'] = result.get('valor_consumo_comp', Decimal('0')) + valor
                
                chave_acum = posto if posto else 'total'
                self.consumo_comp[chave_acum] = self.consumo_comp.get(chave_acum, Decimal('0')) + quantidade
                
            else:
                # CORREÇÃO 2: Consumo geral (sem especificação de compensação)
                print(f"   OK: Identificado como CONSUMO GERAL")
                if posto and posto != "unico":
                    chave_quant = f'consumo_{posto}'
                    chave_valor = f'valor_consumo_{posto}'
                    
                    result[chave_quant] = result.get(chave_quant, Decimal('0')) + quantidade
                    result[f'rs_consumo_{posto}'] = tarifa
                    result[chave_valor] = result.get(chave_valor, Decimal('0')) + valor
                else:
                    # ESTE É O CASO MAIS COMUM PARA GRUPO B CONVENCIONAL
                    result['consumo'] = result.get('consumo', Decimal('0')) + quantidade
                    result['rs_consumo'] = tarifa
                    result['tarifa_comp'] = tarifa
                    result['valor_consumo'] = result.get('valor_consumo', Decimal('0')) + valor
                    print(f"    Salvando consumo geral: {quantidade} kWh")
                
                # Acumulador da classe
                self.consumo_geral = self.consumo_geral or Decimal('0')
                self.consumo_geral += quantidade
                self.rs_consumo_geral = tarifa
                self.valor_consumo_geral = self.valor_consumo_geral or Decimal('0')
                self.valor_consumo_geral += valor

            # ========= TOTALIZAÇÃO AUTOMÁTICA - GRUPO B =========
            # Só calcular totais se existir divisão compensado/não compensado
            if "SCEE" in text_upper or "NÃO COMPENSADO" in text_upper:
                if posto and posto != "unico":
                    # Para tarifa BRANCA com postos
                    comp_key = f'consumo_comp_{posto}'
                    n_comp_key = f'consumo_n_comp_{posto}'
                    total_key = f'consumo_{posto}'
                    
                    total_posto = result.get(comp_key, Decimal('0')) + result.get(n_comp_key, Decimal('0'))
                    if total_posto > Decimal('0'):
                        result[total_key] = total_posto
                        
                else:
                    # Para tarifa CONVENCIONAL
                    comp_total = result.get('consumo_comp', Decimal('0'))
                    n_comp_total = result.get('consumo_n_comp', Decimal('0'))
                    
                    if comp_total > Decimal('0') or n_comp_total > Decimal('0'):
                        result['consumo'] = comp_total + n_comp_total
            
        except (ValueError, IndexError) as e:
            print(f"ERRO na extração de consumo: {e} - Texto: {text[:100]}")

    def _finalizar_totalizacoes(self, result: Dict[str, Any]) -> None:
        """Finaliza totalizações - VERSÃO COM ENERGIA INJETADA E BANDEIRAS CORRIGIDA"""
        
        # Função auxiliar para converter para Decimal de forma segura
        def to_decimal(value):
            if isinstance(value, Decimal):
                return value
            try:
                return Decimal(str(value)) if value else Decimal('0')
            except:
                return Decimal('0')
        
        # ========= GRUPO B - TARIFA BRANCA =========
        postos_b = ['p', 'fp', 'hi']  # Mudança: 'hr' -> 'hi' para Grupo B
        
        for posto in postos_b:
            comp_key = f'consumo_comp_{posto}'
            n_comp_key = f'consumo_n_comp_{posto}'
            total_key = f'consumo_{posto}'  # OK: Variável principal
            
            # Se tem divisão compensado/não compensado, somar para o total
            if comp_key in result or n_comp_key in result:
                # CORREÇÃO: Converter para Decimal antes de somar
                comp_val = to_decimal(result.get(comp_key, 0))
                n_comp_val = to_decimal(result.get(n_comp_key, 0))
                total = comp_val + n_comp_val
                
                if total > Decimal('0'):
                    result[total_key] = total
        
        # ========= GRUPO A - MODALIDADE VERDE/AZUL =========
        # Para Grupo A, a quantidade física é a MESMA para TUSD e TE
        # Então pegamos apenas de UM componente (não somar!)
        
        postos_a = ['p', 'fp', 'hr']
        
        for posto in postos_a:
            total_posto = Decimal('0')
            
            # ESTRATÉGIA: Pegar a quantidade de qualquer componente (TUSD ou TE)
            # pois a quantidade física consumida é a mesma
            
            # Verificar TUSD primeiro
            comp_tusd = to_decimal(result.get(f'consumo_comp_{posto}_tusd', 0))
            n_comp_tusd = to_decimal(result.get(f'consumo_n_comp_{posto}_tusd', 0))
            normal_tusd = to_decimal(result.get(f'consumo_{posto}_tusd', 0))
            
            # Se tem dados de TUSD, usar eles
            if comp_tusd > 0 or n_comp_tusd > 0 or normal_tusd > 0:
                total_posto = comp_tusd + n_comp_tusd + normal_tusd
            else:
                # Senão, verificar TE
                comp_te = to_decimal(result.get(f'consumo_comp_{posto}_te', 0))
                n_comp_te = to_decimal(result.get(f'consumo_n_comp_{posto}_te', 0))
                normal_te = to_decimal(result.get(f'consumo_{posto}_te', 0))
                
                total_posto = comp_te + n_comp_te + normal_te
            
            # Salvar apenas na variável principal do posto
            if total_posto > Decimal('0'):
                result[f'consumo_{posto}'] = total_posto  
        
        # ========= GRUPO B - TARIFA CONVENCIONAL =========
        # Se tem compensado/não compensado mas não tem total geral
        if ('consumo_comp' in result or 'consumo_n_comp' in result):
            # CORREÇÃO: Converter para Decimal antes de somar
            comp_total = to_decimal(result.get('consumo_comp', 0))
            n_comp_total = to_decimal(result.get('consumo_n_comp', 0))
            total_geral = comp_total + n_comp_total
            
            if total_geral > Decimal('0'):
                result['consumo'] = total_geral  
        
        # 1. CONSUMO TOTAL (P + FP + HI)
        if 'consumo' not in result or result.get('consumo', Decimal('0')) == Decimal('0'):
            consumo_p = to_decimal(result.get('consumo_p', 0))
            consumo_fp = to_decimal(result.get('consumo_fp', 0))
            consumo_hi = to_decimal(result.get('consumo_hi', 0))
            
            if consumo_p > 0 or consumo_fp > 0 or consumo_hi > 0:
                result['consumo'] = consumo_p + consumo_fp + consumo_hi
                print(f"OK: Consumo total B Branca: {result['consumo']}")
        
        # 2. CONSUMO COMPENSADO TOTAL (consumo_comp_p + consumo_comp_fp + consumo_comp_hi)
        consumo_comp_p = to_decimal(result.get('consumo_comp_p', 0))
        consumo_comp_fp = to_decimal(result.get('consumo_comp_fp', 0))
        consumo_comp_hi = to_decimal(result.get('consumo_comp_hi', 0))

        if consumo_comp_p > 0 or consumo_comp_fp > 0 or consumo_comp_hi > 0:
            total_comp = consumo_comp_p + consumo_comp_fp + consumo_comp_hi
            result['consumo_comp'] = total_comp
            print(f"OK: Consumo compensado total B Branca: {total_comp}")

        # 3. CONSUMO NÃO COMPENSADO TOTAL (consumo_n_comp_p + consumo_n_comp_fp + consumo_n_comp_hi)
        consumo_n_comp_p = to_decimal(result.get('consumo_n_comp_p', 0))
        consumo_n_comp_fp = to_decimal(result.get('consumo_n_comp_fp', 0))
        consumo_n_comp_hi = to_decimal(result.get('consumo_n_comp_hi', 0))

        if consumo_n_comp_p > 0 or consumo_n_comp_fp > 0 or consumo_n_comp_hi > 0:
            total_n_comp = consumo_n_comp_p + consumo_n_comp_fp + consumo_n_comp_hi
            result['consumo_n_comp'] = total_n_comp
            print(f"OK: Consumo não compensado total B Branca: {total_n_comp}")
        
        self._finalizar_energia_injetada(result)
        result['bandeira'] = self.bandeira_codigo
        
        # ========= NOVO: CALCULAR VALOR TOTAL DAS BANDEIRAS =========
        valor_bandeira_total = Decimal('0')
        
        # Lista de todos os possíveis campos de valor de bandeira
        campos_bandeira = [
            # Bandeiras gerais (sem posto)
            'valor_adc_bandeira_amarela',
            'valor_adc_bandeira_vermelha', 
            
            # Bandeiras por posto (Grupo B - Tarifa Branca)
            'valor_adc_bandeira_amarela_p',
            'valor_adc_bandeira_amarela_fp', 
            'valor_adc_bandeira_amarela_hi',
            'valor_adc_bandeira_vermelha_p',
            'valor_adc_bandeira_vermelha_fp',
            'valor_adc_bandeira_vermelha_hi',
            
            # Bandeiras por posto (Grupo A)
            'valor_adc_bandeira_amarela_hr',
            'valor_adc_bandeira_vermelha_hr',
        ]
        
        # Somar todos os valores de bandeira encontrados
        for campo in campos_bandeira:
            if campo in result:
                valor = result[campo]
                if isinstance(valor, Decimal) and valor > Decimal('0'):
                    valor_bandeira_total += valor
                    print(f"    {campo}: R$ {valor}")
        
        # Salvar o total se houver valores
        if valor_bandeira_total > Decimal('0'):
            result['valor_bandeira'] = valor_bandeira_total
            print(f"OK: Valor TOTAL das bandeiras: R$ {valor_bandeira_total}")
        else:
            result['valor_bandeira'] = Decimal('0')
            print(f"LISTA: Nenhuma bandeira tarifária encontrada")
                
    def _eh_linha_injecao(self, text: str, parts: List[str]) -> bool:
        """Verifica se uma linha é de injeção baseado em características dos valores"""
        try:
            # Procurar índice do kWh
            kwh_index = self._find_correct_kwh_index(parts)
            if kwh_index == -1:
                return False
            
            # Verificar se há valor negativo na posição esperada
            if kwh_index + 4 < len(parts):
                valor_str = parts[kwh_index + 4]
                
                # Remover formatação e verificar sinal
                valor_limpo = valor_str.replace(',', '.').replace('R$', '').strip()
                
                # Se começa com sinal negativo ou tem sinal negativo
                if valor_limpo.startswith('-') or '' in valor_limpo:
                    return True
                
                # Verificar se o valor é negativo numericamente
                try:
                    valor_num = float(valor_limpo)
                    if valor_num < 0:
                        return True
                except:
                    pass
            
            # Verificar se há UC na linha (indicativo de injeção)
            if re.search(r'UC\s*\d{10,}', text):
                return True
            
            # Verificar padrões de GD
            if re.search(r'GD\s*[I1-9]', text.upper()):
                return True
                
            return False
            
        except Exception:
            return False

    
    def _extrair_uc_geradora(self, text: str, parts: List[str]) -> Optional[str]:
        """
        NOVA ESTRATÉGIA com ordem de prioridade:
        1 INJEÇÃO
        2 CADASTRO DE RATEIO  
        3 EXCEDENTE
        """
        
        # PRIORIDADE 1: INJEÇÃO - Verificar se é linha de injeção
        if any(termo in text.upper() for termo in [
            "ENERGIA INJETADA", "INJEÇÃO SCEE", "INJECAO SCEE", "- GD"
        ]):
            # PADRÃO 1: "UC 10014495510 - GD I"
            uc_match = re.search(r'UC\s*(\d{10,})\s*-\s*GD', text)
            if uc_match:
                print(f"   TARGET: UC geradora (INJEÇÃO-GD): {uc_match.group(1)}")
                return uc_match.group(1)
            
            # PADRÃO 2: "UC 10014495510"
            uc_match = re.search(r'UC\s*(\d{10,})', text)
            if uc_match:
                print(f"   TARGET: UC geradora (INJEÇÃO-UC): {uc_match.group(1)}")
                return uc_match.group(1)
        
        # PRIORIDADE 2: CADASTRO DE RATEIO
        if "CADASTRO RATEIO" in text.upper():
            uc_match = re.search(r'UC\s*(\d{10,})', text)
            if uc_match:
                print(f"   TARGET: UC geradora (RATEIO): {uc_match.group(1)}")
                return uc_match.group(1)
        
        # PRIORIDADE 3: EXCEDENTE RECEBIDO
        if "EXCEDENTE RECEBIDO" in text.upper():
            uc_match = re.search(r'UC\s*(\d{10,})', text)
            if uc_match:
                print(f"   TARGET: UC geradora (EXCEDENTE): {uc_match.group(1)}")
                return uc_match.group(1)
        
        # FALLBACK: Procurar números com 10+ dígitos
        numeros_longos = re.findall(r'\d{10,}', text)
        if numeros_longos:
            print(f"   TARGET: UC geradora (FALLBACK): {numeros_longos[0]}")
            return numeros_longos[0]
        
        return None

    def _processar_injecao_grupo_b(self, text: str, parts: List[str], result: Dict[str, Any]) -> None:
        """Processa injeção do Grupo B com identificação de UG - CORRIGIDO PARA USAR ACUMULADOR DA CLASSE"""
        try:
            kwh_index = self._find_correct_kwh_index(parts)
            if kwh_index == -1:
                return
            
            # Para Grupo B, extrair valores
            quantidade = abs(Decimal(parts[kwh_index + 2].replace('.', '').replace(',', '.')))
            tarifa = Decimal(parts[kwh_index + 1].replace(',', '.'))
            valor = abs(Decimal(parts[kwh_index + 4].replace(',', '.')))
            
            # Identificar posto (se houver)
            posto = self._identificar_posto(text)
            
            # CORREÇÃO: Extrair UG geradora - TODAS AS VARIAÇÕES
            uc_geradora = self._extrair_uc_geradora(text, parts)
            
            # CORREÇÃO PRINCIPAL: Salvar no acumulador da CLASSE
            registro = {
                'uc': uc_geradora,
                'posto': posto,
                'quantidade': quantidade,
                'tarifa': tarifa,
                'valor': valor,
                'tipo': 'grupo_b'
            }
            
            self.energia_injetada_registros.append(registro)
            
        except (ValueError, IndexError) as e:
            print(f"ERRO: ERRO injeção B: {e} - Texto: {text[:60]}...")

    def _processar_injecao_grupo_a(self, text: str, parts: List[str], result: Dict[str, Any]) -> None:
        """Processa injeção do Grupo A com identificação de UG - CORRIGIDO PARA USAR ACUMULADOR DA CLASSE"""
        try:
            
            kwh_index = self._find_correct_kwh_index(parts)
            if kwh_index == -1:
                print(f"AVISO: Não encontrou kWh válido em: {text[:50]}...")
                return
            
            # Identificar componente e posto
            componente = self._identificar_componente_energia(text, parts, kwh_index)
            posto = self._identificar_posto(text)
            
            if not componente:
                if "TUSD" in text.upper():
                    componente = "tusd"
                elif "TE" in text.upper():
                    componente = "te"
                else:
                    print(f"AVISO:  Não conseguiu identificar componente em injeção A: {text[:60]}...")
                    return
            
            if not posto:
                print(f"AVISO:  Não conseguiu identificar posto em injeção A: {text[:60]}...")
                return
            
            # Extrair valores
            tarifa = Decimal(parts[kwh_index + 1].replace(',', '.'))
            quantidade = Decimal(parts[kwh_index + 2].replace('.', '').replace(',', '.'))
            valor = abs(Decimal(parts[kwh_index + 4].replace(',', '.')))
            
            # CORREÇÃO: Extrair UG geradora - TODAS AS VARIAÇÕES
            uc_geradora = self._extrair_uc_geradora(text, parts)
        
            # CORREÇÃO PRINCIPAL: Salvar no acumulador da CLASSE
            registro = {
                'uc': uc_geradora,
                'componente': componente,
                'posto': posto,
                'quantidade': quantidade,
                'tarifa': tarifa,
                'valor': valor,
                'tipo': 'grupo_a'
            }
            
            self.energia_injetada_registros.append(registro)
        except (ValueError, IndexError) as e:
            print(f"ERRO: ERRO injeção A: {e} - Texto: {text[:60]}...")

    def _processar_demanda_tabela(self, text: str, parts: List[str], result: Dict[str, Any], grupo: Optional[str] = None) -> None:
        """Processa demanda da tabela principal (baseado no código antigo)"""
        try:
            if "kW" not in text:
                return
                
            kw_index = parts.index("kW")
            # MUDANÇA: usar Decimal em vez de float
            rs_value = Decimal(parts[kw_index + 1].replace(',', '.'))
            quant_value = Decimal(parts[kw_index + 2].replace(',', '.'))
            valor_value = Decimal(parts[kw_index + 4].replace(',', '.'))
            
            # Identificar tipo de demanda baseado no código antigo
            if len(parts) > 1:
                if parts[1] == 'kW':
                    result["rs_demanda_faturada"] = rs_value
                    result["demanda_faturada"] = quant_value
                    result["valor_demanda"] = valor_value
                elif parts[1] == 'ISENTO':
                    result["rs_demanda_isento_faturada"] = rs_value
                    result["demanda_isento_faturada"] = quant_value
                    result["valor_demanda_isento"] = valor_value
                elif parts[1] == 'GERAÇÃO':
                    result["rs_demanda_geracao"] = rs_value
                    result["demanda_geracao"] = quant_value
                    result["valor_demanda_geracao"] = valor_value
                elif parts[1] == 'ULTRAPASSAGEM':
                    result["rs_demanda_ultrapassagem"] = rs_value
                    result["demanda_ultrapassagem"] = quant_value
                    result["valor_demanda_ultrapassagem"] = valor_value
                elif parts[1] == 'ULTRA.':
                    result["rs_demanda_ultrapassagem_geracao"] = rs_value
                    result["demanda_ultrapassagem_geracao"] = quant_value
                    result["valor_demanda_ultra_geracao"] = valor_value
                    
        except (ValueError, IndexError) as e:
            print(f"ERRO: ERRO demanda: {e}")

    def _processar_iluminacao(self, text: str, parts: List[str], result: Dict[str, Any], grupo: Optional[str] = None) -> None:
        """Processa iluminação pública - VERSÃO CORRIGIDA"""
        try:
            for part in reversed(parts):
                # Verificar se a parte parece um número antes de tentar converter
                if re.search(r'\d', part):  # Tem pelo menos um dígito
                    try:
                        valor = safe_decimal_conversion(part, "iluminacao")
                        if valor > Decimal('0'):  # Só aceitar valores positivos
                            result['valor_iluminacao'] = result.get('valor_iluminacao', Decimal('0')) + valor
                            break
                    except Exception:
                        continue
        except Exception as e:
            print(f"ERRO: ERRO iluminação: {e}")
            
    def _processar_juros(self, text: str, parts: List[str], result: Dict[str, Any], grupo: Optional[str] = None) -> None:
        """Processa juros - VERSÃO EXPANDIDA COM MÚLTIPLOS PADRÕES"""
        try:
            # PADRÃO NOVO: "JUROS MORATÓRIA. 0,21"
            juros_pattern = r'JUROS\s*MORAT[ÓO]RIA\.?\s*([\d,]+)'
            juros_match = re.search(juros_pattern, text)
            if juros_match:
                valor = safe_decimal_conversion(juros_match.group(1), "juros")
                if valor > Decimal('0'):
                    self.juros_total += valor
                    result['valor_juros'] = self.juros_total
                    return
            
            valor_match = re.search(r'JUROS.*?([\d,]+)', text)
            if valor_match:
                valor = safe_decimal_conversion(valor_match.group(1), "juros")
                if valor > Decimal('0'):
                    self.juros_total += valor
                    result['valor_juros'] = self.juros_total
                    return
                
            # PADRÃO ANTIGO: Buscar após palavra JUROS
            for i, part in enumerate(parts):
                if "JUROS" in part.upper():
                    for j in range(i+1, len(parts)):
                        current_part = parts[j]
                        
                        if re.search(r'\d', current_part):
                            try:
                                valor = safe_decimal_conversion(current_part, "juros")
                                if valor > Decimal('0'):
                                    self.juros_total += valor
                                    result['valor_juros'] = self.juros_total
                                    return
                            except Exception:
                                continue
        except Exception as e:
            print(f"ERRO: ERRO juros: {e}")

    def _processar_multa(self, text: str, parts: List[str], result: Dict[str, Any], grupo: Optional[str] = None) -> None:
        """Processa multa - VERSÃO EXPANDIDA COM MÚLTIPLOS PADRÕES"""
        try:
            # PADRÃO NOVO: "MULTA - 06/2025. 2,06"
            multa_pattern = r'MULTA\s*(?:-\s*\d{2}/\d{4})?\.\s*([\d,]+)'
            multa_match = re.search(multa_pattern, text)
            if multa_match:
                valor = safe_decimal_conversion(multa_match.group(1), "multa")
                if valor > Decimal('0'):
                    self.multa_total += valor
                    result['valor_multa'] = self.multa_total
                    return
            
            valor_match = re.search(r'MULTA.*?([\d,]+)', text)
            if valor_match:
                valor = safe_decimal_conversion(valor_match.group(1), "multa")
                if valor > Decimal('0'):
                    self.multa_total += valor
                    result['valor_multa'] = self.multa_total
                    return
                
            # PADRÃO ANTIGO: Buscar após palavra MULTA
            for i, part in enumerate(parts):
                if "MULTA" in part.upper():
                    for j in range(i+1, len(parts)):
                        current_part = parts[j]
                        
                        if re.search(r'\d', current_part):
                            try:
                                valor = safe_decimal_conversion(current_part, "multa")
                                if valor > Decimal('0'):
                                    self.multa_total += valor
                                    result['valor_multa'] = self.multa_total
                                    return
                            except Exception:
                                continue
        except Exception as e:
            print(f"ERRO: ERRO multa: {e}")

    def _processar_beneficio(self, text: str, parts: List[str], result: Dict[str, Any], grupo: Optional[str] = None) -> None:
        """Processa benefício tarifário - VERSÃO CORRIGIDA"""
        try:
            if "BRUTO" in text.upper():
                for part in reversed(parts):
                    if re.search(r'\d', part):
                        try:
                            valor = safe_decimal_conversion(part, "beneficio_bruto")
                            if valor != Decimal('0'):  # Aceitar valores positivos ou negativos
                                result['valor_beneficio_bruto'] = valor
                                break
                        except Exception:
                            continue
                            
            elif "LÍQUIDO" in text.upper():
                for part in parts:
                    if re.search(r'\d', part):
                        try:
                            valor = safe_decimal_conversion(part, "beneficio_liquido")
                            if valor != Decimal('0'):  # Aceitar valores positivos ou negativos
                                result['valor_beneficio_liquido'] = valor
                                break
                        except Exception:
                            continue
        except Exception as e:
            print(f"ERRO: ERRO benefício: {e}")

    def _processar_creditos(self, text: str, parts: List[str], result: Dict[str, Any], grupo: Optional[str] = None) -> None:
        """Processa créditos diversos - VERSÃO CORRIGIDA"""
        try:
            for part in parts:
                # Verificar se tem sinal negativo ou parece um valor monetário
                if '-' in part or re.search(r'\d.*,\d{2}', part):
                    try:
                        valor = safe_decimal_conversion(part, "creditos")
                        if valor != Decimal('0'):  # Aceitar qualquer valor diferente de zero
                            if "DIC" in text.upper():
                                self.creditos_total += valor
                                result['valor_dic'] = self.creditos_total
                            elif "CRÉDITO" in text.upper() and "CONSUMO" in text.upper():
                                self.creditos_total += valor
                                result['valor_credito_consumo'] = self.creditos_total
                            elif any(termo in text.upper() for termo in ["BONUS", "BÔNUS"]):
                                result['valor_bonus_itaipu'] = valor
                            break
                    except Exception:
                        continue
        except Exception as e:
            print(f"ERRO: ERRO crédito: {e}")

    def _processar_outros(self, text: str, parts: List[str], result: Dict[str, Any], grupo: Optional[str] = None) -> None:
        """Processa UFER, DMCR e outros itens diversos (baseado no código antigo)"""
        text_upper = text.upper()
        
        def safe_decimal_conversion(value_str: str) -> Optional[Decimal]:
            """Converte string para Decimal de forma segura"""
            try:
                # Limpar a string de caracteres invisíveis e espaços
                cleaned = value_str.strip()
                # Remover caracteres não numéricos exceto vírgula, ponto e sinal negativo
                cleaned = re.sub(r'[^\d\.,\-]', '', cleaned)
                # Substituir vírgula por ponto para decimais
                cleaned = cleaned.replace('.', '').replace(',', '.')
                # Verificar se a string não está vazia após limpeza
                if not cleaned or cleaned in ['-', '.', '-.']:
                    return None
                return Decimal(cleaned)
            except (ValueError, TypeError, decimal.InvalidOperation):
                return None
        
        try:
            # ========== UFER ==========
            if "UFER" in text_upper and "kVArh" in text:
                tipo = self._identificar_posto(text)
                kvarh_index = parts.index("kVArh")
                
                rs_value = safe_decimal_conversion(parts[kvarh_index + 1])
                quant_value = safe_decimal_conversion(parts[kvarh_index + 2])
                valor_value = safe_decimal_conversion(parts[kvarh_index + 4])
                
                if rs_value is not None and quant_value is not None and valor_value is not None:
                    if tipo:
                        result[f"rs_ufer_{tipo}"] = rs_value
                        result[f"ufer_{tipo}"] = quant_value
                        result[f"valor_ufer_{tipo}"] = valor_value
                    else:
                        result["rs_ufer"] = rs_value
                        result["ufer"] = quant_value
                        result["valor_ufer"] = valor_value

            # ========== DMCR ==========
            elif "DMCR" in text_upper and "kVar" in text:
                kvar_index = parts.index("kVar")
                
                rs_value = safe_decimal_conversion(parts[kvar_index + 1])
                quant_value = safe_decimal_conversion(parts[kvar_index + 2])
                valor_value = safe_decimal_conversion(parts[kvar_index + 4])
                
                if rs_value is not None and quant_value is not None and valor_value is not None:
                    result["rs_dmcr"] = rs_value
                    result["dmcr"] = quant_value
                    result["valor_dmcr"] = valor_value

            # ========== DUPLICIDADE DE PAGAMENTO ==========
            elif "DUPLICIDADE DE PAGAMENTO" in text_upper:
                for part in parts:
                    value = safe_decimal_conversion(part)
                    if value is not None and value < Decimal('0'):  # Valores negativos (créditos)
                        result["valor_concessionaria_duplicada"] = value
                        break

            # ========== DIFERENÇA DE DEMANDA ==========
            elif "DIFERENÇA DE DEMANDA" in text_upper and "kW" in text:
                kw_index = parts.index("kW")
                
                rs_value = safe_decimal_conversion(parts[kw_index + 1])
                quant_value = safe_decimal_conversion(parts[kw_index + 2])
                valor_value = safe_decimal_conversion(parts[kw_index + 4])
                
                if rs_value is not None and quant_value is not None and valor_value is not None:
                    result["rs_dif_demanda"] = rs_value
                    result["dif_demanda"] = quant_value
                    result["valor_dif_demanda"] = valor_value

            # ========== PARC INJET S/DESC ==========
            elif "PARC INJET S/DESC" in text_upper and "kWh" in text:
                kwh_index = self._find_correct_kwh_index(parts)
                if kwh_index == -1:
                    return
                
                valor_parc_injet = safe_decimal_conversion(parts[kwh_index + 4])
                if valor_parc_injet is not None:
                    # Acumular valores (pode ter múltiplas linhas)
                    current_value = result.get("valor_parc_injet", Decimal('0'))
                    result["valor_parc_injet"] = current_value + valor_parc_injet

            # ========== CORREÇÃO IPCA ==========
            elif "CORREÇÃO IPCA" in text_upper:
                # Procurar pelo valor (geralmente no final)
                for part in reversed(parts):
                    valor = safe_decimal_conversion(part)
                    if valor is not None:
                        result["valor_correcao_ipca"] = valor
                        break

        except (ValueError, IndexError) as e:
            print(f"ERRO: ERRO outros: {e} - Texto: {text[:50]}")
        except Exception as e:
            print(f"ERRO: ERRO inesperado outros: {type(e).__name__}: {e} - Texto: {text[:50]}")

    def _adicionar_bandeira(self, cor_bandeira: str) -> None:
        """
        Adiciona bandeira ao código usando lógica de bits
        
        Códigos:
        - 0: Verde (sem bandeiras)
        - 1: Vermelha apenas (bit 0)
        - 2: Amarela apenas (bit 1) 
        - 3: Vermelha + Amarela (bits 0+1)
        """
        if cor_bandeira == "vermelha":
            self.bandeira_codigo |= 1  # Ativa bit 0
        elif cor_bandeira == "amarela":
            self.bandeira_codigo |= 2  # Ativa bit 1

    def _processar_bandeira(self, text: str, parts: List[str], result: Dict[str, Any], grupo: Optional[str] = None) -> None:
        """Processa bandeiras tarifárias - VERSÃO CORRIGIDA"""
        try:
  
            # VALIDAÇÃO: Verificar se realmente é uma linha de bandeira
            if not ("ADC BANDEIRA" in text.upper() or "BANDEIRA" in text.upper() or "AD. BAND" in text.upper()):
                return
                
            cor_bandeira = "amarela" if "AMARELA" in text else "vermelha" if "VERMELHA" in text else None
            if not cor_bandeira:
                print(f"AVISO: Bandeira sem cor identificada: {text[:50]}...")
                return
                
            kwh_index = self._find_correct_kwh_index(parts)
            
            if kwh_index == -1:
                print(f"AVISO: Não encontrou kWh válido em bandeira: {text[:50]}...")
                return
            
            # CORREÇÃO: Validar se existem índices suficientes
            if kwh_index + 4 >= len(parts):
                print(f"AVISO: Índices insuficientes para extrair valores da bandeira: {text[:50]}...")
                return
                
            # CORREÇÃO: Usar safe_decimal_conversion em vez de Decimal direto
            try:
                quantidade = safe_decimal_conversion(parts[kwh_index + 2].replace('.', '').replace(',', '.'), f"bandeira_{cor_bandeira}_quantidade")
                tarifa = safe_decimal_conversion(parts[kwh_index + 1].replace(',', '.'), f"bandeira_{cor_bandeira}_tarifa")
                valor = safe_decimal_conversion(parts[kwh_index + 4].replace(',', '.'), f"bandeira_{cor_bandeira}_valor")
            except Exception as e:
                print(f"AVISO: Erro ao converter valores da bandeira {cor_bandeira}: {e} - Texto: {text[:50]}...")
                return
            
            # VALIDAÇÃO: Só processar se quantidade > 0
            if quantidade <= Decimal('0'):
                print(f"AVISO: Bandeira {cor_bandeira} com quantidade zero, ignorando...")
                return
            
            # Registrar a bandeira no código
            self._adicionar_bandeira(cor_bandeira)
            
            posto = self._identificar_posto(text)
            
            if posto:
                result[f'adc_bandeira_{cor_bandeira}_{posto}'] = quantidade
                result[f'rs_adc_bandeira_{cor_bandeira}_{posto}'] = tarifa
                result[f'valor_adc_bandeira_{cor_bandeira}_{posto}'] = valor
            else:
                result[f'adc_bandeira_{cor_bandeira}'] = quantidade
                result[f'rs_adc_bandeira_{cor_bandeira}'] = tarifa
                result[f'valor_adc_bandeira_{cor_bandeira}'] = valor
            
        except (ValueError, IndexError) as e:
            print(f"ERRO: ERRO bandeira: {e} - Texto: {text[:50]}...")

    def _finalizar_energia_injetada(self, result: Dict[str, Any]) -> None:
        """Finaliza processamento de energia injetada com estratégia de fallback para UC"""
        
        if not self.energia_injetada_registros:
            return
        
        # ESTRATÉGIA DE FALLBACK PARA UCs GERADORAS
        registros_sem_uc = [r for r in self.energia_injetada_registros if not r.get('uc')]
        
        if registros_sem_uc:
            print(f"AVISO: {len(registros_sem_uc)} registros sem UC identificada")
            
            # FALLBACK 1: Buscar UC nos dados do SCEE (excedente/geração)
            ucs_do_scee = self._extrair_ucs_do_scee(result)
            
            if ucs_do_scee:
                
                # Se tem apenas 1 UC no SCEE, usar para todos os registros
                if len(ucs_do_scee) == 1:
                    uc_geradora = ucs_do_scee[0]
                    for registro in registros_sem_uc:
                        registro['uc'] = uc_geradora
                  
                # Se tem múltiplas UCs, usar a primeira
                else:
                    print(f" Múltiplas UCs encontradas, usando a primeira: {ucs_do_scee[0]}")
                    for registro in registros_sem_uc:
                        registro['uc'] = ucs_do_scee[0]
            
            # FALLBACK 2: Se não encontrou no SCEE, usar UC da própria fatura
            else:
                uc_fatura = result.get('uc')
                if uc_fatura:
                    print(f"LISTA: Usando UC da fatura como fallback: {uc_fatura}")
                    for registro in registros_sem_uc:
                        registro['uc'] = uc_fatura
                        print(f"   OK: UC {uc_fatura} atribuída como fallback")
                else:
                    print(f"ERRO: Não foi possível identificar UC geradora")
        
        # Preparar dados para pós-processamento
        result['_energia_injetada_ugs_raw'] = self.energia_injetada_registros.copy()

    def _extrair_ucs_do_scee(self, result: Dict[str, Any]) -> List[str]:
        """Extrai UCs geradoras dos dados do SCEE (excedente/geração)"""
        ucs_encontradas = []
        
        # MÉTODO 1: Buscar em dados brutos do SCEE
        for key in ['_geracao_ugs_raw', '_excedente_ugs_raw']:
            if key in result:
                dados_scee = result[key]
                if isinstance(dados_scee, list):
                    for item in dados_scee:
                        if isinstance(item, dict) and 'uc' in item:
                            uc = item['uc']
                            if uc and str(uc) not in ucs_encontradas:
                                ucs_encontradas.append(str(uc))
        
        # MÉTODO 2: Buscar em campos individuais já processados
        for key in ['uc_geradora', 'uc_geradora_1', 'uc_geradora_2']:
            if key in result and result[key]:
                uc = str(result[key])
                if uc not in ucs_encontradas:
                    ucs_encontradas.append(uc)
        
        # MÉTODO 3: Buscar campo 'rateio_fatura' que às vezes tem UC
        rateio = result.get('rateio_fatura', '')
        if rateio and 'UC' in str(rateio):
            uc_match = re.search(r'UC\s*(\d{10,})', str(rateio))
            if uc_match:
                uc = uc_match.group(1)
                if uc not in ucs_encontradas:
                    ucs_encontradas.append(uc)
        
        return ucs_encontradas
    

class TarifaValidator:
    """Validador de tarifas usando a Resolução Homologatória"""
    
    def __init__(self):
        # Tarifas da Resolução 3407/24 (exemplo parcial)
        self.tarifas_referencia = {
            'B1': {
                'BRANCA': {
                    'P': {'TE': 419.58, 'TUSD': 1084.15},
                    'INT': {'TE': 257.70, 'TUSD': 708.62},
                    'FP': {'TE': 257.70, 'TUSD': 333.09}
                },
                'CONVENCIONAL': {
                    'UNICO': {'TE': 271.19, 'TUSD': 474.74}
                }
            }
        }
    
    def validar_modalidade(self, dados_extraidos: Dict) -> Dict[str, Any]:
        """Valida e corrige a modalidade tarifária baseado nas tarifas encontradas"""
        resultado = {
            'modalidade_original': dados_extraidos.get('modalidade_tarifaria'),
            'modalidade_validada': None,
            'confianca': 'baixa',
            'evidencias': []
        }
        
        # Se não tem dados suficientes, retorna
        if not dados_extraidos.get('grupo'):
            return resultado
        
        # Para Grupo B, verificar evidências
        if dados_extraidos['grupo'] == 'B':
            evidencias_branca = []
            evidencias_convencional = []
            
            # Procurar por evidências de tarifa BRANCA
            # 1. Consumo dividido por postos horários
            if any(key in dados_extraidos for key in ['consumo_p', 'consumo_fp', 'consumo_hi', 'consumo_int']):
                evidencias_branca.append('Consumo dividido por postos horários')
            
            # 2. Leituras por posto horário
            if any(key in dados_extraidos for key in ['leitura_atual_energia_ativa_p', 'leitura_atual_energia_ativa_fp']):
                evidencias_branca.append('Leituras separadas por posto horário')
            
            # 3. Bandeiras tarifárias por posto
            if any(key in dados_extraidos for key in ['adc_bandeira_amarela_p', 'adc_bandeira_vermelha_p']):
                evidencias_branca.append('Bandeiras tarifárias por posto horário')
            
            # Procurar por evidências de tarifa CONVENCIONAL
            if 'consumo' in dados_extraidos and 'consumo_p' not in dados_extraidos:
                evidencias_convencional.append('Consumo único sem divisão horária')
            
            if 'leitura_atual_energia_ativa' in dados_extraidos:
                evidencias_convencional.append('Leitura única sem postos horários')
            
            # Determinar modalidade com base nas evidências
            if len(evidencias_branca) > len(evidencias_convencional):
                resultado['modalidade_validada'] = 'BRANCA'
                resultado['confianca'] = 'alta' if len(evidencias_branca) >= 2 else 'média'
                resultado['evidencias'] = evidencias_branca
            elif evidencias_convencional:
                resultado['modalidade_validada'] = 'CONVENCIONAL'
                resultado['confianca'] = 'alta' if len(evidencias_convencional) >= 2 else 'média'
                resultado['evidencias'] = evidencias_convencional
            else:
                # Usar a modalidade original se não há evidências claras
                resultado['modalidade_validada'] = dados_extraidos.get('modalidade_tarifaria', 'CONVENCIONAL')
                resultado['confianca'] = 'baixa'
        
        return resultado

class IrrigacaoExtractor(BaseExtractor):
    """Extrator específico para detectar irrigantes e seus descontos"""
    
    def extract(self, text: str, block_info: Dict) -> Dict[str, Any]:
        result = {}
        
        # Padrões para identificar irrigação - EXPANDIDOS
        padroes_irrigacao = [
            # Padrões com CONSUMO
            r'(CONSUMO.*?(?:HR|RESERVADO).*?(?:C/\s*DESC\.?\s*(\d+)%|DESC\.\s*(\d+)%))',
            r'(CONSUMO.*?(?:HORA\s*RESERVADA).*?(?:C/\s*DESC\.?\s*(\d+)%|DESC\.\s*(\d+)%))',
            
            # Padrões com PARCELA
            r'(PARCELA.*?(?:HR|RESERVADO).*?(?:C/\s*DESC\.?\s*(\d+)%|DESC\.\s*(\d+)%))',
            r'(PARC\..*?(?:HR|RESERVADO).*?(?:C/\s*DESC\.?\s*(\d+)%|DESC\.\s*(\d+)%))',
            
            # Padrões diretos com HR/RESERVADO
            r'((?:HR|RESERVADO).*?(?:C/\s*DESC\.?\s*(\d+)%|DESC\.\s*(\d+)%))',
            r'((?:HORA\s*RESERVADA).*?(?:C/\s*DESC\.?\s*(\d+)%|DESC\.\s*(\d+)%))',
            
            # Padrões com INJEÇÃO
            r'(INJEÇÃO.*?(?:HR|RESERVADO).*?(?:C/\s*DESC\.?\s*(\d+)%|DESC\.\s*(\d+)%))',
            r'(ENERGIA\s*INJETADA.*?(?:HR|RESERVADO).*?(?:C/\s*DESC\.?\s*(\d+)%|DESC\.\s*(\d+)%))',
            
            # Padrões alternativos (sem HR/RESERVADO)
            r'(IRRIGAÇÃO.*?(?:C/\s*DESC\.?\s*(\d+)%|DESC\.\s*(\d+)%))',
            r'(IRRIGACAO.*?(?:C/\s*DESC\.?\s*(\d+)%|DESC\.\s*(\d+)%))',
            
            # Padrões genéricos com desconto alto (provavelmente irrigação)
            r'((?:C/\s*DESC\.?\s*|DESC\.\s*)((?:80|85|90|70|75)%))',
        ]
        
        # Verificar se há desconto de irrigação no texto
        for padrao in padroes_irrigacao:
            matches = re.finditer(padrao, text, re.IGNORECASE)
            for match in matches:
                # Extrair o valor do desconto (pode estar no grupo 2, 3 ou 4)
                desconto = None
                
                # Verificar todos os grupos capturados
                for i in range(2, len(match.groups()) + 1):
                    if match.group(i) and match.group(i).replace('%', '').isdigit():
                        desconto = match.group(i).replace('%', '')
                        break
                
                if desconto:
                    # Validar se é realmente um desconto de irrigação (geralmente >= 60%)
                    try:
                        valor_desconto = int(desconto)
                        if valor_desconto >= 60:  # Descontos de irrigação são tipicamente altos
                            result['irrigante'] = "Sim"
                            result['desconto_irrigacao'] = f"{desconto}%"
                            
                            return result
                    except ValueError:
                        continue
        
        # Verificação adicional: buscar padrões de irrigação menos específicos
        text_upper = text.upper()
        
        # Padrões alternativos sem regex complexo
        if any(termo in text_upper for termo in ['IRRIGAÇÃO', 'IRRIGACAO', 'IRRIGANTE']):
            # Procurar por percentuais altos na mesma linha
            percentuais = re.findall(r'(\d+)%', text)
            for perc in percentuais:
                if int(perc) >= 60:
                    result['irrigante'] = "Sim"
                    result['desconto_irrigacao'] = f"{perc}%"
                    return result
        
        # Verificação por desconto alto em HR/RESERVADO (sem palavra irrigação)
        if any(termo in text_upper for termo in ['HR ', 'RESERVADO', 'HORA RESERVADA']):
            # Procurar por C/ DESC ou DESC. seguido de percentual alto
            desc_matches = re.findall(r'(?:C/\s*DESC\.?\s*|DESC\.\s*)(\d+)%', text, re.IGNORECASE)
            for desc in desc_matches:
                if int(desc) >= 70:  # Percentual ainda mais alto para ter certeza
                    result['irrigante'] = "Sim"
                    result['desconto_irrigacao'] = f"{desc}%"
                    return result
        
        # Se não encontrou desconto, não é irrigante
        result['irrigante'] = "Não"
        result['desconto_irrigacao'] = "0%"
        
        return result

def extract_values_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """Função principal para manter compatibilidade com código existente"""
    processor = FaturaProcessor()
    dados = processor.processar_fatura(pdf_path)
    
    # Validar modalidade tarifária
    validator = TarifaValidator()
    validacao = validator.validar_modalidade(dados)
    
    # Atualizar modalidade se necessário
    if validacao['modalidade_validada'] and validacao['confianca'] in ['alta', 'média']:
        dados['modalidade_tarifaria'] = validacao['modalidade_validada']
        dados['modalidade_tarifaria_validacao'] = validacao
    
    return dados


