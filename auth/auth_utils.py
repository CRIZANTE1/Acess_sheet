import streamlit as st
from app.operations import SheetOperations  # Esta importação é o problema

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
        if hasattr(st.user, 'name'):
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
        return "user"  # Default role if an error occurs

def is_admin():
    """Verifica se o usuário atual é um administrador consultando a aba 'users'."""
    try:
        # A importação é feita DENTRO da função para evitar o ciclo na inicialização
        from app.operations import SheetOperations
        
        user_name = get_user_display_name()
        sheet_operations = SheetOperations()
        users_data = sheet_operations.carregar_dados_aba('users')

        if users_data:
            # Assuming the first row is the header
            header = users_data[0]
            try:
                adm_name_index = header.index('adm_name')
            except ValueError:
                st.error("A coluna 'adm_name' não foi encontrada na aba 'users'.")
                return False

            admin_names = [row[adm_name_index] for row in users_data[1:]]  # Skip header row
            return user_name in admin_names
        else:
            # Não exibe erro se a aba 'users' não existir ou estiver vazia, apenas retorna False
            return False
    except Exception as e:
        st.error(f"Erro na verificação de admin: {str(e)}")
        return False
