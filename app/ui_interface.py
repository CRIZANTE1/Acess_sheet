# app/ui_interface.py

import streamlit as st
import pandas as pd
from datetime import datetime
from app.data_operations import add_record, update_exit_time, delete_record, check_blocked_records
from app.operations import SheetOperations
from app.utils import format_cpf, validate_cpf, get_sao_paulo_time

# --- Funções de Apoio ---
def get_person_status(name, df):
    if name is None or name == "--- Novo Cadastro ---" or name == "": return "Novo", None
    if df.empty: return "Novo", None
    person_records = df[df["Nome"] == name].copy()
    if person_records.empty: return "Novo", None
    person_records['Data_dt'] = pd.to_datetime(person_records['Data'], format='%d/%m/%Y', errors='coerce')
    person_records = person_records.sort_values(by=['Data_dt', 'Horário de Entrada'], ascending=[False, False])
    person_records.dropna(subset=['Data_dt'], inplace=True)
    if person_records.empty: return "Fora", None
    latest_record = person_records.iloc[0]
    horario_saida = latest_record.get("Horário de Saída", "")
    if pd.isna(horario_saida) or str(horario_saida).strip() == "": return "Dentro", latest_record
    else: return "Fora", latest_record

def show_people_inside(df, sheet_operations):
    st.subheader("Pessoas na Unidade")
    inside_df = df[pd.isna(df["Horário de Saída"]) | (df["Horário de Saída"] == "")].copy().sort_values("Nome")
    if inside_df.empty:
        st.info("Ninguém registrado na unidade no momento.")
        return
    for _, row in inside_df.iterrows():
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1: st.write(f"**{row['Nome']}**")
        with col2: st.caption(f"Entrada: {row['Data']} às {row['Horário de Entrada']}")
        with col3:
            record_id = row.get("ID", row['Nome'] + row['Data'])
            if st.button("Sair", key=f"exit_{record_id}", use_container_width=True):
                now = get_sao_paulo_time()
                success, message = update_exit_time(row['Nome'], now.strftime("%d/%m/%Y"), now.strftime("%H:%M"))
                if success:
                    st.success(f"Saída de {row['Nome']} registrada!")
                    data = sheet_operations.carregar_dados()
                    st.session_state.df_acesso_veiculos = pd.DataFrame(data[1:], columns=data[0])
                    st.rerun()
                else: st.error(message)

