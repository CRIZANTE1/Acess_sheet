import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from app.data_operations import add_record, update_exit_time, delete_record, check_entry, check_blocked_records, get_block_info
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

def round_to_nearest_interval(time_value, interval=1):
    """Arredonda o horário para o intervalo mais próximo"""
    if pd.isna(time_value) or time_value == "":
        return "00:00"  # Valor padrão para NaN ou string vazia
    
    if isinstance(time_value, (int, float)):
        hours = int(time_value // 60)
        minutes = int(time_value % 60)
        time_str = f"{hours:02d}:{minutes:02d}"
    else:
        time_str = str(time_value)
    
    # Verificar se o valor está no formato esperado
    try:
        time = datetime.strptime(time_str, "%H:%M")
    except ValueError:
        return "00:00"  # Valor padrão se o formato estiver incorreto
    
    minutes = (time.hour * 60 + time.minute) // interval * interval
    rounded_time = datetime.strptime(f"{minutes // 60:02d}:{minutes % 60:02d}", "%H:%M")
    return rounded_time.strftime("%H:%M")

def vehicle_access_interface():
    st.title("Controle de Acesso BAERI")
    
    # BRIEFING DE SEGURANGA
    with st.expander('Briefing de segurança', expanded=True):
        st.write("**ATENÇÃO:**\n\n"
                 "1. O acesso de veículos deve ser controlado rigorosamente para garantir a segurança do local.\n"
                 "2. Apenas pessoas autorizadas podem liberar o acesso.\n"
                 "3. Em caso de dúvidas, entre em contato com o responsável pela segurança.\n"
                 "4. Mantenha sempre os dados atualizados e verifique as informações antes de liberar o acesso."
                 "\n5. Sempre que for a primeira vez do visitante ou um ano do acesso repassar o video.\n")
        try: # Adicionar vídeo
            st.video("https://youtu.be/QqUkeTucwkI")
        except Exception as e:
            st.error(f"Erro ao carregar o vídeo: {e}")

    blocks()
    
    # Recarregar os dados do Google Sheets para garantir que estão atualizados
    sheet_operations = SheetOperations()
    data_from_sheet = sheet_operations.carregar_dados()
    if data_from_sheet:
        # Use the actual headers from the sheet
        columns = data_from_sheet[0]
        df_temp = pd.DataFrame(data_from_sheet[1:], columns=columns)
        # Rename 'RG' to 'RG/CPF' if 'RG' exists and handle empty values
        if 'RG' in df_temp.columns and 'RG/CPF' not in df_temp.columns:
            df_temp.rename(columns={'RG': 'RG/CPF'}, inplace=True)
        
        # Garantir que valores nulos ou vazios sejam tratados corretamente
        df_temp = df_temp.fillna("")
        st.session_state.df_acesso_veiculos = df_temp
    else:
        st.session_state.df_acesso_veiculos = pd.DataFrame(columns=[
            "Nome", "RG/CPF", "Placa", "Marca do Carro", "Horário de Entrada",
            "Horário de Saída", "Data", "Empresa", "Status da Entrada", "Motivo do Bloqueio", "Aprovador", "Data do Primeiro Registro"
        ])

    # Adicionar ou editar registro
    with st.expander("Adicionar ou Editar Registro", expanded=True):
        unique_names = st.session_state.df_acesso_veiculos["Nome"].unique()
        name_to_add_or_edit = st.selectbox("Selecionar Nome para Adicionar ou Editar:", options=["Novo Registro"] + list(unique_names))
        
        horario_options = generate_time_options()
        default_horario = round_to_nearest_interval(datetime.now().strftime("%H:%M"))

        if name_to_add_or_edit == "Novo Registro":
            # Campos para adicionar novo registro
            name = st.text_input("Nome:")
            rg = st.text_input("RG/CPF:")
            placa = st.text_input("Placa do Carro (opcional):")
            marca_carro = st.text_input("Marca do Carro (opcional):")
            data = st.date_input("Data:")
            horario_entrada = st.selectbox("Horário de Entrada:", options=horario_options, index=horario_options.index(default_horario))
            empresa = st.text_input("Empresa:")
            status = st.selectbox("Status de Entrada", ["Autorizado", "Bloqueado"], index=0)
            motivo = st.text_input("Motivo do Bloqueio") if status == "Bloqueado" else ""
            aprovador = st.text_input("Aprovador") if status == "Autorizado" else ""

            if status == "Bloqueado":
                st.warning("A liberação só pode ser feita por profissional da área responsável ou Gestor da UO.")

            if st.button("Adicionar Registro"):
                if name and rg and horario_entrada and data and empresa:
                    data_obj = datetime.strptime(data.strftime("%Y-%m-%d"), "%Y-%m-%d")
                    data_formatada = data_obj.strftime("%d/%m/%Y")

                    success = add_record(
                        name, rg, placa, marca_carro, 
                        horario_entrada, 
                        data_formatada,
                        empresa, 
                        status, 
                        motivo, 
                        aprovador
                    )
                    if success:
                        st.success("Registro adicionado com sucesso!")
                        # Recarregar dados após a adição
                        st.session_state.df_acesso_veiculos = pd.DataFrame(sheet_operations.carregar_dados()[1:], columns=sheet_operations.carregar_dados()[0])
                        st.rerun()
                    else:
                        st.error("Falha ao adicionar registro.")
                else:
                    st.warning("Por favor, preencha todos os campos obrigatórios: Nome, RG, Horário de Entrada, Data e Empresa.")
        else:
            # Campos para editar registro existente
            existing_record = st.session_state.df_acesso_veiculos[st.session_state.df_acesso_veiculos["Nome"] == name_to_add_or_edit].iloc[0]
            
            # Garantir que o RG/CPF seja preenchido mesmo se for nulo
            rg_cpf_value = existing_record.get("RG/CPF", "")
            if pd.isna(rg_cpf_value):
                rg_cpf_value = ""
            rg = st.text_input("RG/CPF:", value=str(rg_cpf_value))
            
            placa = st.text_input("Placa do Carro (opcional):", value=existing_record["Placa"])
            marca_carro = st.text_input("Marca do Carro (opcional):", value=existing_record["Marca do Carro"])
            
            # Tratar a data para evitar ValueError
            try:
                data_value = datetime.strptime(existing_record["Data"], "%d/%m/%Y")
            except (ValueError, TypeError):
                data_value = datetime.now().date() # Valor padrão se a data for inválida ou vazia
            data = st.date_input("Data:", value=data_value)
            
            horario_entrada_value = existing_record["Horário de Entrada"]
            rounded_horario = round_to_nearest_interval(str(horario_entrada_value) if horario_entrada_value is not None else "")
            horario_entrada_index = horario_options.index(rounded_horario) if rounded_horario in horario_options else 0

            horario_entrada = st.selectbox(
                "Horário de Entrada:",
                options=horario_options,
                index=horario_entrada_index
            )
            empresa = st.text_input("Empresa:", value=existing_record["Empresa"])

            status_options = ["Autorizado", "Bloqueado"]
            status_value = existing_record["Status da Entrada"]
            if pd.isna(status_value) or status_value not in status_options:
                status_value = status_options[0]

            status = st.selectbox(
                "Status de Entrada",
                status_options,
                index=status_options.index(status_value)
            )
            motivo = st.text_input("Motivo do Bloqueio", value=existing_record["Motivo do Bloqueio"]) if status == "Bloqueado" else ""
            aprovador = st.text_input("Aprovador", value=existing_record["Aprovador"]) if status == "Autorizado" else ""

            if status == "Bloqueado":
                st.warning("A liberação só pode ser feita por profissional da área responsável ou Gestor da UO.")

            if st.button("Atualizar Registro"):
                if rg and horario_entrada and data and empresa:
                    data_obj = datetime.strptime(data.strftime("%Y-%m-%d"), "%Y-%m-%d")
                    data_formatada = data_obj.strftime("%d/%m/%Y")

                    success = add_record( # add_record agora também lida com a edição
                        name_to_add_or_edit, 
                        rg, 
                        placa, 
                        marca_carro, 
                        horario_entrada, 
                        data_formatada,
                        empresa, 
                        status, 
                        motivo, 
                        aprovador
                    )
                    if success:
                        st.success("Registro atualizado com sucesso!")
                        # Recarregar dados após a atualização
                        st.session_state.df_acesso_veiculos = pd.DataFrame(sheet_operations.carregar_dados()[1:], columns=sheet_operations.carregar_dados()[0])
                        st.rerun()
                    else:
                        st.error("Falha ao atualizar registro.")
                else:
                    st.warning("Por favor, preencha todos os campos obrigatórios: RG, Horário de Entrada, Data e Empresa.")
                
    # Atualizar horário de saída
    with st.expander("Atualizar Horário de Saída", expanded=False):
        unique_names = st.session_state.df_acesso_veiculos["Nome"].unique()
        name_to_update = st.selectbox("Nome do registro para atualizar horário de saída:", options=unique_names)
        data_to_update = st.date_input("Data do registro para atualizar horário de saída:", key="data_saida")
        horario_saida_options = generate_time_options()
        default_horario_saida = round_to_nearest_interval(datetime.now().strftime("%H:%M"))
        horario_saida = st.selectbox("Novo Horário de Saída (HH:MM):", options=horario_saida_options, index=horario_saida_options.index(default_horario_saida), key="horario_saida")

        if st.button("Atualizar Horário de Saída"):
            if name_to_update and data_to_update and horario_saida:
                data_to_update = datetime.strptime(data_to_update.strftime("%Y-%m-%d"), "%Y-%m-%d")
                success, message = update_exit_time(
                    name_to_update, 
                    data_to_update.strftime("%d/%m/%Y"), 
                    horario_saida
                )
                if success:
                    st.success(message)
                    # Recarregar dados após a atualização
                    st.session_state.df_acesso_veiculos = pd.DataFrame(sheet_operations.carregar_dados()[1:], columns=sheet_operations.carregar_dados()[0])
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.warning("Por favor, selecione o nome, a data e o novo horário de saída.")
                
    # Deletar registro
    with st.expander("Deletar Registro", expanded=False):
        unique_names = st.session_state.df_acesso_veiculos["Nome"].unique()
        name_to_delete = st.selectbox("Nome do registro a ser deletado:", options=unique_names)
        data_to_delete = st.date_input("Data do registro a ser deletado:", key="data_delete")

        if st.button("Deletar Registro"):
            if name_to_delete and data_to_delete:
                data_to_delete = datetime.strptime(data_to_delete.strftime("%Y-%m-%d"), "%Y-%m-%d")
                success = delete_record(
                    name_to_delete, 
                    data_to_delete.strftime("%d/%m/%Y")
                )
                if success:
                    st.success("Registro deletado com sucesso!")
                    # Recarregar dados após a exclusão
                    st.session_state.df_acesso_veiculos = pd.DataFrame(sheet_operations.carregar_dados()[1:], columns=sheet_operations.carregar_dados()[0])
                    st.rerun()
                else:
                    st.error("Falha ao deletar registro.")
            else:
                st.warning("Por favor, selecione o nome e a data do registro a ser deletado.")
    
    # Consultar por Nome
    with st.expander("Consultar Registro por Nome", expanded=False):
        unique_names = st.session_state.df_acesso_veiculos["Nome"].unique()
        name_to_check = st.selectbox("Nome para consulta:", options=unique_names)

        if st.button("Verificar Registro"):
            if name_to_check:
                person, status = check_entry(name_to_check, None)
                if person is not None:
                    st.write(f"Nome: {person['Nome']}")
                    st.write(f"Placa: {person['Placa']}")
                    st.write(f"Marca do Carro: {person['Marca do Carro']}")
                    st.write(f"Horário de Entrada: {person['Horário de Entrada']}")
                    st.write(f"Horário de Saída: {person['Horário de Saída']}")
                    st.write(f"Empresa: {person['Empresa']}")
                    st.write(f"Status de Entrada: {person['Status da Entrada']}")

                    if person['Status da Entrada'] == 'Bloqueada':
                        st.write(f"Motivo do Bloqueio: {person['Motivo do Bloqueio']}")
                        st.write(f"Aprovador do Bloqueio: {person['Aprovador']}")
                    else:
                        st.write(f"Aprovador da Entrada: {person['Aprovador']}")
                else:
                    st.warning(status)
            else:
                st.warning("Por favor, insira o nome.")
    
    # Consulta Geral de Pessoas Autorizadas e Bloqueadas
    with st.expander("Consulta Geral de Pessoas Autorizadas e Bloqueadas", expanded=False):
        status_filter = st.selectbox("Selecione o Status para Consulta:", ["Todos", "Autorizada", "Bloqueada"])
        empresa_filter = st.selectbox("Selecione a Empresa para Consulta:", ["Todas"] + list(st.session_state.df_acesso_veiculos["Empresa"].unique()))

        if st.button("Consultar"):
            if status_filter == "Todos":
                df_filtered = st.session_state.df_acesso_veiculos
            else:
                df_filtered = st.session_state.df_acesso_veiculos[st.session_state.df_acesso_veiculos["Status da Entrada"] == status_filter]
            
            if empresa_filter != "Todas":
                df_filtered = df_filtered[df_filtered["Empresa"] == empresa_filter]
            
            columns_to_display = ["Nome", "Placa", "Marca do Carro", "Empresa", "Status da Entrada", "Motivo do Bloqueio", "Aprovador"]
            df_filtered = df_filtered[columns_to_display]
            
            if not df_filtered.empty:
                st.write(f"Registros de Pessoas {status_filter}as na empresa {empresa_filter}:")
                st.dataframe(df_filtered)
            else:
                st.warning(f"Não há registros encontrados para o status {status_filter} e empresa {empresa_filter}.")
         
    df = st.data_editor(st.session_state.df_acesso_veiculos.fillna(""), num_rows="dynamic")
    st.session_state.df_acesso_veiculos = df

def blocks():
    sheet_operations = SheetOperations()
    data_from_sheet = sheet_operations.carregar_dados()
    if data_from_sheet:
        columns = data_from_sheet[0]
        df_current = pd.DataFrame(data_from_sheet[1:], columns=columns)
        if 'RG' in df_current.columns and 'RG/CPF' not in df_current.columns:
            df_current.rename(columns={'RG': 'RG/CPF'}, inplace=True)
    else:
        df_current = pd.DataFrame(columns=[
            "Nome", "RG/CPF", "Placa", "Marca do Carro", "Horário de Entrada", 
            "Horário de Saída", "Data", "Empresa", "Status da Entrada", "Motivo do Bloqueio", "Aprovador", "Data do Primeiro Registro"
        ])

    blocked_info = check_blocked_records(df_current)
    
    if blocked_info:
        st.error("Registros Bloqueados:\n" + blocked_info)
    else:
        st.empty()













