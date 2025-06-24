import streamlit as st
import pandas as pd
import pygsheets
import random
from datetime import datetime, timedelta

class SheetOperations:
    def __init__(self):
        self.credentials = None
        self.spreadsheet_url = None
        try:
            # --- AUTENTICAÇÃO FINAL E CORRETA PARA STREAMLIT CLOUD ---
            if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
                # 1. Converte o AttrDict do Streamlit para um dicionário Python padrão
                creds_dict = dict(st.secrets["connections"]["gsheets"])
                
                # 2. Guarda a URL da planilha e a REMOVE da cópia do dicionário
                self.spreadsheet_url = creds_dict.pop("spreadsheet", None)
                if not self.spreadsheet_url:
                    st.error("A chave 'spreadsheet' com a URL não foi encontrada nos seus secrets.")
                    return

                # 3. Passa o dicionário de credenciais "limpo" para o parâmetro correto
                self.credentials = pygsheets.authorize(service_account_info=creds_dict)
            else:
                st.error("Configuração 'connections.gsheets' não encontrada nos Streamlit Secrets.")

        except Exception as e:
            st.error(f"Erro crítico ao conectar com o Google Sheets via Secrets: {e}")

    def carregar_dados_aba(self, aba_name):
        if not self.credentials:
            st.warning("Não foi possível conectar ao Google Sheets.")
            return None
        try:
            archive = self.credentials.open_by_url(self.spreadsheet_url)
            aba = archive.worksheet_by_title(aba_name)
            all_values = aba.get_all_values(include_tailing_empty_rows=False)
            if not all_values: return []
            
            header = all_values[0]
            valid_indices = [i for i, h in enumerate(header) if h and h.strip()]
            valid_header = [header[i] for i in valid_indices]
            
            data = [[row[i] if i < len(row) else '' for i in valid_indices] for row in all_values[1:]]
            
            return [valid_header] + data
        except pygsheets.exceptions.WorksheetNotFound:
             st.error(f"Aba da planilha '{aba_name}' não foi encontrada.")
             return None
        except Exception as e:
            st.error(f"Erro ao carregar dados da aba '{aba_name}': {e}")
            return None

    def carregar_dados_aprovadores(self):
        dados = self.carregar_dados_aba('authorizer')
        return [row[0] for row in dados[1:] if row and row[0]] if dados and len(dados) > 1 else []

    def adc_dados(self, new_data_list):
        if not self.credentials: return
        try:
            archive = self.credentials.open_by_url(self.spreadsheet_url)
            aba = archive.worksheet_by_title('acess')
            all_values = aba.get_all_values()
            existing_ids = {row[0] for row in all_values[1:] if row}
            
            new_id = str(random.randint(1000, 9999))
            while new_id in existing_ids: new_id = str(random.randint(1000, 9999))
            
            aba.append_table(values=[new_id] + new_data_list, dimension='ROWS')
        except Exception as e:
            st.error(f"Erro ao adicionar dados: {e}")

    def editar_dados(self, id_registro, updated_data_list):
        if not self.credentials: return False
        try:
            archive = self.credentials.open_by_url(self.spreadsheet_url)
            aba = archive.worksheet_by_title('acess')
            cell_list = aba.find(str(id_registro), matchCase=True, in_column=1)
            if cell_list:
                aba.update_row(cell_list[0].row, [str(id_registro)] + updated_data_list)
                return True
            return False
        except pygsheets.exceptions.CellNotFound:
            return False
        except Exception as e:
            st.error(f"Erro ao editar dados: {e}"); return False

    def excluir_dados(self, id_registro):
        if not self.credentials: return False
        try:
            archive = self.credentials.open_by_url(self.spreadsheet_url)
            aba = archive.worksheet_by_title('acess')
            cell_list = aba.find(str(id_registro), matchCase=True, in_column=1)
            if cell_list:
                aba.delete_rows(cell_list[0].row); return True
            return False
        except Exception as e:
            st.error(f"Erro ao excluir dados: {e}"); return False

# --- FUNÇÕES PÚBLICAS (SINGLETON) ---
@st.cache_resource
def get_sheet_ops():
    return SheetOperations()

def load_data_from_sheets():
    ops = get_sheet_ops()
    data = ops.carregar_dados_aba('acess')
    if data:
        st.session_state.df_acesso_veiculos = pd.DataFrame(data[1:], columns=data[0]).fillna("")
    else:
        st.session_state.df_acesso_veiculos = pd.DataFrame()

