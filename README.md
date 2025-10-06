## Instruções para atualização da planilha Google Sheets:
IMPORTANTE: Você precisará atualizar a estrutura da aba users no Google Sheets:

Renomeie a coluna user_name para user_email
Atualize os dados substituindo os nomes pelos emails correspondentes das contas Google
A estrutura final deve ser:

Coluna A: user_email (exemplo: usuario@exemplo.com)
Coluna B: role (admin ou operacional)



Exemplo da aba 'users':
user_email                    | role
----------------------------- | ------------
admin@empresa.com             | admin
operador1@empresa.com         | operacional
operador2@empresa.com         | operacional