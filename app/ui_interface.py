import streamlit as st
import pandas as pd
from app.data_operations import add_record, update_exit_time, delete_record, check_blocked_records, get_aprovadores
from app.utils import format_cpf, validate_cpf, get_sao_paulo_time, normalize_names

def get_person_status(name, df):
    """Busca o status da pessoa usando o nome já normalizado do DataFrame."""
    if not name: return "Novo", None
    
    person_records = df[df["Nome"] == name].copy()
    if person_records.empty: return "Fora", None
    
    person_records.loc[:, 'Data_dt'] = pd.to_datetime(person_records['Data'], format='%d/%m/%Y', errors='coerce')
    person_records.dropna(subset=['Data_dt'], inplace=True)
    person_records = person_records.sort_values(by=['Data_dt', 'Horário de Entrada'], ascending=[False, False])
    
    if person_records.empty: return "Fora", None
    
    latest_record = person_records.iloc[0]
    horario_saida = latest_record.get("Horário de Saída", "")
    if pd.isna(horario_saida) or str(horario_saida).strip() == "": return "Dentro", latest_record
    else: return "Fora", latest_record

def show_people_inside(df):
    """Mostra pessoas dentro, usando o nome original (já normalizado) para exibição."""
    st.subheader("Pessoas na Unidade")
    inside_df = df[pd.isna(df["Horário de Saída"]) | (df["Horário de Saída"] == "")].copy().sort_values("Nome")
    if inside_df.empty:
        st.info("Ninguém registrado na unidade no momento.")
        return
    for _, row in inside_df.iterrows():
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1: st.write(f"**{row['Nome']}**") # Exibe o nome original
        with col2: st.caption(f"Entrada: {row['Data']} às {row['Horário de Entrada']}")
        with col3:
            record_id = row.get("ID")
            if st.button("Sair", key=f"exit_{record_id}", use_container_width=True):
                now = get_sao_paulo_time()
                # A função de backend usa o nome original para encontrar o registro
                success, message = update_exit_time(row['Nome'], now.strftime("%d/%m/%Y"), now.strftime("%H:%M"))
                if success:
                    st.success(message); st.rerun()
                else: st.error(message)

