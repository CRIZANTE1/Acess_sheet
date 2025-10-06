import streamlit as st
from app.request_queue import RequestQueue, RequestPriority, AUTO_APPROVE_SECONDS
from auth.auth_utils import is_admin, get_user_display_name
from app.utils import clear_access_cache, get_sao_paulo_time
import json

def show_queue_dashboard():
    """Dashboard da fila de requisições"""
    
    # Atualiza automaticamente a cada 5 segundos
    if 'last_ui_refresh' not in st.session_state:
        st.session_state.last_ui_refresh = get_sao_paulo_time()
    
    now = get_sao_paulo_time()
    if (now - st.session_state.last_ui_refresh).total_seconds() >= 5:
        st.session_state.last_ui_refresh = now
        st.rerun()
    
    st.title("📊 Fila de Requisições em Tempo Real")
    
    # Executa verificação em background
    RequestQueue.run_background_check()
    
    summary = RequestQueue.get_summary()
    
    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Pendente", summary['total'])
    
    with col2:
        st.metric("🔴 Urgentes", summary['urgent'])
    
    with col3:
        st.metric("🟠 Alta", summary['high'])
    
    with col4:
        st.metric("🟢 Normais", summary['normal'])
    
    # Controle de auto-aprovação
    with st.expander("⚙️ Configurações de Auto-Aprovação", expanded=False):
        col_toggle, col_info = st.columns([1, 2])
        
        with col_toggle:
            st.session_state.auto_approve_enabled = st.toggle(
                "Auto-aprovação ativa",
                value=st.session_state.get('auto_approve_enabled', True)
            )
        
        with col_info:
            if st.session_state.auto_approve_enabled:
                st.success(f"✅ Operações normais serão aprovadas automaticamente após {AUTO_APPROVE_SECONDS} segundos")
            else:
                st.warning("⚠️ Auto-aprovação desativada. Todas as operações requerem aprovação manual.")
        
        if st.button("🔄 Processar Fila Agora", use_container_width=True):
            approved = RequestQueue.auto_approve_batch()
            if approved > 0:
                st.success(f"✅ {approved} operação(ões) processada(s)!")
                clear_access_cache()
                st.rerun()
            else:
                st.info("Nenhuma operação pronta para processamento.")
    
    st.divider()
    
    # Tabs para diferentes visualizações
    tab1, tab2, tab3 = st.tabs([
        f"⏳ Aguardando Auto ({len(summary['awaiting_auto'])})",
        f"⚠️ Requer Aprovação ({summary['urgent'] + summary['high']})",
        "📜 Todas Pendentes"
    ])
    
    with tab1:
        show_awaiting_auto_approval(summary['awaiting_auto'])
    
    with tab2:
        show_manual_approval_needed()
    
    with tab3:
        show_all_pending()


def show_awaiting_auto_approval(awaiting_list):
    """Mostra operações aguardando auto-aprovação"""
    
    if not awaiting_list:
        st.success("✅ Nenhuma operação aguardando auto-aprovação no momento.")
        return
    
    st.info(f"Estas {len(awaiting_list)} operação(ões) serão aprovadas automaticamente quando o tempo expirar.")
    
    for item in awaiting_list:
        remaining = item['remaining_seconds']
        
        # Barra de progresso visual
        progress = (AUTO_APPROVE_SECONDS - remaining) / AUTO_APPROVE_SECONDS
        
        with st.container(border=True):
            col_info, col_timer, col_action = st.columns([3, 1, 1])
            
            with col_info:
                type_emoji = {
                    "ENTRY": "📥",
                    "EXIT": "📤",
                    "MATERIAL": "📦"
                }
                
                st.write(f"{type_emoji.get(item['type'], '📋')} **{item['type']}**")
                st.caption(f"Pessoa: {item['data'].get('person_name', 'N/A')}")
                
                # Detalhes específicos por tipo
                if item['type'] == 'ENTRY':
                    st.caption(f"Empresa: {item['data'].get('empresa', 'N/A')}")
                elif item['type'] == 'MATERIAL':
                    st.caption(f"Item: {item['data'].get('item', 'N/A')}")
                
                # NOVA: Barra de progresso
                st.progress(progress, text=f"Processando... {remaining}s restantes")
            
            with col_timer:
                # Cor muda conforme o tempo
                if remaining <= 10:
                    st.metric("⏱️ Aprovação em", f"{remaining}s", delta="🟢")
                elif remaining <= 30:
                    st.metric("⏱️ Aprovação em", f"{remaining}s", delta="🟡")
                else:
                    st.metric("⏱️ Aprovação em", f"{remaining}s")
            
            with col_action:
                if is_admin():
                    if st.button("⚡ Aprovar Agora", key=f"approve_{item['id']}", use_container_width=True):
                        if RequestQueue.approve_request(item['id'], get_user_display_name()):
                            st.success("Aprovado!")
                            clear_access_cache()
                            st.rerun()


