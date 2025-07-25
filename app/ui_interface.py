import streamlit as st
import pandas as pd
from datetime import datetime
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
from app.data_operations import update_schedule_status


@st.dialog("Solicitar Liberação Excepcional")
def request_blocklist_override_dialog(name, company):
    """Um diálogo para solicitar a liberação de alguém na blocklist."""
    st.write(f"Você está solicitando uma liberação excepcional para **{name}** da empresa **{company}**.")
    st.warning("Esta pessoa/empresa está na lista de bloqueio permanente. A solicitação requer um motivo legítimo e será registrada para auditoria.")
    reason = st.text_area("**Motivo da Solicitação Excepcional (obrigatório):**", height=150)
    
    if st.button("Enviar Solicitação para Admin", type="primary"):
        if reason.strip():
            now = get_sao_paulo_time()
            requester_name = get_user_display_name()
            if add_record(
                name=name, cpf="", placa="", marca_carro="", 
                horario_entrada=now.strftime("%H:%M"), 
                data=now.strftime("%d/%m/%Y"), 
                empresa=company, 
                status="Pendente de Liberação da Blocklist", 
                motivo=f"EXCEPCIONAL: {reason.strip()}", 
                aprovador=requester_name, 
                first_reg_date=""
            ):
                log_action("REQUEST_BLOCKLIST_OVERRIDE", f"Solicitou liberação da blocklist para '{name}'. Motivo: {reason.strip()}")
                st.success("Sua solicitação excepcional foi enviada para o administrador.")
                if 'df_acesso_veiculos' in st.session_state: del st.session_state.df_acesso_veiculos
                st.rerun()
        else:
            st.error("O motivo é obrigatório para enviar a solicitação.")


def show_scheduled_today(sheet_ops):
    """
    Mostra uma lista de visitantes agendados APENAS PARA HOJE e que ainda
    não tiveram check-in. Agendamentos passados não aparecem.
    """
    st.header("Visitantes Agendados para Hoje")
    
    schedules_data = sheet_ops.carregar_dados_aba('schedules')
    if not schedules_data or len(schedules_data) < 2:
        st.info("Nenhum visitante agendado para hoje.")
        return

    df_schedules = pd.DataFrame(schedules_data[1:], columns=schedules_data[0])
    
    if 'ScheduledDate' not in df_schedules.columns or 'Status' not in df_schedules.columns:
        st.warning("A planilha 'schedules' não contém as colunas 'ScheduledDate' ou 'Status'.")
        return

    today_str = get_sao_paulo_time().strftime("%d/%m/%Y")
    
    today_schedules = df_schedules[
        (df_schedules['ScheduledDate'] == today_str) &
        (df_schedules['Status'] == 'Agendado')
    ].sort_values(by='ScheduledTime')

    if today_schedules.empty:
        st.info("Nenhum visitante pendente de chegada para hoje.")
        return

    st.write("Aguardando chegada:")
    for _, schedule in today_schedules.iterrows():
        schedule_id = schedule['ID']
        visitor_name = schedule['VisitorName']
        company = schedule['Company']
        time = schedule['ScheduledTime']
        
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 2, 2])
            with col1:
                st.write(f"**{visitor_name}**")
                st.caption(f"Empresa: {company}")
            with col2:
                st.write(f"Horário: **{time}**")
                st.caption(f"Autorizado por: {schedule['AuthorizedBy']}")
            with col3:
                if st.button("Registrar Chegada", key=f"checkin_{schedule_id}", use_container_width=True, type="primary"):
                    now = get_sao_paulo_time()
                    if add_record(
                        name=visitor_name,
                        cpf=schedule['VisitorCPF'],
                        placa="",
                        marca_carro="",
                        horario_entrada=now.strftime("%H:%M"),
                        data=now.strftime("%d/%m/%Y"),
                        empresa=company,
                        status="Autorizado",
                        motivo="Visita Agendada",
                        aprovador=schedule['AuthorizedBy'],
                        first_reg_date="" 
                    ):
                        if update_schedule_status(schedule_id, "Realizado", now.strftime("%H:%M")):
                            st.success(f"Chegada de {visitor_name} registrada com sucesso!")
                            log_action("CHECK_IN", f"Check-in realizado para a visita agendada de '{visitor_name}'.")
                            if 'df_acesso_veiculos' in st.session_state:
                                del st.session_state.df_acesso_veiculos
                            st.rerun()
                            
