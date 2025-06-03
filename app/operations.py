import streamlit as st
import pandas as pd
import logging
import random
from app.sheets_api import connect_sheet


class SheetOperations:
    
    def __init__(self):
        """
        O código define uma classe com métodos para conectar-se a um documento Google Sheets, carregar dados de
        uma planilha específica, adicionar novos dados com um ID único, editar dados existentes com base no ID
        e excluir dados com base no ID.
        """
        self.credentials, self.my_archive_google_sheets = connect_sheet()
        if not self.credentials or not self.my_archive_google_sheets:
            logging.error("Credenciais ou URL do Google Sheets inválidos.")

    def carregar_dados(self):
        return self.carregar_dados_aba('acess')
    
    def carregar_dados_funcionarios(self):
        """
        Carrega os dados dos funcionários da aba 'funcionarios' do Google Sheets.
        
        Returns:
            list: Lista com os dados dos funcionários, onde o primeiro item são os cabeçalhos
                 e os demais são os dados de cada funcionário.
        """
        return self.carregar_dados_aba('funcionarios')

    def carregar_dados_aprovadores(self):
        """
        Carrega os dados dos aprovadores da aba 'authorizer' do Google Sheets.
        
        Returns:
            list: Lista com os nomes dos aprovadores autorizados.
        """
        dados = self.carregar_dados_aba('authorizer')
        if dados and len(dados) > 1:  # Verifica se há dados além do cabeçalho
            # Assume que a primeira coluna contém os nomes dos aprovadores
            return [row[0] for row in dados[1:] if row[0].strip()]  # Retorna apenas nomes não vazios
        return []

    def carregar_dados_aba(self, aba_name):
        if not self.credentials or not self.my_archive_google_sheets:
            return None
        try:
            logging.info(f"Tentando ler dados da aba '{aba_name}'...")
            
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            
            if aba_name not in [sheet.title for sheet in archive.worksheets()]:
                logging.error(f"A aba '{aba_name}' não existe no Google Sheets.")
                st.error(f"A aba '{aba_name}' não foi encontrada na planilha.")
                return None
            
            aba = archive.worksheet_by_title(aba_name)
            data = aba.get_all_values()
            
            if not data:
                logging.warning(f"A aba '{aba_name}' está vazia.")
                return []

            # Identificar colunas com nomes não vazios na primeira linha (cabeçalhos)
            header = data[0]
            valid_columns_indices = [i for i, col_name in enumerate(header) if col_name.strip()]
            
            if not valid_columns_indices:
                logging.warning(f"Nenhum cabeçalho válido encontrado na aba '{aba_name}'.")
                return []

            # Filtrar os dados para incluir apenas as colunas válidas e tratar valores vazios
            filtered_data = []
            filtered_data.append([header[i] for i in valid_columns_indices])  # Adiciona os cabeçalhos
            
            for row in data[1:]:  # Para cada linha de dados
                filtered_row = []
                for i in valid_columns_indices:
                    value = row[i] if i < len(row) else ""  # Trata índices fora do range
                    
                    # Tratamento especial para preservar números longos
                    if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.','').replace(',','').isdigit()):
                        try:
                            # Tenta converter para número e depois para string para remover notação científica
                            value = str(int(float(str(value).replace(',', '').replace('.', ''))))
                        except (ValueError, TypeError):
                            value = str(value).strip()
                    else:
                        value = str(value).strip() if value is not None else ""
                    
                    filtered_row.append(value)
                filtered_data.append(filtered_row)
            
            logging.info(f"Dados da aba '{aba_name}' lidos e filtrados com sucesso.")
            return filtered_data
        
        except Exception as e:
            logging.error(f"Erro ao ler dados da aba '{aba_name}': {e}")
            st.error(f"Erro ao ler dados da aba '{aba_name}': {e}")
            return None
        
        
    def adc_dados(self, new_data):
        if not self.credentials or not self.my_archive_google_sheets:
            return
        try:
            logging.info(f"Tentando adicionar dados: {new_data}")
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            aba_name = 'acess'
            if aba_name not in [sheet.title for sheet in archive.worksheets()]:
                logging.error(f"A aba '{aba_name}' não existe no Google Sheets.")
                st.error(f"A aba '{aba_name}' não foi encontrada na planilha.")
                return
            aba = archive.worksheet_by_title(aba_name)

            # Esta parte do código está gerando um novo ID único para os dados a serem adicionados ao
            # Google Sheets. O ID é um número aleatório de 4 dígitos que não pode ser repetido.
            existing_ids = [row[0] for row in aba.get_all_values()[1:]]  #
            while True:
                new_id = random.randint(1000, 9999)
                if str(new_id) not in existing_ids:
                    break

            # Garantir que o horário de saída (índice 5) seja vazio APENAS para novos registros
            # Se for uma edição (já existe um ID), manter o horário de saída existente
            if len(new_data) > 5 and str(new_id) not in existing_ids:
                new_data[5] = ""

            new_data.insert(0, new_id)  # Insere o novo ID no início da lista new_data
            aba.append_table(values=new_data)  # Adiciona a linha à tabela dinamicamente
            logging.info("Dados adicionados com sucesso.")
            st.success("Dados adicionados com sucesso!")
        except Exception as e:
            logging.error(f"Erro ao adicionar dados: {e}", exc_info=True)
            st.error(f"Erro ao adicionar dados: {e}")

    def editar_dados(self, id, updated_data):
        if not self.credentials or not self.my_archive_google_sheets:
            return False
        try:
            logging.info(f"Tentando editar dados do ID {id}")
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            aba = archive.worksheet_by_title('acess')
            data = aba.get_all_values()
            
            # Procurar a linha com o ID correspondente
            for i, row in enumerate(data):
                if row[0] == str(id):  # ID está na primeira coluna
                    # Atualizar a linha com os novos dados, mantendo o ID original
                    updated_row = [str(id)] + updated_data
                    aba.update_row(i + 1, updated_row)  # +1 porque as linhas começam em 1
                    logging.info("Dados editados com sucesso.")
                    return True
                    
            logging.error(f"ID {id} não encontrado.")
            return False
            
        except Exception as e:
            logging.error(f"Erro ao editar dados: {e}", exc_info=True)
            return False

    def excluir_dados(self, id):
        if not self.credentials or not self.my_archive_google_sheets:
            return False
        try:
            logging.info(f"Tentando excluir dados do ID {id}")
            archive = self.credentials.open_by_url(self.my_archive_google_sheets)
            aba = archive.worksheet_by_title('acess')
            data = aba.get_all_values()
            
            # Procurar a linha com o ID correspondente
            for i, row in enumerate(data):
                if row[0] == str(id):  # ID está na primeira coluna
                    aba.delete_rows(i + 1)  # +1 porque as linhas começam em 1
                    logging.info("Dados excluídos com sucesso.")
                    return True
                    
            logging.error(f"ID {id} não encontrado.")
            return False
            
        except Exception as e:
            logging.error(f"Erro ao excluir dados: {e}", exc_info=True)
            return False









