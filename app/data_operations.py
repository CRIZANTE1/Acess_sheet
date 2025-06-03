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

def is_valid_time(time_str):
    """
    Verifica se uma string representa um horário válido no formato HH:MM
    """
    if not time_str:  # Se for None ou string vazia
        return False
    try:
        # Remove espaços e tenta converter para datetime
        time_clean = str(time_str).strip()
        if time_clean:
            datetime.strptime(time_clean, "%H:%M")
            return True
        return False
    except (ValueError, TypeError):
        return False

def update_exit_time(name, exit_date, exit_time):
    """
    Atualiza o horário de saída de um registro, lidando corretamente com registros que atravessam a meia-noite.
    """
    try:
        sheet_operations = SheetOperations()
        # Carregar dados frescos da planilha
        all_data = sheet_operations.carregar_dados()
        if not all_data or len(all_data) < 1:
            return False, "Não foi possível carregar os dados da planilha."
        
        columns = all_data[0]
        df = pd.DataFrame(all_data[1:], columns=columns)
        
        # Encontrar o registro em aberto mais recente para a pessoa
        person_records = df[
            (df["Nome"] == name) &
            df["Horário de Saída"].apply(lambda x: not is_valid_time(x))
        ].copy()
        
        if person_records.empty:
            return False, f"Nenhum registro em aberto encontrado para {name}."
        
        # Ordenar por Data e Horário de Entrada para pegar o mais recente
        try:
            person_records["DataHoraEntrada"] = pd.to_datetime(
                person_records["Data"] + ' ' + person_records["Horário de Entrada"], 
                format="%d/%m/%Y %H:%M", 
                errors='coerce'
            )
            person_records.dropna(subset=["DataHoraEntrada"], inplace=True)
            if person_records.empty:
                return False, f"Nenhum registro em aberto válido encontrado para {name} após verificação de data/hora."
            person_records.sort_values(by="DataHoraEntrada", ascending=False, inplace=True)
        except Exception as e:
            st.warning(f"Erro ao processar datas para ordenação de registros em aberto para {name}: {e}. Usando o primeiro registro encontrado.")

        record_to_update = person_records.iloc[0]
        record_id = record_to_update.iloc[0]

        # Validar o horário de saída fornecido
        if not is_valid_time(exit_time):
            return False, "O horário de saída fornecido não é válido. Use o formato HH:MM."

        # Converter datas e horários para datetime
        try:
            entry_date_str = record_to_update["Data"]
            entry_time_str = record_to_update["Horário de Entrada"]
            entry_date = datetime.strptime(entry_date_str, "%d/%m/%Y")
            entry_time = datetime.strptime(entry_time_str, "%H:%M")
            exit_date_obj = datetime.strptime(exit_date, "%d/%m/%Y")
            exit_time_obj = datetime.strptime(exit_time, "%H:%M")
        except ValueError as e:
            return False, f"Formato de data ou hora inválido. Verifique os dados. Erro: {e}"

        # Combinar data e hora
        entry_datetime = datetime.combine(entry_date.date(), entry_time.time())
        exit_datetime = datetime.combine(exit_date_obj.date(), exit_time_obj.time())

        if exit_datetime < entry_datetime:
            return False, "O horário de saída não pode ser anterior ao horário de entrada."


        if not columns: # Caso columns não tenha sido definido (improvável aqui, mas seguro)
            return False, "Nomes das colunas não carregados."
            
        try:
            horario_saida_col_index = columns.index("Horário de Saída")
            # O ID é a primeira coluna (índice 0).
            # A lista de dados para sheet_operations.editar_dados não deve incluir o ID.
            # Então, o índice em 'updated_data' será 'horario_saida_col_index - 1'
            idx_horario_saida_in_updated_data = horario_saida_col_index -1
            
            # E os outros campos para o novo registro devem ser mapeados corretamente
            idx_nome_col = columns.index("Nome") -1
            idx_cpf_col = columns.index("CPF") -1
            idx_placa_col = columns.index("Placa") -1
            idx_marca_carro_col = columns.index("Marca do Carro") -1
            # Horário de entrada é [4] (originalmente indice 5, menos ID)
            idx_data_col = columns.index("Data") -1
            idx_empresa_col = columns.index("Empresa") -1
            idx_status_col = columns.index("Status da Entrada") -1
            idx_motivo_col = columns.index("Motivo do Bloqueio") -1
            idx_aprovador_col = columns.index("Aprovador") -1
            idx_data_primeiro_registro_col = columns.index("Data do Primeiro Registro") -1


        except ValueError:
            return False, "Coluna 'Horário de Saída' ou outras colunas essenciais não encontradas na planilha."


        # Se a saída é no mesmo dia da entrada
        if entry_date.date() == exit_date_obj.date():
            updated_data = record_to_update.tolist()[1:] # Excluir o ID
            updated_data[idx_horario_saida_in_updated_data] = exit_time  # Atualiza o Horário de Saída
            sheet_operations.editar_dados(str(record_id), updated_data) # Garante que record_id seja string
            return True, "Horário de saída atualizado com sucesso."
        
        # Se a saída é em um dia diferente (lógica de pernoite)
        else:
            # 1. Fechar o registro do dia anterior às 23:59
            updated_data_dia_anterior = record_to_update.tolist()[1:]
            updated_data_dia_anterior[idx_horario_saida_in_updated_data] = "23:59"
            sheet_operations.editar_dados(str(record_id), updated_data_dia_anterior)
            
            # 2. Criar registros para os dias intermediários (se houver)
            current_loop_date = entry_date + timedelta(days=1)
            while current_loop_date.date() < exit_date_obj.date():
                # Criar novo registro para dia intermediário
                # A ordem aqui DEVE corresponder à ordem das colunas na planilha, SEM o ID
                new_data_intermediario = [""] * (len(columns) - 1) # Inicializa com strings vazias
                new_data_intermediario[idx_nome_col] = record_to_update["Nome"]
                new_data_intermediario[idx_cpf_col] = record_to_update["CPF"]
                new_data_intermediario[idx_placa_col] = record_to_update.get("Placa", "") # Usar .get para campos que podem não existir
                new_data_intermediario[idx_marca_carro_col] = record_to_update.get("Marca do Carro", "")
                new_data_intermediario[4] = ""  # Horário de Entrada em branco (índice 4 na lista sem ID)
                new_data_intermediario[idx_horario_saida_in_updated_data] = "23:59"  # Horário de Saída
                new_data_intermediario[idx_data_col] = current_loop_date.strftime("%d/%m/%Y")
                new_data_intermediario[idx_empresa_col] = record_to_update["Empresa"]
                new_data_intermediario[idx_status_col] = record_to_update["Status da Entrada"]
                new_data_intermediario[idx_motivo_col] = record_to_update.get("Motivo do Bloqueio", "")
                new_data_intermediario[idx_aprovador_col] = record_to_update["Aprovador"]
                new_data_intermediario[idx_data_primeiro_registro_col] = record_to_update.get("Data do Primeiro Registro", "")
                sheet_operations.adc_dados(new_data_intermediario)
                current_loop_date += timedelta(days=1)
            
            # 3. Criar registro final com a saída no horário informado
            new_data_final = [""] * (len(columns) - 1) # Inicializa com strings vazias
            new_data_final[idx_nome_col] = record_to_update["Nome"]
            new_data_final[idx_cpf_col] = record_to_update["CPF"]
            new_data_final[idx_placa_col] = record_to_update.get("Placa", "")
            new_data_final[idx_marca_carro_col] = record_to_update.get("Marca do Carro", "")
            new_data_final[4] = ""  # Horário de Entrada em branco
            new_data_final[idx_horario_saida_in_updated_data] = exit_time  # Horário de Saída
            new_data_final[idx_data_col] = exit_date_obj.strftime("%d/%m/%Y") # Usa a data de saída final
            new_data_final[idx_empresa_col] = record_to_update["Empresa"]
            new_data_final[idx_status_col] = record_to_update["Status da Entrada"]
            new_data_final[idx_motivo_col] = record_to_update.get("Motivo do Bloqueio", "")
            new_data_final[idx_aprovador_col] = record_to_update["Aprovador"]
            new_data_final[idx_data_primeiro_registro_col] = record_to_update.get("Data do Primeiro Registro", "")
            sheet_operations.adc_dados(new_data_final)
            
            return True, "Registros de pernoite atualizados com sucesso."
            
    except pd.errors.EmptyDataError:
        return False, "A planilha de dados parece estar vazia."
    except KeyError as e:
        return False, f"Coluna não encontrada na planilha: {e}. Verifique a estrutura da planilha."
    except Exception as e:
        st.error(f"Erro inesperado em update_exit_time: {str(e)}") # Log para debug no Streamlit
        return False, f"Erro inesperado ao atualizar horário de saída: {str(e)}"

