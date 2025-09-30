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
        
        if not all_data or len(all_data) < 2:
            return False, "Não foi possível carregar os dados da planilha."
        
        df = pd.DataFrame(all_data[1:], columns=all_data[0])
        
        # Encontra os registros em aberto (sem horário de saída) para a pessoa especificada
        open_records = df[
            (df["Nome"] == name) & 
            ((df["Horário de Saída"] == "") | pd.isna(df["Horário de Saída"]))
        ]
        
        if open_records.empty:
            return False, "Nenhum registro em aberto encontrado para esta pessoa."

        record_to_update = open_records.iloc[0]
        record_id = record_to_update["ID"]
        
        # Converte as datas
        try:
            entry_date = datetime.strptime(record_to_update["Data"], "%d/%m/%Y")
            exit_date = datetime.strptime(exit_date_str, "%d/%m/%Y")
        except ValueError as e:
            return False, f"Erro ao processar datas: {e}"

        # Caso 1: Saída no mesmo dia da entrada
        if entry_date.date() == exit_date.date():
            original_row = next((row for row in all_data if str(row[0]) == str(record_id)), None)
            if original_row is None: 
                return False, "Registro original não encontrado para edição."
            
            header = all_data[0]
            
            try:
                exit_time_index = header.index("Horário de Saída")
            except ValueError:
                return False, "Coluna 'Horário de Saída' não encontrada na planilha."
            
            updated_data = original_row[1:]  # Pega os dados sem o ID
            updated_data[exit_time_index - 1] = exit_time_str 
            
            if sheet_operations.editar_dados(record_id, updated_data):
                return True, "Horário de saída atualizado com sucesso."
            return False, "Falha ao editar o registro na planilha."
        
        # Caso 2: Pernoite (saída em dia diferente)
        else:
            # Atualiza o primeiro registro para fechar às 23:59
            original_row = next((row for row in all_data if str(row[0]) == str(record_id)), None)
            if original_row is None:
                return False, "Registro original não encontrado."
            
            header = all_data[0]
            
            try:
                exit_time_index = header.index("Horário de Saída")
            except ValueError:
                return False, "Coluna 'Horário de Saída' não encontrada na planilha."
            
            updated_data = original_row[1:]
            updated_data[exit_time_index - 1] = "23:59"
            
            if not sheet_operations.editar_dados(record_id, updated_data):
                return False, "Falha ao atualizar registro de entrada."

            # Cria registros intermediários (00:00 - 23:59)
            current_date = entry_date + timedelta(days=1)
            while current_date.date() < exit_date.date():
                intermediate_data = [
                    name, 
                    record_to_update.get("CPF", ""), 
                    "", 
                    "", 
                    "00:00", 
                    "23:59", 
                    current_date.strftime("%d/%m/%Y"), 
                    record_to_update.get("Empresa", ""), 
                    "Autorizado", 
                    "", 
                    record_to_update.get("Aprovador", ""), 
                    ""
                ]
                
                if not sheet_operations.adc_dados_aba(intermediate_data, 'acess'):
                    return False, f"Falha ao criar registro intermediário para {current_date.strftime('%d/%m/%Y')}."
                
                current_date += timedelta(days=1)

            # Cria registro final com horário de saída real
            final_data = [
                name, 
                record_to_update.get("CPF", ""), 
                "", 
                "", 
                "00:00", 
                exit_time_str, 
                exit_date_str, 
                record_to_update.get("Empresa", ""), 
                "Autorizado", 
                "", 
                record_to_update.get("Aprovador", ""), 
                ""
            ]
            
            if not sheet_operations.adc_dados_aba(final_data, 'acess'):
                return False, "Falha ao criar registro de saída final."
            
            return True, "Registros de pernoite criados com sucesso."
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Erro detalhado em update_exit_time: {error_details}")
        return False, f"Erro ao atualizar horário de saída: {str(e)}"


