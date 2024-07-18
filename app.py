from flask import Flask, request, jsonify
import pyodbc
import spacy
import logging

# Função para baixar e carregar o modelo do SpaCy


def load_spacy_model():
    try:
        nlp = spacy.load('pt_core_news_sm')
    except OSError:
        from spacy.cli import download
        download('pt_core_news_sm')
        nlp = spacy.load('pt_core_news_sm')
    return nlp


# Inicialização do SpaCy
nlp = load_spacy_model()

# Configuração do Flask
app = Flask(__name__)

# Configuração da Conexão com o Banco de Dados
connection_string = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=FAMILIA\\SQLJR;'
    'DATABASE=Projeto_Opcom;'
    'UID=AgenteVirtual;'
    'PWD=cacula123'
)


def query_db(query, params=None):
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        cursor.execute(query, params if params else ())
        result = cursor.fetchall()
        conn.close()
        return result
    except Exception as e:
        logging.error(f"Database query failed: {e}")
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

# Rota para processar perguntas


@app.route('/ask', methods=['POST'])
def ask():
    user_question = request.json.get('question')

    column, query = parse_question(user_question)

    logging.info(f"User question: {user_question}")
    logging.info(f"Parsed column: {column}")
    logging.info(f"Search term: {query}")

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

    logging.info(f"SQL query: {sql_query}")
    logging.info(f"Query result: {result}")

    if result:
        if column:
            response = {column: result[0][list(
                keywords_to_columns.values()).index(column)]}
        else:
            response = {
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
    else:
        response = {
            'answer': 'Desculpe, não encontrei informações para sua pergunta.'}

    return jsonify(response)


# Ponto de entrada para execução do aplicativo
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, host='192.168.0.104')
