# app/notifications.py
import streamlit as st
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
import logging
from datetime import datetime
from app.utils import get_sao_paulo_time
from typing import List, Optional

logger = logging.getLogger(__name__)

class EmailNotifier:
    """Classe responsável pelo envio de notificações por email"""
    
    def __init__(self):
        """Inicializa o notificador com as credenciais do SendGrid"""
        try:
            # Tenta carregar as configurações de email do secrets
            if "email" in st.secrets:
                self.api_key = st.secrets["email"]["sendgrid_api_key"]
                self.from_email = st.secrets["email"]["from_email"]
                self.from_name = st.secrets["email"].get("from_name", "Sistema BAERI")
                self.enabled = True
            else:
                logger.warning("Configurações de email não encontradas no secrets.toml")
                self.enabled = False
        except Exception as e:
            logger.error(f"Erro ao inicializar EmailNotifier: {e}")
            self.enabled = False
    
    def send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str,
        plain_content: Optional[str] = None
    ) -> bool:
        """
        Envia um email usando SendGrid
        
        Args:
            to_email: Email do destinatário
            subject: Assunto do email
            html_content: Conteúdo HTML do email
            plain_content: Conteúdo texto plano (opcional)
        
        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        if not self.enabled:
            logger.warning("Sistema de email não está habilitado")
            return False
        
        try:
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            if plain_content:
                message.add_content(Content("text/plain", plain_content))
            
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Email enviado com sucesso para {to_email}")
                return True
            else:
                logger.error(f"Falha ao enviar email. Status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}")
            return False
    
    def send_bulk_email(
        self,
        recipients: List[str],
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None
    ) -> dict:
        """
        Envia emails para múltiplos destinatários
        
        Returns:
            dict: {"success": int, "failed": int, "failed_emails": List[str]}
        """
        results = {"success": 0, "failed": 0, "failed_emails": []}
        
        for email in recipients:
            if self.send_email(email, subject, html_content, plain_content):
                results["success"] += 1
            else:
                results["failed"] += 1
                results["failed_emails"].append(email)
        
        return results


class NotificationTemplates:
    """Templates de email para diferentes tipos de notificação"""
    
    @staticmethod
    def _get_base_template(content: str) -> str:
        """Template base para todos os emails"""
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
                    background-color: #0066cc;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 30px;
                    border: 1px solid #ddd;
                    border-radius: 0 0 5px 5px;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    font-size: 12px;
                    color: #666;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background-color: #0066cc;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 15px 0;
                }}
                .alert {{
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 15px 0;
                }}
                .success {{
                    background-color: #d4edda;
                    border-left: 4px solid #28a745;
                    padding: 15px;
                    margin: 15px 0;
                }}
                .danger {{
                    background-color: #f8d7da;
                    border-left: 4px solid #dc3545;
                    padding: 15px;
                    margin: 15px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Sistema de Controle de Acesso BAERI</h1>
            </div>
            <div class="content">
                {content}
            </div>
            <div class="footer">
                <p>Esta é uma mensagem automática do Sistema BAERI.</p>
                <p>Por favor, não responda a este email.</p>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def access_request_approved(user_name: str, role: str) -> tuple:
        """Template para notificação de aprovação de acesso"""
        content = f"""
        <h2>✅ Solicitação de Acesso Aprovada</h2>
        <div class="success">
            <p>Olá <strong>{user_name}</strong>,</p>
            <p>Sua solicitação de acesso ao sistema foi <strong>APROVADA</strong>!</p>
        </div>
        <p><strong>Nível de acesso concedido:</strong> {role}</p>
        <p>Você já pode acessar o sistema através do link abaixo:</p>
        <p style="text-align: center;">
            <a href="https://seu-sistema.streamlit.app" class="button">Acessar Sistema</a>
        </p>
        <p>Bem-vindo à equipe!</p>
        """
        
        html = NotificationTemplates._get_base_template(content)
        plain = f"Olá {user_name}, sua solicitação de acesso foi aprovada! Nível: {role}"
        
        return "✅ Solicitação de Acesso Aprovada - Sistema BAERI", html, plain
    
    @staticmethod
    def access_request_rejected(user_name: str, reason: str = "") -> tuple:
        """Template para notificação de rejeição de acesso"""
        reason_text = f"<p><strong>Motivo:</strong> {reason}</p>" if reason else ""
        
        content = f"""
        <h2>❌ Solicitação de Acesso Negada</h2>
        <div class="danger">
            <p>Olá <strong>{user_name}</strong>,</p>
            <p>Infelizmente, sua solicitação de acesso ao sistema foi <strong>NEGADA</strong>.</p>
        </div>
        {reason_text}
        <p>Se você acredita que isso é um erro ou deseja mais informações, 
        entre em contato com o administrador do sistema.</p>
        """
        
        html = NotificationTemplates._get_base_template(content)
        plain = f"Olá {user_name}, sua solicitação de acesso foi negada."
        
        return "❌ Solicitação de Acesso Negada - Sistema BAERI", html, plain
    
    @staticmethod
    def pending_approval_alert(admin_name: str, requester_name: str, requester_email: str, role: str) -> tuple:
        """Template para alertar admin sobre nova solicitação"""
        content = f"""
        <h2>⏳ Nova Solicitação de Acesso Pendente</h2>
        <div class="alert">
            <p>Olá <strong>{admin_name}</strong>,</p>
            <p>Há uma nova solicitação de acesso aguardando sua análise.</p>
        </div>
        <p><strong>Solicitante:</strong> {requester_name}</p>
        <p><strong>Email:</strong> {requester_email}</p>
        <p><strong>Nível solicitado:</strong> {role}</p>
        <p>Por favor, acesse o painel administrativo para analisar:</p>
        <p style="text-align: center;">
            <a href="https://seu-sistema.streamlit.app" class="button">Acessar Painel Admin</a>
        </p>
        """
        
        html = NotificationTemplates._get_base_template(content)
        plain = f"Nova solicitação de {requester_name} ({requester_email}) para {role}"
        
        return "⏳ Nova Solicitação de Acesso - Sistema BAERI", html, plain
    
    @staticmethod
    def blocklist_override_request(admin_name: str, person_name: str, company: str, reason: str, requester: str) -> tuple:
        """Template para solicitação excepcional de liberação de bloqueio"""
        content = f"""
        <h2>⚠️ Solicitação Excepcional de Liberação</h2>
        <div class="danger">
            <p>Olá <strong>{admin_name}</strong>,</p>
            <p>Uma solicitação <strong>EXCEPCIONAL</strong> de liberação de bloqueio foi criada.</p>
        </div>
        <p><strong>Pessoa/Empresa bloqueada:</strong> {person_name} - {company}</p>
        <p><strong>Solicitante:</strong> {requester}</p>
        <p><strong>Justificativa:</strong></p>
        <div class="alert">
            <p>{reason}</p>
        </div>
        <p style="color: red;"><strong>Esta solicitação requer aprovação URGENTE!</strong></p>
        <p style="text-align: center;">
            <a href="https://seu-sistema.streamlit.app" class="button">Analisar Solicitação</a>
        </p>
        """
        
        html = NotificationTemplates._get_base_template(content)
        plain = f"Solicitação excepcional de {requester} para liberar {person_name}"
        
        return "⚠️ URGENTE: Solicitação Excepcional - Sistema BAERI", html, plain
    
    @staticmethod
    def daily_summary(admin_name: str, stats: dict) -> tuple:
        """Template para resumo diário de atividades"""
        content = f"""
        <h2>📊 Resumo Diário do Sistema</h2>
        <p>Olá <strong>{admin_name}</strong>,</p>
        <p>Aqui está o resumo das atividades de hoje ({get_sao_paulo_time().strftime('%d/%m/%Y')}):</p>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr style="background-color: #f2f2f2;">
                <td style="padding: 12px; border: 1px solid #ddd;"><strong>Métrica</strong></td>
                <td style="padding: 12px; border: 1px solid #ddd; text-align: right;"><strong>Valor</strong></td>
            </tr>
            <tr>
                <td style="padding: 12px; border: 1px solid #ddd;">Total de Acessos</td>
                <td style="padding: 12px; border: 1px solid #ddd; text-align: right;">{stats.get('total_accesses', 0)}</td>
            </tr>
            <tr>
                <td style="padding: 12px; border: 1px solid #ddd;">Novos Cadastros</td>
                <td style="padding: 12px; border: 1px solid #ddd; text-align: right;">{stats.get('new_registrations', 0)}</td>
            </tr>
            <tr>
                <td style="padding: 12px; border: 1px solid #ddd;">Solicitações Pendentes</td>
                <td style="padding: 12px; border: 1px solid #ddd; text-align: right;">{stats.get('pending_requests', 0)}</td>
            </tr>
            <tr>
                <td style="padding: 12px; border: 1px solid #ddd;">Bloqueios Aplicados</td>
                <td style="padding: 12px; border: 1px solid #ddd; text-align: right;">{stats.get('blocks_applied', 0)}</td>
            </tr>
        </table>
        
        <p style="text-align: center;">
            <a href="https://seu-sistema.streamlit.app" class="button">Ver Relatório Completo</a>
        </p>
        """
        
        html = NotificationTemplates._get_base_template(content)
        plain = f"Resumo diário: {stats.get('total_accesses', 0)} acessos, {stats.get('pending_requests', 0)} pendentes"
        
        return "📊 Resumo Diário - Sistema BAERI", html, plain


def send_notification(notification_type: str, **kwargs) -> bool:
    """
    Função auxiliar para enviar notificações
    
    Args:
        notification_type: Tipo de notificação ('access_approved', 'access_rejected', etc.)
        **kwargs: Argumentos específicos para cada tipo de notificação
    
    Returns:
        bool: True se enviado com sucesso
    """
    notifier = EmailNotifier()
    
    if not notifier.enabled:
        logger.warning("Sistema de notificações por email não está habilitado")
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
                kwargs['role']
            )
            return notifier.send_email(kwargs['admin_email'], subject, html, plain)
        
        elif notification_type == "blocklist_override":
            subject, html, plain = templates.blocklist_override_request(
                kwargs['admin_name'],
                kwargs['person_name'],
                kwargs['company'],
                kwargs['reason'],
                kwargs['requester']
            )
            return notifier.send_email(kwargs['admin_email'], subject, html, plain)
        
        elif notification_type == "daily_summary":
            subject, html, plain = templates.daily_summary(
                kwargs['admin_name'],
                kwargs['stats']
            )
            return notifier.send_email(kwargs['admin_email'], subject, html, plain)
        
        else:
            logger.error(f"Tipo de notificação desconhecido: {notification_type}")
            return False
            
    except Exception as e:
        logger.error(f"Erro ao enviar notificação {notification_type}: {e}")
        return False
