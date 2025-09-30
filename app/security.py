import re
import streamlit as st
from datetime import datetime, timedelta
from app.utils import get_sao_paulo_time
from app.logger import log_action

class SecurityValidator:
    """Classe para validações de segurança do sistema"""
    
    # Lista de palavras SQL perigosas
    SQL_KEYWORDS = [
        'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE',
        'EXEC', 'EXECUTE', 'SCRIPT', 'UNION', 'SELECT', 'WHERE',
        '--', ';--', '/*', '*/', 'xp_', 'sp_', 'TRUNCATE', 'GRANT',
        'REVOKE', 'SHUTDOWN', 'BACKUP', 'RESTORE'
    ]
    
    # Padrões XSS comuns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',  # onclick, onerror, etc
        r'<iframe',
        r'<object',
        r'<embed',
        r'<applet',
        r'eval\(',
        r'expression\(',
        r'vbscript:'
    ]
    
    # Caracteres perigosos para injeção
    DANGEROUS_CHARS = ['<', '>', '{', '}', '|', '\\', '^', '~', '[', ']', '`']
    
    @staticmethod
    def sanitize_input(text, field_name="campo"):
        """
        Sanitiza entrada de texto removendo caracteres perigosos.
        Retorna (texto_limpo, lista_de_erros)
        """
        if not text or text.strip() == "":
            return text, []
        
        errors = []
        original_text = text
        
        # Remove espaços extras
        text = ' '.join(text.split())
        
        # Verifica SQL Injection
        text_upper = text.upper()
        for keyword in SecurityValidator.SQL_KEYWORDS:
            if keyword in text_upper:
                errors.append(f"Palavra não permitida detectada em {field_name}: '{keyword}'")
                log_action("SECURITY_ALERT", f"SQL Injection attempt detected in {field_name}: {original_text}")
        
        # Verifica XSS
        for pattern in SecurityValidator.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                errors.append(f"Padrão suspeito detectado em {field_name}")
                log_action("SECURITY_ALERT", f"XSS attempt detected in {field_name}: {original_text}")
        
        # Verifica caracteres perigosos
        dangerous_found = [char for char in SecurityValidator.DANGEROUS_CHARS if char in text]
        if dangerous_found:
            errors.append(f"Caracteres não permitidos em {field_name}: {', '.join(dangerous_found)}")
        
        return text, errors
    
    @staticmethod
    def validate_name(name):
        """
        Valida nome completo.
        Retorna (is_valid, error_message)
        """
        if not name or name.strip() == "":
            return False, "Nome não pode estar vazio"
        
        name = name.strip()
        
        # Sanitiza entrada
        clean_name, errors = SecurityValidator.sanitize_input(name, "Nome")
        if errors:
            return False, "; ".join(errors)
        
        # Deve ter pelo menos 2 palavras (nome e sobrenome)
        words = name.split()
        if len(words) < 2:
            return False, "Nome deve conter pelo menos nome e sobrenome"
        
        # Cada palavra deve ter pelo menos 2 caracteres
        if any(len(word) < 2 for word in words):
            return False, "Cada parte do nome deve ter pelo menos 2 caracteres"
        
        # Deve conter apenas letras, espaços e caracteres acentuados
        if not re.match(r'^[a-zA-ZÀ-ÿ\s]+$', name):
            return False, "Nome deve conter apenas letras e espaços"
        
        # Verifica tamanho máximo
        if len(name) > 100:
            return False, "Nome muito longo (máximo 100 caracteres)"
        
        # Verifica tamanho mínimo
        if len(name) < 5:
            return False, "Nome muito curto (mínimo 5 caracteres)"
        
        return True, clean_name
    
    @staticmethod
    def validate_empresa(empresa):
        """
        Valida nome da empresa.
        Retorna (is_valid, error_message)
        """
        if not empresa or empresa.strip() == "":
            return False, "Empresa não pode estar vazia"
        
        empresa = empresa.strip()
        
        # Sanitiza entrada
        clean_empresa, errors = SecurityValidator.sanitize_input(empresa, "Empresa")
        if errors:
            return False, "; ".join(errors)
        
        # Pode conter letras, números, espaços e alguns caracteres especiais
        if not re.match(r'^[a-zA-Z0-9À-ÿ\s\.\-&]+$', empresa):
            return False, "Empresa contém caracteres não permitidos"
        
        # Verifica tamanho
        if len(empresa) < 2:
            return False, "Nome da empresa muito curto (mínimo 2 caracteres)"
        
        if len(empresa) > 100:
            return False, "Nome da empresa muito longo (máximo 100 caracteres)"
        
        return True, clean_empresa
    
    @staticmethod
    def validate_all_fields(name, cpf, empresa, placa="", motivo=""):
        """
        Valida todos os campos de uma só vez.
        Retorna (is_valid, dict_campos_limpos, lista_erros)
        """
        errors = []
        clean_data = {}
        
        # Valida nome
        is_valid_name, result_name = SecurityValidator.validate_name(name)
        if not is_valid_name:
            errors.append(f"❌ Nome: {result_name}")
        else:
            clean_data['name'] = result_name
        
        # Valida CPF (usando função existente)
        from app.utils import validate_cpf, format_cpf
        if not validate_cpf(cpf):
            errors.append("❌ CPF: Formato inválido")
        else:
            clean_data['cpf'] = format_cpf(cpf)
        
        # Valida empresa
        is_valid_empresa, result_empresa = SecurityValidator.validate_empresa(empresa)
        if not is_valid_empresa:
            errors.append(f"❌ Empresa: {result_empresa}")
        else:
            clean_data['empresa'] = result_empresa
        
        # Valida placa se fornecida
        if placa and placa.strip():
            from app.utils import validate_placa, format_placa
            if not validate_placa(placa):
                errors.append("❌ Placa: Formato inválido")
            else:
                clean_data['placa'] = format_placa(placa)
        else:
            clean_data['placa'] = ""
        
        # Valida motivo se fornecido
        if motivo and motivo.strip():
            clean_motivo, motivo_errors = SecurityValidator.sanitize_input(motivo, "Motivo")
            if motivo_errors:
                errors.extend([f"❌ Motivo: {err}" for err in motivo_errors])
            else:
                clean_data['motivo'] = clean_motivo
        else:
            clean_data['motivo'] = ""
        
        is_valid = len(errors) == 0
        return is_valid, clean_data, errors


