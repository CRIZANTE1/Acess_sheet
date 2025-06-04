import streamlit as st
import pandas as pd
from app.ui_interface import vehicle_access_interface
from app.admin_page import admin_page
from app.summary_page import summary_page 
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_user_logged_in, is_admin
from app.operations import SheetOperations
from app.data_operations import get_cached_sheet_data, load_data_from_sheets

st.set_page_config(page_title="Controle de Acesso BAERI", layout="wide")

def main():
    load_data_from_sheets()

    if is_user_logged_in():
        show_user_header()
        show_logout_button()

        user_is_admin = is_admin()
        
        page_options = [] 
        if user_is_admin:
            page_options.append("Controle de Acesso") 
            page_options.append("Configurações do Sistema")
            page_options.append("Resumo")
        else:
            page_options.append("Resumo") 
            
        page = st.sidebar.selectbox("Escolha a página:", page_options)
        
        if page == "Controle de Acesso":
            vehicle_access_interface()
            
        elif page == "Configurações do Sistema":
            if user_is_admin:
                admin_page()
            else:
                st.error("Você não tem permissões para acessar esta página.")
        elif page == "Resumo": 
            summary_page()
    else:
        show_login_page()
        
    st.caption('Desenvolvido por Cristian Ferreira Carlos, CE9X,+551131038708, cristiancarlos@vibraenergia.com.br')

if __name__ == "__main__":
    main()