def show_manual_approval_needed():
    """Mostra operações que requerem aprovação manual"""
    
    if not is_admin():
        st.warning("⚠️ Você precisa de permissão de administrador para aprovar operações prioritárias.")
        return
    
    pending_high = RequestQueue.get_pending_requests(RequestPriority.HIGH)
    pending_urgent = RequestQueue.get_pending_requests(RequestPriority.URGENT)
    
    all_priority = pending_urgent + pending_high
    
    if not all_priority:
        st.success("✅ Nenhuma operação prioritária aguardando aprovação.")
        return
    
    st.error(f"🚨 {len(all_priority)} operação(ões) requerem sua aprovação imediata!")
    
    for req in all_priority:
        priority_color = "🔴" if req['priority'] == RequestPriority.URGENT else "🟠"
        
        with st.container(border=True):
            st.subheader(f"{priority_color} {req['type']} - {req['priority']}")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Solicitante:** {req['requester_name']}")
                st.write(f"**Criado em:** {req['created_at'].strftime('%d/%m/%Y %H:%M:%S')}")
                
                st.write("**Detalhes:**")
                for key, value in req['data'].items():
                    if key != 'person_name':
                        st.text(f"  • {key}: {value}")
            
            with col2:
                st.write("")  # Espaçamento
                
                if st.button("✅ Aprovar", key=f"approve_manual_{req['id']}", type="primary", use_container_width=True):
                    if RequestQueue.approve_request(req['id'], get_user_display_name()):
                        st.success("✅ Aprovado!")
                        clear_access_cache()
                        st.rerun()
                
                reason = st.text_input("Motivo (para rejeitar):", key=f"reason_{req['id']}")
                
                if st.button("❌ Rejeitar", key=f"reject_{req['id']}", use_container_width=True):
                    if reason:
                        if RequestQueue.reject_request(req['id'], reason):
                            st.info("Operação rejeitada.")
                            st.rerun()
                    else:
                        st.error("Informe o motivo da rejeição.")


def format_elapsed_time(seconds):
    """Formata tempo decorrido de forma legível"""
    if seconds < 60:
        return f"{int(seconds)}s atrás"
    elif seconds < 3600:
        mins = int(seconds / 60)
        return f"{mins}min atrás"
    else:
        hours = int(seconds / 3600)
        return f"{hours}h atrás"

def show_all_pending():
    """Mostra todas as requisições pendentes"""
    
    all_pending = RequestQueue.get_pending_requests()
    
    if not all_pending:
        st.success("✅ Fila vazia!")
        return
    
    now = get_sao_paulo_time()
    
    st.dataframe(
        [{
            'ID': req['id'][-8:],
            'Tipo': req['type'],
            'Prioridade': req['priority'],
            'Solicitante': req['requester_name'],
            'Criado': format_elapsed_time((now - req['created_at']).total_seconds()),  # NOVO
            'Status': req['status']
        } for req in all_pending],
        use_container_width=True,
        hide_index=True
    )



