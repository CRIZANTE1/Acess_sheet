import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import time
import locale
from app.operations import SheetOperations

def show_progress_bar(progress_placeholder):
    progress_text = "Aguarde o carregamento da página..."
    with st.spinner(progress_text):
        for _ in range(100):
            time.sleep(0.010)
    

def initialize_columns(df):
    """Certifica-se de que todas as colunas necessárias estão presentes no DataFrame"""
    required_columns = [
        "Nome", "CPF", "Placa", "Marca do Carro", "Horário de Entrada", 
        "Data", "Empresa", "Status da Entrada", "Motivo do Bloqueio", "Aprovador", "Data do Primeiro Registro"
    ]
    for column in required_columns:
        if column not in df.columns:
            df[column] = ""
    return df

def check_briefing_needed(df, name, current_date):
    """
    Verifica se um visitante precisa fazer o briefing baseado em seu histórico completo.
    
    Args:
        df (pd.DataFrame): DataFrame com todos os registros
        name (str): Nome do visitante
        current_date (str): Data atual no formato dd/mm/yyyy
    
    Returns:
        tuple: (precisa_briefing, motivo)
            precisa_briefing: True se precisar fazer briefing
            motivo: String explicando o motivo
    """
    # Pegar todos os registros do visitante
    visitor_records = df[df["Nome"] == name].copy()
    
    if visitor_records.empty:
        return True, "primeiro_acesso"
        
    try:
        # Converter a data atual para datetime
        current_date = datetime.strptime(current_date, "%d/%m/%Y")
        
        # Converter todas as datas para datetime
        visitor_records["Data"] = pd.to_datetime(visitor_records["Data"], format="%d/%m/%Y")
        
        # Encontrar a data do acesso mais recente
        last_access = visitor_records["Data"].max()
        
        # Calcular a diferença em dias
        days_since_last_access = (current_date - last_access).days
        
        if days_since_last_access >= 365:
            return True, "mais_de_um_ano"
        
        return False, None
        
    except ValueError as e:
        st.error(f"Erro ao processar datas: {str(e)}")
        return False, None

def add_record(name, cpf, placa, marca_carro, horario_entrada, data, empresa, status, motivo=None, aprovador=None):
    sheet_operations = SheetOperations()
    
    # Carregar dados existentes para verificar e adicionar
    data_from_sheet = sheet_operations.carregar_dados()
    if data_from_sheet:
        # A primeira linha são os cabeçalhos
        columns = data_from_sheet[0]
        df = pd.DataFrame(data_from_sheet[1:], columns=columns)
    else:
        df = pd.DataFrame(columns=[
            "Nome", "CPF", "Placa", "Marca do Carro", "Horário de Entrada", 
            "Horário de Saída", "Data", "Empresa", "Status da Entrada", "Motivo do Bloqueio", "Aprovador", "Data do Primeiro Registro"
        ])
    
    df = initialize_columns(df)  # Certifique-se de que todas as colunas necessárias estão presentes
    
    # Função auxiliar para formatar data
    def format_date(date_str):
        try:
            # Tenta primeiro o formato dd/mm/yyyy
            return datetime.strptime(date_str, "%d/%m/%Y").strftime("%d/%m/%Y")
        except ValueError:
            try:
                # Tenta o formato yyyy-mm-dd
                return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
            except ValueError:
                try:
                    # Tenta converter de timestamp se for um objeto datetime
                    return date_str.strftime("%d/%m/%Y")
                except AttributeError:
                    return None

    # Formatar a data do novo registro
    data_formatada = format_date(data)
    if not data_formatada:
        st.error(f"Erro: Data '{data}' está em um formato inválido.")
        return False

    # Verificar necessidade de briefing
    needs_briefing, motivo_briefing = check_briefing_needed(df, name, data_formatada)
    if needs_briefing:
        mensagem = "ATENÇÃO! {} precisa fazer o briefing de segurança pois {}.".format(
            name,
            "é seu primeiro acesso" if motivo_briefing == "primeiro_acesso" else "já se passou mais de 1 ano desde seu último acesso"
        )
        st.warning(mensagem)

    # Verifica se já existe um registro com o mesmo nome e data
    existing_record = df[(df["Nome"] == name) & (df["Data"] == data_formatada)]

    success = False
    if not existing_record.empty:
        # Atualiza o registro existente
        record_id = existing_record["ID"].iloc[0]
        horario_saida = existing_record["Horário de Saída"].iloc[0] if "Horário de Saída" in existing_record else ""
        updated_data = [
            name, cpf, placa, marca_carro, horario_entrada, 
            horario_saida,  # Mantém o horário de saída existente
            data_formatada, empresa, 
            status, motivo if motivo else "", aprovador if aprovador else "", 
            existing_record["Data do Primeiro Registro"].iloc[0]
        ]
        # A API editar_dados precisa do ID para identificar a linha, mas o ID não faz parte dos dados da linha
        success = sheet_operations.editar_dados(record_id, updated_data)
        if success:
            st.success("Registro atualizado com sucesso!")
    else:
        # Adiciona um novo registro
        existing_visitor_records = df[df["Nome"] == name]

        if existing_visitor_records.empty:
            first_registration_date = data_formatada
        else:
            existing_dates = existing_visitor_records["Data"].dropna()
            if existing_dates.empty:
                first_registration_date = data_formatada
            else:
                try:
                    dates = pd.to_datetime(existing_dates, format="%d/%m/%Y")
                    first_registration_date = min(dates).strftime("%d/%m/%Y")
                except ValueError:
                    first_registration_date = data_formatada

        new_record_list = [
            name, cpf, placa, marca_carro, horario_entrada, "", # Horário de Saída vazio para novo registro
            data_formatada, empresa,
            status, motivo if motivo else "", aprovador if aprovador else "",
            first_registration_date
        ]
        sheet_operations.adc_dados(new_record_list)
        success = True
        st.success("Novo registro adicionado com sucesso!")

    # Forçar atualização dos dados no cache
    if success and "df_acesso_veiculos" in st.session_state:
        del st.session_state.df_acesso_veiculos
        
    return success

