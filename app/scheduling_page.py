import streamlit as st
import pandas as pd
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
    
        # Aprovador com confirmação
        st.markdown("### 👤 Autorização da Visita")
        authorizer = get_user_display_name()
        st.text_input("Você (Responsável pelo Agendamento):", value=authorizer, disabled=True)
        
        confirmacao_agendamento = st.checkbox(
            "✓ Confirmo que estou ciente e autorizo este agendamento",
            help="Você está assumindo a responsabilidade por este agendamento"
        )
        
        if not confirmacao_agendamento:
            st.warning("⚠️ **Você deve confirmar a ciência do agendamento.**")
    
        submit_button = st.form_submit_button(
            "Agendar Visita",
            disabled=not confirmacao_agendamento
        )
    
    if submit_button:
        if not all([visitor_name, visitor_cpf, company, scheduled_date, scheduled_time]):
            st.error("Por favor, preencha todos os campos.")
        elif not validate_cpf(visitor_cpf):
            st.error("O CPF informado é inválido.")
        elif not confirmacao_agendamento:
            st.error("❌ Você deve confirmar que está ciente do agendamento.")
        else:
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
                ""  # CheckInTime inicialmente vazio
            ]
            
            if sheet_ops.adc_dados_aba(new_schedule_data, 'schedules'):
                st.success(f"✅ Visita para '{visitor_name.strip()}' agendada com sucesso para {date_str} às {time_str}!")
                log_action("CREATE_SCHEDULE", f"Agendou visita para '{visitor_name.strip()}' em {date_str}. Confirmado ciente.")
            else:
                st.error("Ocorreu um erro ao salvar o agendamento. Tente novamente.")

    st.divider()
    
    st.header("Status dos Agendamentos")
    schedules_data = sheet_ops.carregar_dados_aba('schedules')
    
    if not schedules_data or len(schedules_data) < 2:
        st.info("Nenhum agendamento encontrado para exibir.")
        return

    df_schedules = pd.DataFrame(schedules_data[1:], columns=schedules_data[0])
    
    df_schedules['ScheduledDate_dt'] = pd.to_datetime(df_schedules['ScheduledDate'], format='%d/%m/%Y', errors='coerce')
  
    df_schedules.dropna(subset=['ScheduledDate_dt'], inplace=True)

    if df_schedules.empty:
        st.info("Nenhum agendamento com data válida encontrado.")
        return

    today_date = get_sao_paulo_time().date()

    # Filtra os DataFrames para cada categoria
    no_shows = df_schedules[
        (df_schedules['ScheduledDate_dt'].dt.date < today_date) &
        (df_schedules['Status'] == 'Agendado')
    ]

    pending_schedules = df_schedules[
        (df_schedules['ScheduledDate_dt'].dt.date >= today_date) &
        (df_schedules['Status'] == 'Agendado')
    ].sort_values(by='ScheduledDate_dt')

    completed_schedules = df_schedules[df_schedules['Status'] == 'Realizado'].sort_values(by='ScheduledDate_dt', ascending=False)

    tab1, tab2, tab3 = st.tabs([
        f"Pendentes ({len(pending_schedules)})", 
        f"Realizados ({len(completed_schedules)})", 
        f"Não Compareceram ({len(no_shows)})"
    ])

    with tab1:
        st.subheader("Visitas Agendadas Pendentes")
        if pending_schedules.empty:
            st.info("Nenhuma visita futura agendada.")
        else:
            st.dataframe(
                pending_schedules[['ScheduledDate', 'ScheduledTime', 'VisitorName', 'Company', 'AuthorizedBy']],
                hide_index=True, use_container_width=True
            )
    
    with tab2:
        st.subheader("Histórico de Visitas Realizadas")
        if completed_schedules.empty:
            st.info("Nenhuma visita foi marcada como realizada ainda.")
        else:
            st.dataframe(
                completed_schedules[['ScheduledDate', 'VisitorName', 'Company', 'CheckInTime', 'AuthorizedBy']],
                hide_index=True, use_container_width=True
            )

    with tab3:
        st.subheader("Agendamentos Não Comparecidos (No-Show)")
        if no_shows.empty:
            st.info("Nenhum agendamento marcado como não comparecido.")
        else:
            st.dataframe(
                no_shows[['ScheduledDate', 'VisitorName', 'Company', 'AuthorizedBy']],
                hide_index=True, use_container_width=True
            )
