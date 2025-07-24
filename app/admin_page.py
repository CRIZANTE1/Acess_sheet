import streamlit as st
import pandas as pd
from datetime import datetime
from auth.auth_utils import is_admin, get_user_display_name
from app.operations import SheetOperations
from app.data_operations import (
    update_record_status, 
    delete_record_by_id,
    get_blocklist,
    add_to_blocklist,
    remove_from_blocklist
)
from app.logger import log_action

def display_pending_requests(sheet_ops):
    """Lida com a lógica da aba de Aprovações Pendentes."""
    st.header("Aprovação de Acessos Pendentes")
    all_data = sheet_ops.carregar_dados() 
    
    if not all_data or len(all_data) < 2:
        st.info("Não há dados de acesso para analisar ou a planilha está vazia.")
        return

    df = pd.DataFrame(all_data[1:], columns=all_data[0])
    pending_requests = df[df['Status da Entrada'] == 'Pendente de Aprovação']
    
    if pending_requests.empty:
        st.success("Tudo certo! Nenhuma solicitação de acesso pendente no momento.")
    else:
        st.warning(f"Você tem {len(pending_requests)} solicitação(ões) de acesso para analisar.")
        for _, row in pending_requests.iterrows():
            record_id = row['ID']
            person_name = row['Nome']
            request_date = row['Data']
            requester = row['Aprovador']
            reason = row.get('Motivo do Bloqueio', 'Motivo não especificado.')

            with st.container(border=True):
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
                        if update_record_status(record_id, "Autorizado", admin_name):
                            log_action("APPROVE_ACCESS", f"Aprovou a entrada de '{person_name}' (Solicitante: {requester}).")
                            st.rerun()
                with action_col2:
                    if st.button("❌ Negar Solicitação", key=f"deny_{record_id}", use_container_width=True):
                        if delete_record_by_id(record_id):
                            log_action("DENY_ACCESS", f"Negou a entrada de '{person_name}' (Solicitante: {requester}).")
                            st.rerun()

def display_blocklist_management(sheet_ops):
    """Lida com a lógica da aba de Gerenciamento de Bloqueios."""
    st.header("Gerenciamento de Bloqueios")

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
                admin_name = get_user_display_name()
                if add_to_blocklist(block_type, values_to_block, reason, admin_name):
                    st.success(f"{block_type}(s) bloqueada(s) com sucesso!")
                    st.cache_data.clear()
                    st.rerun()

    st.divider()
    st.subheader("Remover Bloqueios (Liberar Acesso)")
    blocklist_df = get_blocklist()

    if blocklist_df.empty:
        st.info("A lista de bloqueios está vazia.")
    else:
        st.write("Lista de entidades atualmente bloqueadas:")
        st.dataframe(blocklist_df, use_container_width=True, hide_index=True, column_order=("Type", "Value", "Reason", "BlockedBy", "Timestamp"))
        
        options_to_unblock = {f"{row['Type']}: {row['Value']} (ID: {row['ID']})": row['ID'] for _, row in blocklist_df.iterrows()}
        selections_formatted = st.multiselect("Selecione um ou mais bloqueios para remover:", options=options_to_unblock.keys(), key="unblock_multiselect")
        
        if st.button("Liberar Selecionados"):
            if not selections_formatted:
                st.warning("Nenhum bloqueio selecionado para liberação.")
            else:
                ids_to_unblock = [options_to_unblock[item] for item in selections_formatted]
                if remove_from_blocklist(ids_to_unblock):
                    st.success("Bloqueios removidos com sucesso!")
                    st.cache_data.clear()
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
    
    tab1, tab2, tab3 = st.tabs(["Aprovações Pendentes", "Gerenciar Bloqueios", "Logs do Sistema"])

    with tab1:
        display_pending_requests(sheet_ops)
    with tab2:
        display_blocklist_management(sheet_ops)
    with tab3:
        display_logs(sheet_ops)
        
    st.divider()
    with st.expander("Status e Configurações do Sistema"):
        st.subheader("Informações de Login OIDC")
        st.json({
            "status": "Ativo",
            "provedor": "Configurado no secrets.toml"
        })
        st.subheader("Status do Sistema")
        st.json({
            "sistema": "Controle de Acesso de Pessoas e Veículos",
            "versão": "2.4.0", # Versão atualizada com gerenciamento de blocklist
            "modo_login": "OIDC (OpenID Connect) com Papéis via Google Sheets",
            "status": "Operacional",
            "Developer": "Cristian Ferreira Carlos",
            "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    
