import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from functools import wraps
from app.operations import SheetOperations

# Cache para armazenar os dados
_sheet_data_cache = {
    'data': None,
    'last_update': None
}

# Decorator para implementar throttling
def throttle_requests(min_time=1):
    """Decorator para garantir um intervalo mínimo entre chamadas"""
    last_call = {}
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            if func.__name__ in last_call:
                time_since_last_call = now - last_call[func.__name__]
                if time_since_last_call < min_time:
                    time.sleep(min_time - time_since_last_call)
            result = func(*args, **kwargs)
            last_call[func.__name__] = time.time()
            return result
        return wrapper
    return decorator

# Função para obter dados com cache
def get_cached_sheet_data(force_refresh=False):
    """Obtém dados do cache ou atualiza se necessário"""
    now = datetime.now()
    cache_age = (now - _sheet_data_cache['last_update']).total_seconds() if _sheet_data_cache['last_update'] else None
    
    if force_refresh or not _sheet_data_cache['data'] or not cache_age or cache_age > 60:  # Cache de 1 minuto
        try:
            sheet_operations = SheetOperations()
            data = sheet_operations.carregar_dados()
            _sheet_data_cache['data'] = data
            _sheet_data_cache['last_update'] = now
        except Exception as e:
            if not _sheet_data_cache['data']:
                raise e
            st.warning("Usando dados em cache devido a erro de conexão")
    
    return _sheet_data_cache['data']

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
        data = get_cached_sheet_data()
        if not data:
            return False, "Erro ao carregar dados"
            
        df = pd.DataFrame(data[1:], columns=data[0])
        person_records = df[
            (df["Nome"] == name) &
            ((df["Horário de Saída"].isna()) | (df["Horário de Saída"] == ""))
        ]
        
        if person_records.empty:
            return False, "Nenhum registro em aberto encontrado para esta pessoa."
        
        # Pegar o registro mais recente
        record = person_records.iloc[0]
        record_id = record.iloc[0]  # ID do registro usando .iloc
        
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
            sheet_operations = SheetOperations()
            sheet_operations.editar_dados(record_id, updated_data)
            return True, "Horário de saída atualizado com sucesso."
        
        # Se a saída é em um dia diferente
        else:
            # 1. Fechar o registro do dia anterior às 23:59
            updated_data = list(record[1:])
            updated_data[5] = "23:59"  # Horário de Saída
            sheet_operations = SheetOperations()
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
        # Força atualização do cache após adicionar novo registro
        get_cached_sheet_data(force_refresh=True)
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar registro: {str(e)}")
        return False

def delete_record(name, data):
    """
    Deleta um registro de acesso.
    """
    try:
        sheet_data = get_cached_sheet_data()
        if not sheet_data:
            return False
            
        df = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])
        
        # Encontrar o registro para deletar
        record = df[(df["Nome"] == name) & (df["Data"] == data)]
        
        if record.empty:
            return False
            
        record_id = record.iloc[0].iloc[0]  # ID está na primeira coluna usando .iloc
        sheet_operations = SheetOperations()
        success = sheet_operations.excluir_dados(record_id)
        if success:
            # Força atualização do cache após deletar registro
            get_cached_sheet_data(force_refresh=True)
        return success
        
    except Exception as e:
        st.error(f"Erro ao deletar registro: {str(e)}")
        return False

def check_entry(name, data):
    """
    Verifica um registro de entrada.
    """
    try:
        sheet_data = get_cached_sheet_data()
        if not sheet_data:
            return None, "Erro ao carregar dados"
            
        df = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])
        
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
        sheet_data = get_cached_sheet_data()
        if not sheet_data:
            return None
            
        df = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])
        
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



