def update_exit_time(name, date_saida, new_exit_time):
    sheet_operations = SheetOperations()
    data_from_sheet = sheet_operations.carregar_dados()
    if not data_from_sheet:
        return False, "Não foi possível carregar os dados para atualização."

    columns = data_from_sheet[0]
    df = pd.DataFrame(data_from_sheet[1:], columns=columns)

    # Encontrar todos os registros da pessoa
    person_records = df[df["Nome"] == name].copy()
    
    if person_records.empty:
        return False, "Nenhum registro encontrado para esta pessoa."

    try:
        # Converter as datas dos registros para datetime
        person_records['Data_dt'] = pd.to_datetime(person_records['Data'], format='%d/%m/%Y')
        
        # Filtrar registros sem horário de saída
        open_records = person_records[
            (person_records['Horário de Saída'].isna()) | 
            (person_records['Horário de Saída'] == '')
        ]

        if open_records.empty:
            return False, "Não há registros em aberto para esta pessoa."

        # Converter a data de saída para datetime para comparação
        try:
            data_saida_dt = datetime.strptime(date_saida, "%d/%m/%Y")
        except ValueError:
            return False, "Data de saída em formato inválido."

        # Se houver apenas um registro em aberto, usar ele
        if len(open_records) == 1:
            closest_record = open_records.iloc[0]
        else:
            # Se houver múltiplos registros em aberto, encontrar o registro mais recente antes da data de saída
            open_records = open_records[open_records['Data_dt'] <= data_saida_dt]
            if open_records.empty:
                return False, "Não há registros de entrada anteriores à data de saída informada."
            closest_record = open_records.iloc[-1]  # Pega o registro mais recente

        # Validar se a data de saída não é anterior à data de entrada
        data_entrada_dt = closest_record['Data_dt']
        if data_saida_dt < data_entrada_dt:
            return False, f"A data de saída ({date_saida}) não pode ser anterior à data de entrada ({closest_record['Data']})."

        # Se a saída for no mesmo dia da entrada, validar horários
        if data_saida_dt.date() == data_entrada_dt.date():
            try:
                horario_entrada = datetime.strptime(closest_record['Horário de Entrada'], "%H:%M")
                horario_saida = datetime.strptime(new_exit_time, "%H:%M")
                
                # Criar objetos datetime completos para comparação
                entrada_dt = datetime.combine(data_entrada_dt.date(), horario_entrada.time())
                saida_dt = datetime.combine(data_saida_dt.date(), horario_saida.time())
                
                if saida_dt < entrada_dt:
                    return False, "O horário de saída não pode ser anterior ao horário de entrada no mesmo dia."
            except ValueError as e:
                return False, f"Erro ao processar horários: {str(e)}"
            
            # Atualizar o horário de saída
            record_id = closest_record['ID']
            updated_data = [
                closest_record['Nome'],
                closest_record['CPF'],
                closest_record['Placa'],
                closest_record['Marca do Carro'],
                closest_record['Horário de Entrada'],
                new_exit_time,
                closest_record['Data'],
                closest_record['Empresa'],
                closest_record['Status da Entrada'],
                closest_record.get('Motivo do Bloqueio', ''),
                closest_record.get('Aprovador', ''),
                closest_record.get('Data do Primeiro Registro', closest_record['Data'])
            ]
            
            success = sheet_operations.editar_dados(record_id, updated_data)
        else:
            # Se a saída for em dia diferente:
            # 1. Fecha o registro original com saída às 23:59
            record_id = closest_record['ID']
            updated_data = [
                closest_record['Nome'],
                closest_record['CPF'],
                closest_record['Placa'],
                closest_record['Marca do Carro'],
                closest_record['Horário de Entrada'],
                "23:59",
                closest_record['Data'],
                closest_record['Empresa'],
                closest_record['Status da Entrada'],
                closest_record.get('Motivo do Bloqueio', ''),
                closest_record.get('Aprovador', ''),
                closest_record.get('Data do Primeiro Registro', closest_record['Data'])
            ]
            
            success1 = sheet_operations.editar_dados(record_id, updated_data)
            
            # 2. Cria registros intermediários para os dias entre entrada e saída
            current_date = data_entrada_dt + timedelta(days=1)
            while current_date.date() <= data_saida_dt.date():
                # Se for o último dia (dia da saída), usa o horário de saída informado
                horario_saida = new_exit_time if current_date.date() == data_saida_dt.date() else "23:59"
                
                new_record = [
                    closest_record['Nome'],
                    closest_record['CPF'],
                    closest_record['Placa'],
                    closest_record['Marca do Carro'],
                    "00:00",
                    horario_saida,
                    current_date.strftime("%d/%m/%Y"),
                    closest_record['Empresa'],
                    closest_record['Status da Entrada'],
                    closest_record.get('Motivo do Bloqueio', ''),
                    closest_record.get('Aprovador', ''),
                    closest_record.get('Data do Primeiro Registro', closest_record['Data'])
                ]
                
                sheet_operations.adc_dados(new_record)
                current_date += timedelta(days=1)
                
            success = success1

        if success:
            return True, f"Registros de saída atualizados com sucesso para o período de {closest_record['Data']} até {date_saida}."
        else:
            return False, "Erro ao atualizar os registros de saída."
            
    except Exception as e:
        return False, f"Erro ao processar atualização: {str(e)}"


