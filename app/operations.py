import streamlit as st
import pandas as pd
import logging
import random
from app.sheets_api import connect_sheet
import pygsheets 

class SheetOperations:
    
    def __init__(self):
        """
        Classe para encapsular operações com o Google Sheets,
        suportando múltiplas abas como 'acess', 'users', 'blocklist', etc.
        """
        self.credentials, self.my_archive_google_sheets = connect_sheet()
        if not self.credentials or not self.my_archive_google_sheets:
            logging.error("Credenciais ou URL do Google Sheets inválidos.")

    def carregar_dados(self):
        """Função de conveniência para carregar dados da aba 'acess'."""
        return self.carregar_dados_aba('acess')
    
    def carregar_dados_aprovadores(self):
        """Carrega a lista de nomes dos aprovadores da aba 'authorizer'."""
        dados = self.carregar_dados_aba('authorizer')
        if dados and len(dados) > 1:
            return [row[0] for row in dados[1:] if row and row[0].strip()]
        return []

    def carregar_dados_aba(self, aba_name):
        """Carrega todos os dados de uma aba específica da planilha."""
        if not self.credentials or not self.my_archive_google_sheets:
            return None
        try:
            logging.info(f"Tentando ler dados da aba '{aba_name}'...")
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            
            try:
                aba = archive.worksheet_by_title(aba_name)
            except pygsheets.exceptions.WorksheetNotFound:
                logging.warning(f"A aba '{aba_name}' não foi encontrada na planilha.")
                return None
            
            data = aba.get_all_values()
            
            if not data:
                logging.warning(f"A aba '{aba_name}' está vazia.")
                return []

            header = data[0]
            valid_columns_indices = [i for i, col_name in enumerate(header) if col_name.strip()]
            
            if not valid_columns_indices:
                return [[]] # Retorna lista com lista vazia para indicar cabeçalho vazio

            filtered_data = [[header[i] for i in valid_columns_indices]]
            for row in data[1:]:
                filtered_row = [str(row[i]).strip() if i < len(row) else "" for i in valid_columns_indices]
                filtered_data.append(filtered_row)
            
            return filtered_data
        
        except Exception as e:
            logging.error(f"Erro ao ler dados da aba '{aba_name}': {e}")
            st.error(f"Erro ao ler dados da aba '{aba_name}': {e}")
            return None
        
    def adc_dados_aba(self, new_data, aba_name):
        """
        Função genérica e "silenciosa" para adicionar dados a uma aba específica.
        Retorna True em caso de sucesso, False em caso de falha. Não mostra UI.
        """
        if not self.credentials or not self.my_archive_google_sheets:
            return False
        try:
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            
            try:
                aba = archive.worksheet_by_title(aba_name)
            except pygsheets.exceptions.WorksheetNotFound:
                aba = archive.add_worksheet(aba_name)
                if aba_name == 'blocklist':
                    aba.update_row(1, ["ID", "Type", "Value", "Reason", "BlockedBy", "Timestamp"])
                elif aba_name == 'acess':
                    aba.update_row(1, ["ID", "Nome", "CPF", "Placa", "Marca do Carro", "Horário de Entrada", "Horário de Saída", "Data", "Empresa", "Status da Entrada", "Motivo do Bloqueio", "Aprovador", "Data do Primeiro Registro"])
                elif aba_name == 'logs':
                    aba.update_row(1, ["Timestamp", "User", "Action", "Details"])
            
            all_values = aba.get_all_values()
            existing_ids = [row[0] for row in all_values[1:] if row and row[0]]
            while True:
                new_id = random.randint(10000, 99999)
                if str(new_id) not in existing_ids:
                    break

            new_data.insert(0, new_id)
            aba.append_table(values=new_data)
            logging.info(f"Dados adicionados com sucesso à aba '{aba_name}'.")
            return True
        except Exception as e:
            logging.error(f"Erro ao adicionar dados à aba '{aba_name}': {e}", exc_info=True)
            return False
            
    def adc_dados(self, new_data):
        """Função de conveniência para adicionar dados à aba 'acess' e mostrar mensagem de sucesso."""
        if self.adc_dados_aba(new_data, 'acess'):
            st.success("Dados adicionados com sucesso!")
        else:
            st.error("Falha ao adicionar dados na planilha 'acess'.")

    def editar_dados(self, id, updated_data):
        """Edita uma linha na aba 'acess'."""
        if not self.credentials or not self.my_archive_google_sheets:
            return False
        try:
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            aba = archive.worksheet_by_title('acess')
            data = aba.get_all_values()
            
            for i, row in enumerate(data):
                if row and row[0] == str(id):
                    updated_row = [str(id)] + updated_data
                    aba.update_row(i + 1, updated_row)
                    return True
            return False
        except Exception as e:
            logging.error(f"Erro ao editar dados: {e}", exc_info=True)
            return False



    def excluir_dados_por_id_aba(self, id_to_delete, aba_name):
        """Exclui uma linha de uma aba específica com base no ID."""
        if not self.credentials or not self.my_archive_google_sheets:
            return False
        try:
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            aba = archive.worksheet_by_title(aba_name)
            
            all_values = aba.get_all_values()
            
            row_to_delete_index = -1
            for i, row in enumerate(all_values[1:]):
                if row and str(row[0]) == str(id_to_delete):
                    # i+2 porque começamos no índice 1 e as linhas da planilha começam em 1 (i=0 -> linha 2)
                    row_to_delete_index = i + 2 
                    break # Encontrou, pode parar de procurar

            if row_to_delete_index != -1:
                # Se encontrou a linha, deleta pelo seu índice
                aba.delete_rows(row_to_delete_index)
                logging.info(f"Dados do ID {id_to_delete} excluídos com sucesso da aba '{aba_name}'.")
                return True
            else:
                # Se o loop terminar e não encontrar, registra o erro
                logging.error(f"ID {id_to_delete} não encontrado na aba '{aba_name}'.")
                st.warning(f"Não foi possível encontrar o registro com ID {id_to_delete} para exclusão.")
                return False
                
        except Exception as e:
            logging.error(f"Erro ao excluir dados da aba '{aba_name}': {e}", exc_info=True)
            st.error(f"Erro crítico ao tentar excluir dados: {e}")
            return False



