def get_person_status(name, df):
    """Verifica o status mais recente, incluindo o novo status de liberação."""
    if not name or name == "--- Novo Cadastro ---": return "Novo", None
    if df.empty: return "Novo", None
    person_records = df[df["Nome"] == name].copy()
    if person_records.empty: return "Novo", None
    latest_record = person_records.iloc[0]
    status_entrada = latest_record.get("Status da Entrada", "")
    horario_saida = latest_record.get("Horário de Saída", "")
    if status_entrada in ["Bloqueado", "Pendente de Aprovação", "Pendente de Liberação da Blocklist"]:
        return "Bloqueado", latest_record
    if pd.isna(horario_saida) or str(horario_saida).strip() == "": return "Dentro", latest_record
    return "Fora", latest_record

def show_people_inside(df, sheet_operations):
    """Mostra uma lista de pessoas atualmente dentro com um botão de saída rápida."""
    st.subheader("Pessoas na Unidade")
    inside_df = df[(df["Status da Entrada"] == "Autorizado") & (pd.isna(df["Horário de Saída"]) | (df["Horário de Saída"] == ""))].copy().sort_values("Nome")
    if inside_df.empty:
        st.info("Ninguém registrado na unidade no momento.")
        return
    for _, row in inside_df.iterrows():
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1: st.write(f"**{row['Nome']}**")
        with col2: st.caption(f"Entrada: {row['Data']} às {row['Horário de Entrada']}")
        with col3:
            if st.button("Sair", key=f"exit_{row.get('ID')}", use_container_width=True, disabled=st.session_state.get('processing', False)):
                st.session_state.processing = True
                now = get_sao_paulo_time()
                success, message = update_exit_time(row['Nome'], now.strftime("%d/%m/%Y"), now.strftime("%H:%M"))
                if success:
                    log_action("REGISTER_EXIT", f"Registrou saída para '{row['Nome']}'.")
                    st.success(f"Saída de {row['Nome']} registrada!")
                    if 'df_acesso_veiculos' in st.session_state: del st.session_state.df_acesso_veiculos
                else: st.error(message)
                st.session_state.processing = False
                st.rerun()