def delete_record(name, data):
    sheet_operations = SheetOperations()
    data_from_sheet = sheet_operations.carregar_dados()
    if not data_from_sheet:
        st.error("Não foi possível carregar os dados para exclusão.")
        return False

    columns = data_from_sheet[0]
    df = pd.DataFrame(data_from_sheet[1:], columns=columns)

    name_lower = name.lower()
    df['Nome_lower'] = df['Nome'].str.lower()

    record_to_delete = df[((df['Nome_lower'] == name_lower) & (df['Data'] == data))]
    
    if not record_to_delete.empty:
        record_id = record_to_delete["ID"].iloc[0]
        success = sheet_operations.excluir_dados(record_id)
        if success:
            return True
        else:
            st.error("Erro ao excluir registro no Google Sheets.")
            return False
    else:
        st.warning("Registro não encontrado para exclusão.")
        return False


def check_entry(name, data):
    sheet_operations = SheetOperations()
    data_from_sheet = sheet_operations.carregar_dados()
    if not data_from_sheet:
        return None, "Não foi possível carregar os dados para verificação."

    columns = data_from_sheet[0]
    df = pd.DataFrame(data_from_sheet[1:], columns=columns)

    name_lower = name.lower()
    df['Nome_lower'] = df['Nome'].str.lower()

    if data:
        person = df[(df['Nome_lower'] == name_lower) & (df['Data'] == data)]
    else:
        person = df[df['Nome_lower'] == name_lower]
    
    if not person.empty:
        return person.iloc[0], "Registro encontrado."
    else:
        return None, "Nome e/ou data não encontrados."


    

