import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from typing import List, Optional, Dict
from app.utils import get_sao_paulo_time
from app.operations import SheetOperations

logger = logging.getLogger(__name__)

class GmailNotifier:
    """Classe responsável pelo envio de notificações via Gmail SMTP"""
    
    def __init__(self):
        """Inicializa o notificador com credenciais do Gmail"""
        try:
            if "email" in st.secrets:
                self.smtp_server = "smtp.gmail.com"
                self.smtp_port = 587
                self.email = st.secrets["email"]["gmail_user"]
                self.password = st.secrets["email"]["gmail_app_password"]
                self.from_name = st.secrets["email"].get("from_name", "Sistema BAERI")
                self.enabled = True
            else:
                logger.warning("Configurações de email não encontradas")
                self.enabled = False
        except Exception as e:
            logger.error(f"Erro ao inicializar GmailNotifier: {e}")
            self.enabled = False
    
    def send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str,
        plain_content: Optional[str] = None
    ) -> bool:
        """
        Envia email via Gmail SMTP
        
        Args:
            to_email: Email do destinatário
            subject: Assunto
            html_content: Conteúdo HTML
            plain_content: Conteúdo texto plano
        
        Returns:
            bool: True se enviado com sucesso
        """
        if not self.enabled:
            logger.warning("Sistema de email não habilitado")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Adiciona versão texto plano
            if plain_content:
                part1 = MIMEText(plain_content, 'plain', 'utf-8')
                msg.attach(part1)
            
            # Adiciona versão HTML
            part2 = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(part2)
            
            # Conecta e envia
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)
            
            logger.info(f"Email enviado com sucesso para {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar email para {to_email}: {e}")
            return False
    
    def send_bulk_email(
        self,
        recipients: List[str],
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None
    ) -> Dict[str, any]:
        """Envia emails para múltiplos destinatários"""
        results = {"success": 0, "failed": 0, "failed_emails": []}
        
        for email in recipients:
            if self.send_email(email, subject, html_content, plain_content):
                results["success"] += 1
            else:
                results["failed"] += 1
                results["failed_emails"].append(email)
        
        return results


