import streamlit as st
import pandas as pd
import os
import json
import bcrypt
from datetime import datetime
from auth import is_admin

def admin_page():
    # Verificar se o usuário é administrador
    if not is_admin():
        st.error("Acesso negado. Esta página é restrita a administradores.")
        # Botão para voltar à página principal
        if st.button("Voltar para Página Principal"):
            st.session_state.pagina_atual = 'principal'
            st.rerun()
        return

    st.title("Painel de Administração")

    # Menu lateral de navegação administrativa
    opcao_admin = st.sidebar.radio(
        "Selecione a função:",
        ["Configurações do Sistema", "Voltar para Principal"]
    )

    # Botão de voltar para página principal
    if opcao_admin == "Voltar para Principal":
        st.session_state.pagina_atual = 'principal'
        st.rerun()
    else:
        st.header("Configurações do Sistema")

        # Exibir informações de configuração do sistema
        st.subheader("Informações de Login OIDC")

        # Informações sobre o provedor configurado
        st.json({
            "status": "Ativo",
            "provedor": "Configurado no secrets.toml"
        })

        st.markdown("""
        Para alterar as configurações de login OIDC:

        1. Edite o arquivo `.streamlit/secrets.toml`
        2. Configure as credenciais do provedor OIDC desejado
        3. Reinicie a aplicação para que as alterações tenham efeito
        """)

        # Status do sistema
        st.subheader("Status do Sistema")
        st.json({
            "sistema": "Controle de Acesso de Veículos",
            "versão": "1.0.0",
            "modo_login": "OIDC (OpenID Connect)",
            "status": "Ativo",
            "Developer": "Cristian Ferreira Carlos",
            "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
