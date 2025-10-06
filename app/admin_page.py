import streamlit as st
import pandas as pd
from datetime import datetime
from auth.auth_utils import is_admin, get_user_display_name, get_user_email
from app.security import SecurityValidator, show_security_alert

from app.operations import SheetOperations
from app.data_operations import (
    update_record_status, 
    delete_record_by_id,
    get_blocklist,
    add_to_blocklist,
    remove_from_blocklist,
    get_users, 
    add_user,    
    remove_user,
    update_access_request_status
)
from app.logger import log_action
from app.utils import clear_access_cache

def display_user_management(sheet_ops):
    """Lida com a lógica da aba de Gerenciamento de Usuários."""
    st.header("Gerenciamento de Usuários do Sistema")

    with st.container(border=True):
        st.subheader("Adicionar Novo Usuário")
        new_user_email = st.text_input("Email do Usuário (conta Google):", placeholder="usuario@exemplo.com")
        # Por segurança, o admin só pode adicionar usuários operacionais pela UI.
        new_user_role = "operacional"
        st.info(f"O usuário será adicionado com o papel de **{new_user_role}**.")

        if st.button("Adicionar Usuário", type="primary"):
            if not new_user_email.strip():
                st.error("O email do usuário não pode estar vazio.")
            elif "@" not in new_user_email:
                st.error("Por favor, insira um email válido.")
            else:
                if add_user(new_user_email.strip().lower(), new_user_role):
                    st.success(f"Usuário '{new_user_email.strip()}' adicionado com sucesso!")
                    clear_access_cache()
                    st.rerun()

    st.divider()

    st.subheader("Remover Usuário Operacional")
    users_df = get_users()

    if users_df.empty:
        st.info("Nenhum usuário encontrado para gerenciar.")
    else:
        operational_users = users_df[users_df['role'] == 'operacional']
        
        if operational_users.empty:
            st.info("Não há usuários operacionais para remover.")
        else:
            users_to_remove = st.multiselect(
                "Selecione um ou mais usuários operacionais para remover:",
                options=operational_users['user_email'].tolist()
            )
            
            if st.button("Remover Usuários Selecionados", type="secondary"):
                if not users_to_remove:
                    st.warning("Nenhum usuário selecionado para remoção.")
                else:
                    success_count = 0
                    for user in users_to_remove:
                        if remove_user(user):
                            success_count += 1
                    
                    st.success(f"{success_count} de {len(users_to_remove)} usuário(s) removido(s) com sucesso!")
                    if success_count > 0:
                        clear_access_cache()
                        st.rerun()

