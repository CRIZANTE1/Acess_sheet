from datetime import datetime, timedelta
import pandas as pd

def generate_time_options():
    """Gera uma lista de horários de 00:00 a 23:59 em intervalos de 1 minuto"""
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