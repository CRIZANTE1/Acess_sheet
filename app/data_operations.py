# app/data_operations.py

import streamlit as st
import pandas as pd
import logging
import random
import os
import json
import pygsheets
from datetime import datetime

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
                # Fallback local
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
            return [[row[i] for i in valid_indices] for row in all_values]
        except Exception as e:
            st.error(f"Erro ao carregar dados da aba '{aba_name}': {e}")
            return None

    def carregar_dados_aprovadores(self):
        dados = self.carregar_dados_aba('authorizer')
        return [row[0] for row in dados[1:]] if dados and len(dados) > 1 else []

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


# Instancia a classe internamente
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

def update_exit_time(name, exit_date_str, exit_time_str):
    all_data = _sheet_ops.carregar_dados_aba('acess')
    df = pd.DataFrame(all_data[1:], columns=all_data[0])
    open_records = df[(df["Nome"] == name) & ((df["Horário de Saída"] == "") | pd.isna(df["Horário de Saída"]))]
    if open_records.empty: return False, "Nenhum registro em aberto."
    
    record_to_update = open_records.iloc[0]
    record_id = record_to_update["ID"]
    
    header = all_data[0]
    original_row = next((row for row in all_data if row[0] == record_id), None)
    if not original_row: return False, "Registro original não encontrado."
    
    updated_data = original_row[1:]
    exit_time_index = header.index("Horário de Saída") - 1
    updated_data[exit_time_index] = exit_time_str
    
    if _sheet_ops.editar_dados(record_id, updated_data):
        return True, "Saída registrada com sucesso."
    return False, "Falha ao registrar saída."

def delete_record(name, data_str):
    all_data = _sheet_ops.carregar_dados_aba('acess')
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