def display_access_requests(sheet_ops):
    """Gerencia solicitações de acesso de novos usuários."""
    st.header("Solicitações de Acesso ao Sistema")
    
    requests_data = sheet_ops.carregar_dados_aba('access_requests')
    
    if not requests_data or len(requests_data) < 2:
        st.info("Nenhuma solicitação de acesso pendente no momento.")
        return
    
    df_requests = pd.DataFrame(requests_data[1:], columns=requests_data[0])
    
    pending_requests = df_requests[df_requests['status'] == 'Pendente'].sort_values(
        by='request_date', ascending=False
    )
    
    approved_requests = df_requests[df_requests['status'] == 'Aprovado'].sort_values(
        by='request_date', ascending=False
    )
    
    rejected_requests = df_requests[df_requests['status'] == 'Rejeitado'].sort_values(
        by='request_date', ascending=False
    )
    
    tab1, tab2, tab3 = st.tabs([
        f"Pendentes ({len(pending_requests)})",
        f"Aprovadas ({len(approved_requests)})",
        f"Rejeitadas ({len(rejected_requests)})"
    ])
    
    with tab1:
        if pending_requests.empty:
            st.success("✅ Nenhuma solicitação pendente no momento.")
        else:
            st.warning(f"⏳ Você tem {len(pending_requests)} solicitação(ões) para analisar.")
            
            for _, request in pending_requests.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.subheader(f"👤 {request['user_name']}")
                        st.write(f"**Email:** {request['user_email']}")
                        st.write(f"**Departamento:** {request['department']}")
                        st.write(f"**Acesso Solicitado:** `{request['desired_role']}`")
                        st.write(f"**Data da Solicitação:** {request['request_date']}")
                        
                        if request.get('manager_email'):
                            st.write(f"**Gestor:** {request['manager_email']}")
                    
                    with col2:
                        st.metric("Status", "⏳ Pendente", delta=None)
                    
                    st.write("**Justificativa:**")
                    st.info(request['justification'])
                    
                    st.divider()
                    
                    col_approve, col_reject = st.columns(2)
                    
                    request_id = request['ID']
                    
                    with col_approve:
                        if st.button(
                            "✅ Aprovar Acesso",
                            key=f"approve_req_{request_id}",
                            use_container_width=True,
                            type="primary"
                        ):
                            admin_name = get_user_display_name()
                            
                            # Atualiza o status da solicitação
                            if update_access_request_status(
                                request_id, 
                                "Aprovado", 
                                admin_name
                            ):
                                # Adiciona o usuário ao sistema
                                if add_user(request['user_email'], request['desired_role']):
                                    log_action(
                                        "APPROVE_ACCESS_REQUEST",
                                        f"Aprovou solicitação de '{request['user_email']}' para '{request['desired_role']}'"
                                    )
                                    
                                    # NOVO: Envia email de aprovação
                                    try:
                                        from app.notifications import send_notification
                                        import logging
                                        send_notification(
                                            "access_approved",
                                            to_email=request['user_email'],
                                            user_name=request['user_name'],
                                            role=request['desired_role']
                                        )
                                    except Exception as e:
                                        logging.error(f"Erro ao enviar email de aprovação: {e}")
                                    
                                    st.success(f"✅ Acesso aprovado para {request['user_name']}!")
                                    clear_access_cache()
                                    st.rerun()
                                else:
                                    st.error("Erro ao adicionar usuário ao sistema.")
                            else:
                                st.error("Erro ao atualizar status da solicitação.")
                    
                    with col_reject:
                        if st.button(
                            "❌ Rejeitar",
                            key=f"reject_req_{request_id}",
                            use_container_width=True
                        ):
                            admin_name = get_user_display_name()
                            
                            if update_access_request_status(
                                request_id,
                                "Rejeitado",
                                admin_name
                            ):
                                log_action(
                                    "REJECT_ACCESS_REQUEST",
                                    f"Rejeitou solicitação de '{request['user_email']}'"
                                )
                                
                                # NOVO: Envia email de rejeição
                                try:
                                    from app.notifications import send_notification
                                    import logging
                                    send_notification(
                                        "access_rejected",
                                        to_email=request['user_email'],
                                        user_name=request['user_name'],
                                        reason="Sua solicitação foi analisada e não foi aprovada neste momento."
                                    )
                                except Exception as e:
                                    logging.error(f"Erro ao enviar email de rejeição: {e}")
                                
                                st.info(f"Solicitação de {request['user_name']} foi rejeitada.")
                                st.rerun()
    
    with tab2:
        if approved_requests.empty:
            st.info("Nenhuma solicitação aprovada ainda.")
        else:
            st.dataframe(
                approved_requests[[
                    'request_date', 'user_name', 'user_email', 
                    'desired_role', 'department', 'reviewed_by'
                ]],
                use_container_width=True,
                hide_index=True
            )
    
    with tab3:
        if rejected_requests.empty:
            st.info("Nenhuma solicitação rejeitada.")
        else:
            st.dataframe(
                rejected_requests[[
                    'request_date', 'user_name', 'user_email',
                    'desired_role', 'department', 'reviewed_by'
                ]],
                use_container_width=True,
                hide_index=True
            )

