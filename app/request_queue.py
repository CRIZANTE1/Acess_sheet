import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from app.utils import get_sao_paulo_time
from auth.auth_utils import get_user_display_name, get_user_email
from app.logger import log_action

# Configurações
AUTO_APPROVE_SECONDS = 60  # Aprovação em 60 segundos
BATCH_CHECK_INTERVAL_SECONDS = 10  # Verifica a cada 10 segundos

class RequestType:
    """Tipos de requisição"""
    ENTRY = "ENTRY"  # Entrada normal
    EXIT = "EXIT"    # Saída normal
    MATERIAL = "MATERIAL"  # Saída de material
    EXCEPTION = "EXCEPTION"  # Exceção que precisa admin
    BLOCKLIST_OVERRIDE = "BLOCKLIST_OVERRIDE"  # Liberação de bloqueado


class RequestPriority:
    """Prioridades de requisição"""
    NORMAL = "Normal"  # Auto-aprovação
    HIGH = "Alta"      # Aprovação manual
    URGENT = "Urgente" # Aprovação imediata


class RequestQueue:
    """Gerenciador de fila de requisições em session_state"""
    
    @staticmethod
    def initialize():
        """Inicializa a fila no session_state"""
        if 'request_queue' not in st.session_state:
            st.session_state.request_queue = []
        
        if 'last_batch_check' not in st.session_state:
            st.session_state.last_batch_check = get_sao_paulo_time()
        
        if 'auto_approve_enabled' not in st.session_state:
            st.session_state.auto_approve_enabled = True
    
    @staticmethod
    def add_request(
        request_type: str,
        priority: str,
        data: Dict,
        callback_on_approve=None
    ) -> str:
        """
        Adiciona uma requisição à fila.
        
        Args:
            request_type: Tipo da requisição (ENTRY, EXIT, etc)
            priority: Prioridade (Normal, Alta, Urgente)
            data: Dados da requisição
            callback_on_approve: Função a ser executada quando aprovada
        
        Returns:
            ID da requisição
        """
        RequestQueue.initialize()
        
        request_id = f"REQ_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        now = get_sao_paulo_time()
        
        request = {
            'id': request_id,
            'type': request_type,
            'priority': priority,
            'data': data,
            'status': 'pending',
            'created_at': now,
            'requester_name': get_user_display_name(),
            'requester_email': get_user_email(),
            'callback': callback_on_approve,
            'approved_at': None,
            'approved_by': None
        }
        
        st.session_state.request_queue.append(request)
        
        log_action(
            "ADD_TO_QUEUE",
            f"{request_type} - {priority} - {data.get('person_name', 'N/A')}"
        )
        
        return request_id
    
    @staticmethod
    def get_pending_requests(priority_filter: Optional[str] = None) -> List[Dict]:
        """Retorna requisições pendentes"""
        RequestQueue.initialize()
        
        pending = [
            req for req in st.session_state.request_queue 
            if req['status'] == 'pending'
        ]
        
        if priority_filter:
            pending = [req for req in pending if req['priority'] == priority_filter]
        
        return pending
    
    @staticmethod
    def get_request_by_id(request_id: str) -> Optional[Dict]:
        """Busca uma requisição por ID"""
        RequestQueue.initialize()
        
        for req in st.session_state.request_queue:
            if req['id'] == request_id:
                return req
        return None
    
    @staticmethod
    def approve_request(request_id: str, approver: str = "Sistema") -> bool:
        """Aprova uma requisição e executa sua ação."""
        RequestQueue.initialize()
        
        for req in st.session_state.request_queue:
            if req['id'] == request_id and req['status'] == 'pending':
                now = get_sao_paulo_time()
                req['status'] = 'approved'
                req['approved_at'] = now
                req['approved_by'] = approver
                
                # NOVA: Tenta executar o callback com retry
                if req['callback']:
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            success = req['callback'](req['data'])
                            if success:
                                log_action(
                                    "APPROVE_REQUEST",
                                    f"{req['type']} aprovada por {approver}"
                                )
                                return True
                            else:
                                # Falhou mas não houve exceção
                                if attempt < max_retries - 1:
                                    import time
                                    time.sleep(1)  # Aguarda 1s antes de tentar novamente
                                    continue
                        except Exception as e:
                            if attempt < max_retries - 1:
                                log_action("ERROR_APPROVE_RETRY", f"Tentativa {attempt+1} falhou: {e}")
                                import time
                                time.sleep(1)
                                continue
                            else:
                                # Última tentativa falhou
                                log_action("ERROR_APPROVE_REQUEST", f"Erro após {max_retries} tentativas: {e}")
                                req['status'] = 'error'
                                req['error_message'] = str(e)
                                return False
                
                return True
        
        return False
    
    @staticmethod
    def reject_request(request_id: str, reason: str = "") -> bool:
        """Rejeita uma requisição"""
        RequestQueue.initialize()
        
        for req in st.session_state.request_queue:
            if req['id'] == request_id and req['status'] == 'pending':
                req['status'] = 'rejected'
                req['rejection_reason'] = reason
                req['rejected_at'] = get_sao_paulo_time()
                
                log_action(
                    "REJECT_REQUEST",
                    f"{req['type']} rejeitada - {reason}"
                )
                return True
        
        return False
    
    @staticmethod
    def auto_approve_batch() -> int:
        """
        Aprova automaticamente requisições Normal que passaram do tempo.
        Retorna número de requisições aprovadas.
        """
        RequestQueue.initialize()
        
        if not st.session_state.auto_approve_enabled:
            return 0
        
        now = get_sao_paulo_time()
        approved_count = 0
        approved_details = []  # NOVO: guarda detalhes
        
        pending_normal = RequestQueue.get_pending_requests(RequestPriority.NORMAL)
        
        for req in pending_normal:
            time_elapsed = (now - req['created_at']).total_seconds()
            
            if time_elapsed >= AUTO_APPROVE_SECONDS:
                if RequestQueue.approve_request(req['id'], "Sistema (Auto)"):
                    approved_count += 1
                    # NOVO: guarda o que foi aprovado
                    person_name = req['data'].get('person_name', 'N/A')
                    approved_details.append(f"{req['type']}: {person_name}")
        
        # NOVO: Mostra detalhes se houver aprovações
        if approved_count > 0 and approved_details:
            details_text = "\n".join(approved_details[:3])  # Mostra até 3
            st.toast(f"✅ Auto-aprovado:\n{details_text}", icon="✅")
        
        return approved_count
    
    @staticmethod
    def cleanup_old_requests(hours: int = 24):
        """Remove requisições antigas (aprovadas/rejeitadas)"""
        RequestQueue.initialize()
        
        now = get_sao_paulo_time()
        cutoff = now - timedelta(hours=hours)
        
        st.session_state.request_queue = [
            req for req in st.session_state.request_queue
            if req['status'] == 'pending' or req['created_at'] > cutoff
        ]
    
    @staticmethod
    def get_summary() -> Dict:
        """Retorna resumo da fila"""
        RequestQueue.initialize()
        
        pending = RequestQueue.get_pending_requests()
        
        summary = {
            'total': len(pending),
            'urgent': len([r for r in pending if r['priority'] == RequestPriority.URGENT]),
            'high': len([r for r in pending if r['priority'] == RequestPriority.HIGH]),
            'normal': len([r for r in pending if r['priority'] == RequestPriority.NORMAL]),
            'awaiting_auto': []
        }
        
        # Calcula tempo restante para auto-aprovação
        now = get_sao_paulo_time()
        for req in pending:
            if req['priority'] == RequestPriority.NORMAL:
                elapsed = (now - req['created_at']).total_seconds()
                remaining = max(0, AUTO_APPROVE_SECONDS - elapsed)
                
                if remaining > 0:
                    summary['awaiting_auto'].append({
                        'id': req['id'],
                        'type': req['type'],
                        'remaining_seconds': int(remaining),
                        'data': req['data']
                    })
        
        return summary
    
    @staticmethod
    def run_background_check():
        """Executa verificação periódica em background"""
        RequestQueue.initialize()
        
        now = get_sao_paulo_time()
        
        # Inicializa se não existir
        if 'last_batch_check' not in st.session_state:
            st.session_state.last_batch_check = now
            return
        
        time_since_check = (now - st.session_state.last_batch_check).total_seconds()
        
        if time_since_check >= BATCH_CHECK_INTERVAL_SECONDS:
            # Auto-aprova requisições Normal
            try:
                approved = RequestQueue.auto_approve_batch()
                
                # MUDANÇA: Não mostra toast aqui, só no dashboard
                if approved > 0:
                    # Apenas loga
                    log_action("AUTO_APPROVE_BATCH", f"{approved} operação(ões) auto-aprovada(s)")
            except Exception as e:
                log_action("ERROR_AUTO_APPROVE", f"Erro: {e}")
            
            # Limpa requisições antigas
            try:
                RequestQueue.cleanup_old_requests(hours=1)  # Mude de 24h para 1h
            except Exception as e:
                log_action("ERROR_CLEANUP", f"Erro: {e}")
            
            st.session_state.last_batch_check = now