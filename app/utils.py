import pandas as pd
import re
from datetime import datetime, timedelta
import pytz
from unidecode import unidecode
from fuzzywuzzy import process, fuzz
from collections import Counter

def get_sao_paulo_time():
    """Retorna o horário atual no fuso horário de São Paulo."""
    utc_now = datetime.now(pytz.utc)
    sao_paulo_tz = pytz.timezone("America/Sao_Paulo")
    return utc_now.astimezone(sao_paulo_tz)

def clean_and_sort_name(name):
    """Limpa e ordena as palavras de um nome para uma comparação robusta."""
    if not isinstance(name, str):
        return ""
    # Remove acentos, pontuação e converte para minúsculas
    name = unidecode(name).lower()
    name = re.sub(r'[^\w\s]', '', name)
    # Ordena as palavras para que "Silva Jose" e "Jose Silva" sejam idênticos
    return ' '.join(sorted(name.split()))

def normalize_names(name_series: pd.Series, threshold=85) -> pd.Series:
    """
    Normaliza nomes usando fuzzywuzzy como ferramenta principal para agrupar,
    e então elege o representante mais comum de cada grupo.
    """
    original_names = name_series.dropna().unique()
    if len(original_names) == 0:
        return name_series

    # 1. Limpa todos os nomes únicos para criar uma lista de "mestres" para comparação
    cleaned_masters = {name: clean_name_for_matching(name) for name in original_names}
    master_list = list(cleaned_masters.values())

    # 2. Para cada nome original, encontra a qual grupo "mestre" ele pertence
    original_to_master_map = {}
    for original_name, cleaned_name in cleaned_masters.items():
        # Usa fuzzywuzzy para encontrar a melhor correspondência na lista de mestres
        best_match, score = process.extractOne(cleaned_name, master_list, scorer=fuzz.WRatio)
        if score >= threshold:
            original_to_master_map[original_name] = best_match
        else:
            original_to_master_map[original_name] = cleaned_name # É seu próprio mestre

    # 3. Inverte o mapa para agrupar: {mestre -> [lista de nomes originais]}
    master_to_originals_map = {}
    for original, master in original_to_master_map.items():
        if master not in master_to_originals_map:
            master_to_originals_map[master] = []
        master_to_originals_map[master].append(original)

    # 4. Para cada grupo, elege o representante (a forma original mais comum)
    final_map = {}
    for master, originals_in_group in master_to_originals_map.items():
        # Conta a frequência dos nomes originais neste grupo
        group_counts = name_series[name_series.isin(originals_in_group)].value_counts()
        if not group_counts.empty:
            representative = group_counts.index[0]
        else:
            representative = originals_in_group[0] # Fallback
        
        # Mapeia todos os nomes originais do grupo para o representante final
        for original in originals_in_group:
            final_map[original] = representative
            
    # 5. Aplica o mapa final à série original
    return name_series.map(final_map)


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
    cpf_digits = ''.join(filter(str.isdigit, str(cpf)))
    if len(cpf_digits) != 11: return cpf
    return f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"

def validate_cpf(cpf):
    cpf_digits = ''.join(filter(str.isdigit, str(cpf)))
    if len(cpf_digits) != 11 or len(set(cpf_digits)) == 1: return False
    soma = sum(int(cpf_digits[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    if resto == 10: resto = 0
    if resto != int(cpf_digits[9]): return False
    soma = sum(int(cpf_digits[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    if resto == 10: resto = 0
    if resto != int(cpf_digits[10]): return False
    return True

def round_to_nearest_interval(time_value, interval=1):
    try:
        if pd.isna(time_value) or time_value == "": return get_sao_paulo_time().strftime("%H:%M")
        time_obj = datetime.strptime(str(time_value), "%H:%M")
        total_minutes = time_obj.hour * 60 + time_obj.minute
        rounded_minutes = (total_minutes // interval) * interval
        hours, minutes = divmod(rounded_minutes, 60)
        return f"{hours:02d}:{minutes:02d}"
    except (ValueError, TypeError):
        return get_sao_paulo_time().strftime("%H:%M")