def display_pending_requests(sheet_ops):
    """Lida com a lógica da aba de Aprovações Pendentes."""
    st.header("Aprovação de Acessos Pendentes")
    all_data = sheet_ops.carregar_dados()  # Carrega dados de 'acess'
    
    if not all_data or len(all_data) < 2:
        st.info("Não há dados de acesso para analisar ou a planilha está vazia.")
        return

    df = pd.DataFrame(all_data[1:], columns=all_data[0])
    
    pending_statuses = ['Pendente de Aprovação', 'Pendente de Liberação da Blocklist']
    pending_requests = df[df['Status da Entrada'].isin(pending_statuses)]
    
    if pending_requests.empty:
        st.success("Tudo certo! Nenhuma solicitação de acesso pendente no momento.")
    else:
        st.warning(f"Você tem {len(pending_requests)} solicitação(ões) de acesso para analisar.")
        
        # Prioriza as solicitações da blocklist, mostrando-as primeiro
        pending_requests = pending_requests.sort_values(by='Status da Entrada', ascending=False)

        for _, row in pending_requests.iterrows():
            record_id = row['ID']
            person_name = row['Nome']
            empresa_name = row.get('Empresa', '') # Pega o nome da empresa para a busca na blocklist
            request_date = row['Data']
            requester = row['Aprovador']
            reason = row.get('Motivo do Bloqueio', 'Motivo não especificado.')
            current_status = row['Status da Entrada']

            with st.container(border=True):
                if current_status == 'Pendente de Liberação da Blocklist':
                    st.error("⚠️ **SOLICITAÇÃO EXCEPCIONAL (BLOCKLIST)**")

                st.subheader(f"Solicitação para: {person_name}")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Data da Solicitação:** {request_date}")
                    st.write(f"**Solicitante (Operacional):** {requester}")
                with col2:
                    st.write(f"**Justificativa/Motivo:**")
                    st.info(reason)
                
                action_col1, action_col2 = st.columns(2)
                with action_col1:
                    if st.button("✅ Aprovar Entrada", key=f"approve_{record_id}", use_container_width=True, type="primary"):
                        admin_name = get_user_display_name()
                        
                        success_acess = update_record_status(record_id, "Autorizado", admin_name)
                        
                        if success_acess:
                            log_action("APPROVE_ACCESS", f"Aprovou a entrada de '{person_name}' (Sol: {requester}). Status anterior: {current_status}")
                            
                            if current_status == 'Pendente de Liberação da Blocklist':
                                st.info(f"Processando remoção de bloqueio permanente para '{person_name}'...")
                                blocklist_df = get_blocklist()
                                
                                # Tenta encontrar o ID do bloqueio pelo nome da pessoa
                                person_block = blocklist_df[(blocklist_df['Type'] == 'Pessoa') & (blocklist_df['Value'] == person_name)]
                                
                                block_id_to_remove = None
                                if not person_block.empty:
                                    block_id_to_remove = person_block.iloc[0]['ID']

                                if block_id_to_remove:
                                    if remove_from_blocklist([block_id_to_remove]):
                                        st.success(f"Bloqueio permanente para '{person_name}' removido com sucesso!")
                                        clear_access_cache()
                                    else:
                                        st.error(f"A entrada foi aprovada, mas FALHA ao remover o bloqueio permanente. Remova manualmente na aba 'Gerenciar Bloqueios'.")
                                else:
                                    st.warning(f"A entrada foi aprovada, mas não foi encontrado um bloqueio permanente correspondente para '{person_name}' para remover.")

                            clear_access_cache()
                            st.rerun()

                with action_col2:
                    if st.button("❌ Negar Solicitação", key=f"deny_{record_id}", use_container_width=True):
                        if delete_record_by_id(record_id):
                            log_action("DENY_ACCESS", f"Negou a entrada de '{person_name}' (Sol: {requester}). Status anterior: {current_status}")
                            clear_access_cache()
                            st.rerun()
                            
