import streamlit as st
import pandas as pd
import logging
import random
import os
import json
import pygsheets

class SheetOperations:
    
    def __init__(self):
        try:
            logging.info("SheetOperations: Tentando conectar ao Google Sheets...")
            if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
                service_account_info = dict(st.secrets["connections"]["gsheets"])
                spreadsheet_url = service_account_info.pop("spreadsheet")
                json_credentials = json.dumps(service_account_info)
                os.environ["GCP_SERVICE_ACCOUNT"] = json_credentials
                self.credentials = pygsheets.authorize(service_account_env_var="GCP_SERVICE_ACCOUNT")
                self.my_archive_google_sheets = spreadsheet_url
            else:
                credentials_path = os.path.join(os.path.dirname(__file__), 'credentials', 'cred.json')
                self.credentials = pygsheets.authorize(service_file=credentials_path)
                self.my_archive_google_sheets = "https://docs.google.com/spreadsheets/d/1sZ6PMTRTTyYekggsA4XWAJAn39XCVsDfpqXwrwMTXP8/edit?gid=0#gid=0"
            logging.info("SheetOperations: Conexão bem sucedida.")
        except Exception as e:
            logging.error(f"SheetOperations: Erro durante a autorização: {e}")
            st.error(f"Erro crítico ao conectar com o Google Sheets: {e}")
            self.credentials = None
            self.my_archive_google_sheets = None
    
    def carregar_dados(self):
        return self.carregar_dados_aba('acess')
    
    def carregar_dados_funcionarios(self):
        return self.carregar_dados_aba('funcionarios')

    def carregar_dados_aprovadores(self):
        dados = self.carregar_dados_aba('authorizer')
        if dados and len(dados) > 1:
            return [row[0] for row in dados[1:] if row and row[0].strip()]
        return []

    # --- FUNÇÃO CORRIGIDA ---
    def carregar_dados_aba(self, aba_name):
        if not self.credentials or not self.my_archive_google_sheets:
            st.error("Conexão com Google Sheets não configurada.")
            return None
        try:
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            aba = archive.worksheet_by_title(aba_name)
            all_values = aba.get_all_values()

            if not all_values:
                logging.warning(f"A aba '{aba_name}' está vazia ou não foi encontrada.")
                return []

            header = all_values[0]
            # Encontra os índices das colunas que têm um nome (não são vazias)
            valid_column_indices = [i for i, col_name in enumerate(header) if col_name.strip()]

            if not valid_column_indices:
                logging.warning(f"Nenhum cabeçalho válido encontrado na aba '{aba_name}'.")
                return []

            # Filtra os dados, mantendo apenas as colunas válidas
            filtered_data = []
            for row in all_values:
                # Cria uma nova linha apenas com os valores das colunas válidas
                filtered_row = [row[i] for i in valid_column_indices if i < len(row)]
                filtered_data.append(filtered_row)
            
            return filtered_data

        except Exception as e:
            logging.error(f"Erro ao ler dados da aba '{aba_name}': {e}")
            st.error(f"Erro ao carregar dados da aba '{aba_name}'. Verifique o console.")
            return None
        
    def adc_dados(self, new_data):
        if not self.credentials: return
        try:
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            aba = archive.worksheet_by_title('acess')
            
            all_values = aba.get_all_values()
            existing_ids = {row[0] for row in all_values[1:] if row} # Garante que a linha não esteja vazia
            
            while True:
                new_id = random.randint(1000, 9999)
                if str(new_id) not in existing_ids:
                    break

            new_data.insert(0, str(new_id))
            aba.append_table(values=new_data)
        except Exception as e:
            logging.error(f"Erro ao adicionar dados: {e}", exc_info=True)
            st.error(f"Erro ao adicionar dados: {e}")

    def editar_dados(self, id_registro, updated_data):
        if not self.credentials: return False
        try:
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            aba = archive.worksheet_by_title('acess')
            data = aba.get_all_values()
            
            for i, row in enumerate(data):
                if row and row[0] == str(id_registro):
                    # Garante que o número de colunas corresponda ao cabeçalho original
                    header_len = len(data[0])
                    full_updated_row = [str(id_registro)] + updated_data
                    # Trunca ou preenche a linha para corresponder ao tamanho do cabeçalho
                    final_row = (full_updated_row + [''] * header_len)[:header_len]
                    aba.update_row(i + 1, final_row)
                    return True
            return False
        except Exception as e:
            logging.error(f"Erro ao editar dados: {e}", exc_info=True)
            return False

    def excluir_dados(self, id_registro):
        if not self.credentials: return False
        try:
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            aba = archive.worksheet_by_title('acess')
            data = aba.get_all_values()
            
            for i, row in enumerate(data):
                if row and row[0] == str(id_registro):
                    aba.delete_rows(i + 1)
                    return True
            return False
        except Exception as e:
            logging.error(f"Erro ao excluir dados: {e}", exc_info=True)
            return False