def vehicle_access_interface():
    st.title("Controle de Acesso BAERI")
    aprovadores_autorizados = get_aprovadores()

    with st.expander("Briefing de Segurança e Lembretes", expanded=True):
        st.write("""
        **ATENÇÃO:**
        1. O acesso de veículos deve ser controlado rigorosamente para garantir a segurança do local.
        2. Apenas pessoas autorizadas podem liberar o acesso.
        3. Em caso de dúvidas, entre em contato com o responsável pela segurança.
        4. Mantenha sempre os dados atualizados e verifique as informações antes de liberar o acesso.
        5. **Sempre que for a primeira vez do visitante ou um ano desde o último acesso, repassar o vídeo abaixo.**
        """)
        try: st.video("https://youtu.be/QqUkeTucwkI")
        except Exception as e: st.error(f"Erro ao carregar o vídeo: {e}")
        
    df = st.session_state.get('df_acesso_veiculos', pd.DataFrame())

    if df.empty:
        st.warning("Planilha vazia ou não carregada.")
        if st.button("Tentar Recarregar"):
            from app.data_operations import load_data_from_sheets
            load_data_from_sheets(); st.rerun()
        return

    # --- NORMALIZAÇÃO CENTRALIZADA E SIMPLES ---
    if "Nome" in df.columns and not df.empty:
        df['Nome'] = normalize_names_simple(df['Nome'])
    
    # Esta linha AGORA VAI funcionar corretamente.
    unique_names = sorted(list(df["Nome"].unique()))

    blocked_info = check_blocked_records(df)
    if blocked_info: st.error("Atenção! Pessoas com bloqueio ativo:\n\n" + blocked_info)

    col_main, col_sidebar = st.columns([2, 1])
    with col_main:
        st.header("Painel de Registro")
        search_options = ["--- Novo Cadastro ---"] + unique_names
        selected_name = st.selectbox("Busque por um nome:", options=search_options, index=0, key="person_selector")
        
        if selected_name == "--- Novo Cadastro ---":
            status = "Novo"
            latest_record = None
        else:
            status, latest_record = get_person_status(selected_name, df)
        
        if status == "Dentro":
            st.info(f"**{selected_name}** está **DENTRO** da unidade.")
            st.write(f"**Entrada em:** {latest_record['Data']} às {latest_record['Horário de Entrada']}")
            if st.button(f"✅ Registrar Saída de {selected_name}", use_container_width=True, type="primary"):
                now = get_sao_paulo_time()
                success, message = update_exit_time(selected_name, now.strftime("%d/%m/%Y"), now.strftime("%H:%M"))
                if success: st.success(message); st.rerun()
                else: st.error(message)

        elif status == "Fora":
            st.success(f"**{selected_name}** está **FORA** da unidade.")
            st.write(f"**Última saída em:** {latest_record.get('Data', 'N/A')} às {latest_record.get('Horário de Saída', 'N/A')}")
            with st.form(key="reentry_form"):
                st.write("Registrar nova entrada:")
                placa = st.text_input("Placa", value=str(latest_record.get("Placa", "")))
                empresa = st.text_input("Empresa", value=str(latest_record.get("Empresa", "")))
                aprovador = st.selectbox("Aprovador:", options=aprovadores_autorizados)
                if st.form_submit_button(f"▶️ Registrar Entrada de {selected_name}", use_container_width=True, type="primary"):
                    now = get_sao_paulo_time()
                    if add_record(name=selected_name, cpf=str(latest_record.get("CPF", "")), placa=placa, marca_carro=str(latest_record.get("Marca do Carro", "")), horario_entrada=now.strftime("%H:%M"), data=now.strftime("%d/%m/%Y"), empresa=empresa, status="Autorizado", motivo="", aprovador=aprovador):
                        st.success(f"Nova entrada de {selected_name} registrada!"); st.rerun()

        elif status == "Novo":
            st.info("Pessoa não encontrada. Preencha o formulário.")
            with st.form(key="new_visitor_form"):
                st.write("**Formulário de Primeiro Acesso**")
                name = st.text_input("Nome Completo:")
                cpf = st.text_input("CPF:")
                empresa = st.text_input("Empresa:")
                status_entrada = st.selectbox("Status", ["Autorizado", "Bloqueado"], index=0)
                motivo_bloqueio = st.text_input("Motivo (se Bloqueado):") if status_entrada == "Bloqueado" else ""
                aprovador = st.selectbox("Aprovador:", options=aprovadores_autorizados) if status_entrada == "Autorizado" else ""
                placa = st.text_input("Placa (Opcional):")
                marca_carro = st.text_input("Marca (Opcional):")
                if st.form_submit_button("➕ Cadastrar e Registrar", use_container_width=True, type="primary"):
                    if not name or not cpf or not empresa or (status_entrada == "Autorizado" and not aprovador): st.error("Preencha os campos obrigatórios.")
                    elif not validate_cpf(cpf): st.error("CPF inválido.")
                    else:
                        now = get_sao_paulo_time()
                        if add_record(name=name, cpf=format_cpf(cpf), placa=placa, marca_carro=marca_carro, horario_entrada=now.strftime("%H:%M"), data=now.strftime("%d/%m/%Y"), empresa=empresa, status=status_entrada, motivo=motivo_bloqueio, aprovador=aprovador):
                            st.success(f"Novo registro para {name} criado!"); st.rerun()

    with col_sidebar:
        show_people_inside(df)
    
    st.divider()

    with st.expander("Gerenciamento de Registros (Bloquear, Deletar)"):
        st.warning("Use para ações administrativas.")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Bloquear Pessoa")
            person_to_block = st.selectbox("Selecione para bloquear:", options=[""] + unique_names, key="block_person", index=0)
            if person_to_block:
                motivo = st.text_input("Motivo:", key="block_reason")
                if st.button("Aplicar Bloqueio", key="apply_block"):
                    if motivo and not df[df["Nome"] == person_to_block].empty:
                        now = get_sao_paulo_time()
                        last_record = df[df["Nome"] == person_to_block].sort_values("Data").iloc[-1]
                        if add_record(name=person_to_block, cpf=str(last_record.get("CPF", "")), placa="", marca_carro="", horario_entrada=now.strftime("%H:%M"), data=now.strftime("%d/%m/%Y"), empresa=str(last_record.get("Empresa", "")), status="Bloqueado", motivo=motivo, aprovador=""):
                            st.success(f"{person_to_block} bloqueado com sucesso."); st.rerun()

        with col2:
            st.subheader("Deletar Último Registro")
            person_to_delete = st.selectbox("Selecione para deletar:", options=[""] + unique_names, key="delete_person", index=0)
            if person_to_delete:
                if st.button("Deletar Último Registro", key="apply_delete", type="secondary"):
                    records = df[df["Nome"] == person_to_delete].copy()
                    records.loc[:, 'Data_dt'] = pd.to_datetime(records['Data'], format='%d/%m/%Y', errors='coerce')
                    last_record = records.sort_values(by='Data_dt', ascending=False).iloc[0]
                    if delete_record(last_record['Nome'], last_record['Data']):
                        st.success(f"Último registro de {person_to_delete} deletado."); st.rerun()
    
    with st.expander("Visualizar todos os registros"):
        st.dataframe(df.fillna(""), use_container_width=True, hide_index=True)


