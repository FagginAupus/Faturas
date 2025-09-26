import sys
from decimal import Decimal
from typing import Dict, Any, Optional

class CalculadoraAUPUS:
    """
    Classe responsável APENAS pelos cálculos específicos da AUPUS
    Todas as totalizações e finalizações ficam no Leitor de PDFs
    """
    
    def __init__(self):
        """Inicializa a calculadora com parâmetros padrão da AUPUS"""   
        
        # Flag para debug/logs
        self.debug = True
        
        # Descontos padrão AUPUS
        self.desconto_fatura_padrao = Decimal('0.05')    # 5%
        self.desconto_bandeira_padrao = Decimal('0.05')  # 5%
    
    def calcular_valores_aupus(self, dados_extraidos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Método principal - calcula APENAS os valores AUPUS
        
        Args:
            dados_extraidos: Dicionário com dados FINALIZADOS do Leitor
            
        Returns:
            Dicionário atualizado APENAS com os cálculos AUPUS
        """
        try:
            # Fazer cópia para não modificar o original
            dados = dados_extraidos.copy()
            
            # Identificar características da fatura
            grupo = dados.get("grupo", "")
            modalidade = dados.get("modalidade_tarifaria", "")
            tipo_fornecimento = dados.get("tipo_fornecimento", "")
            modo_calc = dados.get("modo_calc", 0)  # 0 = com imposto, 1 = sem imposto
            
            if self.debug:
                print(f"\n{'='*60}")
                print(f"🧮 CALCULADORA AUPUS - INICIANDO")
                print(f"📊 {grupo} {modalidade} | {tipo_fornecimento}")
                print(f"⚙️ Modo: {'SEM imposto' if modo_calc == 1 else 'COM imposto'}")
                print(f"{'='*60}")
            
            # ETAPA 1: Verificar se há compensação SCEE
            tem_compensacao = self._tem_compensacao_scee(dados)
            
            if not tem_compensacao:
                if self.debug:
                    print("⚠️ Fatura sem compensação SCEE")
                
                # ✅ CORRIGIDO: Aplicar compensação completa usando a MESMA função
                dados = self._aplicar_compensacao_completa(dados, criar_do_zero=True)
                
                # Re-verificar compensação
                tem_compensacao = self._tem_compensacao_scee(dados)
                if not tem_compensacao:
                    if self.debug:
                        print("⏭️ Fatura sem compensação SCEE - sem cálculos AUPUS")
                    return dados
                else:
                    if self.debug:
                        print("✅ Compensação completa criada - prosseguindo com AUPUS")
            
            # ETAPA 2: Aplicar compensação completa adicional se necessário (para quem já tinha compensação)
            elif self._to_decimal(dados.get("consumo_n_comp", 0)) > 0:
                dados = self._aplicar_compensacao_completa(dados, criar_do_zero=False)
            
            # ETAPA 3: Obter quantidade SCEE (já calculada pelo Leitor)
            quant_scee = self._obter_quantidade_scee(dados)
            if quant_scee <= 0:
                if self.debug:
                    print("⚠️ Quantidade SCEE zerada")
                return dados
            
            # ETAPA 4: Obter tarifa de compensação
            tarifa_comp = self._obter_tarifa_compensacao(dados, modo_calc)
            if tarifa_comp <= 0:
                if self.debug:
                    print("⚠️ Tarifa de compensação não encontrada")
                return dados
            
            # ETAPA 5: Obter impostos (já extraídos pelo Leitor)
            impostos = self._obter_impostos(dados)
            
            # ETAPA 6: Obter bandeiras (já totalizadas pelo Leitor)
            bandeiras = self._obter_bandeiras(dados)
            
            # ETAPA 7: Obter descontos (planilha ou padrão)
            descontos = self._obter_descontos(dados)
            
            # ETAPA 8: Calcular valores AUPUS
            resultados_aupus = self._calcular_aupus(
                quant_scee, tarifa_comp, impostos, bandeiras, descontos, dados
            )
            
            # ETAPA 9: Adicionar resultados aos dados originais
            dados.update(resultados_aupus)
            
            # ETAPA 10: Relatório final
            if self.debug:
                self._imprimir_relatorio(dados, quant_scee, tarifa_comp)
            
            return dados
            
        except Exception as e:
            print(f"❌ ERRO na Calculadora AUPUS: {e}")
            import traceback
            traceback.print_exc()
            return dados_extraidos
    
    def _tem_compensacao_scee(self, dados: Dict[str, Any]) -> bool:
        """Verifica se há compensação SCEE (dados já finalizados pelo Leitor)"""
        # O Leitor já calculou os totais
        return (
            self._to_decimal(dados.get("consumo_comp", 0)) > 0 or
            self._to_decimal(dados.get("energia_injetada", 0)) > 0 or
            any(self._to_decimal(dados.get(f"consumo_comp_{posto}", 0)) > 0 
                for posto in ['p', 'fp', 'hi']) or
            any(self._to_decimal(dados.get(f"energia_injetada_{posto}", 0)) > 0 
                for posto in ['p', 'fp', 'hi', 'hr'])
        )
    
    def _aplicar_compensacao_completa(self, dados: Dict[str, Any], criar_do_zero: bool = False) -> Dict[str, Any]:
        """
        ✅ FUNÇÃO UNIFICADA: Aplica compensação completa
        
        Args:
            dados: Dados da fatura
            criar_do_zero: True = criar compensação do zero, False = ajustar existente
        """
        try:
            if criar_do_zero:
                # ========== MODO: CRIAR COMPENSAÇÃO DO ZERO ==========
                consumo_total = self._to_decimal(dados.get("consumo", 0))
                tipo_fornecimento = dados.get("tipo_fornecimento", "")
                
                if consumo_total <= 0:
                    if self.debug:
                        print("⚠️ Consumo total zerado, não é possível criar compensação")
                    return dados
                
                tarifa_minima = self._obter_tarifa_minima(tipo_fornecimento)
                
                if consumo_total > tarifa_minima:
                    economia_estimada = self._calcular_economia_estimada_criar(
                        dados, consumo_total, tarifa_minima
                    )
                    
                    if self._perguntar_compensacao_completa_criar(
                        consumo_total, tarifa_minima, economia_estimada
                    ):
                        # Criar estrutura de compensação
                        novo_n_comp = tarifa_minima
                        novo_comp = consumo_total - novo_n_comp
                        
                        dados["consumo_n_comp"] = novo_n_comp
                        dados["consumo_comp"] = novo_comp
                        
                        # Copiar tarifas
                        rs_consumo_n_comp = self._to_decimal(dados.get("rs_consumo_n_comp", 0))
                    
                        # Recalcular valores
                        self._recalcular_valores_consumo(dados, consumo_total, novo_n_comp, rs_consumo_n_comp)
                        
                        # Recalcular bandeiras
                        diferenca_bandeiras = self._recalcular_bandeiras_compensacao_completa(
                            dados, consumo_total, novo_n_comp
                        )
                        
                        # Ajustar valor da fatura
                        if diferenca_bandeiras > 0:
                            valor_atual = self._to_decimal(dados.get("valor_concessionaria", 0))
                            dados["valor_concessionaria"] = valor_atual - diferenca_bandeiras
                        
                        if self.debug:
                            print(f"✅ Compensação criada do zero:")
                            print(f"   • Consumo total: {consumo_total} kWh")
                            print(f"   • Não compensado: {novo_n_comp} kWh")
                            print(f"   • SCEE: {novo_comp} kWh")
            else:
                # ========== MODO: AJUSTAR COMPENSAÇÃO EXISTENTE ==========
                consumo_n_comp = self._to_decimal(dados.get("consumo_n_comp", 0))
                consumo_comp = self._to_decimal(dados.get("consumo_comp", 0))
                tipo_fornecimento = dados.get("tipo_fornecimento", "")
                
                tarifa_minima = self._obter_tarifa_minima(tipo_fornecimento)
                consumo_total = consumo_n_comp + consumo_comp
                
                if (consumo_n_comp != tarifa_minima and 
                    consumo_total > tarifa_minima and 
                    consumo_n_comp > tarifa_minima):
                    
                    economia_estimada = self._calcular_economia_estimada_ajustar(
                        dados, consumo_n_comp, tarifa_minima
                    )
                    
                    if self._perguntar_compensacao_completa_ajustar(
                        consumo_n_comp, consumo_comp, tarifa_minima, economia_estimada
                    ):
                        # Aplicar compensação completa
                        novo_n_comp = tarifa_minima
                        novo_comp = consumo_total - novo_n_comp
                        
                        dados["consumo_n_comp"] = novo_n_comp
                        dados["consumo_comp"] = novo_comp
                        
                        # Recalcular valor da fatura de consumo
                        if "rs_consumo_n_comp" in dados:
                            rs_n_comp = self._to_decimal(dados["rs_consumo_n_comp"])
                            self._recalcular_valores_consumo(dados, consumo_n_comp, novo_n_comp, rs_n_comp)
                        
                        # Recalcular bandeiras
                        diferenca_bandeiras = self._recalcular_bandeiras_compensacao_completa(
                            dados, consumo_n_comp, novo_n_comp
                        )
                        
                        # Ajustar valor da fatura
                        if diferenca_bandeiras > 0:
                            valor_atual = self._to_decimal(dados.get("valor_concessionaria", 0))
                            dados["valor_concessionaria"] = valor_atual - diferenca_bandeiras
                        
                        if self.debug:
                            print(f"✅ Compensação ajustada:")
                            print(f"   • Não compensado: {consumo_n_comp} → {novo_n_comp} kWh")
                            print(f"   • SCEE: {consumo_comp} → {novo_comp} kWh")
            
            return dados
            
        except Exception as e:
            if self.debug:
                print(f"⚠️ Erro na compensação completa: {e}")
            return dados
    
    def _recalcular_valores_consumo(self, dados: Dict[str, Any], consumo_antigo: Decimal, 
                                   consumo_novo: Decimal, rs_tarifa: Decimal) -> None:
        """Recalcula valores de consumo após compensação"""
        if rs_tarifa > 0 and "valor_concessionaria" in dados:
            valor_concessionaria_atual = self._to_decimal(dados["valor_concessionaria"])
            valor_antigo = consumo_antigo * rs_tarifa
            valor_novo = consumo_novo * rs_tarifa
            diferenca = valor_antigo - valor_novo
            
            dados["valor_consumo_n_comp"] = valor_novo
            dados["valor_concessionaria"] = valor_concessionaria_atual - diferenca
    
    def _calcular_economia_estimada_criar(self, dados: Dict[str, Any], 
                                        consumo_total: Decimal, tarifa_minima: Decimal) -> Decimal:
        """Calcula economia para criação de compensação"""
        rs_consumo = self._to_decimal(dados.get("rs_consumo", 0))
        if rs_consumo > 0:
            economia_consumo = (consumo_total - tarifa_minima) * rs_consumo
            economia_bandeiras = self._calcular_economia_bandeiras_estimada(
                dados, consumo_total, tarifa_minima
            )
            return economia_consumo + economia_bandeiras
        return Decimal('0')
    
    def _calcular_economia_estimada_ajustar(self, dados: Dict[str, Any], 
                                          consumo_atual: Decimal, tarifa_minima: Decimal) -> Decimal:
        """Calcula economia para ajuste de compensação existente"""
        rs_n_comp = self._to_decimal(dados.get("rs_consumo_n_comp", 0))
        if rs_n_comp > 0:
            economia_consumo = (consumo_atual - tarifa_minima) * rs_n_comp
            economia_bandeiras = self._calcular_economia_bandeiras_estimada(
                dados, consumo_atual, tarifa_minima
            )
            return economia_consumo + economia_bandeiras
        return Decimal('0')
    
    def _calcular_economia_bandeiras_estimada(self, dados: Dict[str, Any],
                                            consumo_atual: Decimal, consumo_novo: Decimal) -> Decimal:
        """Calcula economia estimada das bandeiras"""
        economia_total = Decimal('0')
        
        try:
            for posto in ['p', 'fp', 'hi', 'hr', '']:
                sufixo = f"_{posto}" if posto else ""
                
                rs_amarela = self._to_decimal(dados.get(f"rs_adc_bandeira_amarela{sufixo}", 0))
                rs_vermelha = self._to_decimal(dados.get(f"rs_adc_bandeira_vermelha{sufixo}", 0))
                
                if rs_amarela > 0:
                    economia_total += (consumo_atual - consumo_novo) * rs_amarela
                
                if rs_vermelha > 0:
                    economia_total += (consumo_atual - consumo_novo) * rs_vermelha
                
                if rs_amarela > 0 or rs_vermelha > 0:
                    break
            
        except Exception:
            pass
        
        return economia_total
    
    def _perguntar_compensacao_completa_criar(self, consumo_total: Decimal, 
                                            tarifa_minima: Decimal, economia: Decimal) -> bool:
        """Pergunta sobre criação de compensação"""
        novo_comp = consumo_total - tarifa_minima
        
        print(f"\n{'='*60}")
        print(f"⚡ COMPENSAÇÃO COMPLETA DISPONÍVEL (Criar do zero)")
        print(f"{'='*60}")
        print(f"📊 Situação atual:")
        print(f"   • Consumo total: {consumo_total} kWh")
        print(f"   • Compensação SCEE: 0 kWh")
        print(f"\n🎯 Após criar compensação completa:")
        print(f"   • Não compensado: {tarifa_minima} kWh (mínimo)")
        print(f"   • SCEE: {novo_comp} kWh (novo)")
        if economia > 0:
            print(f"   • Economia estimada: R$ {economia:,.2f}")
        print(f"{'='*60}")
        
        resposta = input("🤔 Criar compensação completa? (s/n): ").strip().lower()
        return resposta in ['s', 'sim', 'y', 'yes']
    
    def _perguntar_compensacao_completa_ajustar(self, n_comp: Decimal, comp: Decimal, 
                                              minima: Decimal, economia: Decimal) -> bool:
        """Pergunta sobre ajuste de compensação existente"""
        total = n_comp + comp
        novo_comp = total - minima
        
        print(f"\n{'='*60}")
        print(f"⚡ COMPENSAÇÃO COMPLETA DISPONÍVEL (Ajustar)")
        print(f"{'='*60}")
        print(f"📊 Situação atual:")
        print(f"   • Não compensado: {n_comp} kWh")
        print(f"   • SCEE: {comp} kWh")
        print(f"   • Total: {total} kWh")
        print(f"\n🎯 Após compensação completa:")
        print(f"   • Não compensado: {minima} kWh (mínimo)")
        print(f"   • SCEE: {novo_comp} kWh")
        if economia > 0:
            print(f"   • Economia estimada: R$ {economia:,.2f}")
        print(f"{'='*60}")
        
        resposta = input("🤔 Aplicar compensação completa? (s/n): ").strip().lower()
        return resposta in ['s', 'sim', 'y', 'yes']
    
    def _recalcular_bandeiras_compensacao_completa(self, dados: Dict[str, Any], 
                                                  consumo_antigo: Decimal, 
                                                  consumo_novo: Decimal) -> Decimal:
        """
        Recalcula bandeiras amarela e vermelha após compensação completa
        Retorna a diferença total economizada
        """
        diferenca_total = Decimal('0')
        
        try:
            rs_amarela = Decimal('0')
            rs_vermelha = Decimal('0')
            
            # Buscar tarifas de bandeiras
            for posto in ['p', 'fp', 'hi', 'hr', '']:
                sufixo = f"_{posto}" if posto else ""
                
                if rs_amarela == 0:
                    rs_amarela = self._to_decimal(dados.get(f"rs_adc_bandeira_amarela{sufixo}", 0))
                if rs_vermelha == 0:
                    rs_vermelha = self._to_decimal(dados.get(f"rs_adc_bandeira_vermelha{sufixo}", 0))
                
                if rs_amarela > 0 and rs_vermelha > 0:
                    break
            
            # Recalcular bandeira amarela
            if rs_amarela > 0:
                valor_antigo_amarela = consumo_antigo * rs_amarela
                valor_novo_amarela = consumo_novo * rs_amarela
                diferenca_amarela = valor_antigo_amarela - valor_novo_amarela
                diferenca_total += diferenca_amarela
                
                if self.debug and diferenca_amarela > 0:
                    print(f"   🟡 Bandeira Amarela: R$ {valor_antigo_amarela:,.2f} → R$ {valor_novo_amarela:,.2f} (economia: R$ {diferenca_amarela:,.2f})")
            
            # Recalcular bandeira vermelha  
            if rs_vermelha > 0:
                valor_antigo_vermelha = consumo_antigo * rs_vermelha
                valor_novo_vermelha = consumo_novo * rs_vermelha
                diferenca_vermelha = valor_antigo_vermelha - valor_novo_vermelha
                diferenca_total += diferenca_vermelha
                
                if self.debug and diferenca_vermelha > 0:
                    print(f"   🔴 Bandeira Vermelha: R$ {valor_antigo_vermelha:,.2f} → R$ {valor_novo_vermelha:,.2f} (economia: R$ {diferenca_vermelha:,.2f})")
            
            # Atualizar valor_bandeira total
            if diferenca_total > 0:
                valor_bandeira_atual = self._to_decimal(dados.get("valor_bandeira", 0))
                if valor_bandeira_atual > 0:
                    novo_valor_bandeira = valor_bandeira_atual - diferenca_total
                    dados["valor_bandeira"] = max(novo_valor_bandeira, Decimal('0'))
                    
                    if self.debug:
                        print(f"   🎌 Total Bandeiras: R$ {valor_bandeira_atual:,.2f} → R$ {novo_valor_bandeira:,.2f}")
            
            return diferenca_total
            
        except Exception as e:
            if self.debug:
                print(f"⚠️ Erro ao recalcular bandeiras: {e}")
            return Decimal('0')
    
    def _obter_quantidade_scee(self, dados: Dict[str, Any]) -> Decimal:
        """Obtém quantidade SCEE total (já calculada pelo Leitor)"""
        consumo_comp = self._to_decimal(dados.get("consumo_comp", 0))
        if consumo_comp > 0:
            if self.debug:
                print(f"📊 Quantidade SCEE: {consumo_comp} kWh (consumo compensado)")
            return consumo_comp
        
        energia_injetada = self._to_decimal(dados.get("energia_injetada", 0))
        if energia_injetada > 0:
            if self.debug:
                print(f"📊 Quantidade SCEE: {energia_injetada} kWh (energia injetada)")
            return energia_injetada
        
        if self.debug:
            print("⚠️ Quantidade SCEE não encontrada")
        return Decimal('0')
    
    def _obter_tarifa_compensacao(self, dados: Dict[str, Any], modo_calc: int = 0) -> Decimal:
        """Obtém tarifa de compensação"""
        sufixo = "_si" if modo_calc == 1 else ""
        modo_str = "SEM imposto" if modo_calc == 1 else "COM imposto"
        
        if self.debug:
            print(f"🔍 Buscando tarifa compensação {modo_str}...")
        
        campos_tarifa = [
            f"rs_consumo_n_comp_fp{sufixo}",
            f"rs_consumo_n_comp_p{sufixo}",
            f"rs_consumo_n_comp_hi{sufixo}",
            f"rs_consumo_n_comp{sufixo}",
            f"rs_consumo_n_comp_fp_tusd{sufixo}",
            f"rs_consumo_n_comp_p_tusd{sufixo}",
            f"rs_consumo_n_comp_hr_tusd{sufixo}",
            f"rs_consumo_n_comp_fp_te{sufixo}",
            f"rs_consumo_n_comp_p_te{sufixo}",
            f"rs_consumo_n_comp_hr_te{sufixo}",
            f"rs_consumo{sufixo}",
            "tarifa_comp"
        ]
        
        for campo in campos_tarifa:
            tarifa = self._to_decimal(dados.get(campo, 0))
            if tarifa > 0:
                if self.debug:
                    print(f"📊 Tarifa encontrada em '{campo}': R$ {tarifa:,.6f}")
                return tarifa
        
        if modo_calc == 1:
            return self._obter_tarifa_compensacao(dados, 0)
        
        if self.debug:
            print("⚠️ Tarifa de compensação não encontrada")
        return Decimal('0')
    
    def _obter_impostos(self, dados: Dict[str, Any]) -> Dict[str, Decimal]:
        """Obtém impostos (já extraídos pelo Leitor)"""
        return {
            'pis': self._to_decimal(dados.get("aliquota_pis", 0)),
            'cofins': self._to_decimal(dados.get("aliquota_cofins", 0)),
            'icms': self._to_decimal(dados.get("aliquota_icms", 0))
        }
    
    def _obter_bandeiras(self, dados: Dict[str, Any]) -> Dict[str, Decimal]:
        """Obtém dados de bandeiras (já totalizados pelo Leitor)"""
        valor_total = self._to_decimal(dados.get("valor_bandeira", 0))
        
        rs_amarela = Decimal('0')
        rs_vermelha = Decimal('0')
        
        for posto in ['p', 'fp', 'hi', 'hr', '']:
            sufixo = f"_{posto}" if posto else ""
            
            if rs_amarela == 0:
                rs_amarela = self._to_decimal(dados.get(f"rs_adc_bandeira_amarela{sufixo}", 0))
            if rs_vermelha == 0:
                rs_vermelha = self._to_decimal(dados.get(f"rs_adc_bandeira_vermelha{sufixo}", 0))
            
            if rs_amarela > 0 and rs_vermelha > 0:
                break
        
        resultado = {
            'rs_amarela': rs_amarela,
            'rs_vermelha': rs_vermelha,
            'valor_total': valor_total
        }
        
        if self.debug and valor_total > 0:
            print(f"🎌 Bandeiras: Amarela=R${rs_amarela:,.6f} | Vermelha=R${rs_vermelha:,.6f} | Total=R${valor_total:,.2f}")
        
        return resultado
    
    def _obter_descontos(self, dados: Dict[str, Any]) -> Dict[str, Decimal]:
        """Obtém descontos (planilha ou padrão)"""
        desconto_fatura = dados.get("desconto_fatura")
        desconto_bandeira = dados.get("desconto_bandeira")
        
        if desconto_fatura is not None:
            desc_fat = self._to_decimal(desconto_fatura)
        else:
            desc_fat = self.desconto_fatura_padrao
        
        if desconto_bandeira is not None:
            desc_band = self._to_decimal(desconto_bandeira)
        else:
            desc_band = self.desconto_bandeira_padrao
        
        if self.debug:
            origem_fat = "planilha" if desconto_fatura is not None else "padrão"
            origem_band = "planilha" if desconto_bandeira is not None else "padrão"
            print(f"💡 Descontos - Fatura: {desc_fat*100:.0f}% ({origem_fat}) | Bandeira: {desc_band*100:.0f}% ({origem_band})")
        
        return {
            'fatura': desc_fat,
            'bandeira': desc_band
        }
    
    def _calcular_aupus(self, quant_scee: Decimal, tarifa_comp: Decimal,
                       impostos: Dict, bandeiras: Dict, descontos: Dict,
                       dados: Dict[str, Any]) -> Dict[str, Decimal]:
        """Calcula valores AUPUS - LÓGICA PRINCIPAL"""
        # 1. Valor do consumo compensado (sem desconto AUPUS)
        valor_comp = quant_scee * tarifa_comp
        
        # 2. Fator de impostos
        fator_impostos = ((Decimal('1') - impostos['pis'] - impostos['cofins']) * 
                         (Decimal('1') - impostos['icms']))
        
        # 3. Valor das bandeiras compensado (sem desconto AUPUS)
        valor_band_comp = Decimal('0')
        if fator_impostos > 0:
            if bandeiras['rs_amarela'] > 0:
                valor_band_comp += bandeiras['rs_amarela'] * quant_scee
            if bandeiras['rs_vermelha'] > 0:
                valor_band_comp += bandeiras['rs_vermelha'] * quant_scee
        
        # 4. Aplicar descontos AUPUS
        valor_com_desconto = valor_comp * (Decimal('1') - descontos['fatura'])
        valor_bandeira_com_desconto = valor_band_comp * (Decimal('1') - descontos['bandeira'])
        
        # 5. Valor total AUPUS
        valor_aupus = valor_com_desconto + valor_bandeira_com_desconto
        
        # 6. Valores finais
        valor_concessionaria = self._to_decimal(dados.get("valor_concessionaria", 0))
        valor_juros = self._to_decimal(dados.get("valor_juros", 0))
        valor_multa = self._to_decimal(dados.get("valor_multa", 0))
        
        rs_juros_multa = valor_juros + valor_multa
        valor_consorcio = valor_aupus + valor_concessionaria - rs_juros_multa
        valor_s_desconto = valor_comp + valor_band_comp + valor_concessionaria - rs_juros_multa
        valor_economia = valor_s_desconto - valor_consorcio
        
        return {
            'valor_comp': valor_comp,
            'valor_band_comp': valor_band_comp,
            'valor_com_desconto': valor_com_desconto,
            'valor_bandeira_com_desconto': valor_bandeira_com_desconto,
            'valor_aupus': valor_aupus,
            'valor_consorcio': valor_consorcio,
            'valor_s_desconto': valor_s_desconto,
            'valor_economia': valor_economia
        }
    
    # ========== MÉTODOS AUXILIARES ==========
    
    def _obter_tarifa_minima(self, tipo_fornecimento: str) -> Decimal:
        """Retorna tarifa mínima baseada no tipo de fornecimento"""
        tipo_upper = tipo_fornecimento.upper()
        if "TRIFÁSICO" in tipo_upper:
            return Decimal('100')
        elif "MONOFÁSICO" in tipo_upper:
            return Decimal('30')
        elif "BIFÁSICO" in tipo_upper:
            return Decimal('50')
        else:
            return Decimal('100')  # Padrão
    
    def _imprimir_relatorio(self, dados: Dict[str, Any], quant_scee: Decimal, tarifa_comp: Decimal):
        """Imprime relatório final dos cálculos AUPUS"""
        print(f"\n{'='*60}")
        print(f"📋 RELATÓRIO AUPUS")
        print(f"{'='*60}")
        print(f"📊 Quantidade SCEE: {quant_scee:,.0f} kWh")
        print(f"💰 Tarifa compensação: R$ {tarifa_comp:,.6f}")
        print(f"💸 Sem desconto AUPUS: R$ {dados.get('valor_s_desconto', 0):,.2f}")
        print(f"💵 Com desconto AUPUS: R$ {dados.get('valor_consorcio', 0):,.2f}")
        print(f"💚 Economia AUPUS: R$ {dados.get('valor_economia', 0):,.2f}")

        valor_juros = self._to_decimal(dados.get('valor_juros', 0))
        valor_multa = self._to_decimal(dados.get('valor_multa', 0))
        if valor_juros > 0 or valor_multa > 0:
            print(f"⚠️ Juros: R$ {valor_juros:,.2f} | Multa: R$ {valor_multa:,.2f}")
        
        valor_bandeira = self._to_decimal(dados.get('valor_bandeira', 0))
        if valor_bandeira > 0:
            print(f"🎌 Bandeiras tarifárias: R$ {valor_bandeira:,.2f}")
        
        print(f"{'='*60}")
    
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