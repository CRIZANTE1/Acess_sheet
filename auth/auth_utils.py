import streamlit as st
from app.data_operations import get_sheet_ops

def is_oidc_available():
    """Verifica se o login OIDC está configurado e disponível"""
    try:
        return hasattr(st.user, 'is_logged_in')
    except Exception:
        return False

def is_user_logged_in():
    """Verifica se o usuário está logado"""
    try:
        return st.user.is_logged_in
    except Exception:
        return False

def get_user_display_name():
    """Retorna o nome de exibição do usuário"""
    try:
        if hasattr(st.user, 'name') and st.user.name:
            return st.user.name
        elif hasattr(st.user, 'email'):
            return st.user.email
        return "Usuário"
    except Exception:
        return "Usuário"

def get_user_role():
    """Retorna o papel do usuário (admin ou usuário normal)"""
    try:
        if hasattr(st.user, 'role'):
            return st.user.role
        return "user"  # Default role if not specified
    except Exception:
        return "user"

def is_admin():
    """Verifica se o usuário atual é um administrador consultando a aba 'users'."""
    try:
        user_name = get_user_display_name()
        # Usa a função singleton para obter a instância da classe de operações
        sheet_operations = get_sheet_ops() 
        users_data = sheet_operations.carregar_dados_aba('users')

        if users_data and len(users_data) > 1:
            header = users_data[0]
            try:
                # O nome de exibição do OIDC pode ter variações, então é melhor verificar o e-mail
                email_index = header.index('email')
                user_email = st.user.email if hasattr(st.user, 'email') else None
                if not user_email:
                    return False
                
                admin_emails = {row[email_index] for row in users_data[1:] if row and len(row) > email_index}
                return user_email in admin_emails
            
            except ValueError:
                # Fallback para o nome, se a coluna 'email' não existir
                st.warning("Coluna 'email' não encontrada na aba 'users'. Verificando por 'adm_name'.")
                adm_name_index = header.index('adm_name')
                admin_names = {row[adm_name_index] for row in users_data[1:] if row and len(row) > adm_name_index}
                return user_name in admin_names
        else:
            return False
    except Exception as e:
        st.error(f"Erro na verificação de admin: {str(e)}")
        return False
