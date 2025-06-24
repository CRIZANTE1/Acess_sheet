import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from app.operations import SheetOperations

def update_exit_time(name, exit_date, exit_time):
    """
    Atualiza o horário de saída de um registro, lidando corretamente com registros que atravessam a meia-noite
    e com horários de entrada vazios.
    """
    try:
        sheet_operations = SheetOperations()
        all_data = sheet_operations.carregar_dados()
        if not all_data or len(all_data) < 2:
            return False, "Nenhum dado encontrado na planilha."
        
        df = pd.DataFrame(all_data[1:], columns=all_data[0])
        
        person_records_open = df[
            (df["Nome"] == name) &
            ((df["Horário de Saída"].isna()) | (df["Horário de Saída"] == "") | (df["Horário de Saída"].str.strip() == ""))
        ]
        
        if person_records_open.empty:
            return False, "Nenhum registro em aberto encontrado para esta pessoa."

        person_records_open['Data_dt'] = pd.to_datetime(person_records_open['Data'], format='%d/%m/%Y', errors='coerce')
        person_records_open.dropna(subset=['Data_dt'], inplace=True)
        record_to_update = person_records_open.sort_values(by='Data_dt', ascending=False).iloc[0]
        
        record_id = record_to_update.get("ID")
        if not record_id:
            return False, "Não foi possível identificar o ID do registro para atualização."
        
        entry_time_str = record_to_update.get("Horário de Entrada", "00:00")
        if not entry_time_str or pd.isna(entry_time_str): entry_time_str = "00:00"
        
        entry_time = datetime.strptime(str(entry_time_str), "%H:%M").time()
        entry_date = datetime.strptime(record_to_update["Data"], "%d/%m/%Y")
        exit_date_obj = datetime.strptime(exit_date, "%d/%m/%Y")
        
        # Encontra a linha original para preservar a ordem das colunas
        original_row = None
        header = all_data[0]
        for row in all_data[1:]:
            if str(row[0]) == str(record_id):
                original_row = row
                break
        
        if original_row is None: return False, "Registro original não encontrado."
        
        exit_time_index = header.index("Horário de Saída")
        updated_data = original_row[1:]
        updated_data[exit_time_index - 1] = exit_time
        
        sheet_operations.editar_dados(record_id, updated_data)
        return True, "Horário de saída atualizado com sucesso."
            
    except Exception as e:
        return False, f"Erro ao atualizar horário de saída: {str(e)}"

def add_record(name, cpf, placa, marca_carro, horario_entrada, data, empresa, status, motivo, aprovador):
    """Adiciona um novo registro de acesso."""
    try:
        sheet_operations = SheetOperations()
        # Garante que a data do primeiro registro seja enviada corretamente
        first_reg_date = data if status == "Autorizado" else ""
        new_data = [
            name, cpf, placa, marca_carro, horario_entrada, "", data, empresa, 
            status, motivo, aprovador, first_reg_date
        ]
        sheet_operations.adc_dados(new_data)
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar registro: {str(e)}")
        return False

def delete_record(name, data_str):
    """Deleta um registro de acesso com base no nome e na data."""
    try:
        sheet_operations = SheetOperations()
        all_data = sheet_operations.carregar_dados()
        df = pd.DataFrame(all_data[1:], columns=all_data[0])
        
        # Filtra para encontrar o registro exato
        records_to_delete = df[(df["Nome"] == name) & (df["Data"] == data_str)]
        
        if records_to_delete.empty:
            return False
        
        # Pega o ID do primeiro registro encontrado (pode haver múltiplos no mesmo dia)
        record_id = records_to_delete.iloc[0]['ID']
        return sheet_operations.excluir_dados(record_id)
    except Exception:
        return False

def check_blocked_records(df):
    """Verifica se o último registro de cada pessoa é 'Bloqueado'."""
    try:
        if df.empty or 'Data' not in df.columns or 'Nome' not in df.columns:
            return None

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





















