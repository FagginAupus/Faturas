# 📋 ANÁLISE COMPLETA DOS CAMPOS DE SAÍDA - Leitor_Faturas_PDF.py

## 🎯 OBJETIVO
Documentar todos os campos retornados pelo sistema atual para garantir **100% de compatibilidade** na reestruturação modular.

## 📊 METODOLOGIA DE ANÁLISE
1. Análise do código fonte `Leitor_Faturas_PDF.py`
2. Teste com PDFs reais da pasta `Faturas/`
3. Documentação de tipos e estruturas
4. Mapeamento para Calculadora_AUPUS.py e Exportar_Planilha.py

## 🔑 CAMPOS OBRIGATÓRIOS CRÍTICOS

### **DADOS BÁSICOS** (sempre presentes)
```python
'uc': str                      # Unidade Consumidora
'grupo': str                   # A ou B
'modalidade_tarifaria': str    # CONVENCIONAL, BRANCA, VERDE, AZUL
'tipo_fornecimento': str       # MONOFÁSICO, BIFÁSICO, TRIFÁSICO
'endereco': str               # Endereço completo
'cnpj_cpf': str              # Documento do cliente
'medidor': str               # Número do medidor
'mes_referencia': str        # MM/YYYY
'data_leitura': str          # DD/MM/YY
'vencimento': str            # DD/MM/YYYY
```

### **CONSUMO** (Grupo B - foco inicial)
```python
# CONVENCIONAL
'consumo': Decimal           # Total geral kWh
'consumo_comp': Decimal      # Compensado SCEE kWh
'consumo_n_comp': Decimal    # Não compensado kWh

# TARIFA BRANCA (postos horários)
'consumo_p': Decimal         # Ponta kWh
'consumo_fp': Decimal        # Fora ponta kWh
'consumo_hi': Decimal        # Horário intermediário kWh
'consumo_comp_p': Decimal    # Compensado ponta
'consumo_comp_fp': Decimal   # Compensado fora ponta
'consumo_comp_hi': Decimal   # Compensado intermediário
'consumo_n_comp_p': Decimal  # Não compensado ponta
'consumo_n_comp_fp': Decimal # Não compensado fora ponta
'consumo_n_comp_hi': Decimal # Não compensado intermediário
```

### **TARIFAS** (valores R$/kWh)
```python
'rs_consumo': Decimal                # Tarifa consumo geral
'rs_consumo_comp': Decimal           # Tarifa compensado
'rs_consumo_n_comp': Decimal         # Tarifa não compensado

# BRANCA - por posto
'rs_consumo_p': Decimal              # Tarifa ponta
'rs_consumo_fp': Decimal             # Tarifa fora ponta
'rs_consumo_hi': Decimal             # Tarifa intermediário
'rs_consumo_comp_p': Decimal         # Tarifa compensado ponta
'rs_consumo_comp_fp': Decimal        # Tarifa compensado fora ponta
'rs_consumo_comp_hi': Decimal        # Tarifa compensado intermediário
'rs_consumo_n_comp_p': Decimal       # Tarifa não compensado ponta
'rs_consumo_n_comp_fp': Decimal      # Tarifa não compensado fora ponta
'rs_consumo_n_comp_hi': Decimal      # Tarifa não compensado intermediário
```

### **VALORES MONETÁRIOS**
```python
'valor_concessionaria': Decimal      # Total da fatura
'valor_consumo': Decimal             # Valor do consumo
'valor_consumo_comp': Decimal        # Valor compensado
'valor_consumo_n_comp': Decimal      # Valor não compensado
'valor_juros': Decimal               # Juros por atraso
'valor_multa': Decimal               # Multa por atraso
'valor_iluminacao': Decimal          # Contribuição iluminação pública
```

### **IMPOSTOS**
```python
'aliquota_icms': Decimal             # % ICMS (ex: 0.19 para 19%)
'aliquota_pis': Decimal              # % PIS
'aliquota_cofins': Decimal           # % COFINS
'valor_icms': Decimal                # Valor R$ ICMS
'valor_pis': Decimal                 # Valor R$ PIS
'valor_cofins': Decimal              # Valor R$ COFINS
```

### **SCEE (Sistema de Compensação)**
```python
'saldo': Decimal                     # Saldo total kWh
'excedente_recebido': Decimal        # Excedente recebido kWh
'credito_recebido': Decimal          # Crédito recebido kWh
'energia_injetada': Decimal          # Energia injetada total kWh
'geracao_ciclo': Decimal             # Geração no ciclo kWh

# Múltiplas UCs geradoras (listas)
'uc_geradora_1': str                 # UC da primeira geradora
'uc_geradora_2': str                 # UC da segunda geradora (se existir)
'geracao_ugs_1': Decimal             # Geração da UG 1
'geracao_ugs_2': Decimal             # Geração da UG 2
'excedente_ugs_1': Decimal           # Excedente da UG 1
'excedente_ugs_2': Decimal           # Excedente da UG 2
```