def update_record_status(record_id, new_status, approver_name):
    """
    Função administrativa para atualizar o status e o aprovador de um registro.
    """
    try:
        sheet_operations = SheetOperations()
        all_data = sheet_operations.carregar_dados()
        
        if not all_data or len(all_data) < 2:
            st.error("Não foi possível carregar dados para atualização.")
            return False

        header = all_data[0]
        df = pd.DataFrame(all_data[1:], columns=header)
        
        record_to_update = df[df['ID'] == str(record_id)]
        if record_to_update.empty:
            st.error(f"Registro com ID {record_id} não encontrado para atualização.")
            return False

        original_row_list = next((row for row in all_data if str(row[0]) == str(record_id)), None)
        if original_row_list is None:
            return False # Segurança extra
        
        updated_data = original_row_list[1:]

        status_index = header.index("Status da Entrada")
        approver_index = header.index("Aprovador")
        
        # Atualiza o status e o aprovador
        updated_data[status_index - 1] = new_status
        updated_data[approver_index - 1] = approver_name

        if new_status == "Autorizado":
            cpf_index = header.index("CPF")
            current_cpf = record_to_update.iloc[0].get('CPF', '')
            
            if not current_cpf or str(current_cpf).strip() == '':
                person_name = record_to_update.iloc[0]['Nome']
                
                previous_records_with_cpf = df[
                    (df['Nome'] == person_name) & 
                    (df['CPF'].notna()) & 
                    (df['CPF'] != '')
                ]
                
                if not previous_records_with_cpf.empty:
                    last_valid_cpf = previous_records_with_cpf.iloc[0]['CPF']
                    updated_data[cpf_index - 1] = last_valid_cpf
                    log_action("ENRICH_DATA", f"CPF '{last_valid_cpf}' adicionado ao registro {record_id} para '{person_name}' durante a aprovação.")

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

def editar_dados_aba(self, row_id, updated_data, aba_name):
    """Edita uma linha em uma aba específica com base no ID."""
    if not self.credentials or not self.my_archive_google_sheets:
        return False
    try:
        archive = self.credentials.open_by_url(self.my_archive_google_sheets)
        aba = archive.worksheet_by_title(aba_name)
        
        all_values = aba.get_all_values()
        row_to_update_index = -1
        
        # Itera sobre as linhas para encontrar o ID
        for i, row in enumerate(all_values):
            # Compara o valor da primeira coluna (ID)
            if row and str(row[0]) == str(row_id):
                row_to_update_index = i + 1
                break
        
        if row_to_update_index != -1:
            updated_row = [str(row_id)] + updated_data
            aba.update_row(row_to_update_index, updated_row)
            logging.info(f"Dados do ID {row_id} editados com sucesso na aba '{aba_name}'.")
            return True
        else:
            logging.error(f"ID {row_id} não encontrado na aba '{aba_name}' para edição.")
            return False
            
    except Exception as e:
        logging.error(f"Erro ao editar dados na aba '{aba_name}': {e}", exc_info=True)
        st.error(f"Erro crítico ao tentar editar dados: {e}")
        return False

def editar_dados(self, id, updated_data):
    """Função de conveniência para editar dados na aba 'acess'."""
    return self.editar_dados_aba(id, updated_data, 'acess')
    
def remove_from_blocklist(block_ids):
    """Remove uma ou mais entradas da blocklist pelo ID."""
    try:
        sheet_ops = SheetOperations()
        blocklist_df = get_blocklist()
        if blocklist_df.empty: return True

        for block_id in block_ids:
            value_to_log = "ID Desconhecido"
            if not blocklist_df[blocklist_df['ID'] == str(block_id)].empty:
                 value_to_log = blocklist_df[blocklist_df['ID'] == str(block_id)]['Value'].iloc[0]

            if not sheet_ops.excluir_dados_por_id_aba(block_id, 'blocklist'):
                st.error(f"Falha ao remover o bloqueio para '{value_to_log}' (ID: {block_id}). A operação foi interrompida.")
                return False
            else:
                log_action("REMOVE_FROM_BLOCKLIST", f"Liberado: '{value_to_log}' (ID do bloqueio: {block_id})")
        
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


