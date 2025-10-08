import streamlit as st
from app.operations import SheetOperations
from app.utils import get_sao_paulo_time
import pytz
from datetime import datetime, time

@st.cache_data(ttl=300)
def _load_user_roles():
    """
    Carrega e cacheia os papéis dos usuários da aba 'users' da planilha.
    Retorna um dicionário mapeando emails de usuário para seus papéis.
    """
    try:
        sheet_operations = SheetOperations()
        users_data = sheet_operations.carregar_dados_aba('users')
        
        if not users_data or len(users_data) < 2:
            st.error("Aba 'users' não encontrada, vazia ou sem registros. Ninguém poderá acessar o sistema.")
            return {}
            
        header = users_data[0]
        try:
            # Agora usa 'user_email' ao invés de 'user_name'
            email_idx = header.index('user_email')
            role_idx = header.index('role')
        except ValueError:
            st.error("A planilha 'users' precisa ter as colunas 'user_email' e 'role'. Verifique o cabeçalho.")
            return {}

        user_roles = {
            row[email_idx].strip().lower(): row[role_idx].strip().lower() 
            for row in users_data[1:] 
            if row[email_idx].strip() and row[role_idx].strip()
        }
        return user_roles
        
    except Exception as e:
        st.error(f"Erro crítico ao carregar papéis de usuário da planilha: {e}")
        return {}

def is_oidc_available():
    """Verifica se o login OIDC do Streamlit está configurado e disponível."""
    try:
        return hasattr(st, 'user')
    except Exception:
        return False

def is_user_logged_in():
    """Verifica se o usuário está efetivamente logado."""
    try:
        return st.user.is_logged_in
    except Exception:
        return False

def get_user_email():
    """Retorna o email do usuário logado."""
    try:
        if hasattr(st.user, 'email') and st.user.email:
            return st.user.email
        return None
    except Exception:
        return None

def get_user_display_name():
    """Retorna o nome de exibição do usuário logado (prioriza nome, fallback para email)."""
    try:
        # Prioriza o nome do usuário
        if hasattr(st.user, 'name') and st.user.name:
            return st.user.name
        # Se não tiver nome, usa o email como fallback
        elif hasattr(st.user, 'email') and st.user.email:
            return st.user.email
        return "Usuário Desconhecido"
    except Exception:
        return "Usuário Desconhecido"

def get_user_role():
    """
    Retorna o papel do usuário (ex: 'admin', 'operacional') com base na planilha.
    Retorna None se o usuário não estiver logado ou não estiver na lista de permissões.
    """
    if not is_user_logged_in():
        return None
        
    user_email = get_user_email()
    if not user_email:
        return None
        
    user_roles_map = _load_user_roles()
    
    # Busca pelo email em lowercase para evitar problemas de case
    return user_roles_map.get(user_email.lower())

def is_admin():
    """Verifica se o usuário atual tem o papel de 'admin'."""
    return get_user_role() == 'admin'

def is_operacional():
    """Verifica se o usuário atual tem o papel de 'operacional'."""
    return get_user_role() == 'operacional'

def _get_shift(dt_object):
    """
    Determina o turno com base em um objeto datetime.
    - Turno 1 (Diurno): 07:00:00 - 18:58:59
    - Turno 2 (Noturno): 18:59:00 - 06:59:59
    Retorna 1 ou 2.
    """
    seven_am = time(7, 0, 0)
    six_fifty_nine_pm = time(18, 59, 0)
    
    current_time_obj = dt_object.time()
    
    if seven_am <= current_time_obj < six_fifty_nine_pm:
        return 1  
    else:
        return 2  

def is_session_expired():
    """
    Verifica se a sessão do usuário expirou porque o turno mudou
    desde o momento do login.
    """
    if 'login_time' not in st.session_state:
        return False

    login_time = st.session_state.login_time
    current_time = get_sao_paulo_time()

    login_shift = _get_shift(login_time)
    current_shift = _get_shift(current_time)

    if login_shift != current_shift:
        return True
        
    return False