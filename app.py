from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import spacy
import logging
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

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

# Configuração do Flask
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f'mssql+pyodbc://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}'
    f'@{os.getenv("DB_SERVER")}/{os.getenv("DB_DATABASE")}'
    '?driver=ODBC+Driver+17+for+SQL+Server'  
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# Inicialização do SQLAlchemy
db = SQLAlchemy(app)

# Modelo para a tabela admat


class Admat(db.Model):
    __tablename__ = 'admat'
    codigo = db.Column('CÓDIGO', db.Integer, primary_key=True)
    substitutos = db.Column('SUBSTITUTOS', db.String(255))
    nome = db.Column('NOME', db.String(255))
    fabricante = db.Column('FABRICANTE', db.String(255))
    embalagem = db.Column('EMBALAGEM', db.String(255))
    preco_38 = db.Column('PREÇO 38%', db.String(255))
    comprador = db.Column('COMPRADOR', db.String(255))
    ecom = db.Column('ECOM', db.String(255))
    arred_mult = db.Column('ARRED_MULT', db.String(255))
    segmento = db.Column('SEGMENTO', db.String(255))
    categoria = db.Column('CATEGORIA', db.String(255))
    grupo = db.Column('GRUPO', db.String(255))


# Mapeamento de palavras-chave para colunas da tabela
keywords_to_columns = {
    'código': 'codigo',
    'substitutos': 'substitutos',
    'nome': 'nome',
    'fabricante': 'fabricante',
    'embalagem': 'embalagem',
    'preço': 'preco_38',
    'comprador': 'comprador',
    'ecom': 'ecom',
    'arred_mult': 'arred_mult',
    'segmento': 'segmento',
    'categoria': 'categoria',
    'grupo': 'grupo'
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

# Função para formatar a resposta


def format_response(result):
    return {
        'CÓDIGO': result.codigo,
        'SUBSTITUTOS': result.substitutos,
        'NOME': result.nome,
        'FABRICANTE': result.fabricante,
        'EMBALAGEM': result.embalagem,
        'PREÇO 38%': result.preco_38,
        'COMPRADOR': result.comprador,
        'ECOM': result.ecom,
        'ARRED_MULT': result.arred_mult,
        'SEGMENTO': result.segmento,
        'CATEGORIA': result.categoria,
        'GRUPO': result.grupo
    }

# Rota para processar perguntas


@app.route('/ask', methods=['POST'])
def ask():
    user_question = request.json.get('question')
    column, query = parse_question(user_question)

    logging.info(f"User question: {user_question}")
    logging.info(f"Parsed column: {column}")
    logging.info(f"Search term: {query}")

    if query:
        # Consultar a tabela Admat usando SQLAlchemy
        result = Admat.query.filter(
            (Admat.codigo.like(f'%{query}%')) |
            (Admat.substitutos.like(f'%{query}%')) |
            (Admat.nome.like(f'%{query}%')) |
            (Admat.fabricante.like(f'%{query}%')) |
            (Admat.embalagem.like(f'%{query}%')) |
            (Admat.preco_38.like(f'%{query}%')) |
            (Admat.comprador.like(f'%{query}%')) |
            (Admat.ecom.like(f'%{query}%')) |
            (Admat.arred_mult.like(f'%{query}%')) |
            (Admat.segmento.like(f'%{query}%')) |
            (Admat.categoria.like(f'%{query}%')) |
            (Admat.grupo.like(f'%{query}%'))
        ).all()
    else:
        result = []

    logging.info(f"Query result: {result}")

    if result:
        response = format_response(result[0])
    else:
        response = {
            'answer': 'Desculpe, não encontrei informações para sua pergunta.'}

    return jsonify(response)


# Ponto de entrada para execução do aplicativo
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
