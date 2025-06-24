from datetime import datetime, timedelta
import pandas as pd
import pytz

def get_sao_paulo_time():
    """Retorna o horário atual com o fuso horário de São Paulo (America/Sao_Paulo)."""
    utc_now = datetime.now(pytz.utc)
    sao_paulo_tz = pytz.timezone("America/Sao_Paulo")
    return utc_now.astimezone(sao_paulo_tz)

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
    cpf_digits = ''.join(filter(str.isdigit, str(cpf)))
    if len(cpf_digits) != 11:
        return cpf # Retorna o original se não for um CPF completo
    return f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"

def validate_cpf(cpf):
    """Valida o CPF completo com dígitos verificadores."""
    cpf_digits = ''.join(filter(str.isdigit, str(cpf)))
    if len(cpf_digits) != 11 or len(set(cpf_digits)) == 1:
        return False
    
    # Validação do primeiro dígito
    soma = sum(int(cpf_digits[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    if resto == 10: resto = 0
    if resto != int(cpf_digits[9]): return False
    
    # Validação do segundo dígito
    soma = sum(int(cpf_digits[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    if resto == 10: resto = 0
    if resto != int(cpf_digits[10]): return False
    
    return True

def round_to_nearest_interval(time_value, interval=1):
    """Arredonda o horário para o intervalo mais próximo."""
    try:
        if pd.isna(time_value) or time_value == "":
            return get_sao_paulo_time().strftime("%H:%M")
        
        time_obj = datetime.strptime(str(time_value), "%H:%M")
        total_minutes = time_obj.hour * 60 + time_obj.minute
        rounded_minutes = (total_minutes // interval) * interval
        hours, minutes = divmod(rounded_minutes, 60)
        return f"{hours:02d}:{minutes:02d}"
    except (ValueError, TypeError):
        return get_sao_paulo_time().strftime("%H:%M")
