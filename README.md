# Sistema de Controle de Acesso e Briefing v3.0

Este sistema robusto gerencia o controle de acesso de visitantes e veículos, utilizando o Google Sheets como um banco de dados flexível. A aplicação é construída com Streamlit e inclui autenticação segura via Google (OIDC), um sistema de papéis de usuário, fluxo de aprovação para acessos restritos, log de auditoria, sistema de bloqueio permanente e múltiplas camadas de segurança.

## 🎯 Funcionalidades Principais

### Controle de Acesso
-   **Controle de Acesso em Tempo Real:** Registra entradas e saídas de pessoas e veículos com validação completa
-   **Validação de Placas:** Suporte para placas antigas (ABC-1234) e Mercosul (ABC1D23) com formatação automática
-   **Agendamento de Visitas:** Sistema completo de agendamento com check-in automático
-   **Verificação de Briefing de Segurança:** Alerta automático para repassar briefing quando necessário (primeira visita ou mais de 1 ano desde último acesso)

### Segurança e Autenticação
-   **Autenticação Segura:** Login via Google OIDC com suporte a múltiplos provedores
-   **Sistema de Papéis (Roles):** Permissões de usuário (`admin`, `operacional`) gerenciadas via planilha
-   **Validações de Segurança Avançadas:**
    - Proteção contra SQL Injection
    - Proteção contra XSS (Cross-Site Scripting)
    - Sanitização automática de inputs
    - Rate Limiting (limite de tentativas)
    - Timeout de sessão por inatividade (30 minutos)
    - Bloqueio por tentativas falhadas
-   **Confirmação de Aprovador:** Sistema obrigatório de confirmação "O aprovador está ciente?" antes de autorizar acessos

### Fluxos Administrativos
-   **Fluxo de Aprovação:** Usuários operacionais podem solicitar liberação de acessos bloqueados
-   **Gerenciamento de Bloqueios (Blocklist):** Bloqueio permanente de pessoas ou empresas com justificativa obrigatória
-   **Solicitações Excepcionais:** Processo especial para liberar entidades bloqueadas permanentemente
-   **Log de Auditoria:** Registro completo de todas as ações críticas do sistema

### Relatórios e Visualização
-   **Dashboard de Resumo:** Estatísticas mensais de acessos
-   **Consultas Personalizadas:** Busca por nome, período, empresa
-   **Contador de Impacto Ambiental:** Cálculo de papel e árvores economizadas pela digitalização
-   **Visualização de Histórico:** Histórico completo de cada visitante

## 🔒 Recursos de Segurança

### Validações Implementadas
- ✅ **Nome Completo:** Mínimo 2 palavras, apenas letras
- ✅ **CPF:** Validação completa com dígitos verificadores
- ✅ **Placa:** Formatos brasileiros (antiga e Mercosul)
- ✅ **Empresa:** Caracteres permitidos com sanitização
- ✅ **Proteção SQL Injection:** Detecção de palavras-chave perigosas
- ✅ **Proteção XSS:** Filtro de padrões HTML/JavaScript maliciosos
- ✅ **Rate Limiting:** Controle de tentativas por minuto
- ✅ **Session Management:** Timeout automático e renovação

### Logs de Segurança
Todas as ações são registradas incluindo:
- Tentativas de acesso bloqueadas
- Violações de segurança detectadas
- Alterações administrativas
- Solicitações de liberação
- Falhas de validação

## 💻 Requisitos do Sistema

- Python 3.8 ou superior
- Conexão com internet para acesso ao Google Sheets e autenticação Google
- Credenciais do Google Cloud para acesso ao Google Sheets
- Configuração OIDC para login Google

