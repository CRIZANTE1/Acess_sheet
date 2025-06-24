import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from app.data_operations import add_record, update_exit_time, delete_record, check_entry, check_blocked_records, get_block_info
from app.operations import SheetOperations
from app.utils import generate_time_options, format_cpf, validate_cpf, test_cpf, round_to_nearest_interval

def vehicle_access_interface():
    st.title("Controle de Acesso BAERI")
    
    # Carregar aprovadores autorizados
    sheet_operations = SheetOperations()
    aprovadores_autorizados = sheet_operations.carregar_dados_aprovadores()
    
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
    data_from_sheet = sheet_operations.carregar_dados()
    if data_from_sheet:
        # Use the actual headers from the sheet
        columns = data_from_sheet[0]
        df_temp = pd.DataFrame(data_from_sheet[1:], columns=columns)
        
        # Garantir que valores nulos ou vazios sejam tratados corretamente
        df_temp = df_temp.fillna("")
        
        # Converter a coluna de data para datetime para ordenação correta
        df_temp['Data_Ordenacao'] = pd.to_datetime(df_temp['Data'], format='%d/%m/%Y', errors='coerce')
        
        # Ordenar por data (mais recente primeiro) e horário de entrada
        df_temp = df_temp.sort_values(by=['Data_Ordenacao', 'Horário de Entrada'], ascending=[False, False])
        
        # Remover a coluna auxiliar de ordenação
        df_temp = df_temp.drop('Data_Ordenacao', axis=1)
        
        st.session_state.df_acesso_veiculos = df_temp
    else:
        st.session_state.df_acesso_veiculos = pd.DataFrame(columns=[
            "Nome", "CPF", "Placa", "Marca do Carro", "Horário de Entrada",
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
            cpf = st.text_input("CPF:")
            
            # Validação do CPF
            if cpf:
                if not validate_cpf(cpf):
                    st.error("CPF inválido! O CPF deve ter 11 dígitos.")
                else:
                    cpf = format_cpf(cpf)
            
            # Adicionar checkbox para controle de veículo
            com_veiculo = st.checkbox("Entrada com veículo")
            
            # Campos de veículo só aparecem se a checkbox estiver marcada
            if com_veiculo:
                placa = st.text_input("Placa do Carro:")
                marca_carro = st.text_input("Marca do Carro:")
            else:
                placa = ""
                marca_carro = ""
            
            data = st.date_input("Data:")
            # Definir horário atual como padrão
            horario_atual = datetime.now().strftime("%H:%M")
            horario_index = horario_options.index(round_to_nearest_interval(horario_atual)) if round_to_nearest_interval(horario_atual) in horario_options else 0
            horario_entrada = st.selectbox("Horário de Entrada:", options=horario_options, index=horario_index)
            empresa = st.text_input("Empresa:")
            status = st.selectbox("Status de Entrada", ["Autorizado", "Bloqueado"], index=0)
            motivo = st.text_input("Motivo do Bloqueio") if status == "Bloqueado" else ""
            
            # Usar selectbox para aprovadores
            if status == "Autorizado":
                if aprovadores_autorizados:
                    aprovador = st.selectbox("Aprovador:", options=aprovadores_autorizados)
                else:
                    st.error("Não foram encontrados aprovadores autorizados. Por favor, verifique a planilha.")
                    aprovador = ""
            else:
                aprovador = ""

            if status == "Bloqueado":
                st.warning("A liberação só pode ser feita por profissional da área responsável ou Gestor da UO.")

            if st.button("Adicionar Registro"):
                if name and cpf and validate_cpf(cpf) and horario_entrada and data and empresa:
                    if status == "Autorizado" and not aprovador:
                        st.error("Por favor, selecione um aprovador autorizado.")
                        return
                        
                    data_obj = datetime.strptime(data.strftime("%Y-%m-%d"), "%Y-%m-%d")
                    data_formatada = data_obj.strftime("%d/%m/%Y")

                    success = add_record(
                        name, cpf, placa, marca_carro, 
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
                    st.warning("Por favor, preencha todos os campos obrigatórios com dados válidos: Nome, CPF, Horário de Entrada, Data e Empresa.")
        else:
            # Campos para editar registro existente
            existing_record = st.session_state.df_acesso_veiculos[st.session_state.df_acesso_veiculos["Nome"] == name_to_add_or_edit].iloc[0]
            
            # Mostrar informações atuais do registro
            st.info(f"""
            Informações atuais do registro:
            - Horário de Entrada: {existing_record['Horário de Entrada']}
            - Horário de Saída: {existing_record['Horário de Saída'] if existing_record['Horário de Saída'] else 'Não registrado'}
            - Data: {existing_record['Data']}
            """)
            
            # Tratamento especial para o campo CPF para preservar números longos
            cpf_value = ""
            if "CPF" in existing_record:
                cpf_value = str(existing_record["CPF"])
                
            # Garantir que o valor seja uma string e remover formatação científica
            if pd.isna(cpf_value) or cpf_value is None or cpf_value == "nan":
                cpf_value = ""
            else:
                try:
                    # Remove formatação existente e aplica nova formatação
                    cpf_value = ''.join(filter(str.isdigit, str(cpf_value)))
                    if len(cpf_value) == 11:
                        cpf_value = format_cpf(cpf_value)
                except (ValueError, TypeError):
                    cpf_value = str(cpf_value).strip()
            
            cpf = st.text_input("CPF:", value=cpf_value)
            
            # Validação do CPF
            if cpf:
                if not validate_cpf(cpf):
                    st.error("CPF inválido! Por favor, insira um CPF válido.")
                else:
                    cpf = format_cpf(cpf)
            
            # Adicionar checkbox para controle de veículo
            tem_veiculo = existing_record["Placa"] != "" or existing_record["Marca do Carro"] != ""
            com_veiculo = st.checkbox("Entrada com veículo", value=tem_veiculo)
            
            # Campos de veículo só aparecem se a checkbox estiver marcada
            if com_veiculo:
                placa = st.text_input("Placa do Carro:", value=existing_record["Placa"])
                marca_carro = st.text_input("Marca do Carro:", value=existing_record["Marca do Carro"])
            else:
                placa = ""
                marca_carro = ""
            
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
            
            # Usar selectbox para aprovadores na edição
            if status == "Autorizado":
                if aprovadores_autorizados:
                    # Se o aprovador atual não está na lista, adicione-o temporariamente
                    current_approver = existing_record["Aprovador"]
                    if current_approver and current_approver not in aprovadores_autorizados:
                        temp_aprovadores = [current_approver] + aprovadores_autorizados
                    else:
                        temp_aprovadores = aprovadores_autorizados
                    
                    aprovador = st.selectbox(
                        "Aprovador:",
                        options=temp_aprovadores,
                        index=0 if current_approver in temp_aprovadores else 0
                    )
                else:
                    st.error("Não foram encontrados aprovadores autorizados. Por favor, verifique a planilha.")
                    aprovador = existing_record["Aprovador"]
            else:
                aprovador = ""

            if status == "Bloqueado":
                st.warning("A liberação só pode ser feita por profissional da área responsável ou Gestor da UO.")

            if st.button("Atualizar Registro"):
                if cpf and validate_cpf(cpf) and horario_entrada and data and empresa:
                    if status == "Autorizado" and not aprovador:
                        st.error("Por favor, selecione um aprovador autorizado.")
                        return
                        
                    data_obj = datetime.strptime(data.strftime("%Y-%m-%d"), "%Y-%m-%d")
                    data_formatada = data_obj.strftime("%d/%m/%Y")

                    success = add_record(
                        name_to_add_or_edit, 
                        cpf, 
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
                    st.warning("Por favor, preencha todos os campos obrigatórios com dados válidos: CPF, Horário de Entrada, Data e Empresa.")
                
    # Atualizar horário de saída
    with st.expander("Atualizar Horário de Saída", expanded=False):
        unique_names = st.session_state.df_acesso_veiculos["Nome"].unique()
        name_to_update = st.selectbox("Nome do registro para atualizar horário de saída:", options=unique_names)

        if name_to_update:
            # Mostrar registros em aberto para a pessoa selecionada
            person_records = st.session_state.df_acesso_veiculos[
                (st.session_state.df_acesso_veiculos["Nome"] == name_to_update) &
                ((st.session_state.df_acesso_veiculos["Horário de Saída"].isna()) | 
                 (st.session_state.df_acesso_veiculos["Horário de Saída"] == ""))
            ]

            if not person_records.empty:
                st.write("Registros em aberto para esta pessoa:")
                for _, record in person_records.iterrows():
                    st.info(f"""
                    Data de Entrada: {record['Data']}
                    Horário de Entrada: {record['Horário de Entrada']}
                    Empresa: {record['Empresa']}
                    Placa: {record['Placa'] if record['Placa'] else 'Não informada'}
                    """)
                
                st.info("""
                **Como registrar a saída:**
                1. Se a pessoa saiu no mesmo dia da entrada, selecione a mesma data e o horário de saída
                2. Se a pessoa saiu em um dia diferente (ex: entrou ontem e saiu hoje):
                   - Selecione a data atual da saída
                   - O sistema irá:
                     * Fechar o registro do dia anterior às 23:59
                     * Criar novos registros para os dias intermediários (00:00 às 23:59)
                     * Registrar a saída final no último dia com o horário informado
                """)
            else:
                st.warning("Não há registros em aberto para esta pessoa.")

        data_to_update = st.date_input("Data da Saída:", key="data_saida", value=datetime.now())
        horario_saida_options = generate_time_options()
        default_horario_saida = round_to_nearest_interval(datetime.now().strftime("%H:%M"))
        horario_saida = st.selectbox("Horário de Saída:", options=horario_saida_options, index=horario_saida_options.index(default_horario_saida), key="horario_saida")

        col1, col2 = st.columns(2)
        with col1:
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
                    st.write(f"CPF: {person['CPF']}")
                    st.write(f"Placa: {person['Placa']}")
                    st.write(f"Marca do Carro: {person['Marca do Carro']}")
                    st.write(f"Horário de Entrada: {person['Horário de Entrada']}")
                    st.write(f"Horário de Saída: {person['Horário de Saída']}")
                    st.write(f"Empresa: {person['Empresa']}")
                    st.write(f"Status de Entrada: {person['Status da Entrada']}")

                    if person['Status da Entrada'] == 'Bloqueado':
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
        status_filter = st.selectbox("Selecione o Status para Consulta:", ["Todos", "Autorizado", "Bloqueado"])
        empresa_filter = st.selectbox("Selecione a Empresa para Consulta:", ["Todas"] + list(st.session_state.df_acesso_veiculos["Empresa"].unique()))

        if st.button("Consultar"):
            if status_filter == "Todos":
                df_filtered = st.session_state.df_acesso_veiculos
            else:
                df_filtered = st.session_state.df_acesso_veiculos[st.session_state.df_acesso_veiculos["Status da Entrada"] == status_filter]
            
            if empresa_filter != "Todas":
                df_filtered = df_filtered[df_filtered["Empresa"] == empresa_filter]
            
            columns_to_display = ["Nome", "CPF", "Placa", "Marca do Carro", "Empresa", "Status da Entrada", "Motivo do Bloqueio", "Aprovador"]
            df_filtered = df_filtered[columns_to_display]
            
            if not df_filtered.empty:
                st.write(f"Registros de Pessoas com status {status_filter} na empresa {empresa_filter}:")
                st.dataframe(df_filtered)
            else:
                st.warning(f"Não há registros encontrados para o status {status_filter} e empresa {empresa_filter}.")
         
    st.dataframe(st.session_state.df_acesso_veiculos.fillna(""))
    

def blocks():
    sheet_operations = SheetOperations()
    data_from_sheet = sheet_operations.carregar_dados()
    if data_from_sheet:
        columns = data_from_sheet[0]
        df_current = pd.DataFrame(data_from_sheet[1:], columns=columns)
    else:
        df_current = pd.DataFrame(columns=[
            "Nome", "CPF", "Placa", "Marca do Carro", "Horário de Entrada", 
            "Horário de Saída", "Data", "Empresa", "Status da Entrada", "Motivo do Bloqueio", "Aprovador", "Data do Primeiro Registro"
        ])

    blocked_info = check_blocked_records(df_current)
    
    if blocked_info:
        st.error("Registros Bloqueados:\n" + blocked_info)
    else:
        st.empty()

























