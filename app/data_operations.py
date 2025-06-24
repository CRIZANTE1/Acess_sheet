
import streamlit as st
import pandas as pd
import logging
import random
import os
import json
import pygsheets
from datetime import datetime, timedelta

# A CLASSE 'SheetOperations' AGORA VIVE AQUI DENTRO
class SheetOperations:
    def __init__(self):
        try:
            if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
                service_account_info = dict(st.secrets["connections"]["gsheets"])
                spreadsheet_url = service_account_info.pop("spreadsheet")
                self.credentials = pygsheets.authorize(service_account_info=service_account_info)
                self.spreadsheet_url = spreadsheet_url
            else:
                credentials_path = os.path.join(os.path.dirname(__file__), 'credentials', 'cred.json')
                self.credentials = pygsheets.authorize(service_file=credentials_path)
                self.spreadsheet_url = "https://docs.google.com/spreadsheets/d/1sZ6PMTRTTyYekggsA4XWAJAn39XCVsDfpqXwrwMTXP8/edit?gid=0#gid=0"
        except Exception as e:
            st.error(f"Erro crítico ao conectar com o Google Sheets: {e}")
            self.credentials = None

    def carregar_dados_aba(self, aba_name):
        if not self.credentials: return None
        try:
            archive = self.credentials.open_by_url(self.spreadsheet_url)
            aba = archive.worksheet_by_title(aba_name)
            all_values = aba.get_all_values()
            if not all_values: return []
            header = all_values[0]
            valid_indices = [i for i, h in enumerate(header) if h]
            return [[row[i] for i in valid_indices if i < len(row)] for row in all_values]
        except Exception as e:
            st.error(f"Erro ao carregar dados da aba '{aba_name}': {e}")
            return None

    def carregar_dados_aprovadores(self):
        dados = self.carregar_dados_aba('authorizer')
        return [row[0] for row in dados[1:] if row] if dados and len(dados) > 1 else []

    def adc_dados(self, new_data):
        if not self.credentials: return
        try:
            archive = self.credentials.open_by_url(self.spreadsheet_url)
            aba = archive.worksheet_by_title('acess')
            all_values = aba.get_all_values()
            existing_ids = {row[0] for row in all_values[1:] if row}
            new_id = str(random.randint(1000, 9999))
            while new_id in existing_ids: new_id = str(random.randint(1000, 9999))
            aba.append_table(values=[new_id] + new_data)
        except Exception as e:
            st.error(f"Erro ao adicionar dados: {e}")

    def editar_dados(self, id_registro, updated_data):
        if not self.credentials: return False
        try:
            archive = self.credentials.open_by_url(self.spreadsheet_url)
            aba = archive.worksheet_by_title('acess')
            cell = aba.find(str(id_registro), matchCase=True, in_column=1)
            if cell:
                aba.update_row(cell[0].row, [str(id_registro)] + updated_data)
                return True
            return False
        except Exception as e:
            st.error(f"Erro ao editar dados: {e}")
            return False

    def excluir_dados(self, id_registro):
        if not self.credentials: return False
        try:
            archive = self.credentials.open_by_url(self.spreadsheet_url)
            aba = archive.worksheet_by_title('acess')
            cell = aba.find(str(id_registro), matchCase=True, in_column=1)
            if cell:
                aba.delete_rows(cell[0].row)
                return True
            return False
        except Exception as e:
            st.error(f"Erro ao excluir dados: {e}")
            return False

# --- FUNÇÕES PÚBLICAS ---

_sheet_ops = SheetOperations()

def load_data_from_sheets():
    data = _sheet_ops.carregar_dados_aba('acess')
    if data:
        st.session_state.df_acesso_veiculos = pd.DataFrame(data[1:], columns=data[0]).fillna("")
    else:
        st.session_state.df_acesso_veiculos = pd.DataFrame()

def get_aprovadores():
    return _sheet_ops.carregar_dados_aprovadores()

def add_record(name, cpf, placa, marca_carro, horario_entrada, data, empresa, status, motivo, aprovador):
    first_reg_date = data if status == "Autorizado" else ""
    new_data = [name, cpf, placa, marca_carro, horario_entrada, "", data, empresa, status, motivo, aprovador, first_reg_date]
    _sheet_ops.adc_dados(new_data)
    return True

