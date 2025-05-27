import streamlit as st
import pandas as pd
from app.data_operations import mouth_consult # Reutilizando a função de consulta mensal

def summary_page():
    st.title("Resumo do Controle de Acesso")

    st.write("Aqui você pode visualizar um resumo dos dados de acesso de veículos.")

    # Reutilizar a lógica de consulta mensal ou exibir dados de outra forma
    # Por enquanto, vou chamar a função mouth_consult como exemplo.
    # Dependendo do que o usuário quer como "resumo", isso pode precisar ser ajustado.
    mouth_consult()

    # Adicionar um botão para voltar, se necessário
    if st.button("Voltar para Página Principal"):
        st.session_state.pagina_atual = 'principal'
        st.rerun()
