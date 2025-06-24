# app/data_operations.py

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from app.operations import SheetOperations
from app.utils import validate_cpf, round_to_nearest_interval

def generate_time_options():
    times = []
    start_time = datetime.strptime("00:00", "%H:%M")
    end_time = datetime.strptime("23:59", "%H:%M")

    current_time = start_time
    while current_time <= end_time:
        times.append(current_time.strftime("%H:%M"))
        current_time += timedelta(minutes=1)
    
    return times

def format_cpf(cpf):
    """Formata o CPF no padrão XXX.XXX.XXX-XX"""
    cpf = ''.join(filter(str.isdigit, str(cpf)))
    if len(cpf) != 11:
        return cpf
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

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
            ((df["Horário de Saída"].isna()) | (df["Horário de Saída"] == ""))
        ]
        
        if person_records_open.empty:
            return False, "Nenhum registro em aberto encontrado para esta pessoa."

        person_records_open['Data_dt'] = pd.to_datetime(person_records_open['Data'], format='%d/%m/%Y', errors='coerce')
        person_records_open.dropna(subset=['Data_dt'], inplace=True)
        record_to_update = person_records_open.sort_values(by='Data_dt', ascending=False).iloc[0]
        
        record_id = record_to_update.get("ID")
        if not record_id:
            return False, "Não foi possível identificar o ID do registro para atualização."
        
        # Correção para lidar com horários de entrada vazios
        entry_time_str = record_to_update.get("Horário de Entrada", "")
        if not entry_time_str or pd.isna(entry_time_str):
            entry_time = datetime.strptime("00:00", "%H:%M").time()
        else:
            entry_time = datetime.strptime(str(entry_time_str), "%H:%M").time()
        
        entry_date = datetime.strptime(record_to_update["Data"], "%d/%m/%Y")
        exit_date_obj = datetime.strptime(exit_date, "%d/%m/%Y")
        exit_time_obj = datetime.strptime(exit_time, "%H:%M").time()
        
        if entry_date.date() == exit_date_obj.date():
            # Encontra a linha original para preservar a ordem das colunas
            original_row = None
            for row in all_data[1:]:
                if str(row[0]) == str(record_id):
                    original_row = row
                    break
            
            if original_row is None:
                return False, "Registro original não encontrado para atualização."

            header = all_data[0]
            try:
                exit_time_index = header.index("Horário de Saída")
            except ValueError:
                return False, "Coluna 'Horário de Saída' não encontrada na planilha."

            updated_data = original_row[1:] # Pega todos os dados exceto o ID
            updated_data[exit_time_index - 1] = exit_time # -1 porque removemos o ID do slice
            
            sheet_operations.editar_dados(record_id, updated_data)
            return True, "Horário de saída atualizado com sucesso."
        
        else:
            # Saída em dia diferente (pernoite)
            # 1. Fechar o registro do dia da entrada às 23:59
            original_row = None
            for row in all_data[1:]:
                if str(row[0]) == str(record_id):
                    original_row = row
                    break
            
            header = all_data[0]
            exit_time_index = header.index("Horário de Saída")
            updated_data = original_row[1:]
            updated_data[exit_time_index - 1] = "23:59"
            sheet_operations.editar_dados(record_id, updated_data)
            
            # 2. Criar registros para os dias intermediários (se houver)
            current_date = entry_date + timedelta(days=1)
            while current_date.date() < exit_date_obj.date():
                new_data = list(record_to_update.values)
                new_data[header.index("Horário de Entrada")] = "00:00"
                new_data[header.index("Horário de Saída")] = "23:59"
                new_data[header.index("Data")] = current_date.strftime("%d/%m/%Y")
                sheet_operations.adc_dados(new_data[1:]) # Adiciona sem o ID
                current_date += timedelta(days=1)
            
            # 3. Criar registro final com a saída no horário informado
            final_data = list(record_to_update.values)
            final_data[header.index("Horário de Entrada")] = "00:00"
            final_data[header.index("Horário de Saída")] = exit_time
            final_data[header.index("Data")] = exit_date
            sheet_operations.adc_dados(final_data[1:])
            
            return True, "Registros de pernoite atualizados com sucesso."
            
    except Exception as e:
        st.error(f"Erro detalhado em update_exit_time: {str(e)}")
        return False, f"Erro ao atualizar horário de saída: {str(e)}"

