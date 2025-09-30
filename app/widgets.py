import streamlit as st

def aprovador_selector_with_confirmation(
    aprovadores_list, 
    key_prefix="aprovador",
    help_text="Selecione quem está autorizando este acesso"
):
    """
    Widget reutilizável para seleção de aprovador com confirmação.
    
    Args:
        aprovadores_list: Lista de aprovadores disponíveis
        key_prefix: Prefixo para as chaves dos componentes
        help_text: Texto de ajuda para o selectbox
    
    Returns:
        tuple: (aprovador_selecionado, esta_ciente)
    """
    st.markdown("### 👤 Autorização de Acesso")
    col_aprovador, col_confirma = st.columns([2, 1])
    
    with col_aprovador:
        aprovador = st.selectbox(
            "Selecione o Aprovador Responsável:", 
            options=[""] + aprovadores_list, 
            key=f"{key_prefix}_select",
            help=help_text
        )
    
    with col_confirma:
        if aprovador and aprovador != "":
            aprovador_ciente = st.checkbox(
                "✓ Aprovador está ciente?",
                key=f"{key_prefix}_ciente",
                help=f"Confirme que {aprovador} está ciente e autoriza esta ação"
            )
        else:
            aprovador_ciente = False
            st.info("Selecione um aprovador")
    
    # Alertas
    if not aprovador or aprovador == "":
        st.warning("⚠️ **Você deve selecionar um aprovador responsável pela autorização.**")
    elif not aprovador_ciente:
        st.warning(f"⚠️ **Confirme que {aprovador} está ciente desta ação.**")
    
    return aprovador, aprovador_ciente
