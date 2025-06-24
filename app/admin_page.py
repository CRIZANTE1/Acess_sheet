import streamlit as st
from datetime import datetime
# A importação agora é direta, sem causar problemas
from auth.auth_utils import is_admin

def admin_page():
    # Verificar se o usuário é administrador
    if not is_admin():
        st.error("Acesso negado. Esta página é restrita a administradores.")
        # Botão para voltar à página principal
        if st.button("Voltar para Página Principal"):
            # Para simplificar, vamos usar st.switch_page se disponível ou apenas orientar o usuário
            st.warning("Por favor, selecione 'Controle de Acesso' no menu lateral para voltar.")
        return

    st.title("Painel de Administração")

    # Menu lateral de navegação administrativa
    # Este menu já está no main.py, então podemos simplificar aqui.
    st.header("Configurações e Status do Sistema")

    # Exibir informações de configuração do sistema
    st.subheader("Informações de Login OIDC")
    st.json({
        "status": "Ativo",
        "provedor": "Configurado no secrets.toml"
    })
    st.markdown("""
    Para alterar as configurações de login OIDC, edite o arquivo `.streamlit/secrets.toml` e reinicie a aplicação.
    """)

    # Status do sistema
    st.subheader("Status do Sistema")
    st.json({
        "sistema": "Controle de Acesso de Pessoas e Veículos",
        "versão": "2.0.0", # Atualizei a versão para refletir as melhorias
        "modo_login": "OIDC (OpenID Connect)",
        "status": "Operacional",
        "Developer": "Cristian Ferreira Carlos",
        "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
