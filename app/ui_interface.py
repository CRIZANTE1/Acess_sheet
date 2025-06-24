# app/ui_interface.py

import streamlit as st
import pandas as pd
from datetime import datetime
# Importa de data_operations e utils
from app.data_operations import add_record, update_exit_time, delete_record, check_blocked_records, check_entry, get_block_info
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

    # Carrega dados e mostra avisos de bloqueio
    data_from_sheet = sheet_operations.carregar_dados()
    if data_from_sheet:
        columns = data_from_sheet[0]
        df = pd.DataFrame(data_from_sheet[1:], columns=columns)
        
        blocked_info = check_blocked_records(df)
        if blocked_info:
            st.error("Atenção! Pessoas com bloqueio ativo:\n\n" + blocked_info)
        
        df_sorted = df.fillna("").copy()
        df_sorted['Data_Ordenacao'] = pd.to_datetime(df_sorted['Data'], format='%d/%m/%Y', errors='coerce')
        df_sorted = df_sorted.sort_values(by=['Data_Ordenacao', 'Horário de Entrada'], ascending=[False, False])
        st.session_state.df_acesso_veiculos = df_sorted.drop('Data_Ordenacao', axis=1)
    else:
        st.session_state.df_acesso_veiculos = pd.DataFrame()

    df = st.session_state.df_acesso_veiculos
    unique_names = sorted(list(df["Nome"].unique())) if not df.empty else []

    with st.expander("Adicionar ou Editar Registro", expanded=True):
        name_to_add_or_edit = st.selectbox("Selecionar Nome:", options=["Novo Registro"] + unique_names)
        now_sp = get_sao_paulo_time()
        horario_options = generate_time_options()

        if name_to_add_or_edit == "Novo Registro":
            name = st.text_input("Nome:", key="new_name")
            cpf = st.text_input("CPF:", key="new_cpf")
            if cpf and not validate_cpf(cpf): st.error("CPF inválido!")
            
            com_veiculo = st.checkbox("Entrada com veículo", key="new_v_check")
            placa = st.text_input("Placa:", key="new_pl") if com_veiculo else ""
            marca_carro = st.text_input("Marca:", key="new_br") if com_veiculo else ""
            
            data = st.date_input("Data:", value=now_sp, key="new_date")
            horario_entrada = st.selectbox("Horário de Entrada:", options=horario_options, index=horario_options.index(round_to_nearest_interval(now_sp.strftime("%H:%M"))))
            
            empresa = st.text_input("Empresa:", key="new_comp")
            status = st.selectbox("Status:", ["Autorizado", "Bloqueado"], key="new_stat")
            motivo = st.text_input("Motivo:", key="new_mot") if status == "Bloqueado" else ""
            aprovador = st.selectbox("Aprovador:", options=aprovadores_autorizados, key="new_appr") if status == "Autorizado" else ""

            if st.button("Adicionar Registro"):
                if name and cpf and validate_cpf(cpf) and empresa:
                    if add_record(name, format_cpf(cpf), placa, marca_carro, horario_entrada, data.strftime("%d/%m/%Y"), empresa, status, motivo, aprovador):
                        st.success("Registro adicionado!"); st.rerun()
                else:
                    st.warning("Preencha os campos obrigatórios.")
        else:
            record = df[df["Nome"] == name_to_add_or_edit].iloc[0]
            st.info(f"Editando {name_to_add_or_edit} (Entrada: {record['Data']} {record['Horário de Entrada']})")

            # ** CORREÇÃO DO ERRO DE TIMESTAMP **
            cpf_val = str(record.get("CPF", ""))
            placa_val = str(record.get("Placa", ""))
            marca_val = str(record.get("Marca do Carro", ""))
            empresa_val = str(record.get("Empresa", ""))
            status_val = str(record.get("Status da Entrada", "Autorizado"))
            motivo_val = str(record.get("Motivo do Bloqueio", ""))
            aprovador_val = str(record.get("Aprovador", ""))

            cpf = st.text_input("CPF:", value=format_cpf(cpf_val), key="ed_cpf")
            com_veiculo = st.checkbox("Veículo", value=bool(placa_val), key="ed_v_check")
            placa = st.text_input("Placa:", value=placa_val, key="ed_pl") if com_veiculo else ""
            marca_carro = st.text_input("Marca:", value=marca_val, key="ed_br") if com_veiculo else ""
            
            data = st.date_input("Data:", value=datetime.strptime(record["Data"], "%d/%m/%Y"), key="ed_date")
            horario_entrada = st.selectbox("Entrada:", options=horario_options, index=horario_options.index(round_to_nearest_interval(record["Horário de Entrada"])))
            empresa = st.text_input("Empresa:", value=empresa_val, key="ed_comp")
            
            status = st.selectbox("Status:", ["Autorizado", "Bloqueado"], index=0 if status_val == "Autorizado" else 1, key="ed_stat")
            motivo = st.text_input("Motivo:", value=motivo_val, key="ed_mot") if status == "Bloqueado" else ""
            aprovador = st.selectbox("Aprovador:", options=aprovadores_autorizados, index=aprovadores_autorizados.index(aprovador_val) if aprovador_val in aprovadores_autorizados else 0, key="ed_appr") if status == "Autorizado" else ""
            
            if st.button("Atualizar Registro"):
                if add_record(name_to_add_or_edit, format_cpf(cpf), placa, marca_carro, horario_entrada, data.strftime("%d/%m/%Y"), empresa, status, motivo, aprovador):
                    st.success("Registro atualizado!"); st.rerun()

    with st.expander("Atualizar Horário de Saída"):
        name_upd = st.selectbox("Nome para atualizar saída:", options=unique_names, index=None, key="upd_name")
        if name_upd:
            open_rec = df[(df["Nome"] == name_upd) & (df["Horário de Saída"] == "")]
            if not open_rec.empty:
                st.dataframe(open_rec, hide_index=True)
            else:
                st.warning("Não há registros em aberto.")

        data_saida = st.date_input("Data da Saída:", value=now_sp, key="out_date")
        horario_saida = st.selectbox("Horário de Saída:", options=horario_options, index=horario_options.index(round_to_nearest_interval(now_sp.strftime("%H:%M"))), key="out_time")

        if st.button("Atualizar Saída"):
            if name_upd:
                success, msg = update_exit_time(name_upd, data_saida.strftime("%d/%m/%Y"), horario_saida)
                if success: st.success(msg); st.rerun()
                else: st.error(msg)

    with st.expander("Deletar Registro"):
        name_del = st.selectbox("Nome:", options=unique_names, index=None, key="del_name")
        if name_del:
            datas = df[df['Nome'] == name_del]['Data'].unique()
            data_del_str = st.selectbox("Data:", options=datas, key="del_date")
            if st.button("Deletar"):
                if delete_record(name_del, data_del_str):
                    st.success("Deletado!"); st.rerun()

    with st.expander("Consultar por Nome"):
        name_chk = st.selectbox("Nome:", options=unique_names, index=None, key="chk_name")
        if st.button("Verificar", key="btn_chk"):
            if name_chk:
                st.dataframe(df[df['Nome'] == name_chk], hide_index=True)

    st.dataframe(df.fillna(""), use_container_width=True, hide_index=True)






