## Instalação e execução

1- É **necessário** instalar as dependências do projeto, executando o seguinte comando no diretório raiz do projeto

    pip install --upgrade -r requirements.txt

2- Para rodar o projeto, basta executar o comando abaixo na raiz do projeto

    uvicorn app.main:app --host 0.0.0.0 --port 8003

3- Em seguida é possível consutar a documentação e realizar requisições em

    http://0.0.0.0:8003/docs

## Execução de testes

1- Para executar os testes do projeto basta executar o comando a seguir no diretório route_test

    pytest