def get_aprovadores():
    return get_sheet_ops().carregar_dados_aprovadores()

def add_record(name, cpf, placa, marca_carro, horario_entrada, data, empresa, status, motivo, aprovador):
    ops = get_sheet_ops()
    first_reg_date = data if status == "Autorizado" else ""
    new_data = [name, cpf, placa, marca_carro, horario_entrada, "", data, empresa, status, motivo, aprovador, first_reg_date]
    ops.adc_dados(new_data)
    return True

def update_exit_time(name, exit_date_str, exit_time_str):
    ops = get_sheet_ops()
    try:
        all_data = ops.carregar_dados_aba('acess')
        if not all_data: return False, "Planilha vazia."

        header = all_data[0]
        df = pd.DataFrame(all_data[1:], columns=header)
        
        open_records = df[(df["Nome"] == name) & ((df["Horário de Saída"] == "") | pd.isna(df["Horário de Saída"]))]
        if open_records.empty: return False, "Nenhum registro em aberto."
        
        open_records.loc[:, 'Data_dt'] = pd.to_datetime(open_records['Data'], format='%d/%m/%Y', errors='coerce')
        record_to_update = open_records.sort_values(by='Data_dt', ascending=False).iloc[0]

        record_id = record_to_update["ID"]
        entry_date = datetime.strptime(record_to_update["Data"], "%d/%m/%Y")
        exit_date = datetime.strptime(exit_date_str, "%d/%m/%Y")
        
        original_row = next((row for row in all_data[1:] if row[0] == record_id), None)
        if not original_row: return False, "Registro original não encontrado."

        updated_data = original_row[1:]
        exit_time_index = header.index("Horário de Saída") - 1

        if entry_date.date() >= exit_date.date():
            updated_data[exit_time_index] = exit_time_str
            if ops.editar_dados(record_id, updated_data): return True, "Saída registrada."
            return False, "Falha ao editar registro."
        else:
            updated_data[exit_time_index] = "23:59"
            ops.editar_dados(record_id, updated_data)
            current_date = entry_date + timedelta(days=1)
            while current_date.date() < exit_date.date():
                data_pernoite = [name, record_to_update["CPF"], record_to_update["Placa"], record_to_update["Marca do Carro"], "00:00", "23:59", current_date.strftime("%d/%m/%Y"), record_to_update["Empresa"], "Autorizado", "Pernoite", record_to_update.get("Aprovador", ""), ""]
                ops.adc_dados(data_pernoite)
                current_date += timedelta(days=1)
            data_final = [name, record_to_update["CPF"], record_to_update["Placa"], record_to_update["Marca do Carro"], "00:00", exit_time_str, exit_date_str, record_to_update["Empresa"], "Autorizado", "Pernoite", record_to_update.get("Aprovador", ""), ""]
            ops.adc_dados(data_final)
            return True, "Saída com pernoite registrada."
    except Exception as e:
        return False, f"Erro ao registrar saída: {e}"

def delete_record(name, data_str):
    ops = get_sheet_ops()
    all_data = ops.carregar_dados_aba('acess')
    if not all_data: return False
    
    df = pd.DataFrame(all_data[1:], columns=all_data[0])
    records_to_delete = df[(df["Nome"] == name) & (df["Data"] == data_str)]
    if records_to_delete.empty: return False
    
    record_id = records_to_delete.iloc[0]['ID']
    return ops.excluir_dados(record_id)

def check_blocked_records(df):
    if df.empty: return None
    df_copy = df.copy()
    if 'Nome' in df_copy.columns:
        from app.utils import clean_name
        df_copy['Nome_Normalizado'] = df_copy['Nome'].apply(clean_name)
    
    df_copy['Data_dt'] = pd.to_datetime(df_copy['Data'], format='%d/%m/%Y', errors='coerce')
    df_sorted = df_copy.dropna(subset=['Data_dt']).sort_values(by=['Data_dt', 'Horário de Entrada'], ascending=False)
    
    latest_status = df_sorted.drop_duplicates(subset='Nome_Normalizado', keep='first')
    
    blocked = latest_status[latest_status["Status da Entrada"] == "Bloqueado"]
    if blocked.empty: return None
    
    info = "\n".join([f"- **{row['Nome']}**: {row['Motivo do Bloqueio']} (em {row['Data']})" for _, row in blocked.iterrows()])
    return info