@st.cache_data(ttl=60)
def get_users():
    """Carrega e retorna a lista de usuários como um DataFrame."""
    try:
        sheet_ops = SheetOperations()
        users_data = sheet_ops.carregar_dados_aba('users')
        if users_data and len(users_data) > 1:
            return pd.DataFrame(users_data[1:], columns=users_data[0])
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar a lista de usuários: {e}")
        return pd.DataFrame()

def add_user(user_name, role):
    """Adiciona um novo usuário à planilha 'users'."""
    try:
        sheet_ops = SheetOperations()
     
        new_user_data = [user_name, role]
        if sheet_ops.adc_dados_aba(new_user_data, 'users'):
            log_action("ADD_USER", f"Adicionou usuário '{user_name}' com o papel '{role}'.")
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao adicionar usuário: {e}")
        return False

def remove_user(user_name):
    """Remove um usuário da planilha 'users' pelo nome."""
    try:
        sheet_ops = SheetOperations()
        if sheet_ops.excluir_linha_por_valor(user_name, 'user_name', 'users'):
            log_action("REMOVE_USER", f"Removeu o usuário '{user_name}'.")
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao remover usuário: {e}")
        return False

def update_schedule_status(schedule_id, new_status, checkin_time):
    """Atualiza o status e a hora de check-in de um agendamento."""
    try:
        sheet_ops = SheetOperations()
        
        all_schedules = sheet_ops.carregar_dados_aba('schedules')
        if not all_schedules: return False
        
        header = all_schedules[0]
        original_row_list = next((row for row in all_schedules if str(row[0]) == str(schedule_id)), None)
        if not original_row_list: return False
        
        updated_data = original_row_list[1:] # Dados sem ID
        
        status_idx = header.index('Status')
        checkin_idx = header.index('CheckInTime')
        
        updated_data[status_idx - 1] = new_status
        updated_data[checkin_idx - 1] = checkin_time
        
        return sheet_ops.editar_dados_aba(schedule_id, updated_data, 'schedules')
    except Exception as e:
        st.error(f"Erro ao atualizar status do agendamento: {e}")
        return False

def check_briefing_needed(person_name, df):
    """
    Verifica se o briefing de segurança precisa ser repassado.
    Retorna True se a pessoa não tem registro ou o último acesso foi há mais de 1 ano.
    """
    try:
        if df.empty:
            return True, "Primeira visita"
        
        person_records = df[df["Nome"] == person_name].copy()
        if person_records.empty:
            return True, "Primeira visita"
        
        # Procura pela data do primeiro registro
        first_reg_date = person_records.iloc[0].get("Data do Primeiro Registro", "")
        
        if not first_reg_date or pd.isna(first_reg_date) or str(first_reg_date).strip() == "":
            # Se não tem data do primeiro registro, usa a data mais antiga
            person_records['Data_dt'] = pd.to_datetime(person_records['Data'], format='%d/%m/%Y', errors='coerce')
            person_records = person_records.dropna(subset=['Data_dt']).sort_values('Data_dt')
            
            if person_records.empty:
                return True, "Sem histórico válido"
            
            first_date = person_records.iloc[0]['Data_dt']
        else:
            first_date = pd.to_datetime(first_reg_date, format='%d/%m/%Y', errors='coerce')
        
        if pd.isna(first_date):
            return True, "Data inválida no histórico"
        
        now = get_sao_paulo_time()
        days_since_first = (now - first_date).days
        
        if days_since_first > 365:
            return True, f"Último acesso há {days_since_first} dias (mais de 1 ano)"
        
        return False, f"Último acesso há {days_since_first} dias"
        
    except Exception as e:
        print(f"Erro em check_briefing_needed: {e}")
        return False, "Erro ao verificar briefing"




























