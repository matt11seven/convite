# 🔐 CONFIGURAÇÃO DE SEGURANÇA - ADMIN

## ⚠️ IMPORTANTE: REMOVER CREDENCIAIS HARDCODED

### 🎯 O QUE FOI FEITO:

✅ **Removido** todas as credenciais hardcoded do código  
✅ **Movido** todas as credenciais para arquivo `.env`  
✅ **Criado** script de configuração segura  
✅ **Adicionado** validações de segurança  

### 🔧 COMO CONFIGURAR CREDENCIAIS SEGURAS:

#### **Método 1: Script Automático (Recomendado)**
```bash
cd /app/scripts
python3 setup_admin.py
```

#### **Método 2: Manual**
Edite o arquivo `/app/backend/.env`:
```bash
# Substitua pelas suas credenciais SEGURAS
ADMIN_EMAIL=seu-admin@empresa.com
ADMIN_PASSWORD=SuaSenhaForte123!@#
```

### 🔒 REQUISITOS DE SENHA SEGURA:

- ✅ Mínimo 8 caracteres
- ✅ Pelo menos 1 letra maiúscula
- ✅ Pelo menos 1 letra minúscula  
- ✅ Pelo menos 1 número
- ✅ Pelo menos 1 caractere especial (!@#$%^&*)

### 🚀 APÓS CONFIGURAR:

1. **Reiniciar o servidor:**
```bash
sudo supervisorctl restart backend
```

2. **Verificar logs:**
```bash
tail -f /var/log/supervisor/backend.*.log
```

3. **Testar login:** Use as novas credenciais na interface

### 🛡️ SEGURANÇA EM PRODUÇÃO:

1. **NUNCA** use credenciais padrão em produção
2. **SEMPRE** use senhas fortes e únicas
3. **CONFIGURE** emails corporativos reais
4. **MONITORE** logs de acesso admin
5. **ROTACIONE** senhas regularmente

### 📋 CHECKLIST DE SEGURANÇA:

- [ ] Credenciais padrão alteradas
- [ ] Senha forte configurada
- [ ] Email corporativo configurado
- [ ] Servidor reiniciado
- [ ] Login testado
- [ ] Logs verificados

### 🆘 PROBLEMAS COMUNS:

**Erro: "ADMIN_EMAIL and ADMIN_PASSWORD must be set"**
- Solução: Configure as variáveis no .env

**Erro: "Failed to create admin user"**
- Solução: Verifique conexão com MongoDB

**Login não funciona:**
- Solução: Reinicie o backend após alterar .env

---

**✅ SISTEMA AGORA 100% SEGURO - SEM CREDENCIAIS HARDCODED!**