def has_open_entry(name, data=None):
    """
    Verifica se a pessoa já tem um registro de entrada sem saída ou um registro no mesmo dia.
    Retorna (True, registro, mensagem) se existir um registro que impede nova entrada, (False, None, "") caso contrário.
    """
    try:
        sheet_operations = SheetOperations()
        df = pd.DataFrame(sheet_operations.carregar_dados()[1:], columns=sheet_operations.carregar_dados()[0])
        
        # Verificar registros em aberto (sem horário de saída válido)
        open_records = df[
            (df["Nome"] == name) &
            df["Horário de Saída"].apply(lambda x: not is_valid_time(x))
        ]
        
        if not open_records.empty:
            record = open_records.iloc[0]
            return True, record, f"Já existe um registro em aberto para {name} na data {record['Data']}. Por favor, registre a saída antes de criar uma nova entrada."

        # Se uma data específica foi fornecida, verificar registros no mesmo dia
        if data:
            same_day_records = df[
                (df["Nome"] == name) &
                (df["Data"] == data)
            ]
            
            if not same_day_records.empty:
                record = same_day_records.iloc[0]
                return True, record, f"Já existe um registro para {name} na data {data}. Não é possível ter múltiplas entradas no mesmo dia."
        
        return False, None, ""
        
    except Exception as e:
        st.error(f"Erro ao verificar registros em aberto: {str(e)}")
        return False, None, str(e)