class NotificationTemplates:
    """Templates HTML para notificações"""
    
    @staticmethod
    def _get_base_template(content: str) -> str:
        """Template base"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #0066cc 0%, #004999 100%);
                    color: white;
                    padding: 30px 20px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                }}
                .content {{
                    background-color: #ffffff;
                    padding: 30px;
                    border: 1px solid #e0e0e0;
                    border-top: none;
                }}
                .footer {{
                    background-color: #f5f5f5;
                    text-align: center;
                    padding: 20px;
                    font-size: 12px;
                    color: #666;
                    border-radius: 0 0 8px 8px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background-color: #0066cc;
                    color: white !important;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 15px 0;
                    font-weight: bold;
                }}
                .alert {{
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 15px 0;
                    border-radius: 4px;
                }}
                .success {{
                    background-color: #d4edda;
                    border-left: 4px solid #28a745;
                    padding: 15px;
                    margin: 15px 0;
                    border-radius: 4px;
                }}
                .danger {{
                    background-color: #f8d7da;
                    border-left: 4px solid #dc3545;
                    padding: 15px;
                    margin: 15px 0;
                    border-radius: 4px;
                }}
                .info-box {{
                    background-color: #e7f3ff;
                    border: 1px solid #b3d7ff;
                    padding: 15px;
                    margin: 15px 0;
                    border-radius: 4px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏢 Sistema BAERI</h1>
                <p style="margin: 5px 0 0 0; font-size: 14px;">Controle de Acesso</p>
            </div>
            <div class="content">
                {content}
            </div>
            <div class="footer">
                <p><strong>Esta é uma mensagem automática</strong></p>
                <p>Sistema de Controle de Acesso BAERI</p>
                <p style="font-size: 11px; color: #999;">
                    {get_sao_paulo_time().strftime('%d/%m/%Y às %H:%M')}
                </p>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def access_request_approved(user_name: str, role: str) -> tuple:
        """Notificação de aprovação"""
        role_display = "Administrador" if role == "admin" else "Operacional"
        
        content = f"""
        <h2 style="color: #28a745;">✅ Solicitação Aprovada!</h2>
        <div class="success">
            <p>Olá <strong>{user_name}</strong>,</p>
            <p>Sua solicitação de acesso ao sistema foi <strong>APROVADA</strong>! 🎉</p>
        </div>
        
        <div class="info-box">
            <p style="margin: 5px 0;"><strong>📋 Detalhes do Acesso:</strong></p>
            <p style="margin: 5px 0;">• <strong>Nível:</strong> {role_display}</p>
            <p style="margin: 5px 0;">• <strong>Status:</strong> Ativo</p>
        </div>
        
        <p>Você já pode acessar o sistema com sua conta Google.</p>
        
        <div style="text-align: center; margin: 25px 0;">
            <a href="https://seu-app.streamlit.app" class="button">🚀 Acessar Sistema</a>
        </div>
        
        <p style="color: #666; font-size: 14px;">
            Bem-vindo à equipe! Se tiver dúvidas, entre em contato com o administrador.
        </p>
        """
        
        html = NotificationTemplates._get_base_template(content)
        plain = f"Olá {user_name}, sua solicitação de acesso foi aprovada! Nível: {role_display}"
        
        return "✅ Acesso Aprovado - Sistema BAERI", html, plain
    
    @staticmethod
    def access_request_rejected(user_name: str, reason: str = "") -> tuple:
        """Notificação de rejeição"""
        reason_html = f"""
        <div class="alert">
            <p style="margin: 0;"><strong>📝 Motivo:</strong> {reason}</p>
        </div>
        """ if reason else ""
        
        content = f"""
        <h2 style="color: #dc3545;">❌ Solicitação Negada</h2>
        <div class="danger">
            <p>Olá <strong>{user_name}</strong>,</p>
            <p>Sua solicitação de acesso ao sistema foi <strong>NEGADA</strong>.</p>
        </div>
        
        {reason_html}
        
        <p>Se você acredita que isso é um erro ou deseja mais informações, 
        entre em contato com o administrador do sistema.</p>
        
        <p style="color: #666; font-size: 14px; margin-top: 20px;">
            📧 Para recursos, responda a este email ou contate diretamente o administrador.
        </p>
        """
        
        html = NotificationTemplates._get_base_template(content)
        plain = f"Olá {user_name}, sua solicitação de acesso foi negada. {reason if reason else ''}"
        
        return "❌ Solicitação Negada - Sistema BAERI", html, plain
    
    @staticmethod
    def pending_approval_alert(
        admin_name: str, 
        requester_name: str, 
        requester_email: str, 
        role: str,
        department: str,
        justification: str
    ) -> tuple:
        """Alerta de nova solicitação para admin"""
        role_display = "Administrador" if role == "admin" else "Operacional"
        
        content = f"""
        <h2 style="color: #ffc107;">⏳ Nova Solicitação Pendente</h2>
        <div class="alert">
            <p>Olá <strong>{admin_name}</strong>,</p>
            <p>Há uma nova solicitação de acesso aguardando sua análise.</p>
        </div>
        
        <div class="info-box">
            <p style="margin: 5px 0;"><strong>👤 Solicitante:</strong> {requester_name}</p>
            <p style="margin: 5px 0;"><strong>📧 Email:</strong> {requester_email}</p>
            <p style="margin: 5px 0;"><strong>🏢 Departamento:</strong> {department}</p>
            <p style="margin: 5px 0;"><strong>🔑 Nível solicitado:</strong> {role_display}</p>
        </div>
        
        <div style="background-color: #f9f9f9; padding: 15px; border-radius: 4px; margin: 15px 0;">
            <p style="margin: 0 0 10px 0;"><strong>📝 Justificativa:</strong></p>
            <p style="margin: 0; font-style: italic; color: #555;">"{justification}"</p>
        </div>
        
        <div style="text-align: center; margin: 25px 0;">
            <a href="https://seu-app.streamlit.app" class="button">🔍 Analisar Solicitação</a>
        </div>
        
        <p style="color: #666; font-size: 13px;">
            ⚡ <strong>Ação necessária:</strong> Por favor, aprove ou rejeite esta solicitação 
            o mais breve possível.
        </p>
        """
        
        html = NotificationTemplates._get_base_template(content)
        plain = f"Nova solicitação de {requester_name} ({requester_email}) para {role_display}"
        
        return "⏳ Nova Solicitação - Sistema BAERI", html, plain
    
    @staticmethod
    def blocklist_override_request(
        admin_name: str, 
        person_name: str, 
        company: str, 
        reason: str, 
        requester: str
    ) -> tuple:
        """Solicitação excepcional urgente"""
        content = f"""
        <h2 style="color: #dc3545;">⚠️ URGENTE: Liberação Excepcional</h2>
        <div class="danger">
            <p>Olá <strong>{admin_name}</strong>,</p>
            <p>Uma solicitação <strong style="color: #dc3545;">EXCEPCIONAL</strong> 
            de liberação foi criada e requer sua aprovação imediata.</p>
        </div>
        
        <div class="info-box">
            <p style="margin: 5px 0;"><strong>🚫 Bloqueado:</strong> {person_name}</p>
            <p style="margin: 5px 0;"><strong>🏢 Empresa:</strong> {company}</p>
            <p style="margin: 5px 0;"><strong>👤 Solicitante:</strong> {requester}</p>
        </div>
        
        <div style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; 
                    margin: 15px 0; border-radius: 4px;">
            <p style="margin: 0 0 10px 0;"><strong>📋 Justificativa da Liberação:</strong></p>
            <p style="margin: 0; color: #856404;">"{reason}"</p>
        </div>
        
        <div style="background-color: #f8d7da; padding: 15px; border-radius: 4px; margin: 15px 0;">
            <p style="margin: 0; color: #721c24;">
                <strong>⚡ ATENÇÃO:</strong> Esta pessoa/empresa está na blocklist permanente. 
                Avalie cuidadosamente antes de aprovar.
            </p>
        </div>
        
        <div style="text-align: center; margin: 25px 0;">
            <a href="https://seu-app.streamlit.app" class="button" 
               style="background-color: #dc3545;">🚨 Analisar AGORA</a>
        </div>
        """
        
        html = NotificationTemplates._get_base_template(content)
        plain = f"URGENTE: {requester} solicitou liberação excepcional para {person_name} ({company})"
        
        return "🚨 URGENTE: Liberação Excepcional - Sistema BAERI", html, plain


def get_admin_emails() -> List[str]:
    """Retorna lista de emails de administradores do sistema"""
    try:
        if "email" in st.secrets and "admin_emails" in st.secrets["email"]:
            return st.secrets["email"]["admin_emails"]
        
        # Fallback: busca admins na planilha
        sheet_ops = SheetOperations()
        users_data = sheet_ops.carregar_dados_aba('users')
        
        if not users_data or len(users_data) < 2:
            return []
        
        admin_emails = []
        for row in users_data[1:]:
            if len(row) >= 2 and row[1].lower() == 'admin':
                admin_emails.append(row[0])
        
        return admin_emails
        
    except Exception as e:
        logger.error(f"Erro ao buscar emails de admins: {e}")
        return []


def send_notification(notification_type: str, **kwargs) -> bool:
    """
    Envia notificação por email
    
    Args:
        notification_type: Tipo ('access_approved', 'access_rejected', etc.)
        **kwargs: Argumentos específicos
    
    Returns:
        bool: True se sucesso
    """
    notifier = GmailNotifier()
    
    if not notifier.enabled:
        logger.warning("Sistema de notificações não habilitado")
        return False
    
    templates = NotificationTemplates()
    
    try:
        if notification_type == "access_approved":
            subject, html, plain = templates.access_request_approved(
                kwargs['user_name'],
                kwargs['role']
            )
            return notifier.send_email(kwargs['to_email'], subject, html, plain)
        
        elif notification_type == "access_rejected":
            subject, html, plain = templates.access_request_rejected(
                kwargs['user_name'],
                kwargs.get('reason', '')
            )
            return notifier.send_email(kwargs['to_email'], subject, html, plain)
        
        elif notification_type == "pending_approval":
            subject, html, plain = templates.pending_approval_alert(
                kwargs['admin_name'],
                kwargs['requester_name'],
                kwargs['requester_email'],
                kwargs['role'],
                kwargs['department'],
                kwargs['justification']
            )
            
            # Envia para todos os admins
            admin_emails = get_admin_emails()
            if admin_emails:
                results = notifier.send_bulk_email(admin_emails, subject, html, plain)
                return results['success'] > 0
            return False
        
        elif notification_type == "blocklist_override":
            subject, html, plain = templates.blocklist_override_request(
                kwargs['admin_name'],
                kwargs['person_name'],
                kwargs['company'],
                kwargs['reason'],
                kwargs['requester']
            )
            
            # Envia para todos os admins
            admin_emails = get_admin_emails()
            if admin_emails:
                results = notifier.send_bulk_email(admin_emails, subject, html, plain)
                return results['success'] > 0
            return False
        
        else:
            logger.error(f"Tipo de notificação desconhecido: {notification_type}")
            return False
            
    except Exception as e:
        logger.error(f"Erro ao enviar notificação {notification_type}: {e}")
        return False


def notify_all_admins(subject: str, html_content: str, plain_content: str = "") -> Dict:
    """
    Envia notificação para todos os administradores
    
    Returns:
        Dict com resultados do envio
    """
    notifier = GmailNotifier()
    admin_emails = get_admin_emails()
    
    if not admin_emails:
        logger.warning("Nenhum email de administrador encontrado")
        return {"success": 0, "failed": 0, "failed_emails": []}
    
    return notifier.send_bulk_email(admin_emails, subject, html_content, plain_content)
