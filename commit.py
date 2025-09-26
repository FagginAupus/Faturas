#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Commit Automático
Automatiza o processo de commit e push para o GitHub
com timestamp em horário de Brasília
"""

import subprocess
import sys
from datetime import datetime
import pytz

def get_brasilia_time():
    """Retorna o horário atual de Brasília formatado"""
    brasilia_tz = pytz.timezone('America/Sao_Paulo')
    now = datetime.now(brasilia_tz)
    return now.strftime("%d/%m/%Y às %H:%M")

def run_command(command, description=""):
    """Executa comando e retorna resultado"""
    try:
        if description:
            print(f"📋 {description}...")

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        if result.returncode != 0:
            print(f"❌ ERRO: {result.stderr}")
            return False, result.stderr

        if result.stdout.strip():
            print(f"✅ {result.stdout.strip()}")

        return True, result.stdout

    except Exception as e:
        print(f"❌ ERRO na execução: {e}")
        return False, str(e)

def check_git_status():
    """Verifica se há alterações para commit"""
    success, output = run_command("git status --porcelain")
    if not success:
        return False, "Erro ao verificar status do Git"

    if not output.strip():
        return False, "Nenhuma alteração detectada para commit"

    return True, output

def main():
    print("🚀 SCRIPT DE COMMIT AUTOMÁTICO - FATURAS AUPUS")
    print("=" * 55)

    # Verificar se há alterações
    has_changes, status_output = check_git_status()
    if not has_changes:
        print(f"ℹ️  {status_output}")
        input("\nPressione ENTER para sair...")
        return

    print("📂 Alterações detectadas:")
    for line in status_output.strip().split('\n'):
        if line.strip():
            status = line[:2].strip()
            file_name = line[3:].strip()

            if status == 'M':
                print(f"   📝 Modificado: {file_name}")
            elif status == 'A':
                print(f"   ➕ Adicionado: {file_name}")
            elif status == 'D':
                print(f"   ❌ Removido: {file_name}")
            elif status == '??':
                print(f"   📄 Novo arquivo: {file_name}")
            else:
                print(f"   🔄 {status}: {file_name}")

    print("\n" + "=" * 55)

    # Obter horário de Brasília
    brasilia_time = get_brasilia_time()
    default_message = f"Update: {brasilia_time}"

    # Solicitar mensagem adicional
    print(f"💬 Mensagem padrão: '{default_message}'")
    additional_message = input("\n📝 Digite mensagem adicional (ou ENTER para usar padrão): ").strip()

    # Construir mensagem final
    if additional_message:
        final_message = f"{additional_message}\n\nUpdate: {brasilia_time}"
    else:
        final_message = default_message

    print(f"\n📋 Mensagem final do commit:")
    print(f"   '{final_message}'")

    # Confirmar commit
    confirm = input("\n❓ Confirmar commit e push? (s/N): ").strip().lower()
    if confirm not in ['s', 'sim', 'y', 'yes']:
        print("❌ Operação cancelada pelo usuário")
        input("\nPressione ENTER para sair...")
        return

    print("\n🔄 Iniciando processo de commit...")

    # Adicionar todos os arquivos
    success, _ = run_command("git add .", "Adicionando arquivos")
    if not success:
        input("\nPressione ENTER para sair...")
        return

    # Fazer commit
    commit_command = f'git commit -m "{final_message}"'
    success, _ = run_command(commit_command, "Fazendo commit")
    if not success:
        input("\nPressione ENTER para sair...")
        return

    # Push para o repositório
    success, _ = run_command("git push origin main", "Enviando para GitHub")
    if not success:
        input("\nPressione ENTER para sair...")
        return

    print("\n🎉 SUCESSO! Commit e push realizados com sucesso!")
    print(f"⏰ Horário: {brasilia_time}")
    print(f"💬 Mensagem: {final_message}")

    input("\nPressione ENTER para sair...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operação interrompida pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        input("\nPressione ENTER para sair...")
        sys.exit(1)