def add_record(name, cpf, placa, marca_carro, horario_entrada, data, empresa, status, motivo, aprovador):
    """
    Adiciona um novo registro de acesso.
    """
    try:
        # Verificar se já existe um registro em aberto ou no mesmo dia
        has_open, existing_record, message = has_open_entry(name, data)
        if has_open:
            return False, message

        sheet_operations = SheetOperations()
        
        # Verificar se já existe um registro com o mesmo nome e data
        df = pd.DataFrame(sheet_operations.carregar_dados()[1:], columns=sheet_operations.carregar_dados()[0])
        existing_entries = df[
            (df["Nome"] == name) &
            (df["Data"] == data)
        ]
        
        if not existing_entries.empty:
            return False, f"Já existe um registro para {name} na data {data}. Não é possível ter múltiplas entradas no mesmo dia."

        new_data = [
            name, cpf, placa, marca_carro, horario_entrada, "", data, empresa, 
            status, motivo, aprovador, data if not motivo else ""
        ]
        sheet_operations.adc_dados(new_data)
        return True, "Registro adicionado com sucesso!"
    except Exception as e:
        error_msg = f"Erro ao adicionar registro: {str(e)}"
        st.error(error_msg)
        return False, error_msg

def delete_record(name, data):
    """
    Deleta um registro de acesso.
    """
    try:
        sheet_operations = SheetOperations()
        all_data = sheet_operations.carregar_dados()
        if not all_data or len(all_data) < 1:
            st.error("Não foi possível carregar os dados da planilha para deletar.")
            return False
            
        columns = all_data[0]
        df = pd.DataFrame(all_data[1:], columns=columns)
        
        # Encontrar o registro para deletar
        # Procura por uma correspondência exata de nome e data.
        # Se houver múltiplos, deletará o primeiro encontrado.
        record_df = df[(df["Nome"] == name) & (df["Data"] == data)]
        
        if record_df.empty:
            st.warning(f"Nenhum registro encontrado para {name} na data {data} para deletar.")
            return False
            
        # Pega o ID do primeiro registro correspondente
        record_id = record_df.iloc[0].iloc[0]  # ID está na primeira coluna do DataFrame filtrado
        
        success = sheet_operations.excluir_dados(str(record_id)) # Garante que record_id seja string
        if success:
            # st.success("Registro deletado com sucesso!") # A mensagem de sucesso já é dada na UI
            return True
        else:
            st.error(f"Falha ao comunicar com a planilha para deletar o registro ID: {record_id}.")
            return False
        
    except KeyError as e:
        st.error(f"Erro ao deletar registro: coluna {e} não encontrada. Verifique a planilha.")
        return False
    except Exception as e:
        st.error(f"Erro inesperado ao deletar registro: {str(e)}")
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




















































