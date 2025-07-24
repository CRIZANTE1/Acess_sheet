import streamlit as st
import pandas as pd
from datetime import datetime
from auth.auth_utils import is_admin, get_user_display_name
from app.operations import SheetOperations
from app.data_operations import update_record_status, delete_record_by_id
from app.logger import log_action

def admin_page():
    if not is_admin():
        st.error("Acesso negado. Esta página é restrita a administradores.")
        st.warning("Por favor, selecione outra opção no menu lateral.")
        return

    st.title("Painel Administrativo")

    sheet_ops = SheetOperations()
    all_data = sheet_ops.carregar_dados()

    if not all_data:
        st.warning("Não foi possível carregar os dados. Verifique a conexão com a planilha.")
        return
        
    df = pd.DataFrame(all_data[1:], columns=all_data[0])
    
    st.header("Aprovação de Acessos Pendentes")
    
    pending_requests = df[df['Status da Entrada'] == 'Pendente de Aprovação']
    
    if pending_requests.empty:
        st.success("Tudo certo! Nenhuma solicitação de acesso pendente no momento.")
    else:
        st.warning(f"Você tem {len(pending_requests)} solicitação(ões) de acesso para analisar.")
        
        for index, row in pending_requests.iterrows():
            record_id = row['ID']
            person_name = row['Nome']
            request_date = row['Data']
            requester = row['Aprovador']
            reason = row.get('Motivo do Bloqueio', 'Motivo não especificado na solicitação.')

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
                        else:
                            st.error("Ocorreu um erro ao tentar aprovar a solicitação.")
                
                with action_col2:
                    if st.button("❌ Negar e Remover Solicitação", key=f"deny_{record_id}", use_container_width=True):
                        if delete_record_by_id(record_id):
                            log_action("DENY_ACCESS", f"Negou a entrada de '{person_name}' (Solicitante: {requester}).")
                            st.success("Solicitação negada e removida com sucesso.")
                            st.rerun()
                        else:
                            st.error("Ocorreu um erro ao tentar negar a solicitação.")

    st.divider()

    with st.expander("Visualizar Últimos Logs de Atividade"):
        try:
            log_data = sheet_ops.carregar_dados_aba('logs')
            if log_data and len(log_data) > 1:
                log_df = pd.DataFrame(log_data[1:], columns=log_data[0])
                log_df_sorted = log_df.sort_index(ascending=False)
                st.dataframe(log_df_sorted, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma atividade de log registrada ainda.")
        except Exception as e:
            st.warning(f"Não foi possível carregar os logs: {e}")

    with st.expander("Status e Configurações do Sistema"):
        st.subheader("Informações de Login OIDC")
        st.json({
            "status": "Ativo",
            "provedor": "Configurado no secrets.toml"
        })
        st.subheader("Status do Sistema")
        st.json({
            "sistema": "Controle de Acesso de Pessoas e Veículos",
            "versão": "2.3.0", # Versão atualizada com logging
            "modo_login": "OIDC (OpenID Connect) com Papéis via Google Sheets",
            "status": "Operacional",
            "Developer": "Cristian Ferreira Carlos",
            "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
