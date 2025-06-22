#!/usr/bin/env python3
"""
Script de Configuração de Admin
Sistema de Convites Enterprise - Configuração Segura de Credenciais
"""

import os
import sys
import getpass
import re
from pathlib import Path

def validate_email(email):
    """Validar formato de email."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validar força da senha."""
    if len(password) < 8:
        return False, "Senha deve ter pelo menos 8 caracteres"
    
    if not re.search(r'[A-Z]', password):
        return False, "Senha deve conter pelo menos uma letra maiúscula"
    
    if not re.search(r'[a-z]', password):
        return False, "Senha deve conter pelo menos uma letra minúscula"
    
    if not re.search(r'\d', password):
        return False, "Senha deve conter pelo menos um número"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Senha deve conter pelo menos um caractere especial"
    
    return True, "Senha válida"

def update_env_file(admin_email, admin_password):
    """Atualizar arquivo .env com novas credenciais."""
    env_path = Path(__file__).parent.parent / "backend" / ".env"
    
    if not env_path.exists():
        print(f"❌ Arquivo .env não encontrado: {env_path}")
        return False
    
    # Ler arquivo atual
    with open(env_path, 'r') as f:
        content = f.read()
    
    # Atualizar credenciais
    content = re.sub(r'ADMIN_EMAIL=.*', f'ADMIN_EMAIL={admin_email}', content)
    content = re.sub(r'ADMIN_PASSWORD=.*', f'ADMIN_PASSWORD={admin_password}', content)
    
    # Salvar arquivo
    with open(env_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Credenciais atualizadas em {env_path}")
    return True

def main():
    """Função principal do script."""
    print("🔐 CONFIGURAÇÃO SEGURA DE ADMIN")
    print("=" * 50)
    print("Configure as credenciais do administrador do sistema")
    print("ATENÇÃO: Use credenciais FORTES para produção!")
    print()
    
    # Configurar email
    while True:
        admin_email = input("📧 Email do administrador: ").strip()
        if validate_email(admin_email):
            break
        else:
            print("❌ Email inválido. Tente novamente.")
    
    # Configurar senha
    while True:
        admin_password = getpass.getpass("🔑 Senha do administrador: ")
        
        if not admin_password:
            print("❌ Senha não pode estar vazia.")
            continue
        
        valid, message = validate_password(admin_password)
        if valid:
            # Confirmar senha
            confirm_password = getpass.getpass("🔑 Confirme a senha: ")
            if admin_password == confirm_password:
                break
            else:
                print("❌ Senhas não coincidem. Tente novamente.")
        else:
            print(f"❌ {message}")
    
    print()
    print("📋 RESUMO DA CONFIGURAÇÃO:")
    print(f"Email: {admin_email}")
    print(f"Senha: {'*' * len(admin_password)}")
    print()
    
    confirm = input("Confirma as configurações? (s/N): ").lower().strip()
    if confirm not in ['s', 'sim', 'y', 'yes']:
        print("❌ Configuração cancelada.")
        return
    
    # Atualizar arquivo .env
    if update_env_file(admin_email, admin_password):
        print()
        print("✅ CONFIGURAÇÃO CONCLUÍDA!")
        print("🔄 Reinicie o servidor backend para aplicar as mudanças:")
        print("   sudo supervisorctl restart backend")
        print()
        print("🔒 LEMBRETE DE SEGURANÇA:")
        print("   - Mantenha estas credenciais seguras")
        print("   - Não compartilhe em repositórios públicos")
        print("   - Use senhas diferentes para cada ambiente")
    else:
        print("❌ Falha ao atualizar configurações.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Configuração cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        sys.exit(1)