def add_record(name, cpf, placa, marca_carro, horario_entrada, data, empresa, status, motivo, aprovador):
    """Adiciona um novo registro de acesso."""
    try:
        sheet_operations = SheetOperations()
        new_data = [
            name, cpf, placa, marca_carro, horario_entrada, "", data, empresa, 
            status, motivo, aprovador, data if status == "Autorizado" else ""
        ]
        sheet_operations.adc_dados(new_data)
        st.success("Registro adicionado com sucesso!")
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar registro: {str(e)}")
        return False

def delete_record(name, data):
    """Deleta um registro de acesso com base no nome e na data."""
    try:
        sheet_operations = SheetOperations()
        all_data = sheet_operations.carregar_dados()
        df = pd.DataFrame(all_data[1:], columns=all_data[0])
        
        records_to_delete = df[(df["Nome"] == name) & (df["Data"] == data)]
        
        if records_to_delete.empty:
            st.warning(f"Nenhum registro encontrado para {name} na data {data}.")
            return False
        
        record_id = records_to_delete.iloc[0]['ID']
        return sheet_operations.excluir_dados(record_id)
        
    except Exception as e:
        st.error(f"Erro ao deletar registro: {str(e)}")
        return False

def check_entry(name, data):
    """Verifica um registro de entrada."""
    try:
        sheet_operations = SheetOperations()
        df = pd.DataFrame(sheet_operations.carregar_dados()[1:], columns=sheet_operations.carregar_dados()[0])
        
        if data:
            record = df[(df["Nome"] == name) & (df["Data"] == data)]
        else:
            record = df[df["Nome"] == name]
            
        if record.empty:
            return None, "Registro não encontrado."
            
        return record.iloc[0], "Registro encontrado."
        
    except Exception as e:
        return None, f"Erro ao verificar registro: {str(e)}"

def check_blocked_records(df):
    """Verifica se o último registro de cada pessoa é 'Bloqueado'."""
    try:
        if df.empty or 'Data' not in df.columns or 'Horário de Entrada' not in df.columns:
            return None

        df_copy = df.copy()
        df_copy['Data_dt'] = pd.to_datetime(df_copy['Data'], format='%d/%m/%Y', errors='coerce')
        df_sorted = df_copy.dropna(subset=['Data_dt']).sort_values(by=['Data_dt', 'Horário de Entrada'], ascending=False)
        
        latest_status_df = df_sorted.drop_duplicates(subset='Nome', keep='first')
        
        blocked_df = latest_status_df[latest_status_df["Status da Entrada"] == "Bloqueado"]
        
        if blocked_df.empty:
            return None
        
        info = ""
        for _, row in blocked_df.iterrows():
            info += f"- **{row['Nome']}**: {row['Motivo do Bloqueio']} (em {row['Data']})\n"
            
        return info
        
    except Exception as e:
        # Não mostra o erro na tela principal para não poluir
        print(f"Erro ao verificar registros bloqueados: {str(e)}")
        return None

def get_block_info(name):
    """Obtém informações de bloqueio de uma pessoa."""
    try:
        sheet_operations = SheetOperations()
        df = pd.DataFrame(sheet_operations.carregar_dados()[1:], columns=sheet_operations.carregar_dados()[0])
        
        blocked = df[(df["Nome"] == name) & (df["Status da Entrada"] == "Bloqueado")]
        if blocked.empty:
            return None
            
        latest = blocked.iloc[0]
        return {
            "motivo": latest["Motivo do Bloqueio"],
            "data": latest["Data"],
            "aprovador": latest["Aprovador"]
        }
    except Exception as e:
        return None

def load_data_from_sheets():
    # Esta função agora é chamada diretamente na interface para popular o session_state
    # Mantida aqui caso seja necessária em outros módulos no futuro.
    try:
        sheet_operations = SheetOperations()
        data = sheet_operations.carregar_dados()
        if data:
            columns = data[0]
            df = pd.DataFrame(data[1:], columns=columns)
            st.session_state.df_acesso_veiculos = df
        else:
            st.session_state.df_acesso_veiculos = pd.DataFrame(columns=[
                "ID", "Nome", "CPF", "Placa", "Marca do Carro", "Horário de Entrada", "Horário de Saída", 
                "Data", "Empresa", "Status da Entrada", "Motivo do Bloqueio", "Aprovador", "Data do Primeiro Registro"
            ])
    except Exception as e:
        st.error(f"Falha ao carregar dados das planilhas: {e}")






























