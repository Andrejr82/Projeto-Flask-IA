# Use a imagem base do Python
FROM python:3.10

# Defina o diretório de trabalho no contêiner
WORKDIR /app

# Copie os arquivos do projeto para o contêiner
COPY . .

# Copie o arquivo .env para o contêiner
COPY .env .env

# Instale as dependências do projeto
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --upgrade pip

# Exponha a porta para o Flask
EXPOSE 5000

# Comando para iniciar o Flask com Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