# --- FUNÇÃO DE SAÍDA (PERNOITE) CORRIGIDA ---
def update_exit_time(name, exit_date_str, exit_time_str):
    try:
        all_data = _sheet_ops.carregar_dados_aba('acess')
        if not all_data: return False, "Planilha vazia."

        header = all_data[0]
        df = pd.DataFrame(all_data[1:], columns=header)
        
        # Encontra o último registro em aberto da pessoa
        open_records = df[(df["Nome"] == name) & ((df["Horário de Saída"] == "") | pd.isna(df["Horário de Saída"]))]
        if open_records.empty: return False, "Nenhum registro em aberto encontrado para esta pessoa."
        
        # Garante que estamos pegando o mais recente
        open_records['Data_dt'] = pd.to_datetime(open_records['Data'], format='%d/%m/%Y', errors='coerce')
        record_to_update = open_records.sort_values(by='Data_dt', ascending=False).iloc[0]

        record_id = record_to_update["ID"]
        entry_date = datetime.strptime(record_to_update["Data"], "%d/%m/%Y")
        exit_date = datetime.strptime(exit_date_str, "%d/%m/%Y")

        # Cenário 1: Saída no mesmo dia da entrada
        if entry_date.date() == exit_date.date():
            original_row = next((row for row in all_data if row[0] == record_id), None)
            if not original_row: return False, "Registro original não encontrado."
            
            updated_data = original_row[1:]
            exit_time_index = header.index("Horário de Saída") - 1
            updated_data[exit_time_index] = exit_time_str
            
            if _sheet_ops.editar_dados(record_id, updated_data):
                return True, "Saída registrada com sucesso."
            else:
                return False, "Falha ao editar o registro."

        # Cenário 2: Pernoite
        else:
            # 1. Fecha o registro do dia da entrada às 23:59
            original_row = next((row for row in all_data if row[0] == record_id), None)
            if not original_row: return False, "Registro original não encontrado."
            
            updated_data = original_row[1:]
            exit_time_index = header.index("Horário de Saída") - 1
            updated_data[exit_time_index] = "23:59"
            _sheet_ops.editar_dados(record_id, updated_data)

            # 2. Cria registros para os dias intermediários (se houver)
            current_date = entry_date + timedelta(days=1)
            while current_date.date() < exit_date.date():
                new_data = [
                    record_to_update["Nome"], record_to_update["CPF"], record_to_update["Placa"],
                    record_to_update["Marca do Carro"], "00:00", "23:59", current_date.strftime("%d/%m/%Y"),
                    record_to_update["Empresa"], "Autorizado", "Pernoite", record_to_update.get("Aprovador", "")
                ]
                # Remove o primeiro campo do cabeçalho (ID) para alinhar
                data_to_add = {h: v for h, v in zip(header[1:], new_data)}
                _sheet_ops.adc_dados(list(data_to_add.values()))
                current_date += timedelta(days=1)

            # 3. Cria o registro final para o dia da saída
            final_data = [
                record_to_update["Nome"], record_to_update["CPF"], record_to_update["Placa"],
                record_to_update["Marca do Carro"], "00:00", exit_time_str, exit_date_str,
                record_to_update["Empresa"], "Autorizado", "Pernoite", record_to_update.get("Aprovador", "")
            ]
            final_data_to_add = {h: v for h, v in zip(header[1:], final_data)}
            _sheet_ops.adc_dados(list(final_data_to_add.values()))
            
            return True, "Saída com pernoite registrada com sucesso."

    except Exception as e:
        return False, f"Erro inesperado ao registrar saída: {e}"


def delete_record(name, data_str):
    all_data = _sheet_ops.carregar_dados_aba('acess')
    if not all_data: return False
    df = pd.DataFrame(all_data[1:], columns=all_data[0])
    records_to_delete = df[(df["Nome"] == name) & (df["Data"] == data_str)]
    if records_to_delete.empty: return False
    record_id = records_to_delete.iloc[0]['ID']
    return _sheet_ops.excluir_dados(record_id)

def check_blocked_records(df):
    if df.empty: return None
    df_copy = df.copy()
    df_copy['Data_dt'] = pd.to_datetime(df_copy['Data'], format='%d/%m/%Y', errors='coerce')
    df_sorted = df_copy.dropna(subset=['Data_dt']).sort_values(by=['Data_dt', 'Horário de Entrada'], ascending=False)
    latest_status = df_sorted.drop_duplicates(subset='Nome', keep='first')
    blocked = latest_status[latest_status["Status da Entrada"] == "Bloqueado"]
    if blocked.empty: return None
    info = "\n".join([f"- **{row['Nome']}**: {row['Motivo do Bloqueio']} (em {row['Data']})" for _, row in blocked.iterrows()])
    return info