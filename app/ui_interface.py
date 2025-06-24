import streamlit as st
import pandas as pd
from datetime import datetime
from app.data_operations import add_record, update_exit_time, delete_record, check_entry, check_blocked_records
from app.operations import SheetOperations
from app.utils import generate_time_options, format_cpf, validate_cpf, round_to_nearest_interval, get_sao_paulo_time

def vehicle_access_interface():
    st.title("Controle de Acesso BAERI")
    
    sheet_operations = SheetOperations()
    aprovadores_autorizados = sheet_operations.carregar_dados_aprovadores()
    
    # BRIEFING DE SEGURANÇA
    with st.expander('Briefing de segurança', expanded=True):
        st.write("**ATENÇÃO:**\n\n"
                 "1. O acesso de veículos deve ser controlado rigorosamente para garantir a segurança do local.\n"
                 "2. Apenas pessoas autorizadas podem liberar o acesso.\n"
                 "3. Em caso de dúvidas, entre em contato com o responsável pela segurança.\n"
                 "4. Mantenha sempre os dados atualizados e verifique as informações antes de liberar o acesso."
                 "\n5. Sempre que for a primeira vez do visitante ou um ano do acesso repassar o video.\n")
        try:
            st.video("https://youtu.be/QqUkeTucwkI")
        except Exception as e:
            st.error(f"Erro ao carregar o vídeo: {e}")

    # Carrega os dados mais recentes para a função 'blocks' e para o estado da sessão
    data_from_sheet = sheet_operations.carregar_dados()
    if data_from_sheet:
        columns = data_from_sheet[0]
        df_current = pd.DataFrame(data_from_sheet[1:], columns=columns)
        
        # Função para exibir bloqueios ativos
        blocked_info = check_blocked_records(df_current)
        if blocked_info:
            st.error("Atenção! Pessoas com bloqueio ativo:\n\n" + blocked_info)
        
        df_current = df_current.fillna("")
        df_current['Data_Ordenacao'] = pd.to_datetime(df_current['Data'], format='%d/%m/%Y', errors='coerce')
        df_current = df_current.sort_values(by=['Data_Ordenacao', 'Horário de Entrada'], ascending=[False, False])
        df_current = df_current.drop('Data_Ordenacao', axis=1)
        st.session_state.df_acesso_veiculos = df_current
    else:
        st.session_state.df_acesso_veiculos = pd.DataFrame(columns=[
            "Nome", "CPF", "Placa", "Marca do Carro", "Horário de Entrada", "Horário de Saída", 
            "Data", "Empresa", "Status da Entrada", "Motivo do Bloqueio", "Aprovador", "Data do Primeiro Registro"
        ])

    df = st.session_state.df_acesso_veiculos
    unique_names = list(df["Nome"].unique()) if "Nome" in df.columns else []

    # --- Adicionar ou editar registro ---
    with st.expander("Adicionar ou Editar Registro", expanded=True):
        name_to_add_or_edit = st.selectbox("Selecionar Nome para Adicionar ou Editar:", options=["Novo Registro"] + unique_names)
        
        now_sp = get_sao_paulo_time()
        horario_options = generate_time_options()

        if name_to_add_or_edit == "Novo Registro":
            # --- Campos para adicionar novo registro ---
            name = st.text_input("Nome:", key="new_name")
            cpf = st.text_input("CPF:", key="new_cpf")
            if cpf and not validate_cpf(cpf): st.error("CPF inválido!")
            
            com_veiculo = st.checkbox("Entrada com veículo", key="new_vehicle_check")
            placa = st.text_input("Placa do Carro:", key="new_plate") if com_veiculo else ""
            marca_carro = st.text_input("Marca do Carro:", key="new_brand") if com_veiculo else ""
            
            data = st.date_input("Data:", value=now_sp, key="new_date")
            horario_atual_str = now_sp.strftime("%H:%M")
            horario_index = horario_options.index(round_to_nearest_interval(horario_atual_str))
            horario_entrada = st.selectbox("Horário de Entrada:", options=horario_options, index=horario_index, key="new_entry_time")
            
            empresa = st.text_input("Empresa:", key="new_company")
            status = st.selectbox("Status de Entrada", ["Autorizado", "Bloqueado"], index=0, key="new_status")
            motivo = st.text_input("Motivo do Bloqueio", key="new_reason") if status == "Bloqueado" else ""
            aprovador = st.selectbox("Aprovador:", options=aprovadores_autorizados, key="new_approver") if status == "Autorizado" else ""

            if status == "Bloqueado":
                st.warning("A liberação só pode ser feita por profissional da área responsável ou Gestor da UO.")

            if st.button("Adicionar Registro"):
                if name and cpf and validate_cpf(cpf) and empresa:
                    data_formatada = data.strftime("%d/%m/%Y")
                    success = add_record(name, format_cpf(cpf), placa, marca_carro, horario_entrada, data_formatada, empresa, status, motivo, aprovador)
                    if success:
                        st.success("Registro adicionado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Falha ao adicionar registro.")
                else:
                    st.warning("Por favor, preencha todos os campos obrigatórios com dados válidos.")
        else:
            # --- Campos para editar registro existente ---
            existing_record = df[df["Nome"] == name_to_add_or_edit].iloc[0]
            
            st.info(f"Editando registro de {name_to_add_or_edit}\n- Entrada: {existing_record['Data']} às {existing_record['Horário de Entrada']}")
            
            # ** CORREÇÃO DO ERRO DE TIMESTAMP **
            # Converte os valores para string ANTES de passá-los para os widgets
            cpf_value = str(existing_record.get("CPF", ""))
            placa_value = str(existing_record.get("Placa", ""))
            marca_value = str(existing_record.get("Marca do Carro", ""))
            empresa_value = str(existing_record.get("Empresa", ""))
            status_value = str(existing_record.get("Status da Entrada", "Autorizado"))
            motivo_value = str(existing_record.get("Motivo do Bloqueio", ""))
            aprovador_value = str(existing_record.get("Aprovador", ""))
            horario_entrada_value = str(existing_record.get("Horário de Entrada", ""))

            cpf = st.text_input("CPF:", value=format_cpf(cpf_value), key="edit_cpf")
            if cpf and not validate_cpf(cpf): st.error("CPF inválido! Por favor, insira um CPF válido.")
            
            tem_veiculo = bool(placa_value or marca_value)
            com_veiculo = st.checkbox("Entrada com veículo", value=tem_veiculo, key="edit_vehicle_check")
            placa = st.text_input("Placa do Carro:", value=placa_value, key="edit_plate") if com_veiculo else ""
            marca_carro = st.text_input("Marca do Carro:", value=marca_value, key="edit_brand") if com_veiculo else ""
            
            data = st.date_input("Data:", value=datetime.strptime(existing_record["Data"], "%d/%m/%Y"), key="edit_date")
            
            horario_index = horario_options.index(round_to_nearest_interval(horario_entrada_value))
            horario_entrada = st.selectbox("Horário de Entrada:", options=horario_options, index=horario_index, key="edit_entry_time")
            empresa = st.text_input("Empresa:", value=empresa_value, key="edit_company")
            
            status_options = ["Autorizado", "Bloqueado"]
            status = st.selectbox("Status de Entrada", status_options, index=status_options.index(status_value) if status_value in status_options else 0, key="edit_status")
            motivo = st.text_input("Motivo do Bloqueio", value=motivo_value, key="edit_reason") if status == "Bloqueado" else ""
            
            if status == "Autorizado":
                if aprovador_value and aprovador_value not in aprovadores_autorizados:
                    aprovadores_autorizados.insert(0, aprovador_value)
                aprovador = st.selectbox("Aprovador:", options=aprovadores_autorizados, index=aprovadores_autorizados.index(aprovador_value) if aprovador_value in aprovadores_autorizados else 0, key="edit_approver")
            else:
                aprovador = ""

            if st.button("Atualizar Registro"):
                data_formatada = data.strftime("%d/%m/%Y")
                # Ao pressionar o botão, os valores já são strings e não causarão erro
                success = add_record(name_to_add_or_edit, format_cpf(cpf), placa, marca_carro, horario_entrada, data_formatada, empresa, status, motivo, aprovador)
                if success:
                    st.success("Registro atualizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Falha ao atualizar registro.")

    # --- Atualizar horário de saída ---
    with st.expander("Atualizar Horário de Saída", expanded=False):
        name_to_update = st.selectbox("Nome do registro para atualizar horário de saída:", options=unique_names, index=None, key="update_exit_name")
        if name_to_update:
            person_records = df[(df["Nome"] == name_to_update) & (df["Horário de Saída"] == "")]
            if not person_records.empty:
                st.write("Registros em aberto para esta pessoa:")
                st.dataframe(person_records, hide_index=True)
            else:
                st.warning("Não há registros em aberto para esta pessoa.")

        data_to_update = st.date_input("Data da Saída:", value=now_sp, key="data_saida")
        horario_saida_str = now_sp.strftime("%H:%M")
        horario_saida_index = horario_options.index(round_to_nearest_interval(horario_saida_str))
        horario_saida = st.selectbox("Horário de Saída:", options=horario_options, index=horario_saida_index, key="horario_saida")

        if st.button("Atualizar Horário de Saída"):
            if name_to_update:
                data_formatada = data_to_update.strftime("%d/%m/%Y")
                success, message = update_exit_time(name_to_update, data_formatada, horario_saida)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.warning("Por favor, selecione o nome para atualizar.")
    
    # --- Deletar registro ---
    with st.expander("Deletar Registro", expanded=False):
        name_to_delete = st.selectbox("Nome do registro a ser deletado:", options=unique_names, index=None, key="name_del")
        if name_to_delete:
            registros_pessoa = df[df['Nome'] == name_to_delete]
            datas_disponiveis = registros_pessoa['Data'].unique()
            data_to_delete_str = st.selectbox("Selecione a data do registro a deletar:", options=datas_disponiveis, key="date_del")
            if st.button("Deletar Registro"):
                if delete_record(name_to_delete, data_to_delete_str):
                    st.success("Registro deletado com sucesso!")
                    st.rerun()
                else:
                    st.error("Falha ao deletar registro.")

    # --- Consultar por Nome ---
    with st.expander("Consultar Registro por Nome", expanded=False):
        name_to_check = st.selectbox("Nome para consulta:", options=unique_names, index=None, key="name_check")
        if st.button("Verificar Registro", key="btn_check"):
            if name_to_check:
                registros_pessoa = df[df['Nome'] == name_to_check]
                if not registros_pessoa.empty:
                    st.dataframe(registros_pessoa, hide_index=True)
                else:
                    st.warning("Nenhum registro encontrado.")
            else:
                st.warning("Por favor, selecione um nome.")

    # --- Tabela Geral ---
    st.dataframe(df.fillna(""), use_container_width=True, hide_index=True)










