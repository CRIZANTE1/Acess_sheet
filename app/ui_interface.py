# app/ui_interface.py

import streamlit as st
import pandas as pd
from datetime import datetime
from app.data_operations import add_record, update_exit_time
from app.operations import SheetOperations
from app.utils import format_cpf, validate_cpf

# --- Funções de Apoio para a Nova Interface ---

def get_person_status(name, df):
    """Verifica o status mais recente de uma pessoa (Dentro, Fora, Novo)."""
    if name is None or name == "--- Novo Cadastro ---":
        return "Novo", None

    # Garante que o dataframe não esteja vazio
    if df.empty:
        return "Novo", None

    person_records = df[df["Nome"] == name].copy()
    if person_records.empty:
        return "Novo", None

    # Ordenar para garantir que o registro mais recente esteja no topo
    person_records['Data_dt'] = pd.to_datetime(person_records['Data'], format='%d/%m/%Y', errors='coerce')
    person_records = person_records.sort_values(by=['Data_dt', 'Horário de Entrada'], ascending=[False, False])
    
    # Remove registros onde a data não pôde ser convertida e pega o mais recente
    person_records.dropna(subset=['Data_dt'], inplace=True)
    if person_records.empty:
        return "Fora", None # Se todos os registros tinham data inválida, assume que está fora

    latest_record = person_records.iloc[0]
    
    # Verifica se o Horário de Saída está preenchido
    horario_saida = latest_record.get("Horário de Saída", "")
    if pd.isna(horario_saida) or str(horario_saida).strip() == "":
        return "Dentro", latest_record
    else:
        return "Fora", latest_record

def show_people_inside(df, sheet_operations):
    """Mostra uma lista de pessoas atualmente dentro com um botão de saída rápida."""
    st.subheader("Pessoas na Unidade")
    
    # Filtra registros sem horário de saída
    inside_df = df[pd.isna(df["Horário de Saída"]) | (df["Horário de Saída"] == "")].copy()
    
    # Ordena por nome para facilitar a visualização
    inside_df = inside_df.sort_values("Nome")

    if inside_df.empty:
        st.info("Ninguém registrado na unidade no momento.")
        return

    for _, row in inside_df.iterrows():
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.write(f"**{row['Nome']}**")
        with col2:
            st.caption(f"Entrada: {row['Data']} às {row['Horário de Entrada']}")
        with col3:
            # Usamos o ID do registro para a chave do botão, garantindo que seja único
            record_id = row.get("ID", row['Nome'] + row['Data']) # Fallback se a coluna ID não existir
            if st.button("Sair", key=f"exit_{record_id}", use_container_width=True):
                now = datetime.now()
                success, message = update_exit_time(
                    row['Nome'], 
                    now.strftime("%d/%m/%Y"), 
                    now.strftime("%H:%M")
                )
                if success:
                    st.success(f"Saída de {row['Nome']} registrada!")
                    # Recarregar dados e a página
                    st.session_state.df_acesso_veiculos = pd.DataFrame(sheet_operations.carregar_dados()[1:], columns=sheet_operations.carregar_dados()[0])
                    st.rerun()
                else:
                    st.error(message)

# --- A Nova Interface Principal ---

