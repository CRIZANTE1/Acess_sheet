import streamlit as st
from datetime import datetime
import pytz
import pygsheets
from app.sheets_api import connect_sheet
from auth.auth_utils import get_user_display_name, is_user_logged_in

LOG_SHEET_NAME = 'logs'

def _get_sao_paulo_time_str():
    """Retorna o timestamp atual formatado para São Paulo."""
    sao_paulo_tz = pytz.timezone("America/Sao_Paulo")
    return datetime.now(sao_paulo_tz).strftime('%Y-%m-%d %H:%M:%S')

def log_action(action: str, details: str = ""):
    """
    Registra uma ação do usuário na planilha de logs.
    É projetado para não quebrar a aplicação se o log falhar.
    """
    if not is_user_logged_in():
        return

    try:
        user = get_user_display_name()
        timestamp = _get_sao_paulo_time_str()
        log_entry = [timestamp, user, action, details]

        credentials, spreadsheet_url = connect_sheet()
        if not credentials:
            print(f"LOGGING FAILED: Não foi possível conectar ao Google Sheets.")
            return

        gc = credentials
        spreadsheet = gc.open_by_url(spreadsheet_url)

        try:
            worksheet = spreadsheet.worksheet_by_title(LOG_SHEET_NAME)
        except pygsheets.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(LOG_SHEET_NAME)
            worksheet.update_row(1, ["Timestamp", "User", "Action", "Details"])
            print(f"LOGGING INFO: Criada nova planilha de log '{LOG_SHEET_NAME}'.")

        worksheet.append_table(values=log_entry, start='A2', overwrite=False)

    except Exception as e:
        print(f"CRITICAL LOGGING ERROR: Falha ao escrever na planilha de logs. Erro: {e}")