def vehicle_access_interface():
    """Renderiza a interface principal de controle de acesso."""
    st.title("Controle de Acesso BAERI")
    
    if 'processing' not in st.session_state:
        st.session_state.processing = False

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
    
    if 'df_acesso_veiculos' not in st.session_state:
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
            if status_atual == "Pendente de Liberação da Blocklist":
                 st.error(f"**{selected_name}** possui uma **SOLICITAÇÃO EXCEPCIONAL PENDENTE**.")
                 st.info("Aguarde um administrador analisar o pedido de alta prioridade.")
            elif status_atual == "Pendente de Aprovação":
                st.warning(f"**{selected_name}** já possui uma solicitação de acesso **PENDENTE DE APROVAÇÃO**.")
                st.info("Aguarde um administrador analisar o pedido.")
            else:
                motivo = latest_record.get('Motivo do Bloqueio', 'Não especificado')
                st.error(f"**{selected_name}** possui status **BLOQUEADO**.")
                st.write(f"**Motivo:** {motivo}")
                st.write("Para permitir a entrada, uma solicitação deve ser enviada para aprovação de um administrador.")
                if st.button(f"⚠️ Solicitar Liberação de Acesso para {selected_name}", use_container_width=True, type="primary", disabled=st.session_state.processing):
                    st.session_state.processing = True
                    now = get_sao_paulo_time()
                    requester_name = get_user_display_name()
                    if add_record(name=selected_name, cpf=str(latest_record.get("CPF", "")), placa="", marca_carro="", horario_entrada=now.strftime("%H:%M"), data=now.strftime("%d/%m/%Y"), empresa=str(latest_record.get("Empresa", "")), status="Pendente de Aprovação", motivo=f"Solicitação para bloqueio: '{motivo}'", aprovador=requester_name, first_reg_date=""):
                        log_action("REQUEST_ACCESS", f"Solicitou liberação para '{selected_name}'. Motivo: {motivo}")
                        st.success(f"Solicitação para {selected_name} enviada para o administrador!")
                        if 'df_acesso_veiculos' in st.session_state: del st.session_state.df_acesso_veiculos
                    st.session_state.processing = False
                    st.rerun()

        elif status == "Dentro":
            st.info(f"**{selected_name}** está **DENTRO** da unidade.")
            st.write(f"**Entrada em:** {latest_record['Data']} às {latest_record['Horário de Entrada']}")
            if st.button(f"✅ Registrar Saída de {selected_name}", use_container_width=True, type="primary", disabled=st.session_state.processing):
                st.session_state.processing = True
                now = get_sao_paulo_time()
                success, message = update_exit_time(selected_name, now.strftime("%d/%m/%Y"), now.strftime("%H:%M"))
                if success:
                    log_action("REGISTER_EXIT", f"Registrou saída para '{selected_name}'.")
                    st.success(message)
                    if 'df_acesso_veiculos' in st.session_state: del st.session_state.df_acesso_veiculos
                else: st.error(message)
                st.session_state.processing = False
                st.rerun()

        elif status == "Fora":
            st.success(f"**{selected_name}** está **FORA** da unidade.")
            st.write(f"**Última saída em:** {latest_record.get('Data', 'N/A')} às {latest_record.get('Horário de Saída', 'N/A')}")
            
            with st.container(border=True):
                st.write("Registrar nova entrada:")
                placa = st.text_input("Placa", value=latest_record.get("Placa", ""), key="fora_placa")
                empresa = st.text_input("Empresa", value=latest_record.get("Empresa", ""), key="fora_empresa")
                aprovador = st.selectbox("Aprovador:", options=aprovadores_autorizados, key="fora_aprovador")
                
                if st.button(f"▶️ Registrar Entrada de {selected_name}", use_container_width=True, type="primary", disabled=st.session_state.processing):
                    is_blocked, reason = is_entity_blocked(selected_name, empresa)
                    if is_blocked:
                        log_action("BLOCKED_ACCESS_ATTEMPT", f"Tentativa de '{selected_name}' interceptada.")
                        request_blocklist_override_dialog(selected_name, empresa)
                    else:
                        st.session_state.processing = True
                        now = get_sao_paulo_time()
                        if add_record(name=selected_name, cpf=str(latest_record.get("CPF", "")), placa=placa, marca_carro=str(latest_record.get("Marca do Carro", "")), horario_entrada=now.strftime("%H:%M"), data=now.strftime("%d/%m/%Y"), empresa=empresa, status="Autorizado", motivo="", aprovador=aprovador, first_reg_date=""):
                            log_action("REGISTER_ENTRY", f"Registrou nova entrada para '{selected_name}'. Placa: {placa}.")
                            st.success(f"Nova entrada de {selected_name} registrada!")
                            if 'df_acesso_veiculos' in st.session_state: del st.session_state.df_acesso_veiculos
                        st.session_state.processing = False
                        st.rerun()
        
        elif status == "Novo":
            st.info("Pessoa não encontrada. Preencha o formulário.")
            with st.container(border=True):
                st.write("**Formulário de Primeiro Acesso**")
                name = st.text_input("Nome Completo:", key="novo_nome")
                cpf = st.text_input("CPF:", key="novo_cpf")
                empresa = st.text_input("Empresa:", key="novo_empresa")
                aprovador = st.selectbox("Aprovador:", options=aprovadores_autorizados, key="novo_aprovador")
                placa = st.text_input("Placa (Opcional):", key="novo_placa")
                marca_carro = st.text_input("Marca (Opcional):", key="novo_marca")

                if st.button("➕ Cadastrar e Registrar Entrada", use_container_width=True, type="primary", disabled=st.session_state.processing):
                    if not all([name, cpf, empresa, aprovador]):
                        st.error("Preencha todos os campos obrigatórios.")
                    elif not validate_cpf(cpf):
                        st.error("CPF inválido.")
                    else:
                        is_blocked, reason = is_entity_blocked(name.strip(), empresa.strip())
                        if is_blocked:
                            log_action("BLOCKED_ACCESS_ATTEMPT", f"Tentativa de '{name.strip()}' interceptada.")
                            request_blocklist_override_dialog(name.strip(), empresa.strip())
                        else:
                            st.session_state.processing = True
                            now = get_sao_paulo_time()
                            if add_record(name=name.strip(), cpf=format_cpf(cpf), placa=placa, marca_carro=marca_carro, horario_entrada=now.strftime("%H:%M"), data=now.strftime("%d/%m/%Y"), empresa=empresa.strip(), status="Autorizado", motivo="", aprovador=aprovador, first_reg_date=now.strftime("%d/%m/%Y")):
                                log_action("CREATE_RECORD", f"Cadastrou novo visitante: '{name.strip()}'.")
                                st.success(f"Novo registro para {name} criado com sucesso!")
                                if 'df_acesso_veiculos' in st.session_state: del st.session_state.df_acesso_veiculos
                            st.session_state.processing = False
                            st.rerun()

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
                    if st.button("Aplicar Bloqueio", key="apply_block", type="primary", disabled=st.session_state.processing):
                        st.session_state.processing = True
                        if motivo and not df[df["Nome"] == person_to_block].empty:
                            now = get_sao_paulo_time()
                            last_record = df[df["Nome"] == person_to_block].iloc[0]
                            if add_record(name=str(person_to_block), cpf=str(last_record.get("CPF", "")), placa="", marca_carro="", horario_entrada=now.strftime("%H:%M"), data=now.strftime("%d/%m/%Y"), empresa=str(last_record.get("Empresa", "")), status="Bloqueado", motivo=motivo, aprovador="Admin", first_reg_date=""):
                                log_action("BLOCK_USER", f"Bloqueou o usuário '{person_to_block}'. Motivo: {motivo}.")
                                st.success(f"{person_to_block} foi bloqueado com sucesso.")
                                if 'df_acesso_veiculos' in st.session_state: del st.session_state.df_acesso_veiculos
                        else:
                            st.error("O motivo é obrigatório e a pessoa deve ter pelo menos um registro anterior.")
                        st.session_state.processing = False
                        st.rerun()
            with col2:
                st.subheader("Deletar Último Registro")
                person_to_delete = st.selectbox("Selecione a pessoa para deletar o último registro:", options=[""] + unique_names, key="delete_person", index=0)
                if person_to_delete:
                    if st.button("Deletar Último Registro", key="apply_delete", type="secondary", disabled=st.session_state.processing):
                        st.session_state.processing = True
                        records = df[df["Nome"] == person_to_delete].copy()
                        if not records.empty:
                            last_record_id = records.iloc[0]['ID']
                            if delete_record_by_id(last_record_id):
                                log_action("DELETE_RECORD", f"Deletou o último registro de '{person_to_delete}' (ID: {last_record_id}).")
                                st.success(f"Último registro de {person_to_delete} deletado com sucesso.")
                                if 'df_acesso_veiculos' in st.session_state: del st.session_state.df_acesso_veiculos
                            else: st.error("Falha ao deletar o registro.")
                        else: st.warning(f"Nenhum registro encontrado para {person_to_delete}.")
                        st.session_state.processing = False
                        st.rerun()
    
    with st.expander("Visualizar todos os registros"):
            if not df.empty:
               
                colunas_para_exibir = [
                    "Data",
                    "Horário de Entrada",
                    "Horário de Saída",
                    "Nome",
                    "Empresa",
                    "Placa",
                    "Status da Entrada",
                    "Aprovador"
                    
                ]
                
                df_visualizacao = df[colunas_para_exibir].copy()
    
                st.dataframe(
                    df_visualizacao.fillna(""), 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.info("Nenhum registro para exibir.")

    show_scheduled_today(sheet_operations)


