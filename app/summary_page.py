
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
    if "df_acesso_veiculos" in st.session_state and not st.session_state.df_acesso_veiculos.empty:
        df = st.session_state.df_acesso_veiculos.copy()
        
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        
        if selected_month is None: selected_month = datetime.now().month
        if selected_year is None: selected_year = datetime.now().year
        
        df_month = df[
            (df['Data'].dt.month == selected_month) & 
            (df['Data'].dt.year == selected_year)
        ]
        
        total_acessos = len(df_month)
        acessos_autorizados = len(df_month[df_month['Status da Entrada'] == 'Autorizado'])
        acessos_bloqueados = len(df_month[df_month['Status da Entrada'] == 'Bloqueado'])
        
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Total de Acessos no Mês", total_acessos)
        with col2: st.metric("Acessos Autorizados", acessos_autorizados)
        with col3: st.metric("Acessos Bloqueados", acessos_bloqueados)
        
        if not df_month.empty:
            acessos_por_dia = df_month.groupby(df_month['Data'].dt.day).size()
            st.bar_chart(acessos_por_dia)
            st.caption("Acessos por dia do mês")

def consulta_nome_mes(selected_month=None, selected_year=None):
    """Consulta todas as entradas de uma pessoa específica no mês"""
    if "df_acesso_veiculos" in st.session_state and not st.session_state.df_acesso_veiculos.empty:
        df = st.session_state.df_acesso_veiculos.copy()
        
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        
        if selected_month is None: selected_month = datetime.now().month
        if selected_year is None: selected_year = datetime.now().year
        
        nomes_unicos = sorted(df['Nome'].unique())
        if not nomes_unicos:
            st.warning("Nenhum nome encontrado nos registros.")
            return
            
        nome_selecionado = st.selectbox("Selecione o nome para consulta:", nomes_unicos)
        
        if nome_selecionado:
            df_pessoa = df[
                (df['Data'].dt.month == selected_month) & 
                (df['Data'].dt.year == selected_year) &
                (df['Nome'] == nome_selecionado)
            ]
            
            if df_pessoa.empty:
                st.warning(f"Nenhum registro encontrado para {nome_selecionado} em {get_month_name(selected_month)} de {selected_year}.")
            else:
                st.success(f"Encontrados {len(df_pessoa)} registros para {nome_selecionado} em {get_month_name(selected_month)} de {selected_year}:")
                
                acessos_autorizados = len(df_pessoa[df_pessoa['Status da Entrada'] == 'Autorizado'])
                acessos_bloqueados = len(df_pessoa[df_pessoa['Status da Entrada'] == 'Bloqueado'])
                
                col1, col2, col3 = st.columns(3)
                with col1: st.metric("Total de Acessos", len(df_pessoa))
                with col2: st.metric("Acessos Autorizados", acessos_autorizados)
                with col3: st.metric("Acessos Bloqueados", acessos_bloqueados)
                
                df_pessoa = df_pessoa.sort_values(['Data', 'Horário de Entrada'])
                
                colunas_exibir = ['Data', 'Horário de Entrada', 'Horário de Saída', 'Empresa', 'Status da Entrada', 'Motivo do Bloqueio', 'Aprovador']
                df_exibir = df_pessoa[colunas_exibir].copy()
                df_exibir['Data'] = df_exibir['Data'].dt.strftime('%d/%m/%Y')
                
                st.dataframe(df_exibir, hide_index=True, use_container_width=True)

def summary_page():
    st.title("Resumo do Controle de Acesso")
    st.write("Aqui você pode visualizar um resumo dos dados de acesso de veículos.")

    # --- Seção de Filtros (sem alterações) ---
    col1, col2 = st.columns(2)
    with col1:
        meses = {get_month_name(i): i for i in range(1, 13)}
        mes_selecionado = st.selectbox("Selecione o mês:", options=list(meses.keys()), index=datetime.now().month - 1)
    with col2:
        ano_atual = datetime.now().year
        ano_selecionado = st.selectbox("Selecione o ano:", options=range(ano_atual - 5, ano_atual + 1), index=5)

    mes_numero = meses[mes_selecionado]

    # --- Abas de Visualização (sem alterações) ---
    tab1, tab2 = st.tabs(["Estatísticas Gerais", "Consulta por Nome"])
    
    with tab1:
        st.subheader(f"Estatísticas de {mes_selecionado} de {ano_selecionado}")
        month_consult(mes_numero, ano_selecionado)
        
        st.divider() # Adiciona um separador visual
        
        # --- (CORRIGIDO) Contador de Redução de Papel ---
        st.subheader("Impacto Ambiental da Digitalização")

        if "df_acesso_veiculos" in st.session_state:
            total_registros = len(st.session_state.df_acesso_veiculos)
        else:
            total_registros = 0
            st.warning("Dados de acesso não encontrados.")

        # Lógica de cálculo ajustada:
        # Premissa 1: Cada folha de papel físico continha 10 registros.
        # Premissa 2: 1 árvore produz aproximadamente 8.000 folhas de papel.
        registros_por_folha = 10
        folhas_por_arvore = 8000

        folhas_economizadas = total_registros // registros_por_folha
        
        # Para o cálculo de árvores, usamos o número de folhas, não o de registros.
        # Usamos a divisão de ponto flutuante para mostrar frações de árvores salvas.
        arvores_salvas = folhas_economizadas / folhas_por_arvore

        # Exibição em colunas para um visual mais limpo
        col_a, col_b, col_c = st.columns(3)
        col_a.metric(label="Registros Digitais", value=f"{total_registros:,}".replace(",", "."))
        col_b.metric(label="Folhas de Papel Economizadas", value=f"{folhas_economizadas:,}".replace(",", "."))
        
        # Formata o número de árvores salvas para ter 3 casas decimais
        col_c.metric(label="Árvores Salvas (Estimativa)", value=f"{arvores_salvas:.3f}".replace(".", ","))

        st.caption(f"Cálculo baseado na premissa de {registros_por_folha} registros por folha e {folhas_por_arvore:,} folhas por árvore.".replace(",", "."))
        
    with tab2:
        st.subheader(f"Consulta de Acessos por Nome - {mes_selecionado} de {ano_selecionado}")
        consulta_nome_mes(mes_numero, ano_selecionado)

    st.info("Para realizar edições ou solicitar novas funcionalidades, por favor, entre em contato com o desenvolvedor.")
