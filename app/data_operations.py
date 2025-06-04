import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from app.operations import SheetOperations


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
    # Remove caracteres não numéricos
    cpf = ''.join(filter(str.isdigit, str(cpf)))
    if len(cpf) != 11:
        return cpf
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

def validate_cpf(cpf):
    """Valida o CPF"""
    # Remove caracteres não numéricos
    cpf = ''.join(filter(str.isdigit, str(cpf)))
    
    # Verifica se tem 11 dígitos
    if len(cpf) != 11:
        return False
    
    # Verifica se todos os dígitos são iguais
    if len(set(cpf)) == 1:
        return False
    
    # Validação do primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[9]):
        return False
    
    # Validação do segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[10]):
        return False
    
    return True

def round_to_nearest_interval(time_value, interval=1):
    """Arredonda o horário para o intervalo mais próximo"""
    try:
        # Se for string vazia ou None, retorna horário atual
        if pd.isna(time_value) or time_value == "":
            now = datetime.now()
            return now.strftime("%H:%M")
        
        # Se for número (minutos desde meia-noite)
        if isinstance(time_value, (int, float)):
            hours = int(time_value // 60)
            minutes = int(time_value % 60)
            time_str = f"{hours:02d}:{minutes:02d}"
        else:
            time_str = str(time_value)
        
        # Tenta converter para datetime
        try:
            time = datetime.strptime(time_str, "%H:%M")
        except ValueError:
            # Se falhar, usa horário atual
            now = datetime.now()
            return now.strftime("%H:%M")
        
        # Arredonda para o intervalo mais próximo
        total_minutes = time.hour * 60 + time.minute
        rounded_minutes = (total_minutes // interval) * interval
        
        # Converte de volta para horas e minutos
        hours = rounded_minutes // 60
        minutes = rounded_minutes % 60
        
        return f"{hours:02d}:{minutes:02d}"
    except Exception:
        # Em caso de qualquer erro, retorna horário atual
        now = datetime.now()
        return now.strftime("%H:%M")

def update_exit_time(name, exit_date, exit_time):
    """
    Atualiza o horário de saída de um registro, lidando corretamente com registros que atravessam a meia-noite.
    """
    try:
        sheet_operations = SheetOperations()
        df = pd.DataFrame(sheet_operations.carregar_dados()[1:], columns=sheet_operations.carregar_dados()[0])
        
        # Encontrar o registro em aberto mais recente para a pessoa
        person_records = df[
            (df["Nome"] == name) &
            ((df["Horário de Saída"].isna()) | (df["Horário de Saída"] == ""))
        ]
        
        if person_records.empty:
            return False, "Nenhum registro em aberto encontrado para esta pessoa."
        
        # Pegar o registro mais recente (assumindo que a data está no formato dd/mm/yyyy)
        record = person_records.iloc[0]
        record_id = record[0]  # ID do registro
        
        # Converter datas e horários para datetime
        entry_date = datetime.strptime(record["Data"], "%d/%m/%Y")
        entry_time = datetime.strptime(record["Horário de Entrada"], "%H:%M")
        exit_date_obj = datetime.strptime(exit_date, "%d/%m/%Y")
        exit_time_obj = datetime.strptime(exit_time, "%H:%M")
        
        # Combinar data e hora
        entry_datetime = datetime.combine(entry_date.date(), entry_time.time())
        exit_datetime = datetime.combine(exit_date_obj.date(), exit_time_obj.time())
        
        # Se a saída é no mesmo dia da entrada
        if entry_date.date() == exit_date_obj.date():
            # Atualizar o registro com o horário de saída
            updated_data = list(record[1:])  # Excluir o ID
            updated_data[5] = exit_time  # Índice 5 é o Horário de Saída
            sheet_operations.editar_dados(record_id, updated_data)
            return True, "Horário de saída atualizado com sucesso."
        
        # Se a saída é em um dia diferente
        else:
            # 1. Fechar o registro do dia anterior às 23:59
            updated_data = list(record[1:])
            updated_data[5] = "23:59"  # Horário de Saída
            sheet_operations.editar_dados(record_id, updated_data)
            
            # 2. Criar registros para os dias intermediários (se houver)
            current_date = entry_date + timedelta(days=1)
            while current_date.date() < exit_date_obj.date():
                new_data = [
                    record["Nome"],
                    record["CPF"],
                    record["Placa"],
                    record["Marca do Carro"],
                    "",  # Horário de Entrada em branco
                    "23:59",  # Horário de Saída
                    current_date.strftime("%d/%m/%Y"),
                    record["Empresa"],
                    record["Status da Entrada"],
                    record["Motivo do Bloqueio"],
                    record["Aprovador"],
                    record["Data do Primeiro Registro"] if "Data do Primeiro Registro" in record else ""
                ]
                sheet_operations.adc_dados(new_data)
                current_date += timedelta(days=1)
            
            # 3. Criar registro final com a saída no horário informado
            final_data = [
                record["Nome"],
                record["CPF"],
                record["Placa"],
                record["Marca do Carro"],
                "",  # Horário de Entrada em branco
                exit_time,  # Horário de Saída
                exit_date,
                record["Empresa"],
                record["Status da Entrada"],
                record["Motivo do Bloqueio"],
                record["Aprovador"],
                record["Data do Primeiro Registro"] if "Data do Primeiro Registro" in record else ""
            ]
            sheet_operations.adc_dados(final_data)
            
            return True, "Registros atualizados com sucesso para todo o período."
            
    except Exception as e:
        return False, f"Erro ao atualizar horário de saída: {str(e)}"

def add_record(name, cpf, placa, marca_carro, horario_entrada, data, empresa, status, motivo, aprovador):
    """
    Adiciona um novo registro de acesso.
    """
    try:
        sheet_operations = SheetOperations()
        new_data = [
            name, cpf, placa, marca_carro, horario_entrada, "", data, empresa, 
            status, motivo, aprovador, data if not motivo else ""
        ]
        sheet_operations.adc_dados(new_data)
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar registro: {str(e)}")
        return False

def delete_record(name, data):
    """
    Deleta um registro de acesso.
    """
    try:
        sheet_operations = SheetOperations()
        df = pd.DataFrame(sheet_operations.carregar_dados()[1:], columns=sheet_operations.carregar_dados()[0])
        
        # Encontrar o registro para deletar
        record = df[(df["Nome"] == name) & (df["Data"] == data)]
        
        if record.empty:
            return False
            
        record_id = record.iloc[0][0]  # ID está na primeira coluna
        return sheet_operations.excluir_dados(record_id)
        
    except Exception as e:
        st.error(f"Erro ao deletar registro: {str(e)}")
        return False

def check_entry(name, data):
    """
    Verifica um registro de entrada.
    """
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
        st.error(f"Erro ao verificar registro: {str(e)}")
        return None, f"Erro ao verificar registro: {str(e)}"

def check_blocked_records(df):
    """
    Verifica registros bloqueados.
    """
    try:
        blocked = df[df["Status da Entrada"] == "Bloqueado"]
        if blocked.empty:
            return None
            
        info = ""
        for _, row in blocked.iterrows():
            info += f"Nome: {row['Nome']}\n"
            info += f"Motivo: {row['Motivo do Bloqueio']}\n"
            info += f"Data: {row['Data']}\n"
            info += "---\n"
            
        return info
        
    except Exception as e:
        st.error(f"Erro ao verificar registros bloqueados: {str(e)}")
        return None

def get_block_info(name):
    """
    Obtém informações de bloqueio de uma pessoa.
    """
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
        st.error(f"Erro ao obter informações de bloqueio: {str(e)}")
        return None


def load_data_from_sheets():
    # Forçar atualização dos dados
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
















































