import streamlit as st

from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_user_logged_in, get_user_role
from app.data_operations import load_data_from_sheets
from app.logger import log_action

from app.ui_interface import vehicle_access_interface
from app.admin_page import admin_page
from app.summary_page import summary_page 

st.set_page_config(page_title="Controle de Acesso BAERI", layout="wide")

def main():
    if 'df_acesso_veiculos' not in st.session_state:
        load_data_from_sheets()

    if is_user_logged_in():

        user_role = get_user_role()

        if user_role is None:
            st.error("Acesso Negado. Seu usuário não tem permissão para usar este sistema.")
            st.warning("Por favor, entre em contato com o administrador para solicitar seu cadastro na planilha 'users'.")
            st.stop() 

        if 'login_logged' not in st.session_state:
            log_action("LOGIN", f"Usuário acessou o sistema com papel '{user_role}'.")
            st.session_state.login_logged = True
            
        show_user_header()
        show_logout_button()
        
        page_options = []
        if user_role == 'admin':
            page_options.extend(["Controle de Acesso", "Painel Administrativo", "Resumo"])
        elif user_role == 'operacional':
            page_options.extend(["Controle de Acesso", "Resumo"])
        
        page = st.sidebar.selectbox("Escolha a página:", page_options)
        
        if page == "Controle de Acesso":
            vehicle_access_interface()
        elif page == "Painel Administrativo" and user_role == 'admin':
            admin_page()
        elif page == "Resumo": 
            summary_page()
    else:
        show_login_page()
        
    st.caption('Desenvolvido por Cristian Ferreira Carlos, CE9X,+551131038708, cristiancarlos@vibraenergia.com.br')

if __name__ == "__main__":
    main()

