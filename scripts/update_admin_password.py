#!/usr/bin/env python3
"""
Script para atualizar senha do admin no banco de dados
"""

import sys
import os
sys.path.append('/app/backend')

from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

from pymongo import MongoClient
from passlib.context import CryptContext

# Environment variables
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

if not ADMIN_EMAIL or not ADMIN_PASSWORD:
    print("❌ ADMIN_EMAIL e ADMIN_PASSWORD devem estar configurados no .env")
    sys.exit(1)

# MongoDB setup
client = MongoClient(MONGO_URL)
db = client.convites_secure_db
users_collection = db.users

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def update_admin_password():
    """Atualiza a senha do admin no banco de dados."""
    try:
        # Encontrar usuário admin
        admin_user = users_collection.find_one({"email": ADMIN_EMAIL})
        
        if not admin_user:
            print(f"❌ Usuário admin não encontrado: {ADMIN_EMAIL}")
            return False
        
        # Hash da nova senha
        new_password_hash = pwd_context.hash(ADMIN_PASSWORD)
        
        # Atualizar senha
        result = users_collection.update_one(
            {"email": ADMIN_EMAIL},
            {
                "$set": {
                    "password_hash": new_password_hash,
                    "role": "admin"  # Garantir que é admin
                }
            }
        )
        
        if result.modified_count > 0:
            print(f"✅ Senha do admin atualizada com sucesso: {ADMIN_EMAIL}")
            print(f"✅ Nova senha: {'*' * len(ADMIN_PASSWORD)}")
            return True
        else:
            print("❌ Nenhuma alteração foi feita")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao atualizar senha: {e}")
        return False

if __name__ == "__main__":
    print("🔐 ATUALIZANDO SENHA DO ADMIN")
    print("=" * 40)
    update_admin_password()