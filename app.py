from flask import Flask, request, jsonify
import pyodbc
import spacy
import logging
from dotenv import load_dotenv
import os
from flask_cors import CORS
from flask_caching import Cache

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração do Flask e CORS
app = Flask(__name__)
CORS(app)

# Configuração do cache
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Configuração de logs estruturados
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Função para baixar e carregar o modelo do SpaCy
def load_spacy_model():
    try:
        return spacy.load('pt_core_news_sm')
    except OSError:
        from spacy.cli import download
        download('pt_core_news_sm')
        return spacy.load('pt_core_news_sm')

# Inicialização do SpaCy
nlp = load_spacy_model()

# Configuração da Conexão com o Banco de Dados com Timeout
connection_string = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={os.getenv('DB_SERVER')};"
    f"DATABASE={os.getenv('DB_NAME')};"
    f"UID={os.getenv('DB_USER')};"
    f"PWD={os.getenv('DB_PASSWORD')};"
    "Connection Timeout=5;"  # Timeout de 5 segundos para evitar travamento
)

# Função para realizar consultas no banco de dados com tratamento de erros
def query_db(query, params=None):
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        cursor.execute(query, params if params else ())
        result = cursor.fetchall()
        conn.close()
        return result
    except pyodbc.OperationalError as e:
        logging.error(f"Erro operacional no banco de dados: {e}")
        return []
    except pyodbc.Error as e:
        logging.error(f"Erro de banco de dados: {e}")
        return []
    except Exception as e:
        logging.error(f"Erro desconhecido: {e}")
        return []

# Mapeamento de palavras-chave para colunas da tabela
keywords_to_columns = {
    'código': 'CÓDIGO',
    'substitutos': 'SUBSTITUTOS',
    'nome': 'NOME',
    'fabricante': 'FABRICANTE',
    'embalagem': 'EMBALAGEM',
    'preço': 'PREÇO 38%',
    'comprador': 'COMPRADOR',
    'ecom': 'ECOM',
    'arred_mult': 'ARRED_MULT',
    'segmento': 'SEGMENTO',
    'categoria': 'CATEGORIA',
    'grupo': 'GRUPO'
}

# Função para identificar a intenção e extrair termos de pesquisa
def parse_question(question):
    doc = nlp(question.lower())
    column = None
    search_term = []

    for token in doc:
        lemma = token.lemma_
        if lemma in keywords_to_columns:
            column = keywords_to_columns[lemma]
        elif not token.is_stop and not token.is_punct:
            search_term.append(token.text)

    return column, ' '.join(search_term)

# Função para formatar a resposta de maneira segura
def format_response(result):
    try:
        return {
            'CÓDIGO': result[0][0],
            'SUBSTITUTOS': result[0][1],
            'NOME': result[0][2],
            'FABRICANTE': result[0][3],
            'EMBALAGEM': result[0][4],
            'PREÇO 38%': result[0][5],
            'COMPRADOR': result[0][6],
            'ECOM': result[0][7],
            'ARRED_MULT': result[0][8],
            'SEGMENTO': result[0][9],
            'CATEGORIA': result[0][10],
            'GRUPO': result[0][11]
        }
    except IndexError as e:
        logging.error(f"Erro ao formatar resposta: {e}")
        return {'error': 'Erro ao processar a resposta.'}

# Rota para processar perguntas, com cache
@app.route('/ask', methods=['POST'])
@cache.cached(timeout=60, query_string=True)  # Cacheando por 60 segundos
def ask():
    try:
        user_question = request.json.get('question')
        if not user_question:
            return jsonify({'error': 'Pergunta não fornecida.'}), 400

        column, query = parse_question(user_question)

        logging.info(f"Pergunta do usuário: {user_question}")
        logging.info(f"Coluna analisada: {column}")
        logging.info(f"Termo de busca: {query}")

        if query:
            sql_query = """
            SELECT CÓDIGO, SUBSTITUTOS, NOME, FABRICANTE, EMBALAGEM, [PREÇO 38%],
                COMPRADOR, ECOM, ARRED_MULT, SEGMENTO, CATEGORIA, GRUPO
            FROM admat
            WHERE
                CÓDIGO LIKE ? OR
                SUBSTITUTOS LIKE ? OR
                NOME LIKE ? OR
                FABRICANTE LIKE ? OR
                EMBALAGEM LIKE ? OR
                [PREÇO 38%] LIKE ? OR
                COMPRADOR LIKE ? OR
                ECOM LIKE ? OR
                ARRED_MULT LIKE ? OR
                SEGMENTO LIKE ? OR
                CATEGORIA LIKE ? OR
                GRUPO LIKE ?
            """
            result = query_db(sql_query, [f'%{query}%'] * 12)
        else:
            result = []

        logging.info(f"Resultado da consulta SQL: {result}")

        if result:
            response = format_response(result)
        else:
            response = {'answer': 'Desculpe, não encontrei informações para sua pergunta.'}
        return jsonify(response)
    except Exception as e:
        logging.error(f"Erro ao processar a solicitação: {e}")
        return jsonify({'error': 'Ocorreu um erro ao processar sua solicitação.'}), 500

# Ponto de entrada para execução do aplicativo
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))