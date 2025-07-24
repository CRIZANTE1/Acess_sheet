import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from app.operations import SheetOperations
from app.logger import log_action
from app.utils import get_sao_paulo_time


def load_data_from_sheets():
    """Carrega os dados da planilha e armazena no estado da sessão."""
    try:
        sheet_operations = SheetOperations()
        data = sheet_operations.carregar_dados()
        if data:
            st.session_state.df_acesso_veiculos = pd.DataFrame(data[1:], columns=data[0]).fillna("")
        else:
            st.session_state.df_acesso_veiculos = pd.DataFrame()
    except Exception as e:
        st.error(f"Falha ao carregar dados iniciais da planilha: {e}")
        st.session_state.df_acesso_veiculos = pd.DataFrame()

def add_record(name, cpf, placa, marca_carro, horario_entrada, data, empresa, status, motivo, aprovador, first_reg_date=""):
    """Adiciona um novo registro de acesso na planilha."""
    try:
        sheet_operations = SheetOperations()
        new_data = [name, cpf, placa, marca_carro, horario_entrada, "", data, empresa, status, motivo, aprovador, first_reg_date]
        # A função adc_dados já exibe a mensagem de sucesso/erro
        sheet_operations.adc_dados(new_data)
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar registro: {e}")
        return False

def update_exit_time(name, exit_date_str, exit_time_str):
    """
    Atualiza o horário de saída de um registro em aberto.
    Implementa a lógica de pernoite, criando novos registros para cada dia.
    """
    try:
        sheet_operations = SheetOperations()
        all_data = sheet_operations.carregar_dados()
        df = pd.DataFrame(all_data[1:], columns=all_data[0])
        
        # Encontra os registros em aberto (sem horário de saída) para a pessoa especificada
        open_records = df[(df["Nome"] == name) & ((df["Horário de Saída"] == "") | pd.isna(df["Horário de Saída"]))]
        if open_records.empty:
            return False, "Nenhum registro em aberto encontrado para esta pessoa."

        record_to_update = open_records.iloc[0]
        record_id = record_to_update["ID"]
        entry_date = datetime.strptime(record_to_update["Data"], "%d/%m/%Y")
        exit_date = datetime.strptime(exit_date_str, "%d/%m/%Y")

        # Caso 1: A saída ocorre no mesmo dia da entrada
        if entry_date.date() == exit_date.date():
            original_row = next((row for row in all_data if str(row[0]) == str(record_id)), None)
            if original_row is None: return False, "Registro original não encontrado para edição."
            
            header = all_data[0]
            exit_time_index = header.index("Horário de Saída")
            
            updated_data = original_row[1:] # Pega os dados sem o ID
            updated_data[exit_time_index - 1] = exit_time_str # -1 porque updated_data não tem ID
            
            if sheet_operations.editar_dados(record_id, updated_data):
                return True, "Horário de saída atualizado com sucesso."
            return False, "Falha ao editar o registro na planilha."
        
        else:
            original_row = next((row for row in all_data if str(row[0]) == str(record_id)), None)
            header = all_data[0]
            exit_time_index = header.index("Horário de Saída")
            updated_data = original_row[1:]
            updated_data[exit_time_index - 1] = "23:59"
            sheet_operations.editar_dados(record_id, updated_data)

            # Passo 2: Cria registros para os dias intermediários (se houver)
            current_date = entry_date + timedelta(days=1)
            while current_date.date() < exit_date.date():
                intermediate_data = [name, record_to_update.get("CPF", ""), "", "", "00:00", "23:59", current_date.strftime("%d/%m/%Y"), record_to_update.get("Empresa", ""), "Autorizado", "", record_to_update.get("Aprovador", ""), ""]
                sheet_operations.adc_dados(intermediate_data)
                current_date += timedelta(days=1)

            # Passo 3: Cria o registro final para o dia da saída
            final_data = [name, record_to_update.get("CPF", ""), "", "", "00:00", exit_time_str, exit_date_str, record_to_update.get("Empresa", ""), "Autorizado", "", record_to_update.get("Aprovador", ""), ""]
            sheet_operations.adc_dados(final_data)
            return True, "Registros de pernoite atualizados com sucesso."
            
    except Exception as e:
        return False, f"Erro ao atualizar horário de saída: {e}"

def update_record_status(record_id, new_status, approver_name):
    """Função administrativa para atualizar o status e o aprovador de um registro."""
    try:
        sheet_operations = SheetOperations()
        all_data = sheet_operations.carregar_dados()
        header = all_data[0]
        
        status_index = header.index("Status da Entrada")
        approver_index = header.index("Aprovador")
        
        original_row = next((row for row in all_data if str(row[0]) == str(record_id)), None)
        if original_row is None:
            st.error(f"Registro com ID {record_id} não encontrado.")
            return False

        updated_data = original_row[1:]
        updated_data[status_index - 1] = new_status
        updated_data[approver_index - 1] = approver_name

        if sheet_operations.editar_dados(record_id, updated_data):
            st.success("Status do registro atualizado com sucesso!")
            return True
        else:
            st.error("Falha ao atualizar o status na planilha.")
            return False
            
    except Exception as e:
        st.error(f"Erro ao atualizar o status do registro: {e}")
        return False