class RateLimiter:
    """Controla taxa de requisições para prevenir abuso"""
    
    @staticmethod
    def check_rate_limit(user_id, action, max_attempts=5, time_window=60):
        """
        Verifica se o usuário excedeu o limite de tentativas.
        
        Args:
            user_id: Identificador do usuário
            action: Tipo de ação (ex: 'login', 'create_record')
            max_attempts: Número máximo de tentativas
            time_window: Janela de tempo em segundos
        
        Returns:
            (is_allowed, remaining_attempts, reset_time)
        """
        if 'rate_limits' not in st.session_state:
            st.session_state.rate_limits = {}
        
        key = f"{user_id}_{action}"
        now = get_sao_paulo_time()
        
        if key not in st.session_state.rate_limits:
            st.session_state.rate_limits[key] = {
                'attempts': [],
                'blocked_until': None
            }
        
        rate_data = st.session_state.rate_limits[key]
        
        # Verifica se está bloqueado
        if rate_data['blocked_until']:
            if now < rate_data['blocked_until']:
                remaining_time = (rate_data['blocked_until'] - now).seconds
                return False, 0, remaining_time
            else:
                # Desbloqueio
                rate_data['blocked_until'] = None
                rate_data['attempts'] = []
        
        # Remove tentativas antigas (fora da janela de tempo)
        cutoff_time = now - timedelta(seconds=time_window)
        rate_data['attempts'] = [
            attempt for attempt in rate_data['attempts'] 
            if attempt > cutoff_time
        ]
        
        # Verifica se excedeu o limite
        if len(rate_data['attempts']) >= max_attempts:
            rate_data['blocked_until'] = now + timedelta(seconds=time_window * 2)
            log_action("SECURITY_ALERT", f"Rate limit exceeded for {user_id} on action {action}")
            return False, 0, time_window * 2
        
        # Registra nova tentativa
        rate_data['attempts'].append(now)
        remaining = max_attempts - len(rate_data['attempts'])
        
        return True, remaining, 0
    
    @staticmethod
    def reset_rate_limit(user_id, action):
        """Reseta o rate limit para um usuário e ação específicos"""
        if 'rate_limits' not in st.session_state:
            return
        
        key = f"{user_id}_{action}"
        if key in st.session_state.rate_limits:
            del st.session_state.rate_limits[key]


