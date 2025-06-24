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

    with st.expander("Adicionar ou Editar Registro", expanded=True):
        name_to_add_or_edit = st.selectbox("Selecionar Nome para Adicionar ou Editar:", options=["Novo Registro"] + unique_names)
        
        now_sp = get_sao_paulo_time()
        horario_options = generate_time_options()

        if name_to_add_or_edit == "Novo Registro":
            name = st.text_input("Nome:")
            cpf = st.text_input("CPF:")
            if cpf and not validate_cpf(cpf): st.error("CPF inválido!")
            else: cpf = format_cpf(cpf)

            com_veiculo = st.checkbox("Entrada com veículo")
            placa = st.text_input("Placa do Carro:") if com_veiculo else ""
            marca_carro = st.text_input("Marca do Carro:") if com_veiculo else ""
            
            data = st.date_input("Data:", value=now_sp)
            horario_atual_str = now_sp.strftime("%H:%M")
            horario_index = horario_options.index(round_to_nearest_interval(horario_atual_str))
            horario_entrada = st.selectbox("Horário de Entrada:", options=horario_options, index=horario_index)
            
            empresa = st.text_input("Empresa:")
            status = st.selectbox("Status de Entrada", ["Autorizado", "Bloqueado"], index=0)
            motivo = st.text_input("Motivo do Bloqueio") if status == "Bloqueado" else ""
            aprovador = st.selectbox("Aprovador:", options=aprovadores_autorizados) if status == "Autorizado" else ""

            if st.button("Adicionar Registro"):
                if name and cpf and validate_cpf(cpf) and empresa:
                    data_formatada = data.strftime("%d/%m/%Y")
                    if add_record(name, cpf, placa, marca_carro, horario_entrada, data_formatada, empresa, status, motivo, aprovador):
                        st.rerun()
                else:
                    st.warning("Preencha todos os campos obrigatórios com dados válidos.")
        else:
            existing_record = df[df["Nome"] == name_to_add_or_edit].iloc[0]
            
            st.info(f"Editando registro de {name_to_add_or_edit} (Entrada: {existing_record['Data']} às {existing_record['Horário de Entrada']})")
            
            # --- CORREÇÃO DO ERRO DE TIMESTAMP ---
            # Converte os valores para string ANTES de passá-los para os widgets
            cpf_value = str(existing_record.get("CPF", ""))
            placa_value = str(existing_record.get("Placa", ""))
            marca_value = str(existing_record.get("Marca do Carro", ""))
            empresa_value = str(existing_record.get("Empresa", ""))
            status_value = str(existing_record.get("Status da Entrada", "Autorizado"))
            motivo_value = str(existing_record.get("Motivo do Bloqueio", ""))
            aprovador_value = str(existing_record.get("Aprovador", ""))

            cpf = st.text_input("CPF:", value=format_cpf(cpf_value))
            if cpf and not validate_cpf(cpf): st.error("CPF inválido!")
            
            tem_veiculo = placa_value or marca_value
            com_veiculo = st.checkbox("Entrada com veículo", value=tem_veiculo)
            placa = st.text_input("Placa do Carro:", value=placa_value) if com_veiculo else ""
            marca_carro = st.text_input("Marca do Carro:", value=marca_value) if com_veiculo else ""
            
            data_value = datetime.strptime(existing_record["Data"], "%d/%m/%Y")
            data = st.date_input("Data:", value=data_value)
            
            horario_entrada = st.selectbox("Horário de Entrada:", options=horario_options, index=horario_options.index(round_to_nearest_interval(existing_record["Horário de Entrada"])))
            empresa = st.text_input("Empresa:", value=empresa_value)
            
            status_options = ["Autorizado", "Bloqueado"]
            status = st.selectbox("Status de Entrada", status_options, index=status_options.index(status_value) if status_value in status_options else 0)
            motivo = st.text_input("Motivo do Bloqueio", value=motivo_value) if status == "Bloqueado" else ""
            
            if status == "Autorizado":
                if aprovador_value and aprovador_value not in aprovadores_autorizados:
                    aprovadores_autorizados.insert(0, aprovador_value)
                aprovador = st.selectbox("Aprovador:", options=aprovadores_autorizados, index=aprovadores_autorizados.index(aprovador_value) if aprovador_value in aprovadores_autorizados else 0)
            else:
                aprovador = ""

            if st.button("Atualizar Registro"):
                data_formatada = data.strftime("%d/%m/%Y")
                # Ao pressionar o botão, os valores já são strings e não causarão erro
                if add_record(name_to_add_or_edit, format_cpf(cpf), placa, marca_carro, horario_entrada, data_formatada, empresa, status, motivo, aprovador):
                    st.rerun()

    with st.expander("Atualizar Horário de Saída", expanded=False):
        name_to_update = st.selectbox("Nome para atualizar saída:", options=unique_names, index=None)
        if name_to_update:
            person_records = df[(df["Nome"] == name_to_update) & (df["Horário de Saída"] == "")]
            if not person_records.empty:
                st.write("Registros em aberto:")
                st.dataframe(person_records, hide_index=True)
            else:
                st.warning("Não há registros em aberto para esta pessoa.")

            data_saida = st.date_input("Data da Saída:", value=now_sp, key="data_saida")
            horario_saida_str = now_sp.strftime("%H:%M")
            horario_saida_index = horario_options.index(round_to_nearest_interval(horario_saida_str))
            horario_saida = st.selectbox("Horário de Saída:", options=horario_options, index=horario_saida_index, key="horario_saida")

            if st.button("Atualizar Horário de Saída"):
                data_formatada = data_saida.strftime("%d/%m/%Y")
                success, message = update_exit_time(name_to_update, data_formatada, horario_saida)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    with st.expander("Deletar Registro", expanded=False):
        name_to_delete = st.selectbox("Nome do registro a deletar:", options=unique_names, index=None, key="name_del")
        if name_to_delete:
            registros_pessoa = df[df['Nome'] == name_to_delete]
            datas_disponiveis = registros_pessoa['Data'].unique()
            data_to_delete_str = st.selectbox("Data do registro a deletar:", options=datas_disponiveis, key="date_del")
            if st.button("Deletar Registro Selecionado"):
                if delete_record(name_to_delete, data_to_delete_str):
                    st.success("Registro deletado com sucesso!")
                    st.rerun()
                else:
                    st.error("Falha ao deletar registro.")

    with st.expander("Consultar Registro por Nome", expanded=False):
        name_to_check = st.selectbox("Nome para consulta:", options=unique_names, index=None, key="name_check")
        if name_to_check:
            st.dataframe(df[df['Nome'] == name_to_check], hide_index=True)

    st.dataframe(df.fillna(""), use_container_width=True, hide_index=True)

# A função 'blocks' foi integrada no início da 'vehicle_access_interface' para garantir que os dados estejam sempre atualizados.
# Removida daqui para evitar chamadas duplas.











