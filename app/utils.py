from datetime import datetime, timedelta
import pandas as pd
import pytz
import re



DATE_FORMAT = "%d/%m/%Y"
TIME_FORMAT = "%H:%M"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


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

def clear_access_cache():
    """Limpa o cache de dados de acesso de forma centralizada."""
    import streamlit as st
    if 'df_acesso_veiculos' in st.session_state:
        del st.session_state['df_acesso_veiculos']
    st.cache_data.clear()

def validate_placa(placa):
    """
    Valida placas de veículos brasileiras.
    Aceita formato Mercosul (ABC1D23) e antigo (ABC-1234 ou ABC1234).
    Retorna True se válida ou vazia (placa é opcional).
    """
    if not placa or placa.strip() == "":
        return True  # Placa é opcional
    
    placa_limpa = placa.upper().replace("-", "").replace(" ", "")
    
    # Formato Mercosul: ABC1D23 (3 letras + 1 número + 1 letra + 2 números)
    mercosul = re.match(r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$', placa_limpa)
    
    # Formato antigo: ABC1234 (3 letras + 4 números)
    antigo = re.match(r'^[A-Z]{3}[0-9]{4}$', placa_limpa)
    
    return bool(mercosul or antigo)

def format_placa(placa):
    """
    Formata a placa no padrão adequado.
    Mercosul: ABC1D23
    Antigo: ABC-1234
    """
    if not placa or placa.strip() == "":
        return ""
    
    placa_limpa = placa.upper().replace("-", "").replace(" ", "")
    
    # Verifica se é Mercosul: ABC1D23
    if re.match(r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$', placa_limpa):
        return placa_limpa  # Mercosul não usa hífen
    
    # Verifica se é formato antigo: ABC1234
    if re.match(r'^[A-Z]{3}[0-9]{4}$', placa_limpa):
        return f"{placa_limpa[:3]}-{placa_limpa[3:]}"  # Adiciona hífen
    
    # Se não for nenhum formato válido, retorna como está
    return placa.upper()

def get_placa_tipo(placa):
    """
    Identifica o tipo de placa.
    Retorna: 'Mercosul', 'Antiga' ou 'Inválida'
    """
    if not placa or placa.strip() == "":
        return "Não informada"
    
    placa_limpa = placa.upper().replace("-", "").replace(" ", "")
    
    if re.match(r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$', placa_limpa):
        return "Mercosul"
    elif re.match(r'^[A-Z]{3}[0-9]{4}$', placa_limpa):
        return "Antiga"
    else:
        return "Inválida"


