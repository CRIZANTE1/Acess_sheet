import streamlit as st
from datetime import datetime
from app.operations import SheetOperations
from auth.auth_utils import get_user_display_name
from app.utils import get_sao_paulo_time, format_cpf, validate_cpf
from app.logger import log_action

def scheduling_page():
    st.title("Agendamento de Visitas")
    sheet_ops = SheetOperations()
    
    with st.form(key="scheduling_form"):
        st.write("Preencha os dados abaixo para agendar uma nova visita.")
        
        visitor_name = st.text_input("Nome Completo do Visitante:")
        visitor_cpf = st.text_input("CPF do Visitante:")
        company = st.text_input("Empresa do Visitante:")
        
        col1, col2 = st.columns(2)
        with col1:
            today = get_sao_paulo_time().date()
            scheduled_date = st.date_input("Data da Visita:", value=today, min_value=today)
        with col2:
            scheduled_time = st.time_input("Hora Estimada da Chegada:")

        # O autorizador é o usuário logado que está fazendo o agendamento
        authorizer = get_user_display_name()
        st.text_input("Autorizado Por:", value=authorizer, disabled=True)

        submit_button = st.form_submit_button("Agendar Visita")

    if submit_button:
        if not all([visitor_name, visitor_cpf, company, scheduled_date, scheduled_time]):
            st.error("Por favor, preencha todos os campos.")
        elif not validate_cpf(visitor_cpf):
            st.error("O CPF informado é inválido.")
        else:
            # Formata os dados para salvar
            formatted_cpf = format_cpf(visitor_cpf)
            date_str = scheduled_date.strftime("%d/%m/%Y")
            time_str = scheduled_time.strftime("%H:%M")
            status = "Agendado"
            
            new_schedule_data = [
                visitor_name.strip(), 
                formatted_cpf, 
                company.strip(),
                date_str,
                time_str,
                authorizer,
                status,
                "" # CheckInTime inicialmente vazio
            ]
            
            # Usa a função genérica para adicionar dados à aba 'schedules'
            if sheet_ops.adc_dados_aba(new_schedule_data, 'schedules'):
                st.success(f"Visita para '{visitor_name.strip()}' agendada com sucesso para {date_str} às {time_str}!")
                log_action("CREATE_SCHEDULE", f"Agendou visita para '{visitor_name.strip()}' em {date_str}.")
            else:
                st.error("Ocorreu um erro ao salvar o agendamento. Tente novamente.")

    st.divider()
    
    # Visualização dos próximos agendamentos
    st.header("Próximas Visitas Agendadas")
    schedules_data = sheet_ops.carregar_dados_aba('schedules')
    if schedules_data and len(schedules_data) > 1:
        df_schedules = pd.DataFrame(schedules_data[1:], columns=schedules_data[0])
        df_schedules['ScheduledDateTime'] = pd.to_datetime(df_schedules['ScheduledDate'] + ' ' + df_schedules['ScheduledTime'], format='%d/%m/%Y %H:%M')
        
        future_schedules = df_schedules[
            (df_schedules['Status'] == 'Agendado') &
            (df_schedules['ScheduledDateTime'] >= get_sao_paulo_time())
        ].sort_values(by='ScheduledDateTime')
        
        if future_schedules.empty:
            st.info("Nenhuma visita futura agendada.")
        else:
            st.dataframe(
                future_schedules[['ScheduledDate', 'ScheduledTime', 'VisitorName', 'Company', 'AuthorizedBy']],
                hide_index=True,
                use_container_width=True
            )
