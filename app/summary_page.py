import streamlit as st
import pandas as pd
from datetime import datetime

def month_consult():
    """Mostra estatísticas mensais dos acessos"""
    if "df_acesso_veiculos" in st.session_state:
        df = st.session_state.df_acesso_veiculos
        
        # Converter a coluna de data para datetime
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y')
        
        # Obter o mês atual
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Filtrar registros do mês atual
        df_month = df[
            (df['Data'].dt.month == current_month) & 
            (df['Data'].dt.year == current_year)
        ]
        
        # Calcular estatísticas
        total_acessos = len(df_month)
        acessos_autorizados = len(df_month[df_month['Status da Entrada'] == 'Autorizado'])
        acessos_bloqueados = len(df_month[df_month['Status da Entrada'] == 'Bloqueado'])
        
        # Mostrar estatísticas em colunas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de Acessos no Mês", total_acessos)
        
        with col2:
            st.metric("Acessos Autorizados", acessos_autorizados)
        
        with col3:
            st.metric("Acessos Bloqueados", acessos_bloqueados)
        
        # Mostrar gráfico de barras com acessos por dia
        if not df_month.empty:
            acessos_por_dia = df_month.groupby(df_month['Data'].dt.day).size()
            st.bar_chart(acessos_por_dia)
            st.caption("Acessos por dia do mês")

def summary_page():
    st.title("Resumo do Controle de Acesso")

    st.write("Aqui você pode visualizar um resumo dos dados de acesso de veículos.")

    # Mostrar estatísticas mensais
    st.subheader("Estatísticas do Mês Atual")
    month_consult()

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
