# 🚀 Como Usar o Script de Commit Automático

## 📋 Visão Geral
Script que automatiza commits e push para GitHub com timestamp em horário de Brasília.

## 🎯 Como Usar

### Opção 1: Arquivo .bat (Recomendado)
```bash
# Clique duplo no arquivo ou execute:
commit.bat
```

### Opção 2: Python direto
```bash
# Ativar ambiente virtual
source venv/Scripts/activate  # Linux/Mac
venv\Scripts\activate.bat     # Windows

# Executar script
python commit.py
```

## 📱 Interface do Script

### 1. Verificação Automática
- ✅ Detecta alterações automaticamente
- 📂 Mostra lista de arquivos modificados
- ❌ Cancela se não há alterações

### 2. Mensagem de Commit
- 🕐 **Padrão**: "Update: DD/MM/YYYY às HH:MM"
- ✏️ **Personalizada**: Digite sua mensagem adicional
- ⏎ **Enter**: Usa mensagem padrão

### 3. Confirmação
- ❓ Pergunta se deseja prosseguir
- 📋 Mostra mensagem final antes do commit

### 4. Processo Automático
- ➕ `git add .`
- 💾 `git commit -m "mensagem"`
- 🚀 `git push origin main`

## 📝 Exemplos de Uso

### Exemplo 1: Mensagem Padrão
```
💬 Mensagem padrão: 'Update: 26/09/2024 às 14:30'
📝 Digite mensagem adicional (ou ENTER para usar padrão): [ENTER]

Resultado: "Update: 26/09/2024 às 14:30"
```

### Exemplo 2: Mensagem Personalizada
```
💬 Mensagem padrão: 'Update: 26/09/2024 às 14:30'
📝 Digite mensagem adicional (ou ENTER para usar padrão): Corrigido bug no processamento SCEE

Resultado:
"Corrigido bug no processamento SCEE

Update: 26/09/2024 às 14:30"
```

## ⚠️ Importante
- Script funciona apenas se há alterações para commit
- Requer autenticação GitHub configurada
- Usa fuso horário de Brasília automaticamente
- Confirma antes de executar qualquer ação

## 🔧 Troubleshooting

### Erro de Autenticação
```bash
# Configurar credenciais Git
git config --global user.name "Seu Nome"
git config --global user.email "seu.email@exemplo.com"
```

### Erro de Push
- Verifique conexão com internet
- Confirme se tem permissão no repositório
- Configure token GitHub se necessário

## 🎉 Vantagens
- ⚡ Rápido e automatizado
- 🕐 Timestamp automático em horário brasileiro
- 📋 Interface clara e intuitiva
- ✅ Confirmação de segurança
- 🔄 Processo completo (add + commit + push)