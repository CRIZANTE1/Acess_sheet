import streamlit as st
import pandas as pd
import pygsheets
import os
import json
import logging

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def connect_sheet():
    try:
        logging.info("Tentando conectar ao Google Sheets...")

        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            service_account_info = dict(st.secrets["connections"]["gsheets"])
            spreadsheet_url = service_account_info.pop("spreadsheet")
            
            json_credentials = json.dumps(service_account_info)
            os.environ["GCP_SERVICE_ACCOUNT"] = json_credentials
            
            credentials = pygsheets.authorize(service_account_env_var="GCP_SERVICE_ACCOUNT")
        else:
            # Fallback local
            credentials_path = os.path.join(os.path.dirname(__file__), 'credentials', 'cred.json')
            
            if not os.path.exists(credentials_path):
                logging.error(f"Arquivo de credenciais não encontrado em: {credentials_path}")
                st.error("Credenciais do Google Sheets não configuradas. Configure o arquivo secrets.toml ou cred.json.")
                return None, None
            
            credentials = pygsheets.authorize(service_file=credentials_path)
            
            # Use variável de ambiente ou configuração local
            spreadsheet_url = os.getenv('SPREADSHEET_URL', st.secrets.get('spreadsheet_url', ''))
            
            if not spreadsheet_url:
                logging.error("URL da planilha não configurada.")
                st.error("URL da planilha não foi configurada. Adicione SPREADSHEET_URL nas variáveis de ambiente ou no secrets.toml")
                return None, None

        logging.info("Conexão ao Google Sheets bem sucedida.")
        return credentials, spreadsheet_url

    except Exception as e:
        logging.error(f"Erro durante a autorização do Google Sheets: {e}")
        st.error(f"Erro durante a autorização do Google Sheets: {e}")
        return None, None
