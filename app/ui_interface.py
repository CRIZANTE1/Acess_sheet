import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from app.data_operations import (
    add_record, 
    update_exit_time, 
    delete_record_by_id, 
    check_blocked_records,
    is_entity_blocked 
)
from app.operations import SheetOperations
from app.utils import format_cpf, validate_cpf, get_sao_paulo_time
from auth.auth_utils import get_user_display_name, is_admin
from app.logger import log_action

def get_person_status(name, df):
    """Verifica o status mais recente de uma pessoa (Dentro, Fora, Bloqueado, Novo)."""
    if not name or name == "--- Novo Cadastro ---":
        return "Novo", None
    if df.empty:
        return "Novo", None
    
    person_records = df[df["Nome"] == name].copy()
    if person_records.empty:
        return "Novo", None
    
    latest_record = person_records.iloc[0]
    status_entrada = latest_record.get("Status da Entrada", "")
    horario_saida = latest_record.get("Horário de Saída", "")

    if status_entrada in ["Bloqueado", "Pendente de Aprovação"]:
        return "Bloqueado", latest_record

    if pd.isna(horario_saida) or str(horario_saida).strip() == "":
        return "Dentro", latest_record
    else:
        return "Fora", latest_record

def show_people_inside(df, sheet_operations):
    """Mostra uma lista de pessoas atualmente dentro com um botão de saída rápida."""
    st.subheader("Pessoas na Unidade")
    inside_df = df[
        (df["Status da Entrada"] == "Autorizado") & 
        (pd.isna(df["Horário de Saída"]) | (df["Horário de Saída"] == ""))
    ].copy().sort_values("Nome")

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
            record_id = row.get("ID")
            if record_id:
                if st.button("Sair", key=f"exit_{record_id}", use_container_width=True):
                    now = get_sao_paulo_time()
                    success, message = update_exit_time(row['Nome'], now.strftime("%d/%m/%Y"), now.strftime("%H:%M"))
                    if success:
                        log_action("REGISTER_EXIT", f"Registrou saída para '{row['Nome']}'.")
                        st.success(f"Saída de {row['Nome']} registrada!"); st.rerun()
                    else:
                        st.error(message)

