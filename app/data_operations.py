import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from app.operations import SheetOperations
from app.utils import validate_cpf, format_cpf

def update_exit_time(name, exit_date_str, exit_time_str):
    """Atualiza o horário de saída de um registro."""
    try:
        sheet_operations = SheetOperations()
        all_data = sheet_operations.carregar_dados()
        df = pd.DataFrame(all_data[1:], columns=all_data[0])
        
        open_records = df[(df["Nome"] == name) & (df["Horário de Saída"] == "")]
        if open_records.empty:
            return False, "Nenhum registro em aberto encontrado."

        record_to_update = open_records.iloc[0]
        record_id = record_to_update["ID"]
        
        original_row = [row for row in all_data if row[0] == record_id][0]
        header = all_data[0]
        exit_time_index = header.index("Horário de Saída")
        
        updated_data = original_row[1:]
        updated_data[exit_time_index - 1] = exit_time_str
        
        if sheet_operations.editar_dados(record_id, updated_data):
            return True, "Horário de saída atualizado com sucesso."
        else:
            return False, "Falha ao editar os dados na planilha."
    except Exception as e:
        return False, f"Erro ao atualizar horário: {e}"

def add_record(name, cpf, placa, marca_carro, horario_entrada, data, empresa, status, motivo, aprovador):
    """Adiciona um novo registro de acesso."""
    try:
        sheet_operations = SheetOperations()
        # Garante que a data do primeiro registro seja enviada corretamente
        first_reg_date = data if status == "Autorizado" else ""
        new_data = [name, cpf, placa, marca_carro, horario_entrada, "", data, empresa, status, motivo, aprovador, first_reg_date]
        sheet_operations.adc_dados(new_data)
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar registro: {e}")
        return False

def delete_record(name, data_str):
    """Deleta um registro de acesso com base no nome e na data."""
    try:
        sheet_operations = SheetOperations()
        all_data = sheet_operations.carregar_dados()
        df = pd.DataFrame(all_data[1:], columns=all_data[0])
        records_to_delete = df[(df["Nome"] == name) & (df["Data"] == data_str)]
        if records_to_delete.empty: return False
        
        record_id = records_to_delete.iloc[0]['ID']
        return sheet_operations.excluir_dados(record_id)
    except Exception:
        return False

def check_blocked_records(df):
    """Verifica se o último registro de cada pessoa é 'Bloqueado'."""
    try:
        if df.empty: return None
        df_copy = df.copy()
        df_copy['Data_dt'] = pd.to_datetime(df_copy['Data'], format='%d/%m/%Y', errors='coerce')
        df_sorted = df_copy.dropna(subset=['Data_dt']).sort_values(by=['Data_dt', 'Horário de Entrada'], ascending=False)
        latest_status_df = df_sorted.drop_duplicates(subset='Nome', keep='first')
        blocked_df = latest_status_df[latest_status_df["Status da Entrada"] == "Bloqueado"]
        if blocked_df.empty: return None
        info = ""
        for _, row in blocked_df.iterrows():
            info += f"- **{row['Nome']}**: {row['Motivo do Bloqueio']} (em {row['Data']})\n"
        return info
    except Exception:
        return None

def check_entry(name, data, df):
    record = None
    if data:
        record_df = df[(df["Nome"] == name) & (df["Data"] == data)]
    else:
        record_df = df[df["Nome"] == name]
    if not record_df.empty:
        record = record_df.iloc[0]
        return record, "Registro encontrado."
    return None, "Registro não encontrado."

def get_block_info(name, df):
    blocked_df = df[(df["Nome"] == name) & (df["Status da Entrada"] == "Bloqueado")]
    if not blocked_df.empty:
        latest = blocked_df.iloc[0]
        return {"motivo": latest["Motivo do Bloqueio"], "data": latest["Data"], "aprovador": latest["Aprovador"]}
    return None

# --- FUNÇÃO RESTAURADA ---
def load_data_from_sheets():
    """Carrega os dados da planilha e armazena no estado da sessão."""
    try:
        sheet_operations = SheetOperations()
        data = sheet_operations.carregar_dados()
        if data:
            columns = data[0]
            df = pd.DataFrame(data[1:], columns=columns)
            st.session_state.df_acesso_veiculos = df.fillna("")
        else:
            st.session_state.df_acesso_veiculos = pd.DataFrame()
    except Exception as e:
        st.error(f"Falha ao carregar dados iniciais: {e}")
        st.session_state.df_acesso_veiculos = pd.DataFrame()