def delete_record_by_id(record_id):
    """Função administrativa para deletar um registro com base no seu ID único."""
    try:
        sheet_operations = SheetOperations()
        if sheet_operations.excluir_dados(record_id):
            return True
        else:
            st.error(f"Não foi possível deletar o registro com ID {record_id}.")
            return False
    except Exception as e:
        st.error(f"Erro ao deletar registro por ID: {e}")
        return False

def delete_record(name, data_str):
    """Deleta o registro mais recente de uma pessoa em uma data específica."""
    try:
        sheet_operations = SheetOperations()
        all_data = sheet_operations.carregar_dados()
        df = pd.DataFrame(all_data[1:], columns=all_data[0])
        
        records_to_delete = df[(df["Nome"] == name) & (df["Data"] == data_str)]
        if records_to_delete.empty: 
            return False
        
        record_id = records_to_delete.iloc[0]['ID']
        return sheet_operations.excluir_dados(record_id)
    except Exception as e:
        st.error(f"Erro ao deletar registro por nome e data: {e}")
        return False

def check_blocked_records(df):
    """Verifica os status mais recentes e alerta sobre 'Bloqueado' ou 'Pendente de Aprovação'."""
    try:
        if df.empty: return None
        df_copy = df.copy()
        df_copy['Data_dt'] = pd.to_datetime(df_copy['Data'], format='%d/%m/%Y', errors='coerce')
        df_sorted = df_copy.dropna(subset=['Data_dt']).sort_values(by=['Data_dt', 'Horário de Entrada'], ascending=False)
        
        latest_status_df = df_sorted.drop_duplicates(subset='Nome', keep='first')
        
        attention_statuses = ["Bloqueado", "Pendente de Aprovação", "Pendente de Liberação da Blocklist"]
        attention_df = latest_status_df[latest_status_df["Status da Entrada"].isin(attention_statuses)]
        
        if attention_df.empty: return None
        
        info = ""
        for _, row in attention_df.iterrows():
            status = row['Status da Entrada']
            # <<< ALTERAÇÃO AQUI: FORMATA A MENSAGEM PARA O NOVO STATUS >>>
            if status == "Pendente de Liberação da Blocklist":
                motivo_display = f"AGUARDANDO APROVAÇÃO EXCEPCIONAL (Solicitante: {row.get('Aprovador', 'N/A')})"
            elif status == "Pendente de Aprovação":
                motivo_display = f"Aguardando aprovação do admin (Solicitante: {row.get('Aprovador', 'N/A')})"
            else: # Bloqueado
                motivo_display = f"Motivo: {row.get('Motivo do Bloqueio', 'N/A')}"
            
            info += f"- **{row['Nome']}**: {status} - {motivo_display}\n"
        return info
    except Exception as e:
        print(f"Erro em check_blocked_records: {e}")
        return "Ocorreu um erro ao verificar os status de bloqueio."


@st.cache_data(ttl=60) 
def get_blocklist():
    """Carrega e retorna a blocklist como um DataFrame."""
    try:
        sheet_ops = SheetOperations()
        blocklist_data = sheet_ops.carregar_dados_aba('blocklist')
        if blocklist_data and len(blocklist_data) > 1:
            return pd.DataFrame(blocklist_data[1:], columns=blocklist_data[0])
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar a lista de bloqueios: {e}")
        return pd.DataFrame()

def add_to_blocklist(block_type, values, reason, admin_name):
    """Adiciona uma ou mais entidades à blocklist."""
    try:
        sheet_ops = SheetOperations()
        timestamp = get_sao_paulo_time().strftime('%Y-%m-%d %H:%M:%S')
        for value in values:
            new_entry = [block_type, value, reason, admin_name, timestamp]
            sheet_ops.adc_dados_aba(new_entry, 'blocklist') # Supondo que adc_dados_aba existe
            log_action("ADD_TO_BLOCKLIST", f"Tipo: {block_type}, Valor: '{value}', Motivo: {reason}")
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar à blocklist: {e}")
        return False

def remove_from_blocklist(block_ids):
    """Remove uma ou mais entradas da blocklist pelo ID."""
    try:
        sheet_ops = SheetOperations()
        blocklist_df = get_blocklist()
        if blocklist_df.empty: return True

        for block_id in block_ids:
            value_to_log = blocklist_df[blocklist_df['ID'] == block_id]['Value'].iloc[0]
            if sheet_ops.excluir_dados_por_id_aba(block_id, 'blocklist'):
                 log_action("REMOVE_FROM_BLOCKLIST", f"Liberado: '{value_to_log}' (ID do bloqueio: {block_id})")
            else:
                st.warning(f"Não foi possível remover o bloqueio com ID {block_id}")
        return True
    except Exception as e:
        st.error(f"Erro ao remover da blocklist: {e}")
        return False

def is_entity_blocked(name, company):
    """Verifica se um nome ou empresa está na blocklist."""
    blocklist_df = get_blocklist()
    if blocklist_df.empty:
        return False, None

    person_block = blocklist_df[
        (blocklist_df['Type'] == 'Pessoa') & 
        (blocklist_df['Value'].str.lower() == name.lower())
    ]
    if not person_block.empty:
        return True, person_block.iloc[0]['Reason']

    company_block = blocklist_df[
        (blocklist_df['Type'] == 'Empresa') & 
        (blocklist_df['Value'].str.lower() == company.lower())
    ]
    if not company_block.empty:
        return True, company_block.iloc[0]['Reason']
        
    return False, None

