def check_blocked_records(df):
    """
    Verifica se há registros Bloqueadas e aplica a lógica de liberação recente.
    """
    # Filtra os registros Bloqueadas
    blocked_records = df[df['Status da Entrada'] == 'Bloqueado']

    # Obtém a data mais recente de liberação para cada nome
    recent_release_dates = df[df['Status da Entrada'] == 'Autorizado'].groupby('Nome')['Data'].max()

    def should_show_block(record):
        name = record['Nome']
        block_date = datetime.strptime(record['Data'], '%d/%m/%Y')
        recent_release_date = recent_release_dates.get(name)
        
        if recent_release_date:
            recent_release_date = datetime.strptime(recent_release_date, '%d/%m/%Y')
            return block_date > recent_release_date
        return True

    # Gera a informação de bloqueios que devem ser mostrados
    blocked_info = "\n".join([
        f"Nome: {row['Nome']}, Data: {row['Data']}, Placa: {row['Placa']}, Motivo: {row['Motivo do Bloqueio']}"
        for _, row in blocked_records.iterrows()
        if should_show_block(row)
    ])

    return blocked_info if blocked_info else None


def get_block_info(df, name):
    """
    Obtém o número de bloqueios e os motivos de bloqueio para uma pessoa específica.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados dos registros.
        name (str): Nome da pessoa para consultar.

    Returns:
        tuple: Contém o número de bloqueios e uma lista de motivos.
    """
    person_records = df[df["Nome"] == name]
    blocked_records = person_records[person_records["Status da Entrada"] == "Bloqueado"]
    num_blocks = len(blocked_records)
    reasons = blocked_records["Motivo do Bloqueio"].dropna().unique()
    
    return num_blocks, reasons


#-------------------------------------- Fase de teste ---------------------


def mouth_consult(): # Consulta por mês as entradas de uma pessoa especifica
    with st.expander("Consultar Registro por Nome e Mês", expanded=False):
        unique_names = st.session_state.df_acesso_veiculos["Nome"].unique()
        name_to_check_month = st.selectbox("Nome para consulta por mês:", options=unique_names)
        month_to_check = st.date_input("Mês e ano para consulta:", value=datetime.now())

        if st.button("Verificar Registros do Mês"):
            if name_to_check_month and month_to_check:
                start_date = pd.Timestamp(month_to_check.replace(day=1))
                end_date = (start_date + pd.DateOffset(months=1)) - pd.DateOffset(days=1)
                
                mask = (
                    (st.session_state.df_acesso_veiculos["Nome"] == name_to_check_month) &
                    (pd.to_datetime(st.session_state.df_acesso_veiculos["Data"], format="%d/%m/%Y") >= start_date) &
                    (pd.to_datetime(st.session_state.df_acesso_veiculos["Data"], format="%d/%m/%Y") <= end_date)
                )
                filtered_df = st.session_state.df_acesso_veiculos[mask]
                
                if not filtered_df.empty:
                    # Set the locale for time formatting
                    try:
                        locale.setlocale(locale.LC_TIME, '') # Use default system locale
                    except locale.Error:
                        st.warning("Could not set locale for time formatting. Using default.")
                    st.write(f"Registros de {name_to_check_month} para o mês de {month_to_check.strftime('%B %Y')}:")
                    st.dataframe(filtered_df.drop(columns=["CPF"], errors='ignore'))
                else:
                    st.warning(f"Nenhum registro encontrado para {name_to_check_month} no mês de {month_to_check.strftime('%B %Y')}.")
            else:
                st.warning("Por favor, selecione o nome e o mês para consulta.")



















