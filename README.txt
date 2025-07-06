Execute os arquivo requirements para instalar os freameworks do python necessários 

Endpoints  
Todos os arquivos POST’s tem que tem no Hedears - Key “Contennt-Type” - Value “application/json”
Body sempre com “raw”-”json”

Todos os arquivos que tem “protegido” no Authorization o Auth Type “Bearer Token”
Sugestão: para realizar todos os casos de sucesso faça login com ADM e coloque o Token dele nos Authorization, para os testes de erros forçados é só realizar o login com um funcionario que não tenha autorização.

O arquivo ADM é executado a parte do APP, cada um tem seu banco de dados.
