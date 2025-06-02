import streamlit as st
import pandas as pd
from datetime import datetime

def get_month_name(month):
    """Retorna o nome do mês em português"""
    meses = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    return meses.get(month, "")

def month_consult(selected_month=None, selected_year=None):
    """Mostra estatísticas mensais dos acessos"""
    if "df_acesso_veiculos" in st.session_state:
        df = st.session_state.df_acesso_veiculos.copy()
        
        # Converter a coluna de data para datetime
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y')
        
        # Se não foi especificado mês/ano, usar o atual
        if selected_month is None:
            selected_month = datetime.now().month
        if selected_year is None:
            selected_year = datetime.now().year
        
        # Filtrar registros do mês selecionado
        df_month = df[
            (df['Data'].dt.month == selected_month) & 
            (df['Data'].dt.year == selected_year)
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

def consulta_nome_mes(selected_month=None, selected_year=None):
    """Consulta todas as entradas de uma pessoa específica no mês"""
    if "df_acesso_veiculos" in st.session_state:
        df = st.session_state.df_acesso_veiculos.copy()
        
        # Converter a coluna de data para datetime
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y')
        
        # Se não foi especificado mês/ano, usar o atual
        if selected_month is None:
            selected_month = datetime.now().month
        if selected_year is None:
            selected_year = datetime.now().year
        
        # Lista de nomes únicos para seleção
        nomes_unicos = sorted(df['Nome'].unique())
        nome_selecionado = st.selectbox("Selecione o nome para consulta:", nomes_unicos)
        
        if nome_selecionado:
            # Filtrar registros do mês selecionado para o nome específico
            df_pessoa = df[
                (df['Data'].dt.month == selected_month) & 
                (df['Data'].dt.year == selected_year) &
                (df['Nome'] == nome_selecionado)
            ]
            
            if df_pessoa.empty:
                st.warning(f"Nenhum registro encontrado para {nome_selecionado} em {get_month_name(selected_month)} de {selected_year}.")
            else:
                st.success(f"Encontrados {len(df_pessoa)} registros para {nome_selecionado} em {get_month_name(selected_month)} de {selected_year}:")
                
                # Calcular estatísticas da pessoa
                acessos_autorizados = len(df_pessoa[df_pessoa['Status da Entrada'] == 'Autorizado'])
                acessos_bloqueados = len(df_pessoa[df_pessoa['Status da Entrada'] == 'Bloqueado'])
                
                # Mostrar estatísticas em colunas
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total de Acessos", len(df_pessoa))
                with col2:
                    st.metric("Acessos Autorizados", acessos_autorizados)
                with col3:
                    st.metric("Acessos Bloqueados", acessos_bloqueados)
                
                # Ordenar por data e hora
                df_pessoa = df_pessoa.sort_values(['Data', 'Horário de Entrada'])
                
                # Selecionar e renomear colunas para exibição
                colunas_exibir = [
                    'Data', 'Horário de Entrada', 'Horário de Saída',
                    'Empresa', 'Status da Entrada', 'Motivo do Bloqueio', 'Aprovador'
                ]
                
                # Formatar a data de volta para dd/mm/yyyy para exibição
                df_exibir = df_pessoa[colunas_exibir].copy()
                df_exibir['Data'] = df_exibir['Data'].dt.strftime('%d/%m/%Y')
                
                # Exibir tabela com os registros
                st.dataframe(
                    df_exibir,
                    hide_index=True,
                    use_container_width=True
                )

def summary_page():
    st.title("Resumo do Controle de Acesso")

    st.write("Aqui você pode visualizar um resumo dos dados de acesso de veículos.")

    # Seleção de mês e ano
    col1, col2 = st.columns(2)
    with col1:
        meses = {get_month_name(i): i for i in range(1, 13)}
        mes_selecionado = st.selectbox(
            "Selecione o mês:",
            options=list(meses.keys()),
            index=datetime.now().month - 1
        )
    with col2:
        ano_atual = datetime.now().year
        ano_selecionado = st.selectbox(
            "Selecione o ano:",
            options=range(ano_atual - 2, ano_atual + 1),
            index=2
        )

    # Converter nome do mês para número
    mes_numero = meses[mes_selecionado]

    # Criar abas para diferentes visualizações
    tab1, tab2 = st.tabs(["Estatísticas Gerais", "Consulta por Nome"])
    
    with tab1:
        # Mostrar estatísticas mensais
        st.subheader(f"Estatísticas de {mes_selecionado} de {ano_selecionado}")
        month_consult(mes_numero, ano_selecionado)

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
        
    with tab2:
        st.subheader(f"Consulta de Acessos por Nome - {mes_selecionado} de {ano_selecionado}")
        consulta_nome_mes(mes_numero, ano_selecionado)

    st.info("Para realizar edições ou solicitar novas funcionalidades, por favor, entre em contato com o desenvolvedor.")

    if st.button("Voltar para Página Principal"):
        st.session_state.pagina_atual = 'principal'
        st.rerun()

