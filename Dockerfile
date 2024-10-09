
# Usar uma imagem oficial do Python
FROM python:3.10-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copiar o arquivo requirements.txt para o container
COPY requirements.txt .

# Instalar as dependências listadas no requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copiar o restante do código da aplicação para o container
COPY . .

# Expõe a porta 5000 para o Flask
EXPOSE 5000

# Comando para rodar a aplicação Flask
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
=======
# Usar uma imagem oficial do Python
FROM python:3.10-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copiar o arquivo requirements.txt para o container
COPY requirements.txt .

# Instalar as dependências listadas no requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copiar o restante do código da aplicação para o container
COPY . .

# Expõe a porta 5000 para o Flask
EXPOSE 5000

# Comando para rodar a aplicação Flask
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]

