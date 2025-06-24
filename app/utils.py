from datetime import datetime, timedelta
import pandas as pd
import pytz
from fuzzywuzzy import process

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
    
def normalize_names(name_series: pd.Series, threshold=90) -> pd.Series:
    """
    Normaliza uma série de nomes de forma robusta usando fuzzy matching.
    1. Agrupa nomes semelhantes.
    2. Escolhe o representante mais comum de cada grupo.
    3. Mapeia todos os nomes do grupo para o seu representante.
    """
    # Remove nomes nulos/vazios e obtém uma lista de nomes únicos para processar
    unique_names = name_series.dropna().unique()
    
    # Dicionário para mapear cada nome original ao seu nome canônico/representante
    name_map = {}
    
    # Conjunto para rastrear nomes que já foram atribuídos a um grupo
    processed_names = set()

    for name in unique_names:
        if name in processed_names:
            continue

        # Encontra um grupo de nomes semelhantes ao nome atual
        # Usamos `process.extract` para obter todas as correspondências acima do limiar
        matches = process.extract(name, unique_names, scorer=fuzz.WRatio, limit=None)
        
        # Filtra apenas as correspondências com score alto
        similar_names = [match[0] for match in matches if match[1] >= threshold]
        
        if not similar_names:
            # Se não houver nomes semelhantes, o nome é seu próprio representante
            name_map[name] = name
            processed_names.add(name)
            continue

        # --- Escolhe o melhor representante para o grupo ---
        # Conta a frequência de cada nome semelhante na série original completa
        group_counts = name_series[name_series.isin(similar_names)].value_counts()
        
        if not group_counts.empty:
            # O representante é o nome mais frequente no grupo
            representative = group_counts.index[0]
        else:
            # Fallback: se nenhum nome for encontrado, usa o próprio nome como representante
            representative = name
            
        # Mapeia todos os nomes do grupo para o representante escolhido
        for similar_name in similar_names:
            name_map[similar_name] = representative
            processed_names.add(similar_name)
            
    # Aplica o mapeamento final à série original
    return name_series.map(name_map)

    
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