def display_blocklist_management(sheet_ops):
    """Lida com a lógica da aba de Gerenciamento de Bloqueios."""
    st.header("Gerenciamento de Bloqueios")
    
    if 'processing_blocklist' not in st.session_state:
        st.session_state.processing_blocklist = False
        
    with st.container(border=True):
        st.subheader("Adicionar Bloqueio de Pessoa ou Empresa")
        block_type = st.radio("Selecione o tipo de bloqueio:", ["Pessoa", "Empresa"], horizontal=True, key="block_type")
        
        acess_data = sheet_ops.carregar_dados()
        options = []
        if acess_data and len(acess_data) > 1:
            df_acess = pd.DataFrame(acess_data[1:], columns=acess_data[0])
            source_column = 'Nome' if block_type == "Pessoa" else 'Empresa'
            if source_column in df_acess.columns:
                options = sorted(df_acess[source_column].dropna().unique())
        
        values_to_block = st.multiselect(f"Selecione uma ou mais {block_type.lower()}s para bloquear:", options, key="block_multiselect")
        reason = st.text_area("Motivo do Bloqueio (obrigatório):", key="block_reason")
        
        if st.button("Aplicar Bloqueio", type="primary"):
            if not values_to_block:
                st.error("Selecione pelo menos uma entidade para bloquear.")
            elif not reason.strip():
                st.error("O motivo do bloqueio é obrigatório.")
            else:
                # Valida o motivo
                clean_reason, errors = SecurityValidator.sanitize_input(reason, "Motivo")
                
                if errors:
                    show_security_alert("Motivo contém caracteres não permitidos:", "error")
                    for error in errors:
                        st.error(error)
                else:
                    admin_name = get_user_display_name()
                    if add_to_blocklist(block_type, values_to_block, clean_reason, admin_name):
                        st.success(f"{block_type}(s) bloqueada(s) com sucesso!")
                        clear_access_cache()
                        st.rerun()
    st.divider()

    st.subheader("Remover Bloqueios (Liberar Acesso)")
    
    st.info(
        "Use esta seção para **remover proativamente** um bloqueio permanente. Lembre-se: um bloqueio também é "
        "removido automaticamente quando você aprova uma 'Solicitação Excepcional' na aba de pendências."
    )
    
    blocklist_df = get_blocklist()

    if blocklist_df.empty:
        st.info("A lista de bloqueios está vazia.")
    else:
        st.write("Lista de entidades atualmente bloqueadas:")
        st.dataframe(blocklist_df, use_container_width=True, hide_index=True, column_order=("Type", "Value", "Reason", "BlockedBy", "Timestamp"))
        
        options_to_unblock = {f"{row['Type']}: {row['Value']} (ID: {row['ID']})": row['ID'] for _, row in blocklist_df.iterrows()}
        selections_formatted = st.multiselect("Selecione um ou mais bloqueios para remover:", options=options_to_unblock.keys(), key="unblock_multiselect")
        
        if st.button("Liberar Selecionados", disabled=st.session_state.processing_blocklist):
            st.session_state.processing_blocklist = True 
            
            if not selections_formatted:
                st.warning("Nenhum bloqueio selecionado para liberação.")
                st.session_state.processing_blocklist = False
            else:
                ids_to_unblock = [options_to_unblock[item] for item in selections_formatted]
                success = remove_from_blocklist(ids_to_unblock)
                
                if success:
                    st.success("Bloqueios removidos com sucesso! A lista será atualizada.")
                    clear_access_cache()
                
                st.session_state.processing_blocklist = False 
                st.rerun()
                
def display_logs(sheet_ops):
    """Lida com a lógica da aba de Logs."""
    st.header("Logs de Atividade do Sistema")
    try:
        log_data = sheet_ops.carregar_dados_aba('logs')
        if log_data and len(log_data) > 1:
            log_df = pd.DataFrame(log_data[1:], columns=log_data[0])
            st.dataframe(log_df.sort_values(by="Timestamp", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma atividade de log registrada ainda.")
    except Exception as e:
        st.warning(f"Não foi possível carregar os logs: {e}")

def admin_page():
    """Renderiza a página administrativa completa com abas."""
    if not is_admin():
        st.error("Acesso negado. Esta página é restrita a administradores.")
        return

    st.title("Painel Administrativo")
    sheet_ops = SheetOperations()
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Solicitações de Acesso",  # NOVA ABA
        "Aprovações Pendentes",
        "Gerenciar Bloqueios",
        "Gerenciar Usuários",
        "Logs do Sistema"
    ])

    with tab1:
        display_access_requests(sheet_ops)  # NOVA FUNÇÃO
    with tab2:
        display_pending_requests(sheet_ops)
    with tab3:
        display_blocklist_management(sheet_ops)
    with tab4:
        display_user_management(sheet_ops) 
    with tab5:
        display_logs(sheet_ops)
        
    st.divider()
    with st.expander("Status e Configurações do Sistema"):
        st.subheader("Informações de Login OIDC")
        st.json({
            "status": "Ativo",
            "provedor": "Configurado no secrets"
        })
        st.subheader("Status do Sistema")
        st.json({
            "sistema": "Controle de Acesso de Pessoas e Veículos",
            "versão": "3.0.0", 
            "modo_login": "OIDC (OpenID Connect) com níveis via Google Sheets",
            "status": "Operacional",
            "Developer": "Cristian Ferreira Carlos",
            "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })