import streamlit as st
import pandas as pd
from datetime import datetime
from app.data_operations import (
    add_record, 
    update_exit_time, 
    delete_record_by_id, 
    check_blocked_records,
    is_entity_blocked,
    check_briefing_needed,
    update_schedule_status
)
from app.operations import SheetOperations
from app.utils import (
    format_cpf, 
    validate_cpf, 
    get_sao_paulo_time, 
    clear_access_cache, 
    validate_placa, 
    format_placa, 
    get_placa_tipo
)
from app.security import SecurityValidator, RateLimiter, SessionSecurity, show_security_alert
from app.widgets import aprovador_selector_with_confirmation
from auth.auth_utils import get_user_display_name, is_admin
from app.logger import log_action


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
                clear_access_cache()
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
                            clear_access_cache()
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
    
    # Filtra pessoas com status Autorizado e sem horário de saída
    inside_df = df[
        (df["Status da Entrada"] == "Autorizado") & 
        ((df["Horário de Saída"] == "") | pd.isna(df["Horário de Saída"]))
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
            # Toggle para saída com material
            saida_com_material = st.checkbox(
                "Saiu com material?",
                key=f"mat_toggle_{row.get('ID')}",
                help="Marque se a pessoa está levando materiais"
            )
            
            if saida_com_material:
                sheet_ops = SheetOperations()
                lista_materiais = sheet_ops.carregar_dados_materiais()
                
                if not lista_materiais:
                    st.warning("Nenhum material cadastrado")
                else:
                    # Container para formulário de material
                    with st.expander("📦 Dados do Material", expanded=True):
                        material_item = st.selectbox(
                            "Item:",
                            options=[""] + lista_materiais,
                            key=f"mat_item_{row.get('ID')}"
                        )
                        
                        col_qtd, col_dest = st.columns(2)
                        with col_qtd:
                            material_qtd = st.number_input(
                                "Quantidade:",
                                min_value=1,
                                value=1,
                                key=f"mat_qtd_{row.get('ID')}"
                            )
                        
                        with col_dest:
                            material_destino = st.text_input(
                                "Destino:",
                                placeholder="Ex: Obra, Cliente, Matriz",
                                key=f"mat_dest_{row.get('ID')}"
                            )
                        
                        material_responsavel = st.text_input(
                            "Responsável pela Saída:",
                            value=row['Nome'],
                            key=f"mat_resp_{row.get('ID')}",
                            help="Pessoa responsável por levar o material"
                        )
            
            if st.button("Sair", key=f"exit_{row.get('ID')}", use_container_width=True, disabled=st.session_state.get('processing', False)):
                # Validação se está saindo com material
                if saida_com_material:
                    if not material_item or material_item == "":
                        st.error("❌ Selecione um item")
                        st.stop()
                    if not material_destino or material_destino.strip() == "":
                        st.error("❌ Informe o destino do material")
                        st.stop()
                    if not material_responsavel or material_responsavel.strip() == "":
                        st.error("❌ Informe o responsável pela saída")
                        st.stop()
                
                st.session_state.processing = True
                now = get_sao_paulo_time()
                
                success, message = update_exit_time(
                    row['Nome'], 
                    now.strftime("%d/%m/%Y"), 
                    now.strftime("%H:%M")
                )
                
                if success:
                    # Log de saída normal
                    log_action("REGISTER_EXIT", f"Registrou saída para '{row['Nome']}'.")
                    
                    # Registra saída de material se aplicável
                    if saida_com_material and material_item:
                        # Adiciona registro na aba materials
                        material_data = [
                            material_item,
                            str(material_qtd),
                            material_destino.strip(),
                            material_responsavel.strip()
                        ]
                        
                        if sheet_ops.adc_dados_aba(material_data, 'materials'):
                            # Log de auditoria
                            log_action(
                                "SAIDA_MATERIAL",
                                f"{material_responsavel.strip()} levou {material_qtd}x {material_item} para {material_destino.strip()}"
                            )
                            
                            st.success(f"✅ Saída de {row['Nome']} registrada!")
                            st.info(f"📦 Material: {material_qtd}x {material_item} → {material_destino.strip()}")
                        else:
                            st.warning("⚠️ Saída registrada, mas houve erro ao registrar o material")
                    else:
                        st.success(f"✅ Saída de {row['Nome']} registrada!")
                    
                    clear_access_cache()
                    st.session_state.processing = False
                    st.rerun()
                else: 
                    st.error(f"❌ {message}")
                    st.session_state.processing = False


def vehicle_access_interface():
    """Renderiza a interface principal de controle de acesso."""
    st.title("Controle de Acesso BAERI")
    
    if 'processing' not in st.session_state:
        st.session_state.processing = False

    sheet_operations = SheetOperations()
    
    with st.expander("Briefing de Segurança e Lembretes", expanded=False):
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
                        clear_access_cache()
                    st.session_state.processing = False
                    st.rerun()

        elif status == "Dentro":
            st.info(f"**{selected_name}** está **DENTRO** da unidade.")
            st.write(f"**Entrada em:** {latest_record['Data']} às {latest_record['Horário de Entrada']}")
            
            # Toggle para material
            saida_com_material = st.checkbox(
                "Saiu com material?",
                key=f"mat_toggle_individual_{selected_name}",
                help="Marque se a pessoa está levando materiais"
            )

            material_item = ""
            material_qtd = 1
            material_destino = ""
            material_responsavel = ""

            if saida_com_material:
                lista_materiais = sheet_operations.carregar_dados_materiais()
                
                if not lista_materiais:
                    st.warning("⚠️ Nenhum material cadastrado na aba 'materials'")
                else:
                    with st.container(border=True):
                        st.write("**Dados do Material para Saída**")
                        
                        material_item = st.selectbox(
                            "Item:",
                            options=[""] + lista_materiais,
                            key=f"mat_item_individual_{selected_name}"
                        )
                        
                        col_qtd, col_dest = st.columns(2)
                        with col_qtd:
                            material_qtd = st.number_input(
                                "Quantidade:",
                                min_value=1,
                                value=1,
                                key=f"mat_qtd_individual_{selected_name}"
                            )
                        
                        with col_dest:
                            material_destino = st.text_input(
                                "Destino:",
                                placeholder="Ex: Obra, Cliente, Matriz",
                                key=f"mat_dest_individual_{selected_name}"
                            )
                        
                        material_responsavel = st.text_input(
                            "Responsável pela Saída:",
                            value=selected_name,
                            key=f"mat_resp_individual_{selected_name}",
                            help="Pessoa responsável por levar o material"
                        )

            if st.button(
                f"✅ Registrar Saída de {selected_name}", 
                use_container_width=True, 
                type="primary", 
                disabled=st.session_state.processing
            ):
                # Validação
                if saida_com_material:
                    if not material_item or material_item == "":
                        st.error("❌ Selecione um item")
                        st.stop()
                    if not material_destino or material_destino.strip() == "":
                        st.error("❌ Informe o destino do material")
                        st.stop()
                    if not material_responsavel or material_responsavel.strip() == "":
                        st.error("❌ Informe o responsável pela saída")
                        st.stop()
                
                st.session_state.processing = True
                now = get_sao_paulo_time()
                
                success, message = update_exit_time(
                    selected_name, 
                    now.strftime("%d/%m/%Y"), 
                    now.strftime("%H:%M")
                )
                
                if success:
                    log_action("REGISTER_EXIT", f"Registrou saída para '{selected_name}'.")
                    
                    # Registra material se aplicável
                    if saida_com_material and material_item:
                        material_data = [
                            material_item,
                            str(material_qtd),
                            material_destino.strip(),
                            material_responsavel.strip()
                        ]
                        
                        if sheet_operations.adc_dados_aba(material_data, 'materials'):
                            log_action(
                                "SAIDA_MATERIAL",
                                f"{material_responsavel.strip()} levou {material_qtd}x {material_item} para {material_destino.strip()}"
                            )
                            
                            st.success(f"✅ {message}")
                            st.info(f"📦 Material registrado: {material_qtd}x {material_item} → {material_destino.strip()}")
                        else:
                            st.warning("⚠️ Saída registrada, mas houve erro ao registrar o material")
                    else:
                        st.success(f"✅ {message}")
                    
                    clear_access_cache()
                    st.session_state.processing = False
                    st.rerun()
                else: 
                    st.error(f"❌ {message}")
                    st.session_state.processing = False

        elif status == "Fora":
            st.success(f"**{selected_name}** está **FORA** da unidade.")
            st.write(f"**Última saída em:** {latest_record.get('Data', 'N/A')} às {latest_record.get('Horário de Saída', 'N/A')}")
            
            # Verifica se precisa repassar o briefing
            needs_briefing, briefing_reason = check_briefing_needed(selected_name, df)
            if needs_briefing:
                st.warning(f"⚠️ **ATENÇÃO: Repassar Briefing de Segurança!**")
                st.info(f"Motivo: {briefing_reason}")
            
            with st.container(border=True):
                st.write("Registrar nova entrada:")
                placa = st.text_input("Placa (Opcional)", value=latest_record.get("Placa", ""), key="fora_placa", max_chars=8, help="Formatos aceitos: ABC-1234 ou ABC1D23")
                
                # Validação em tempo real da placa
                if placa and placa.strip():
                    tipo_placa = get_placa_tipo(placa)
                    if tipo_placa == "Inválida":
                        st.error("❌ Placa inválida! Use o formato ABC-1234 (antiga) ou ABC1D23 (Mercosul)")
                    else:
                        st.success(f"✅ Placa válida - Formato: {tipo_placa}")
                
                empresa = st.text_input("Empresa", value=latest_record.get("Empresa", ""), key="fora_empresa", max_chars=100)
                
                # Usa o widget de aprovador
                aprovador, aprovador_ciente = aprovador_selector_with_confirmation(
                    aprovadores_autorizados,
                    key_prefix="fora"
                )
                
                # Botão desabilitado se não tiver aprovador ou confirmação
                button_disabled = st.session_state.processing or not aprovador or aprovador == "" or not aprovador_ciente
                
                if st.button(
                    f"▶️ Registrar Entrada de {selected_name}", 
                    use_container_width=True, 
                    type="primary", 
                    disabled=button_disabled
                ):
                    
                    # Verifica rate limit
                    user_id = get_user_display_name()
                    is_allowed, remaining, reset_time = RateLimiter.check_rate_limit(
                        user_id, 'register_entry', max_attempts=15, time_window=60
                    )
                    
                    if not is_allowed:
                        show_security_alert(
                            f"Muitas tentativas de registro. Aguarde {reset_time} segundos.",
                            "error"
                        )
                        st.stop()
                    
                    # Valida empresa
                    is_valid_empresa, result_empresa = SecurityValidator.validate_empresa(empresa)
                    if not is_valid_empresa:
                        show_security_alert(f"Empresa inválida: {result_empresa}", "error")
                        SessionSecurity.record_failed_attempt(user_id, f"Invalid empresa: {result_empresa}")
                    elif placa and not validate_placa(placa):
                        st.error("❌ Placa inválida! Corrija antes de continuar.")
                        st.info("Formatos aceitos: ABC-1234 (antiga) ou ABC1D23 (Mercosul)")
                    else:
                        is_blocked, reason = is_entity_blocked(selected_name, result_empresa)
                        if is_blocked:
                            log_action("BLOCKED_ACCESS_ATTEMPT", f"Tentativa de '{selected_name}' interceptada.")
                            request_blocklist_override_dialog(selected_name, result_empresa)
                        else:
                            st.session_state.processing = True
                            now = get_sao_paulo_time()
                            placa_formatada = format_placa(placa) if placa else ""
                            
                            if add_record(
                                name=selected_name, 
                                cpf=str(latest_record.get("CPF", "")), 
                                placa=placa_formatada, 
                                marca_carro=str(latest_record.get("Marca do Carro", "")), 
                                horario_entrada=now.strftime("%H:%M"), 
                                data=now.strftime("%d/%m/%Y"), 
                                empresa=result_empresa, 
                                status="Autorizado", 
                                motivo="", 
                                aprovador=aprovador, 
                                first_reg_date=""
                            ):
                                log_action("REGISTER_ENTRY", f"Registrou nova entrada para '{selected_name}'. Placa: {placa_formatada}. Aprovador: {aprovador} (confirmado ciente)")
                                st.success(f"✅ Nova entrada de {selected_name} registrada e autorizada por {aprovador}!")
                                clear_access_cache()
                            
                            st.session_state.processing = False
                            st.rerun()
        
        elif status == "Novo":
            st.info("Pessoa não encontrada. Preencha o formulário.")
            
            # Verifica timeout de sessão
            is_expired, minutes = SessionSecurity.check_session_timeout(timeout_minutes=30)
            if is_expired:
                show_security_alert("Sessão expirou por inatividade. Por favor, recarregue a página.", "warning")
                st.stop()
            
            with st.container(border=True):
                st.write("**Formulário de Primeiro Acesso**")
                st.warning("⚠️ **ATENÇÃO: Esta é a primeira visita. Repassar Briefing de Segurança obrigatoriamente!**")
                
                name = st.text_input("Nome Completo:", key="novo_nome", max_chars=100)
                cpf = st.text_input("CPF:", key="novo_cpf", max_chars=14)
                empresa = st.text_input("Empresa:", key="novo_empresa", max_chars=100)
                
                # Usa o widget de aprovador
                aprovador, aprovador_ciente = aprovador_selector_with_confirmation(
                    aprovadores_autorizados,
                    key_prefix="novo"
                )
                
                st.divider()
                
                placa = st.text_input("Placa (Opcional):", key="novo_placa", max_chars=8, help="Formatos aceitos: ABC-1234 ou ABC1D23")
                
                # Validação em tempo real da placa
                if placa and placa.strip():
                    tipo_placa = get_placa_tipo(placa)
                    if tipo_placa == "Inválida":
                        st.error("❌ Placa inválida! Use o formato ABC-1234 (antiga) ou ABC1D23 (Mercosul)")
                    else:
                        st.success(f"✅ Placa válida - Formato: {tipo_placa}")
                
                marca_carro = st.text_input("Marca (Opcional):", key="novo_marca", max_chars=50)

                # Botão desabilitado se não tiver aprovador ou confirmação
                button_disabled = st.session_state.processing or not aprovador or aprovador == "" or not aprovador_ciente
                
                if st.button(
                    "➕ Cadastrar e Registrar Entrada", 
                    use_container_width=True, 
                    type="primary", 
                    disabled=button_disabled
                ):
                    
                    # Verifica rate limit
                    user_id = get_user_display_name()
                    is_allowed, remaining, reset_time = RateLimiter.check_rate_limit(
                        user_id, 'create_record', max_attempts=10, time_window=60
                    )
                    
                    if not is_allowed:
                        show_security_alert(
                            f"Muitas tentativas de cadastro. Aguarde {reset_time} segundos antes de tentar novamente.",
                            "error"
                        )
                        SessionSecurity.record_failed_attempt(user_id, "Rate limit exceeded on create_record")
                        st.stop()
                    
                    # Validação completa de segurança
                    is_valid, clean_data, errors = SecurityValidator.validate_all_fields(
                        name, cpf, empresa, placa, ""
                    )
                    
                    if not is_valid:
                        show_security_alert("Dados inválidos detectados:", "error")
                        for error in errors:
                            st.error(error)
                        SessionSecurity.record_failed_attempt(user_id, f"Invalid data: {'; '.join(errors)}")
                    elif not all([name, cpf, empresa, aprovador]):
                        st.error("❌ Preencha todos os campos obrigatórios, incluindo o aprovador.")
                    elif not aprovador_ciente:
                        st.error("❌ Você deve confirmar que o aprovador está ciente desta entrada.")
                    else:
                        # Verifica blocklist
                        is_blocked, reason = is_entity_blocked(clean_data['name'], clean_data['empresa'])
                        if is_blocked:
                            log_action("BLOCKED_ACCESS_ATTEMPT", f"Tentativa de '{clean_data['name']}' interceptada.")
                            SessionSecurity.record_failed_attempt(user_id, f"Blocked entity: {clean_data['name']}")
                            request_blocklist_override_dialog(clean_data['name'], clean_data['empresa'])
                        else:
                            st.session_state.processing = True
                            now = get_sao_paulo_time()
                            
                            if add_record(
                                name=clean_data['name'], 
                                cpf=clean_data['cpf'], 
                                placa=clean_data['placa'], 
                                marca_carro=marca_carro.strip() if marca_carro else "", 
                                horario_entrada=now.strftime("%H:%M"), 
                                data=now.strftime("%d/%m/%Y"), 
                                empresa=clean_data['empresa'], 
                                status="Autorizado", 
                                motivo="", 
                                aprovador=aprovador, 
                                first_reg_date=now.strftime("%d/%m/%Y")
                            ):
                                log_action("CREATE_RECORD", f"Cadastrou novo visitante: '{clean_data['name']}'. Aprovador: {aprovador} (confirmado ciente)")
                                st.success(f"✅ Novo registro para {clean_data['name']} criado com sucesso e autorizado por {aprovador}!")
                                
                                # Reseta rate limit em caso de sucesso
                                RateLimiter.reset_rate_limit(user_id, 'create_record')
                                
                                clear_access_cache()
                            
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
                                clear_access_cache()
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
                                clear_access_cache()
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













