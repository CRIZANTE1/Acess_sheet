import streamlit as st
import pandas as pd
from datetime import datetime
from auth.auth_utils import is_admin, get_user_display_name
from app.operations import SheetOperations
from app.data_operations import update_record_status, delete_record_by_id

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
    
    st.header("Aprovação de Acessos")
    
    pending_requests = df[df['Status da Entrada'] == 'Pendente de Aprovação']
    
    if pending_requests.empty:
        st.success("Tudo certo! Nenhuma solicitação de acesso pendente.")
    else:
        st.warning(f"Você tem {len(pending_requests)} solicitação(ões) de acesso pendente(s).")
        
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
                    st.write(f"**Solicitante:** {requester}")
                with col2:
                    st.write(f"**Motivo:**")
                    st.info(reason)
                
                action_col1, action_col2 = st.columns(2)
                with action_col1:
                    if st.button("✅ Aprovar Entrada", key=f"approve_{record_id}", use_container_width=True, type="primary"):
                        admin_name = get_user_display_name()
                        if update_record_status(record_id, "Autorizado", admin_name):
                            st.rerun()
                        else:
                            st.error("Ocorreu um erro ao aprovar.")
                
                with action_col2:
                    if st.button("❌ Negar Entrada", key=f"deny_{record_id}", use_container_width=True):
                        if delete_record_by_id(record_id):
                            st.success("Solicitação negada e removida.")
                            st.rerun()
                        else:
                            st.error("Ocorreu um erro ao negar.")

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
            "versão": "2.1.0", # Versão atualizada
            "modo_login": "OIDC (OpenID Connect)",
            "status": "Operacional",
            "Developer": "Cristian Ferreira Carlos",
            "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