class SessionSecurity:
    """Gerencia segurança de sessão"""
    
    @staticmethod
    def init_session_security():
        """Inicializa variáveis de segurança da sessão"""
        if 'session_id' not in st.session_state:
            import uuid
            st.session_state.session_id = str(uuid.uuid4())
        
        if 'last_activity' not in st.session_state:
            st.session_state.last_activity = get_sao_paulo_time()
        
        if 'failed_attempts' not in st.session_state:
            st.session_state.failed_attempts = {}
    
    @staticmethod
    def check_session_timeout(timeout_minutes=30):
        """
        Verifica se a sessão expirou por inatividade.
        
        Args:
            timeout_minutes: Minutos de inatividade antes de expirar
        
        Returns:
            (is_expired, minutes_inactive)
        """
        SessionSecurity.init_session_security()
        
        now = get_sao_paulo_time()
        last_activity = st.session_state.last_activity
        
        time_diff = now - last_activity
        minutes_inactive = time_diff.total_seconds() / 60
        
        if minutes_inactive > timeout_minutes:
            return True, minutes_inactive
        
        # Atualiza última atividade
        st.session_state.last_activity = now
        return False, minutes_inactive
    
    @staticmethod
    def record_failed_attempt(user_id, reason=""):
        """Registra tentativa de acesso falhada"""
        SessionSecurity.init_session_security()
        
        if user_id not in st.session_state.failed_attempts:
            st.session_state.failed_attempts[user_id] = []
        
        st.session_state.failed_attempts[user_id].append({
            'timestamp': get_sao_paulo_time(),
            'reason': reason
        })
        
        # Mantém apenas últimas 10 tentativas
        st.session_state.failed_attempts[user_id] = \
            st.session_state.failed_attempts[user_id][-10:]
        
        log_action("FAILED_ATTEMPT", f"User {user_id}: {reason}")
    
    @staticmethod
    def is_account_locked(user_id, max_attempts=5, lockout_minutes=15):
        """
        Verifica se a conta está bloqueada por tentativas falhadas.
        
        Returns:
            (is_locked, remaining_lockout_minutes)
        """
        SessionSecurity.init_session_security()
        
        if user_id not in st.session_state.failed_attempts:
            return False, 0
        
        attempts = st.session_state.failed_attempts[user_id]
        now = get_sao_paulo_time()
        
        # Filtra tentativas recentes (última hora)
        recent_attempts = [
            attempt for attempt in attempts
            if (now - attempt['timestamp']).total_seconds() < 3600
        ]
        
        if len(recent_attempts) >= max_attempts:
            # Verifica se ainda está no período de bloqueio
            last_attempt = max(recent_attempts, key=lambda x: x['timestamp'])
            time_since_last = now - last_attempt['timestamp']
            minutes_since = time_since_last.total_seconds() / 60
            
            if minutes_since < lockout_minutes:
                remaining = lockout_minutes - minutes_since
                return True, remaining
            else:
                # Período de bloqueio expirou, limpa tentativas
                st.session_state.failed_attempts[user_id] = []
                return False, 0
        
        return False, 0


def show_security_alert(message, alert_type="error"):
    """Exibe alerta de segurança com estilo apropriado"""
    if alert_type == "error":
        st.error(f"🔒 **ALERTA DE SEGURANÇA:** {message}")
    elif alert_type == "warning":
        st.warning(f"⚠️ **AVISO DE SEGURANÇA:** {message}")
    else:
        st.info(f"ℹ️ {message}")
