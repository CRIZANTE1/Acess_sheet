import streamlit as st

from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_user_logged_in, get_user_role, is_session_expired
from app.utils import get_sao_paulo_time
from app.data_operations import load_data_from_sheets
from app.logger import log_action
from app.ui_interface import vehicle_access_interface
from app.admin_page import admin_page
from app.summary_page import summary_page 
from app.scheduling_page import scheduling_page
from app.security import SessionSecurity

st.set_page_config(page_title="Controle de Acesso BAERI", layout="wide")

def main():
    # Inicializa segurança de sessão
    SessionSecurity.init_session_security()
    
    # Carrega os dados se ainda não estiverem na sessão
    if 'df_acesso_veiculos' not in st.session_state:
        load_data_from_sheets()

    if is_user_logged_in():
        
        # Verifica timeout de sessão por inatividade
        is_expired, minutes = SessionSecurity.check_session_timeout(timeout_minutes=30)
        if is_expired:
            st.warning(f"⚠️ Sua sessão expirou após {int(minutes)} minutos de inatividade. Por favor, faça login novamente.")
            log_action("SESSION_TIMEOUT", f"Sessão expirou por inatividade ({int(minutes)} minutos)")
            
            keys_to_clear = ['login_time', 'login_logged', 'last_activity']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.logout()
            st.rerun()
        
        if 'login_time' not in st.session_state:
            st.session_state.login_time = get_sao_paulo_time()

        if is_session_expired():
            st.warning("Sua sessão expirou devido à troca de turno. Por favor, faça login novamente.")
            log_action("SESSION_EXPIRED", "Sessão do usuário expirou automaticamente.")
            
            keys_to_clear = ['login_time', 'login_logged']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.logout()
            st.rerun()


        user_role = get_user_role()

        if user_role is None:
            from app.access_request_page import request_access_page
            request_access_page()
            return  # Para a execução aqui 

        if 'login_logged' not in st.session_state:
            log_action("LOGIN", f"Usuário acessou o sistema com papel '{user_role}'.")
            st.session_state.login_logged = True
            
        
        show_user_header()
        show_logout_button()
        
        page_options = []
        if user_role == 'admin':
            page_options.extend(["Controle de Acesso", "Agendar Visita", "Painel Administrativo", "Resumo"])
        elif user_role == 'operacional':
            page_options.extend(["Controle de Acesso", "Resumo"])
        
        page = st.sidebar.selectbox("Escolha a página:", page_options)
        
        if page == "Controle de Acesso":
            vehicle_access_interface()
        elif page == "Agendar Visita":
            scheduling_page()    
        elif page == "Painel Administrativo" and user_role == 'admin':
            admin_page()
        elif page == "Resumo": 
            summary_page()
    else:
        # Garante que, se o usuário não estiver logado, o estado da sessão seja limpo
        keys_to_clear = ['login_time', 'login_logged']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
            
        show_login_page()

    
    st.caption('Desenvolvido por Cristian Ferreira Carlos, CE9X,+551131038708, cristiancarlos@vibraenergia.com.br')
    

if __name__ == "__main__":
    main()


