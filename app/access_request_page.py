import streamlit as st
from datetime import datetime
from app.operations import SheetOperations
from app.utils import get_sao_paulo_time
from auth.auth_utils import get_user_email, get_user_display_name

def request_access_page():
    """Página para usuários sem permissão solicitarem acesso ao sistema."""
    st.title("Solicitação de Acesso ao Sistema")
    
    user_email = get_user_email()
    user_name = get_user_display_name()
    
    st.info(f"Você está logado como: **{user_name}** ({user_email})")
    
    st.markdown("""
    ### Você não possui permissão para acessar este sistema
    
    Para solicitar acesso, preencha o formulário abaixo. Um administrador irá analisar sua solicitação.
    """)
    
    # Verifica se já existe uma solicitação pendente
    sheet_ops = SheetOperations()
    existing_requests = sheet_ops.carregar_dados_aba('access_requests')
    
    has_pending = False
    if existing_requests and len(existing_requests) > 1:
        import pandas as pd
        df_requests = pd.DataFrame(existing_requests[1:], columns=existing_requests[0])
        
        user_pending = df_requests[
            (df_requests['user_email'].str.lower() == user_email.lower()) &
            (df_requests['status'] == 'Pendente')
        ]
        
        if not user_pending.empty:
            has_pending = True
            request_data = user_pending.iloc[0]
            
            st.warning("⏳ **Você já possui uma solicitação pendente de análise.**")
            
            with st.container(border=True):
                st.write(f"**Data da Solicitação:** {request_data.get('request_date', 'N/A')}")
                st.write(f"**Função Desejada:** {request_data.get('desired_role', 'N/A')}")
                st.write(f"**Justificativa:**")
                st.info(request_data.get('justification', 'N/A'))
            
            st.info("Por favor, aguarde a análise do administrador. Você será notificado por email.")
    
    if not has_pending:
        with st.form(key="access_request_form"):
            st.subheader("Formulário de Solicitação")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.text_input("Nome Completo:", value=user_name, disabled=True)
                st.text_input("Email:", value=user_email, disabled=True)
            
            with col2:
                desired_role = st.selectbox(
                    "Acesso Desejado:",
                    options=["operacional", "admin"],
                    index=0,
                    help="Operacional: Acesso básico ao sistema. Admin: Acesso completo incluindo aprovações."
                )
                
                department = st.text_input(
                    "Departamento/Setor:",
                    placeholder="Ex: Segurança, Portaria, Administração",
                    max_chars=100
                )
            
            justification = st.text_area(
                "Justificativa para o Acesso (obrigatório):",
                placeholder="Explique por que você precisa acessar este sistema e como irá utilizá-lo...",
                height=150,
                max_chars=500
            )
            
            manager_email = st.text_input(
                "Email do Gestor Imediato (opcional):",
                placeholder="gestor@empresa.com",
                help="Informe o email do seu gestor para agilizar a aprovação"
            )
            
            st.divider()
            
            terms_accepted = st.checkbox(
                "Li e concordo com os termos de uso do sistema",
                help="Ao solicitar acesso, você concorda em seguir as políticas de segurança da empresa"
            )
            
            submit_button = st.form_submit_button(
                "Enviar Solicitação",
                type="primary"
            )
            
            if submit_button:
                if not justification.strip():
                    st.error("❌ A justificativa é obrigatória.")
                elif len(justification.strip()) < 20:
                    st.error("❌ A justificativa deve ter pelo menos 20 caracteres.")
                elif not department.strip():
                    st.error("❌ O departamento/setor é obrigatório.")
                elif not terms_accepted:
                    st.error("❌ Você deve aceitar os termos de uso.")
                else:
                    # Cria a solicitação
                    now = get_sao_paulo_time()
                    
                    request_data = [
                        user_email.lower(),
                        user_name,
                        desired_role,
                        department.strip(),
                        justification.strip(),
                        manager_email.strip() if manager_email else "",
                        now.strftime("%d/%m/%Y %H:%M:%S"),
                        "Pendente",
                        ""  # reviewed_by (vazio inicialmente)
                    ]
                    
                    if sheet_ops.adc_dados_aba(request_data, 'access_requests'):
                        st.success("✅ Sua solicitação foi enviada com sucesso!")
                        
                        # NOVO: Notifica administradores
                        try:
                            from app.notifications import send_notification
                            import logging
                            send_notification(
                                "new_access_request",
                                requester_name=user_name,
                                requester_email=user_email.lower(),
                                role=desired_role,
                                department=department.strip(),
                                justification=justification.strip()
                            )
                        except Exception as e:
                            # Não quebra o fluxo se o email falhar
                            logging.error(f"Erro ao enviar notificação de novo acesso: {e}")

                        st.info("""
                        **Próximos Passos:**
                        1. Um administrador irá analisar sua solicitação
                        2. Você receberá uma notificação por email sobre o resultado
                        3. Se aprovado, você poderá acessar o sistema imediatamente
                        
                        Este processo pode levar até 24 horas úteis.
                        """)
                        
                        # Log da solicitação
                        from app.logger import log_action
                        log_action("ACCESS_REQUEST", f"Usuário '{user_email}' solicitou acesso como '{desired_role}'")
                        
                        st.rerun()
                    else:
                        st.error("❌ Erro ao enviar solicitação. Tente novamente mais tarde.")
    
    st.divider()
    
    with st.expander("ℹ️ Informações sobre os níveis de acesso"):
        st.markdown("""
        ### Operacional
        - Registrar entradas e saídas de visitantes
        - Consultar histórico de acessos
        - Agendar visitas
        - Visualizar relatórios
        
        ### Admin
        - Todas as permissões do Operacional, mais:
        - Aprovar solicitações de acesso
        - Gerenciar bloqueios permanentes
        - Adicionar/remover usuários
        - Acessar logs de auditoria
        - Configurações do sistema
        """)
    
    # Botão de logout
    st.divider()
    if st.button("Sair do Sistema", type="secondary"):
        try:
            st.logout()
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao fazer logout: {e}")