### **BANDEIRAS TARIFÁRIAS**
```python
'valor_bandeira': Decimal            # Total bandeiras
'rs_adc_bandeira_amarela': Decimal   # Tarifa bandeira amarela
'rs_adc_bandeira_vermelha': Decimal  # Tarifa bandeira vermelha
'valor_adc_bandeira_amarela': Decimal # Valor bandeira amarela
'valor_adc_bandeira_vermelha': Decimal # Valor bandeira vermelha

# Por posto (BRANCA)
'rs_adc_bandeira_amarela_p': Decimal
'rs_adc_bandeira_amarela_fp': Decimal
'rs_adc_bandeira_amarela_hi': Decimal
'rs_adc_bandeira_vermelha_p': Decimal
'rs_adc_bandeira_vermelha_fp': Decimal
'rs_adc_bandeira_vermelha_hi': Decimal
```

## 🔍 CAMPOS ESPECÍFICOS POR TIPO

### **GRUPO B CONSUMIDOR COMPENSADO** (prioridade)
- ✅ Todos os campos de CONSUMO com divisão comp/n_comp
- ✅ Todos os campos de SCEE
- ✅ Bandeiras (se aplicável)
- ✅ Impostos completos

### **GRUPO B CONSUMIDOR SIMPLES**
- ✅ Consumo total apenas (`consumo`)
- ✅ Tarifa simples (`rs_consumo`)
- ❌ SCEE = 0 (saldo, excedente_recebido)
- ✅ Impostos completos

### **GRUPO A** (ignorar na primeira fase)
- Campos adicionais: TUSD, TE, demanda
- Múltiplos postos: P, FP, HR
- Estrutura muito mais complexa

## 🛡️ VALIDAÇÃO DE COMPATIBILIDADE

### **Campos usados por Calculadora_AUPUS.py:**
```python
# OBRIGATÓRIOS:
dados.get("uc")
dados.get("grupo")
dados.get("modalidade_tarifaria")
dados.get("consumo_comp")
dados.get("consumo_n_comp")
dados.get("energia_injetada")
dados.get("desconto_fatura")      # Da planilha
dados.get("desconto_bandeira")    # Da planilha
dados.get("aliquota_icms")
dados.get("aliquota_pis")
dados.get("aliquota_cofins")
dados.get("valor_concessionaria")
dados.get("valor_bandeira")
```

### **Campos usados por Exportar_Planilha.py:**
```python
# OBRIGATÓRIOS:
dados.get("uc")
dados.get("nome")                 # Da planilha
dados.get("consumo")
dados.get("saldo")
dados.get("excedente_recebido")
dados.get("valor_economia")       # Calculado pela AUPUS
dados.get("valor_consorcio")      # Calculado pela AUPUS
dados.get("aliquota_icms")
dados.get("aliquota_pis")
dados.get("aliquota_cofins")
```

## 📐 TIPOS DE DADOS OBRIGATÓRIOS

### **Decimal** (cálculos financeiros)
- Todos os valores monetários (valor_*)
- Todos os consumos (consumo_*)
- Todas as tarifas (rs_*)
- Todas as alíquotas (aliquota_*)
- Todos os campos SCEE

### **String**
- UC, grupo, modalidade, endereço
- Datas, nomes, documentos

### **None/Opcional**
- Campos que podem não existir
- Sempre verificar com `.get(campo, default)`

## 🎯 ESTRATÉGIA DE IMPLEMENTAÇÃO

### **1. Classificador de Faturas**
```python
def classify_pdf(self, pdf_path: str) -> ClassificacaoFatura:
    # Identificar: Grupo B Consumidor Compensado vs Simples
    # Usar padrões existentes do Leitor_Faturas_PDF.py
```

### **2. Extratores Específicos**
```python
# B_CONSUMIDOR_COMPENSADO
def extract(self, pdf_path: str) -> Dict[str, Any]:
    # RETORNAR: Todos os campos acima com SCEE
    # GARANTIR: Tipos Decimal para cálculos

# B_CONSUMIDOR_SIMPLES
def extract(self, pdf_path: str) -> Dict[str, Any]:
    # RETORNAR: Campos básicos + consumo
    # ZERAR: saldo=0, excedente_recebido=0, etc.
```

### **3. Processador V2**
```python
def processar_fatura(self, pdf_path: str) -> Dict[str, Any]:
    # SEMPRE retornar dicionário com MESMOS campos
    # GARANTIR compatibilidade 100%
    # IGNORAR tipos não suportados com skip_processing=True
```

## ⚠️ PONTOS CRÍTICOS DE ATENÇÃO

1. **Nomes de campos**: JAMAIS alterar
2. **Tipos Decimal**: Manter para cálculos financeiros
3. **Campos opcionais**: Sempre usar `.get(campo, default)`
4. **SCEE para B simples**: Deve ser Decimal('0'), não None
5. **Modalidade BRANCA**: Dividir em postos P/FP/HI
6. **Múltiplas UGs**: Manter estrutura de listas/índices

## 🚀 PRÓXIMOS PASSOS
1. ✅ Análise completa documentada
2. 🔄 Criar estrutura modular
3. 🔄 Implementar classificador
4. 🔄 Implementar extrator B compensado
5. 🔄 Validar compatibilidade total