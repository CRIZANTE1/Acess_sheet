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
        """Envia email via Gmail SMTP"""
        if not self.enabled:
            logger.warning("Sistema de email não habilitado")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Texto plano
            if plain_content:
                part1 = MIMEText(plain_content, 'plain', 'utf-8')
                msg.attach(part1)
            
            # HTML
            part2 = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(part2)
            
            # Envia
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)
            
            logger.info(f"Email enviado para {to_email}")
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
        """Template base para emails"""
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
                    background-color: #f5f5f5;
                }}
                .email-container {{
                    background-color: #ffffff;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #0066cc 0%, #004999 100%);
                    color: white;
                    padding: 30px 20px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                }}
                .content {{
                    padding: 30px 20px;
                }}
                .footer {{
                    background-color: #f5f5f5;
                    text-align: center;
                    padding: 20px;
                    font-size: 12px;
                    color: #666;
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
                .success-box {{
                    background-color: #d4edda;
                    border-left: 4px solid #28a745;
                    padding: 15px;
                    margin: 15px 0;
                    border-radius: 4px;
                }}
                .danger-box {{
                    background-color: #f8d7da;
                    border-left: 4px solid #dc3545;
                    padding: 15px;
                    margin: 15px 0;
                    border-radius: 4px;
                }}
                .warning-box {{
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
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
                .detail-row {{
                    padding: 8px 0;
                    border-bottom: 1px solid #eee;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
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
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def access_request_approved(user_name: str, role: str, system_url: str = "#") -> tuple:
        """Email de aprovação de solicitação de acesso"""
        role_display = "Administrador" if role == "admin" else "Operacional"
        
        content = f"""
        <h2 style="color: #28a745;">✅ Solicitação Aprovada!</h2>
        <div class="success-box">
            <p>Olá <strong>{user_name}</strong>,</p>
            <p>Sua solicitação de acesso ao Sistema BAERI foi <strong>APROVADA</strong>! 🎉</p>
        </div>
        
        <div class="info-box">
            <div class="detail-row"><strong>📋 Nível de Acesso:</strong> {role_display}</div>
            <div class="detail-row"><strong>✅ Status:</strong> Ativo</div>
        </div>
        
        <p>Você já pode acessar o sistema usando sua conta Google:</p>
        
        <div style="text-align: center; margin: 25px 0;">
            <a href="{system_url}" class="button">🚀 Acessar Sistema</a>
        </div>
        
        <p style="color: #666; font-size: 14px;">
            Bem-vindo à equipe! Em caso de dúvidas, entre em contato com o administrador.
        </p>
        """
        
        html = NotificationTemplates._get_base_template(content)
        plain = f"Olá {user_name}, sua solicitação de acesso foi aprovada! Nível: {role_display}. Acesse: {system_url}"
        
        return "✅ Acesso Aprovado - Sistema BAERI", html, plain
    
    @staticmethod
    def access_request_rejected(user_name: str, reason: str = "") -> tuple:
        """Email de rejeição de solicitação"""
        reason_html = f"""
        <div class="warning-box">
            <p style="margin: 0;"><strong>📝 Motivo:</strong> {reason}</p>
        </div>
        """ if reason else ""
        
        content = f"""
        <h2 style="color: #dc3545;">❌ Solicitação Negada</h2>
        <div class="danger-box">
            <p>Olá <strong>{user_name}</strong>,</p>
            <p>Sua solicitação de acesso ao Sistema BAERI foi <strong>NEGADA</strong>.</p>
        </div>
        
        {reason_html}
        
        <p>Se você acredita que isso é um erro ou deseja mais informações, 
        entre em contato com o administrador do sistema.</p>
        
        <p style="color: #666; font-size: 13px; margin-top: 20px;">
            📧 Para recursos, entre em contato diretamente com o administrador.
        </p>
        """
        
        html = NotificationTemplates._get_base_template(content)
        plain = f"Olá {user_name}, sua solicitação de acesso foi negada. {reason if reason else ''}"
        
        return "❌ Solicitação Negada - Sistema BAERI", html, plain
    
    @staticmethod
    def new_access_request_alert(
        requester_name: str, 
        requester_email: str, 
        role: str,
        department: str,
        justification: str,
        system_url: str = "#"
    ) -> tuple:
        """Email para admin sobre nova solicitação de acesso"""
        role_display = "Administrador" if role == "admin" else "Operacional"
        
        content = f"""
        <h2 style="color: #ffc107;">⏳ Nova Solicitação de Acesso</h2>
        <div class="warning-box">
            <p><strong>Atenção Administrador!</strong></p>
            <p>Uma nova solicitação de acesso está aguardando sua análise.</p>
        </div>
        
        <div class="info-box">
            <div class="detail-row"><strong>👤 Solicitante:</strong> {requester_name}</div>
            <div class="detail-row"><strong>📧 Email:</strong> {requester_email}</div>
            <div class="detail-row"><strong>🏢 Departamento:</strong> {department}</div>
            <div class="detail-row"><strong>🔑 Acesso solicitado:</strong> {role_display}</div>
        </div>
        
        <div style="background-color: #f9f9f9; padding: 15px; border-radius: 4px; margin: 15px 0;">
            <p style="margin: 0 0 10px 0;"><strong>📝 Justificativa:</strong></p>
            <p style="margin: 0; font-style: italic; color: #555;">"{justification}"</p>
        </div>
        
        <div style="text-align: center; margin: 25px 0;">
            <a href="{system_url}" class="button">🔍 Analisar Solicitação</a>
        </div>
        
        <p style="color: #666; font-size: 13px;">
            ⚡ Por favor, aprove ou rejeite esta solicitação o mais breve possível.
        </p>
        """
        
        html = NotificationTemplates._get_base_template(content)
        plain = f"Nova solicitação de acesso: {requester_name} ({requester_email}) - {role_display} - Depto: {department}"
        
        return "⏳ Nova Solicitação de Acesso - Sistema BAERI", html, plain
    
    @staticmethod
    def blocklist_override_request(
        person_name: str, 
        company: str, 
        reason: str, 
        requester: str,
        system_url: str = "#"
    ) -> tuple:
        """Email urgente sobre solicitação de desbloqueio"""
        content = f"""
        <h2 style="color: #dc3545;">🚨 URGENTE: Solicitação de Desbloqueio</h2>
        <div class="danger-box">
            <p><strong>Atenção Administrador!</strong></p>
            <p>Uma solicitação <strong style="color: #dc3545;">EXCEPCIONAL</strong> 
            de liberação foi criada e requer aprovação imediata.</p>
        </div>
        
        <div class="info-box">
            <div class="detail-row"><strong>🚫 Pessoa/Empresa Bloqueada:</strong> {person_name}</div>
            <div class="detail-row"><strong>🏢 Empresa:</strong> {company}</div>
            <div class="detail-row"><strong>👤 Solicitante:</strong> {requester}</div>
            <div class="detail-row" style="border-bottom: none;">
                <strong>📅 Data/Hora:</strong> {get_sao_paulo_time().strftime('%d/%m/%Y às %H:%M')}
            </div>
        </div>
        
        <div class="warning-box">
            <p style="margin: 0 0 10px 0;"><strong>📋 Justificativa da Liberação:</strong></p>
            <p style="margin: 0; color: #856404; font-weight: 500;">"{reason}"</p>
        </div>
        
        <div class="danger-box">
            <p style="margin: 0; font-size: 14px;">
                <strong>⚠️ ATENÇÃO:</strong> Esta pessoa/empresa está na lista de bloqueio permanente. 
                Analise cuidadosamente antes de aprovar esta exceção.
            </p>
        </div>
        
        <div style="text-align: center; margin: 25px 0;">
            <a href="{system_url}" class="button" style="background-color: #dc3545;">
                🚨 ANALISAR AGORA
            </a>
        </div>
        
        <p style="color: #721c24; font-size: 13px; font-weight: bold;">
            ⏰ Esta solicitação requer análise prioritária!
        </p>
        """
        
        html = NotificationTemplates._get_base_template(content)
        plain = f"URGENTE: {requester} solicitou liberação excepcional para {person_name} ({company}). Motivo: {reason}"
        
        return "🚨 URGENTE: Solicitação de Desbloqueio - Sistema BAERI", html, plain


def get_admin_emails() -> List[str]:
    """Retorna lista de emails dos administradores"""
    try:
        # Primeiro tenta pegar do secrets
        if "email" in st.secrets and "admin_emails" in st.secrets["email"]:
            emails = st.secrets["email"]["admin_emails"]
            # Se for uma string, converte para lista
            if isinstance(emails, str):
                return [e.strip() for e in emails.split(',')]
            return emails
        
        # Fallback: busca na planilha
        sheet_ops = SheetOperations()
        users_data = sheet_ops.carregar_dados_aba('users')
        
        if not users_data or len(users_data) < 2:
            logger.warning("Nenhum usuário encontrado na planilha")
            return []
        
        admin_emails = []
        for row in users_data[1:]:
            if len(row) >= 2 and row[1].lower() == 'admin':
                admin_emails.append(row[0])
        
        return admin_emails
        
    except Exception as e:
        logger.error(f"Erro ao buscar emails de admins: {e}")
        return []


def get_system_url() -> str:
    """Retorna a URL do sistema"""
    try:
        if "email" in st.secrets and "system_url" in st.secrets["email"]:
            return st.secrets["email"]["system_url"]
        return "https://seu-app.streamlit.app"
    except:
        return "https://seu-app.streamlit.app"


def send_notification(notification_type: str, **kwargs) -> bool:
    """
    Envia notificação por email
    
    Tipos disponíveis:
    - access_approved: Notifica usuário sobre aprovação
    - access_rejected: Notifica usuário sobre rejeição
    - new_access_request: Notifica admins sobre nova solicitação
    - blocklist_override: Notifica admins sobre desbloqueio urgente
    """
    notifier = GmailNotifier()
    
    if not notifier.enabled:
        logger.warning("Sistema de notificações não habilitado")
        return False
    
    templates = NotificationTemplates()
    system_url = get_system_url()
    
    try:
        if notification_type == "access_approved":
            subject, html, plain = templates.access_request_approved(
                kwargs['user_name'],
                kwargs['role'],
                system_url
            )
            return notifier.send_email(kwargs['to_email'], subject, html, plain)
        
        elif notification_type == "access_rejected":
            subject, html, plain = templates.access_request_rejected(
                kwargs['user_name'],
                kwargs.get('reason', '')
            )
            return notifier.send_email(kwargs['to_email'], subject, html, plain)
        
        elif notification_type == "new_access_request":
            subject, html, plain = templates.new_access_request_alert(
                kwargs['requester_name'],
                kwargs['requester_email'],
                kwargs['role'],
                kwargs['department'],
                kwargs['justification'],
                system_url
            )
            
            # Envia para todos os admins
            admin_emails = get_admin_emails()
            if not admin_emails:
                logger.error("Nenhum email de admin configurado!")
                return False
            
            results = notifier.send_bulk_email(admin_emails, subject, html, plain)
            return results['success'] > 0
        
        elif notification_type == "blocklist_override":
            subject, html, plain = templates.blocklist_override_request(
                kwargs['person_name'],
                kwargs['company'],
                kwargs['reason'],
                kwargs['requester'],
                system_url
            )
            
            # Envia para todos os admins
            admin_emails = get_admin_emails()
            if not admin_emails:
                logger.error("Nenhum email de admin configurado!")
                return False
            
            results = notifier.send_bulk_email(admin_emails, subject, html, plain)
            return results['success'] > 0
        
        else:
            logger.error(f"Tipo de notificação desconhecido: {notification_type}")
            return False
            
    except Exception as e:
        logger.error(f"Erro ao enviar notificação {notification_type}: {e}")
        return False
