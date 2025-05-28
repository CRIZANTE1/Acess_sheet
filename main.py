import streamlit as st
import pandas as pd
from app.ui_interface import vehicle_access_interface
from app.data_operations import mouth_consult
from app.admin_page import admin_page
from app.summary_page import summary_page 
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_user_logged_in, get_user_display_name, is_admin
from app.operations import SheetOperations

st.set_page_config(page_title="Controle de Acesso BAERI", layout="wide")

def load_data_from_sheets():
    if "df_acesso_veiculos" not in st.session_state:
        sheet_operations = SheetOperations()
        data = sheet_operations.carregar_dados()
        if data:
            columns = data[0]
            df = pd.DataFrame(data[1:], columns=columns)
            st.session_state.df_acesso_veiculos = df
        else:
            st.session_state.df_acesso_veiculos = pd.DataFrame(columns=[
            "ID", "Nome", "CPF", "Placa", "Marca do Carro", "Horário de Entrada", 
            "Data", "Empresa", "Status da Entrada", "Motivo do Bloqueio", "Aprovador", "Data do Primeiro Registro", "Horário de Saída"
        ])

def main():
    load_data_from_sheets()

    if is_user_logged_in():
        show_user_header()
        show_logout_button()

        user_is_admin = is_admin()
        
        page_options = [] # Começar com uma lista vazia
        if user_is_admin:
            page_options.append("Controle de Acesso") # Adicionar Controle de Acesso apenas para admin
            page_options.append("Configurações do Sistema")
        else:
            page_options.append("Resumo") # Adicionar opção de resumo para não administradores
            
        page = st.sidebar.selectbox("Escolha a página:", page_options)
        
        if page == "Controle de Acesso":
            vehicle_access_interface()
            mouth_consult()
        elif page == "Configurações do Sistema":
            if user_is_admin:
                admin_page()
            else:
                st.error("Você não tem permissões para acessar esta página.")
        elif page == "Resumo": # Adicionar a condição para a nova página de resumo
            summary_page()
    else:
        show_login_page()
        
    st.caption('Desenvolvido por Cristian Ferreira Carlos, CE9X,+551131038708, cristiancarlos@vibraenergia.com.br')

if __name__ == "__main__":
    main()