def vehicle_access_interface():
    st.title("Controle de Acesso BAERI")

    sheet_operations = SheetOperations()
    aprovadores_autorizados = sheet_operations.carregar_dados_aprovadores()
    
    # Garante que os dados estão carregados no session_state
    if 'df_acesso_veiculos' not in st.session_state:
        data_from_sheet = sheet_operations.carregar_dados()
        if data_from_sheet:
            columns = data_from_sheet[0]
            df_temp = pd.DataFrame(data_from_sheet[1:], columns=columns)
            st.session_state.df_acesso_veiculos = df_temp.fillna("")
        else:
            st.session_state.df_acesso_veiculos = pd.DataFrame()

    df = st.session_state.df_acesso_veiculos if 'df_acesso_veiculos' in st.session_state and not st.session_state.df_acesso_veiculos.empty else pd.DataFrame()

    # --- Layout da Página ---
    col_main, col_sidebar = st.columns([2, 1])

    with col_main:
        st.header("Painel de Registro")

        # --- Campo de Busca ---
        unique_names = sorted(df["Nome"].unique()) if not df.empty else []
        search_options = ["--- Novo Cadastro ---"] + unique_names
        
        selected_name = st.selectbox(
            "Busque por um nome ou selecione 'Novo Cadastro':",
            options=search_options,
            index=0, # Começa em "Novo Cadastro"
            key="person_selector"
        )
        
        status, latest_record = get_person_status(selected_name, df)
        
        # --- Painel de Ações Contextual ---
        
        if status == "Dentro":
            st.info(f"**{selected_name}** está **DENTRO** da unidade.")
            st.write(f"**Entrada registrada em:** {latest_record['Data']} às {latest_record['Horário de Entrada']}")
            
            if st.button(f"✅ Registrar Saída de {selected_name}", use_container_width=True, type="primary"):
                now = datetime.now()
                success, message = update_exit_time(
                    selected_name, 
                    now.strftime("%d/%m/%Y"), 
                    now.strftime("%H:%M")
                )
                if success:
                    st.success(message)
                    st.session_state.df_acesso_veiculos = pd.DataFrame(sheet_operations.carregar_dados()[1:], columns=sheet_operations.carregar_dados()[0])
                    st.session_state.person_selector = "--- Novo Cadastro ---" # Reset selector
                    st.rerun()
                else:
                    st.error(message)

        elif status == "Fora":
            st.success(f"**{selected_name}** está **FORA** da unidade.")
            st.write(f"**Última saída registrada em:** {latest_record.get('Data', 'N/A')} às {latest_record.get('Horário de Saída', 'N/A')}")

            with st.form(key="reentry_form"):
                st.write("Registrar nova entrada (dados pré-preenchidos):")
                
                # Pré-preenche os dados do último registro
                placa = st.text_input("Placa do Veículo", value=latest_record.get("Placa", ""))
                marca_carro = st.text_input("Marca do Veículo", value=latest_record.get("Marca do Carro", ""))
                empresa = st.text_input("Empresa", value=latest_record.get("Empresa", ""))
                aprovador = st.selectbox("Aprovador:", options=aprovadores_autorizados)

                submit_button = st.form_submit_button(f"▶️ Registrar Entrada de {selected_name}", use_container_width=True, type="primary")

                if submit_button:
                    now = datetime.now()
                    success = add_record(
                        name=selected_name,
                        cpf=latest_record.get("CPF", ""),
                        placa=placa,
                        marca_carro=marca_carro,
                        horario_entrada=now.strftime("%H:%M"),
                        data=now.strftime("%d/%m/%Y"),
                        empresa=empresa,
                        status="Autorizado",
                        motivo="",
                        aprovador=aprovador
                    )
                    if success:
                        st.session_state.df_acesso_veiculos = pd.DataFrame(sheet_operations.carregar_dados()[1:], columns=sheet_operations.carregar_dados()[0])
                        st.session_state.person_selector = selected_name # Mantém a pessoa selecionada
                        st.rerun()

        elif status == "Novo":
            st.info("Pessoa não encontrada. Preencha o formulário para o primeiro acesso.")
            with st.form(key="new_visitor_form"):
                st.write("**Formulário de Primeiro Acesso**")
                
                name = st.text_input("Nome Completo:")
                cpf = st.text_input("CPF:")
                empresa = st.text_input("Empresa:")
                placa = st.text_input("Placa do Veículo (Opcional):")
                marca_carro = st.text_input("Marca do Veículo (Opcional):")
                aprovador = st.selectbox("Aprovador:", options=aprovadores_autorizados)
                
                submit_button = st.form_submit_button("➕ Cadastrar e Registrar Entrada", use_container_width=True, type="primary")

                if submit_button:
                    if not name or not cpf or not empresa or not aprovador:
                        st.error("Preencha todos os campos obrigatórios: Nome, CPF, Empresa e Aprovador.")
                    elif not validate_cpf(cpf):
                        st.error("CPF inválido. Verifique o número digitado.")
                    else:
                        now = datetime.now()
                        success = add_record(
                            name=name,
                            cpf=format_cpf(cpf),
                            placa=placa,
                            marca_carro=marca_carro,
                            horario_entrada=now.strftime("%H:%M"),
                            data=now.strftime("%d/%m/%Y"),
                            empresa=empresa,
                            status="Autorizado",
                            motivo="",
                            aprovador=aprovador
                        )
                        if success:
                            st.session_state.df_acesso_veiculos = pd.DataFrame(sheet_operations.carregar_dados()[1:], columns=sheet_operations.carregar_dados()[0])
                            st.session_state.person_selector = name # Seleciona a pessoa recém-cadastrada
                            st.rerun()

    with col_sidebar:
        # --- Painel de Saída Rápida ---
        if not df.empty:
            show_people_inside(df, sheet_operations)
    
    st.divider()
    
    with st.expander("Visualizar todos os registros"):
         st.dataframe(st.session_state.df_acesso_veiculos.fillna(""), use_container_width=True)

    # O briefing pode ficar em um expander no final, menos proeminente
    with st.expander("Lembretes e Briefing de Segurança"):
        st.write("**ATENÇÃO:**\n\n"
                 "1. O acesso de veículos deve ser controlado rigorosamente para garantir a segurança do local.\n"
                 "2. Apenas pessoas autorizadas podem liberar o acesso.\n"
                 "3. Em caso de dúvidas, entre em contato com o responsável pela segurança.\n"
                 "4. Mantenha sempre os dados atualizados e verifique as informações antes de liberar o acesso."
                 "\n5. Sempre que for a primeira vez do visitante ou um ano do acesso repassar o video.\n")
        try:
            st.video("https://youtu.be/QqUkeTucwkI")
        except Exception as e:
            st.error(f"Erro ao carregar o vídeo: {e}")


























