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

def normalize_names(name_series: pd.Series, threshold=75) -> pd.Series:
    """
    Normaliza nomes de forma precisa e performática.
    Usa um pré-processamento inteligente antes do fuzzy matching.
    """
    # 1. Cria um DataFrame com os nomes originais e suas versões limpas/ordenadas
    df_names = pd.DataFrame({'original': name_series.dropna()})
    df_names['cleaned'] = df_names['original'].apply(clean_and_sort_name)

    # 2. Identifica os representantes canônicos
    # O representante de cada grupo de nomes limpos é a forma original mais comum
    # value_counts() nos dá a frequência, e .index[0] o mais frequente
    representatives = df_names.groupby('cleaned')['original'].apply(lambda x: x.value_counts().index[0])
    
    # 3. Mapeia cada nome limpo ao seu representante
    cleaned_to_rep_map = representatives.to_dict()

    # 4. Cria o mapa final do nome original para o representante final
    name_map = {}
    # Obtém a lista de representantes limpos para a busca com fuzzywuzzy
    canonical_cleaned_names = list(cleaned_to_rep_map.keys())

    for original_name in name_series.dropna().unique():
        cleaned_name = clean_and_sort_name(original_name)
        
        # Encontra a melhor correspondência para o nome limpo na lista de representantes limpos
        best_match, score = process.extractOne(cleaned_name, canonical_cleaned_names, scorer=fuzz.WRatio)
        
        if score >= threshold:
            # Se a correspondência for boa, usa o representante daquele grupo
            name_map[original_name] = cleaned_to_rep_map[best_match]
        else:
            # Senão, o nome é seu próprio representante
            name_map[original_name] = original_name

    # 5. Aplica o mapa à série original
    return name_series.map(name_map)


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
