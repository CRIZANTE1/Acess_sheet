from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

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

def validate_cpf(cpf, debug=True):
    """Verifica se o CPF tem 11 dígitos"""
    # Remove caracteres não numéricos e espaços
    cpf = ''.join(filter(str.isdigit, str(cpf)))
    
    # Verifica se tem 11 dígitos
    if len(cpf) != 11:
        if debug:
            st.warning(f"CPF deve ter 11 dígitos. Encontrado: {len(cpf)}")
        return False
    return True

def test_cpf(cpf_to_test):
    """Função para testar a validação de CPF"""
    cpf_limpo = ''.join(filter(str.isdigit, str(cpf_to_test)))
    numeros = [int(digito) for digito in cpf_limpo]
    
    # Calcula primeiro dígito
    soma = sum(a * b for a, b in zip(numeros[0:9], range(10, 1, -1)))
    d1 = (soma * 10 % 11) % 10
    
    # Calcula segundo dígito
    soma = sum(a * b for a, b in zip(numeros[0:10], range(11, 1, -1)))
    d2 = (soma * 10 % 11) % 10
    
    st.write(f"""
    CPF testado: {cpf_to_test}
    CPF limpo: {cpf_limpo}
    Dígitos calculados: {d1} e {d2}
    Dígitos no CPF: {cpf_limpo[9:] if len(cpf_limpo) >= 11 else 'CPF incompleto'}
    """)
    
    return validate_cpf(cpf_to_test)

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
