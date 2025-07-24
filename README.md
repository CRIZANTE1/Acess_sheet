# Sistema de Controle de Acesso e Briefing v2.5

Este sistema robusto gerencia o controle de acesso de visitantes e veículos, utilizando o Google Sheets como um banco de dados flexível. A aplicação é construída com Streamlit e inclui autenticação segura via Google (OIDC), um sistema de papéis de usuário, fluxo de aprovação para acessos restritos, log de auditoria e um sistema de bloqueio permanente.

## Funcionalidades Principais

-   **Controle de Acesso em Tempo Real:** Registra entradas e saídas de pessoas e veículos.
-   **Autenticação Segura:** Login via Google OIDC, garantindo que apenas usuários autenticados acessem o sistema.
-   **Sistema de Papéis (Roles):** Permissões de usuário (`admin`, `operacional`) gerenciadas diretamente por uma planilha, permitindo controle de acesso granular sem alterar o código.
-   **Fluxo de Aprovação:** Usuários operacionais podem solicitar a liberação de acessos temporariamente bloqueados, que devem ser aprovados por um administrador.
-   **Gerenciamento de Bloqueios (Blocklist):** Administradores podem bloquear permanentemente pessoas ou empresas, impedindo qualquer tentativa de acesso futura.
-   **Log de Auditoria:** Todas as ações críticas (logins, registros, aprovações, bloqueios, etc.) são registradas em uma planilha dedicada para fins de segurança e auditoria.
-   **Verificação de Briefing de Segurança:** Alerta automático para a necessidade de repassar o briefing de segurança para visitantes com mais de um ano desde o último acesso registrado.

## Requisitos do Sistema

- Python 3.8 ou superior
- Conexão com internet para acesso ao Google Sheets e autenticação Google
- Credenciais do Google Cloud para acesso ao Google Sheets
- Configuração OIDC para login Google

## Instalação e Uso

1. Clone este repositório para seu computador.

2. Instale as dependências necessárias:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure as credenciais do Google Cloud para acesso ao Google Sheets:
   - Obtenha um arquivo JSON de credenciais de conta de serviço no Google Cloud Console.
   - Salve este arquivo como `app/credentials/cred.json` no diretório do projeto.
   - **Para implantação no Streamlit Cloud:** Não inclua o arquivo `cred.json` diretamente. Em vez disso, adicione o conteúdo do JSON como um segredo no Streamlit Cloud (por exemplo, nomeado `GOOGLE_SHEETS_CREDENTIALS`) e configure a seção `[connections.gsheets]` no `.streamlit/secrets.toml` do Streamlit Cloud para usar este segredo.

4. Configure as credenciais OIDC para login Google:
   - Crie um arquivo `.streamlit/secrets.toml` na raiz do projeto (se ainda não existir).
   - Adicione as configurações OIDC obtidas do Google Cloud Console na seção `[auth]`.
   - Gere um `cookie_secret` forte e aleatório.
   - Certifique-se de que o `redirect_uri` no `secrets.toml` e no Google Cloud Console corresponda ao endereço onde a aplicação será executada (localmente `http://localhost:8501/oauth2callback`, ou o URL do Streamlit Cloud).

   Exemplo de `.streamlit/secrets.toml`:
   ```toml
   [auth]
   client_id = "YOUR_CLIENT_ID"
   client_secret = "YOUR_CLIENT_SECRET"
   server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
   redirect_uri = "YOUR_REDIRECT_URI"
   cookie_secret = "YOUR_COOKIE_SECRET"

   # Para Streamlit Cloud, configure as credenciais do Google Sheets aqui
   [connections.gsheets]
   spreadsheet = "YOUR_SPREADSHEET_URL"
   type = "service_account"
   project_id = "YOUR_PROJECT_ID"
   private_key_id = "YOUR_PRIVATE_KEY_ID"
   private_key = "YOUR_PRIVATE_KEY"
   client_email = "YOUR_CLIENT_EMAIL"
   client_id = "YOUR_CLIENT_ID"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/YOUR_CLIENT_EMAIL"
   universe_domain = "googleapis.com"
   ```

5. Execute o sistema:
   ```bash
   streamlit run main.py
   ```
   - O sistema será iniciado no seu navegador padrão.

## Funcionalidades

- Controle de acesso de visitantes e veículos usando Google Sheets
- Autenticação de usuário via Google OIDC
- Verificação automática de briefing


## Estrutura de Arquivos

```
.
├── app/
│   ├── admin_page.py       # Interface do painel administrativo
│   ├── data_operations.py  # Funções de CRUD e lógica de negócio
│   ├── logger.py           # Módulo para registro de logs de auditoria
│   ├── operations.py       # Classe de baixo nível para interagir com o Google Sheets
│   ├── sheets_api.py       # Conexão e autorização com a API do Google
│   └── ui_interface.py     # Interface principal de controle de acesso
│  
├── auth/
│   ├── auth_utils.py       # Funções de autenticação e verificação de papéis
│   └── login_page.py       # Interface da página de login
│  
├── .streamlit/
│   └── secrets.toml        # Arquivo de segredos (NÃO ENVIAR PARA O GIT)
│
├── main.py                 # Ponto de entrada da aplicação
├── requirements.txt        # Dependências do projeto
└── README.md               # Este arquivo de documentação
```

## Suporte

Para suporte técnico ou dúvidas, entre em contato com o desenvolvedor.

## Notas de Segurança

- Mantenha suas credenciais do Google Cloud e `cookie_secret` em segurança.
- Não compartilhe os arquivos do sistema com pessoas não autorizadas.
- Faça backup regular dos dados no Google Sheets.