def vehicle_access_interface():
    """Renderiza a interface principal de controle de acesso."""
    st.title("Controle de Acesso BAERI")
    sheet_operations = SheetOperations()
    
    with st.expander("Briefing de Segurança e Lembretes", expanded=True):
        st.write("""
        **ATENÇÃO:**
        1. O acesso de veículos deve ser controlado rigorosamente para garantir a segurança do local.
        2. Apenas pessoas autorizadas podem liberar o acesso.
        3. Em caso de dúvidas, entre em contato com o responsável pela segurança.
        4. Mantenha sempre os dados atualizados e verifique as informações antes de liberar o acesso.
        5. **Sempre que for a primeira vez do visitante ou um ano desde o último acesso, repassar o vídeo abaixo.**
        """)
        try:
            st.video("https://youtu.be/QqUkeTucwkI")
        except Exception as e:
            st.error(f"Erro ao carregar o vídeo: {e}")
    
    if 'df_acesso_veiculos' not in st.session_state or st.session_state.df_acesso_veiculos.empty:
        data = sheet_operations.carregar_dados()
        df = pd.DataFrame(data[1:], columns=data[0]).fillna("") if data else pd.DataFrame()
    else:
        df = st.session_state.df_acesso_veiculos

    if not df.empty:
        df['Data_dt'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
        df = df.sort_values(by=['Data_dt', 'Horário de Entrada'], ascending=[False, False]).drop(columns=['Data_dt'])
    
    st.session_state.df_acesso_veiculos = df
        
    aprovadores_autorizados = sheet_operations.carregar_dados_aprovadores()
    blocked_info = check_blocked_records(df)
    if blocked_info: 
        st.error("Atenção! Pessoas com restrição de acesso:\n\n" + blocked_info)

    col_main, col_sidebar = st.columns([2, 1])
    with col_main:
        st.header("Painel de Registro")
        unique_names = sorted(df["Nome"].unique()) if "Nome" in df.columns else []
        search_options = ["--- Novo Cadastro ---"] + unique_names
        selected_name = st.selectbox("Busque por um nome ou selecione 'Novo Cadastro':", options=search_options, index=0, key="person_selector")
        
        status, latest_record = get_person_status(selected_name, df)

        if status == "Bloqueado":
            status_atual = latest_record.get('Status da Entrada', 'Bloqueado')
            if status_atual == "Pendente de Aprovação":
                st.warning(f"**{selected_name}** já possui uma solicitação de acesso **PENDENTE DE APROVAÇÃO**.")
                st.info("Aguarde um administrador analisar o pedido no Painel Administrativo.")
            else:
                motivo = latest_record.get('Motivo do Bloqueio', 'Não especificado')
                st.error(f"**{selected_name}** possui status **BLOQUEADO**.")
                st.write(f"**Motivo:** {motivo}")
                st.write("Para permitir a entrada, uma solicitação deve ser enviada para aprovação de um administrador.")
                if st.button(f"⚠️ Solicitar Liberação de Acesso para {selected_name}", use_container_width=True, type="primary"):
                    now = get_sao_paulo_time()
                    requester_name = get_user_display_name()
                    if add_record(name=selected_name, cpf=str(latest_record.get("CPF", "")), placa="", marca_carro="", horario_entrada=now.strftime("%H:%M"), data=now.strftime("%d/%m/%Y"), empresa=str(latest_record.get("Empresa", "")), status="Pendente de Aprovação", motivo=f"Solicitação para bloqueio: '{motivo}'", aprovador=requester_name, first_reg_date=""):
                        log_action("REQUEST_ACCESS", f"Solicitou liberação para '{selected_name}'. Motivo: {motivo}")
                        st.success(f"Solicitação para {selected_name} enviada para o administrador!"); st.rerun()

        elif status == "Dentro":
            st.info(f"**{selected_name}** está **DENTRO** da unidade.")
            st.write(f"**Entrada em:** {latest_record['Data']} às {latest_record['Horário de Entrada']}")
            if st.button(f"✅ Registrar Saída de {selected_name}", use_container_width=True, type="primary"):
                now = get_sao_paulo_time()
                success, message = update_exit_time(selected_name, now.strftime("%d/%m/%Y"), now.strftime("%H:%M"))
                if success:
                    log_action("REGISTER_EXIT", f"Registrou saída para '{selected_name}'.")
                    st.success(message); st.rerun()
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
                    is_blocked, reason = is_entity_blocked(selected_name, empresa)
                    if is_blocked:
                        st.error(f"ACESSO NEGADO: Acesso permanentemente bloqueado. Motivo: {reason}")
                        log_action("BLOCKED_ACCESS_ATTEMPT", f"Tentativa de acesso de '{selected_name}' da empresa '{empresa}' foi negada pela blocklist.")
                    else:
                        now = get_sao_paulo_time()
                        if add_record(name=selected_name, cpf=str(latest_record.get("CPF", "")), placa=placa, marca_carro=str(latest_record.get("Marca do Carro", "")), horario_entrada=now.strftime("%H:%M"), data=now.strftime("%d/%m/%Y"), empresa=empresa, status="Autorizado", motivo="", aprovador=aprovador, first_reg_date=""):
                            log_action("REGISTER_ENTRY", f"Registrou nova entrada para '{selected_name}'. Placa: {placa}.")
                            st.success(f"Nova entrada de {selected_name} registrada!"); st.rerun()

        elif status == "Novo":
            st.info("Pessoa não encontrada. Preencha o formulário.")
            with st.form(key="new_visitor_form"):
                st.write("**Formulário de Primeiro Acesso**")
                name = st.text_input("Nome Completo:")
                cpf = st.text_input("CPF:")
                empresa = st.text_input("Empresa:")
                aprovador = st.selectbox("Aprovador:", options=aprovadores_autorizados)
                placa = st.text_input("Placa (Opcional):")
                marca_carro = st.text_input("Marca (Opcional):")
                if st.form_submit_button("➕ Cadastrar e Registrar Entrada", use_container_width=True, type="primary"):
                    if not all([name, cpf, empresa, aprovador]):
                        st.error("Preencha todos os campos obrigatórios: Nome, CPF, Empresa e Aprovador.")
                    elif not validate_cpf(cpf):
                        st.error("CPF inválido. Verifique os dígitos.")
                    else:
                        # <<< ALTERAÇÃO AQUI: VERIFICAÇÃO DA BLOCKLIST >>>
                        is_blocked, reason = is_entity_blocked(name.strip(), empresa.strip())
                        if is_blocked:
                            st.error(f"ACESSO NEGADO: Acesso permanentemente bloqueado. Motivo: {reason}")
                            log_action("BLOCKED_ACCESS_ATTEMPT", f"Tentativa de acesso de '{name.strip()}' da empresa '{empresa.strip()}' foi negada pela blocklist.")
                        else:
                            now = get_sao_paulo_time()
                            if add_record(name=name.strip(), cpf=format_cpf(cpf), placa=placa, marca_carro=marca_carro, horario_entrada=now.strftime("%H:%M"), data=now.strftime("%d/%m/%Y"), empresa=empresa.strip(), status="Autorizado", motivo="", aprovador=aprovador, first_reg_date=now.strftime("%d/%m/%Y")):
                                log_action("CREATE_RECORD", f"Cadastrou novo visitante: '{name.strip()}'.")
                                st.success(f"Novo registro para {name} criado com sucesso!"); st.rerun()

    with col_sidebar:
        if not df.empty: 
            show_people_inside(df, sheet_operations)
    
    st.divider()

    if is_admin():
        with st.expander("Gerenciamento de Registros (Ações Administrativas)"):
            st.warning("Use com cuidado. As ações aqui são permanentes e afetam o histórico.")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Bloquear Pessoa")
                person_to_block = st.selectbox("Selecione para bloquear:", options=[""] + unique_names, key="block_person", index=0)
                if person_to_block:
                    motivo = st.text_input("Motivo do Bloqueio:", key="block_reason")
                    if st.button("Aplicar Bloqueio", key="apply_block", type="primary"):
                        if motivo and not df[df["Nome"] == person_to_block].empty:
                            now = get_sao_paulo_time()
                            last_record = df[df["Nome"] == person_to_block].iloc[0]
                            if add_record(name=str(person_to_block), cpf=str(last_record.get("CPF", "")), placa="", marca_carro="", horario_entrada=now.strftime("%H:%M"), data=now.strftime("%d/%m/%Y"), empresa=str(last_record.get("Empresa", "")), status="Bloqueado", motivo=motivo, aprovador="Admin", first_reg_date=""):
                                log_action("BLOCK_USER", f"Bloqueou o usuário '{person_to_block}'. Motivo: {motivo}.")
                                st.success(f"{person_to_block} foi bloqueado com sucesso."); st.rerun()
                        else:
                            st.error("O motivo é obrigatório e a pessoa deve ter pelo menos um registro anterior.")
            with col2:
                st.subheader("Deletar Último Registro")
                person_to_delete = st.selectbox("Selecione a pessoa para deletar o último registro:", options=[""] + unique_names, key="delete_person", index=0)
                if person_to_delete:
                    if st.button("Deletar Último Registro", key="apply_delete", type="secondary"):
                        records = df[df["Nome"] == person_to_delete].copy()
                        if not records.empty:
                            last_record_id = records.iloc[0]['ID']
                            if delete_record_by_id(last_record_id):
                                log_action("DELETE_RECORD", f"Deletou o último registro de '{person_to_delete}' (ID: {last_record_id}).")
                                st.success(f"Último registro de {person_to_delete} deletado com sucesso."); st.rerun()
                            else: st.error("Falha ao deletar o registro.")
                        else:
                            st.warning(f"Nenhum registro encontrado para {person_to_delete}.")
    
    with st.expander("Visualizar todos os registros"):
        st.dataframe(df.fillna(""), use_container_width=True, hide_index=True)







