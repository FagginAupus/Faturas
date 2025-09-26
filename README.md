# Sistema de Processamento de Faturas AUPUS

Sistema automatizado para processamento de faturas de energia elétrica, extração de dados e cálculo de valores do consórcio AUPUS.

## 📋 Visão Geral

O sistema processa faturas de energia elétrica em PDF de duas formas:
- **Via Email**: Busca automaticamente faturas em emails recebidos
- **Via Pasta Local**: Processa PDFs já baixados em uma pasta específica

Após a extração, calcula os valores do consórcio AUPUS apenas para clientes com sigla "CLA" e exporta os resultados para planilhas Excel.

## 🚀 Funcionalidades Principais

### 1. Processamento de Faturas
- Extrai dados essenciais das faturas PDF (UC, consumo, valores, etc.)
- Identifica tipo de cliente pela sigla na planilha de controle
- Aplica cálculos AUPUS apenas para clientes elegíveis (CLA)

### 2. Dois Modos de Operação
- **Email**: Conecta via IMAP, busca emails por período e baixa PDFs
- **Pasta Local**: Processa todos os PDFs em uma pasta específica

### 3. Cálculos AUPUS
- Verifica e aplica compensação SCEE completa quando necessário
- Calcula descontos específicos por cliente
- Gera valores finais do consórcio com economia

### 4. Exportação de Dados
- Atualiza planilha de controle Excel com dados extraídos
- Gera relatórios e gráficos automaticamente
- Executa macro para geração de PDF final

## 📁 Estrutura de Arquivos

```
Faturas/
├── fatura_mail.py          # Script principal
├── Leitor_Faturas_PDF.py   # Extração de dados dos PDFs
├── Calculadora_AUPUS.py    # Cálculos específicos AUPUS
├── Exportar_Planilha.py    # Exportação para Excel
├── Ler_Planilha.py         # Leitura da planilha de controle
├── venv/                   # Ambiente virtual
└── requirements.txt        # Dependências (opcional)
```

## 🛠️ Configuração e Instalação

### Pré-requisitos
- Python 3.11+
- Microsoft Excel (para xlwings)
- Acesso à internet (modo email)

### Instalação

1. **Criar ambiente virtual:**
```bash
python -m venv venv
source venv/Scripts/activate  # Windows
```

2. **Instalar dependências:**
```bash
pip install pandas openpyxl xlwings pymupdf python-dateutil pywin32
```

3. **Configurar caminhos:**
   - Verificar caminhos das pastas no código
   - Ajustar credenciais de email se necessário

## 📧 Configuração Email (Modo 1)

O sistema está configurado para:
- **Servidor**: imap.hostinger.com
- **Email**: faturas.go@aupusenergia.com.br
- **Busca por**: Emails com assunto "Fatura da Equatorial Energia em arquivo"

## 📂 Configuração Pasta Local (Modo 2)

Pasta padrão configurada:
```
~/Dropbox/AUPUS SMART/01. Club AUPUS/01. Usineiros/01. AUPUS ENERGIA/01. FATURAS/2025/08.2025/Pendentes/
```

## 🎯 Como Usar

### Execução
```bash
# Ativar ambiente virtual
source venv/Scripts/activate

# Executar sistema
python fatura_mail.py
```

### Opções Disponíveis
1. **Processar faturas do EMAIL**
   - Digite a data inicial (DD/MM/YYYY)
   - Sistema busca emails do mês especificado
   - Baixa e processa PDFs automaticamente

2. **Processar faturas de PASTA LOCAL**
   - Usa pasta pré-configurada
   - Processa todos os PDFs encontrados

### Fluxo de Processamento
1. **Leitura**: Carrega planilha de controle com dados dos clientes
2. **Extração**: Extrai dados de cada PDF encontrado
3. **Identificação**: Busca UC na planilha e identifica tipo de cliente
4. **Cálculo**: Aplica cálculos AUPUS apenas para clientes CLA
5. **Exportação**: Atualiza planilhas e gera relatórios

## 📊 Tipos de Cliente

- **CLA**: Clientes do consórcio AUPUS (recebem cálculos completos)
- **Outros**: Apenas extração de dados, sem cálculos AUPUS

## 📈 Dados Extraídos e Calculados

### Dados Básicos (Todos os Clientes)
- UC, nome, endereço, CPF/CNPJ
- Consumo total, compensado e não compensado
- Valores da concessionária
- Bandeiras tarifárias

### Cálculos AUPUS (Apenas CLA)
- Valores com desconto AUPUS
- Economia gerada
- Valor final do consórcio
- Compensação SCEE otimizada

## ⚙️ Arquivos de Controle

### Planilha Principal
- **Local**: `~/Dropbox/AUPUS SMART/01. Club AUPUS/_Controles/Controle Clube Aupus.xlsx`
- **Abas**: Controle, DADOS, DEMONSTRATIVO, GRAFICO, SETEMBRO

### Planilha de Saída
- **Local**: `~/Dropbox/AUPUS SMART/01. Club AUPUS/_Controles/06. Controles/AUPUS ENERGIA.xlsm`
- **Função**: Relatório final com macro para PDF

## 🔍 Logs e Debugging

O sistema fornece logs detalhados durante a execução:
- Status de conexão (modo email)
- Arquivos processados
- Dados extraídos
- Cálculos aplicados
- Erros encontrados

## ⚠️ Observações Importantes

1. **Backup**: Sempre faça backup das planilhas antes de executar
2. **Excel**: Mantenha o Excel fechado durante a execução
3. **Rede**: Modo email requer conexão estável
4. **Caminhos**: Verifique se todas as pastas existem
5. **Permissões**: Execute com permissões adequadas

## 🔧 Resolução de Problemas

### Erros Comuns
- **Arquivo bloqueado**: Feche Excel e arquivos PDF
- **Caminho não encontrado**: Verifique estrutura de pastas
- **Erro de conexão**: Verifique credenciais e internet
- **Dependência faltante**: Reinstale packages

### Suporte
Para problemas técnicos, verifique:
1. Logs do sistema
2. Estrutura de pastas
3. Permissões de arquivo
4. Versões das dependências

## 📝 Versão
Sistema desenvolvido para AUPUS Energia - Processamento automatizado de faturas do consórcio de energia.