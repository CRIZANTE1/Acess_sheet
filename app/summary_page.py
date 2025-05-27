import streamlit as st
import pandas as pd
from app.data_operations import mouth_consult # Reutilizando a função de consulta mensal

def summary_page():
    st.title("Resumo do Controle de Acesso")

    st.write("Aqui você pode visualizar um resumo dos dados de acesso de veículos.")

    mouth_consult()

    st.subheader("Contador de Redução de Papel")

    if "df_acesso_veiculos" in st.session_state:
        num_registros = len(st.session_state.df_acesso_veiculos)
    else:
        num_registros = 0
        st.warning("Dados de acesso de veículos não encontrados na sessão.")

    folhas_economizadas = num_registros // 10  
    arvores_salvas = folhas_economizadas // 30 

    dados_reducao_papel = {
        "Métrica": ["Documentos Digitalizados (Registros)", "Economia de Papel (Folhas)", "Árvores Salvas (Estimativa)"],
        "Valor": [num_registros, folhas_economizadas, arvores_salvas]
    }
    df_reducao_papel = pd.DataFrame(dados_reducao_papel)

    st.table(df_reducao_papel)

    st.info("Para realizar edições ou solicitar novas funcionalidades, por favor, entre em contato com o desenvolvedor.")

    if st.button("Voltar para Página Principal"):
        st.session_state.pagina_atual = 'principal'
        st.rerun()