# --- Interface Principal ---
def vehicle_access_interface():
    st.title("Controle de Acesso BAERI")
    sheet_operations = SheetOperations()
    aprovadores_autorizados = sheet_operations.carregar_dados_aprovadores()
    
    if 'df_acesso_veiculos' not in st.session_state or st.session_state.df_acesso_veiculos.empty:
        data = sheet_operations.carregar_dados()
        if data: st.session_state.df_acesso_veiculos = pd.DataFrame(data[1:], columns=data[0]).fillna("")
        else: st.session_state.df_acesso_veiculos = pd.DataFrame(columns=["Nome"])
    df = st.session_state.df_acesso_veiculos

    blocked_info = check_blocked_records(df)
    if blocked_info: st.error("Atenção! Pessoas com bloqueio ativo:\n\n" + blocked_info)

    col_main, col_sidebar = st.columns([2, 1])
    with col_main:
        st.header("Painel de Registro")
        unique_names = sorted(df["Nome"].unique()) if "Nome" in df.columns else []
        search_options = ["--- Novo Cadastro ---"] + unique_names
        selected_name = st.selectbox("Busque por um nome ou selecione 'Novo Cadastro':", options=search_options, index=0, key="person_selector")
        status, latest_record = get_person_status(selected_name, df)
        
        if status == "Dentro":
            st.info(f"**{selected_name}** está **DENTRO** da unidade.")
            st.write(f"**Entrada em:** {latest_record['Data']} às {latest_record['Horário de Entrada']}")
            if st.button(f"✅ Registrar Saída de {selected_name}", use_container_width=True, type="primary"):
                now = get_sao_paulo_time()
                success, message = update_exit_time(selected_name, now.strftime("%d/%m/%Y"), now.strftime("%H:%M"))
                if success:
                    st.success(message)
                    data = sheet_operations.carregar_dados()
                    st.session_state.df_acesso_veiculos = pd.DataFrame(data[1:], columns=data[0])
                    st.session_state.person_selector = "--- Novo Cadastro ---"
                    st.rerun()
                else: st.error(message)
        elif status == "Fora":
            st.success(f"**{selected_name}** está **FORA** da unidade.")
            st.write(f"**Última saída em:** {latest_record.get('Data', 'N/A')} às {latest_record.get('Horário de Saída', 'N/A')}")
            with st.form(key="reentry_form"):
                st.write("Registrar nova entrada:")
                placa = st.text_input("Placa", value=str(latest_record.get("Placa", "")))
                empresa = st.text_input("Empresa", value=str(latest_record.get("Empresa", "")))
                aprovador = st.selectbox("Aprovador:", options=aprovadores_autorizados)
                if st.form_submit_button(f"▶️ Registrar Entrada de {selected_name}", use_container_width=True, type="primary"):
                    now = get_sao_paulo_time()
                    add_record(name=selected_name, cpf=str(latest_record.get("CPF", "")), placa=placa, marca_carro=str(latest_record.get("Marca do Carro", "")), horario_entrada=now.strftime("%H:%M"), data=now.strftime("%d/%m/%Y"), empresa=empresa, status="Autorizado", motivo="", aprovador=aprovador)
                    data = sheet_operations.carregar_dados()
                    st.session_state.df_acesso_veiculos = pd.DataFrame(data[1:], columns=data[0])
                    st.session_state.person_selector = selected_name
                    st.rerun()
        elif status == "Novo":
            st.info("Pessoa não encontrada. Preencha o formulário.")
            with st.form(key="new_visitor_form"):
                st.write("**Formulário de Primeiro Acesso**")
                name = st.text_input("Nome Completo:")
                cpf = st.text_input("CPF:")
                empresa = st.text_input("Empresa:")
                status_entrada = st.selectbox("Status", ["Autorizado", "Bloqueado"], index=0)
                motivo_bloqueio = st.text_input("Motivo (se Bloqueado):") if status_entrada == "Bloqueado" else ""
                aprovador = st.selectbox("Aprovador:", options=aprovadores_autorizados) if status_entrada == "Autorizado" else ""
                placa = st.text_input("Placa (Opcional):")
                marca_carro = st.text_input("Marca (Opcional):")
                if st.form_submit_button("➕ Cadastrar e Registrar", use_container_width=True, type="primary"):
                    if not name or not cpf or not empresa or (status_entrada == "Autorizado" and not aprovador): st.error("Preencha os campos obrigatórios.")
                    elif not validate_cpf(cpf): st.error("CPF inválido.")
                    else:
                        now = get_sao_paulo_time()
                        add_record(name=name, cpf=format_cpf(cpf), placa=placa, marca_carro=marca_carro, horario_entrada=now.strftime("%H:%M"), data=now.strftime("%d/%m/%Y"), empresa=empresa, status=status_entrada, motivo=motivo_bloqueio, aprovador=aprovador)
                        data = sheet_operations.carregar_dados()
                        st.session_state.df_acesso_veiculos = pd.DataFrame(data[1:], columns=data[0])
                        st.session_state.person_selector = name
                        st.rerun()

    with col_sidebar:
        if not df.empty: show_people_inside(df, sheet_operations)
    
    st.divider()

    with st.expander("Gerenciamento de Registros (Bloquear, Deletar)"):
        st.warning("Use para ações administrativas como bloquear ou deletar registros incorretos.")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Bloquear Pessoa")
            person_to_block = st.selectbox("Selecione para bloquear:", options=[""] + unique_names, key="block_person")
            if person_to_block:
                motivo = st.text_input("Motivo do bloqueio:", key="block_reason")
                if st.button("Aplicar Bloqueio", key="apply_block"):
                    if motivo:
                        now = get_sao_paulo_time()
                        # Pega o último registro da pessoa no DataFrame
                        last_record = df[df["Nome"] == person_to_block].sort_values("Data").iloc[-1]
                        
                        # --- CORREÇÃO APLICADA AQUI ---
                        # Converte explicitamente os valores para string antes de passar para add_record
                        add_record(
                            name=str(person_to_block),
                            cpf=str(last_record.get("CPF", "")),
                            placa="",  # Bloqueio não precisa de placa
                            marca_carro="",
                            horario_entrada=now.strftime("%H:%M"),
                            data=now.strftime("%d/%m/%Y"),
                            empresa=str(last_record.get("Empresa", "")),
                            status="Bloqueado",
                            motivo=motivo,
                            aprovador=""
                        )
                        data = sheet_operations.carregar_dados()
                        st.session_state.df_acesso_veiculos = pd.DataFrame(data[1:], columns=data[0])
                        st.rerun()
                    else: st.error("O motivo é obrigatório.")
        with col2:
            st.subheader("Deletar Último Registro")
            person_to_delete = st.selectbox("Selecione para deletar último registro:", options=[""] + unique_names, key="delete_person")
            if person_to_delete:
                if st.button("Deletar Último Registro", key="apply_delete", type="secondary"):
                    records = df[df["Nome"] == person_to_delete].copy()
                    records['Data_dt'] = pd.to_datetime(records['Data'], format='%d/%m/%Y', errors='coerce')
                    last_record = records.sort_values(by='Data_dt', ascending=False).iloc[0]
                    if delete_record(person_to_delete, last_record['Data']):
                        st.success(f"Último registro de {person_to_delete} deletado.")
                        data = sheet_operations.carregar_dados()
                        st.session_state.df_acesso_veiculos = pd.DataFrame(data[1:], columns=data[0])
                        st.rerun()
                    else: st.error("Falha ao deletar registro.")
    
    with st.expander("Visualizar todos os registros"):
        st.dataframe(df.fillna(""), use_container_width=True)














