from flask import Flask, request, jsonify, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS  # Importando o CORS
from sqlalchemy.exc import SQLAlchemyError
from flask_caching import Cache
import spacy
import logging
from dotenv import load_dotenv
import os
import re
import urllib

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Função para carregar o modelo SpaCy com fallback


def load_spacy_model() -> spacy.Language:
    try:
        return spacy.load('pt_core_news_sm')
    except OSError:
        from spacy.cli import download
        download('pt_core_news_sm')
        return spacy.load('pt_core_news_sm')


nlp = load_spacy_model()

# Verificar credenciais do banco de dados


def check_db_credentials():
    missing = [
        var for var in ["DB_USER", "DB_PASSWORD", "DB_SERVER", "DB_DATABASE"]
        if not os.getenv(var)
    ]
    if missing:
        raise ValueError(
            f"As seguintes credenciais estão faltando: {', '.join(missing)}"
        )


check_db_credentials()

# Configurações do Flask
app = Flask(__name__)
CORS(app)  # Adicionando o CORS no aplicativo

cache = Cache(
    app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300}
)

# Função para inicializar o banco de dados


def init_db(app):
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_SERVER = os.getenv("DB_SERVER").replace("\\", "\\\\")  # Corrige escape
    DB_DATABASE = os.getenv("DB_DATABASE")

    # Codificar a senha para evitar problemas com caracteres especiais
    password_encoded = urllib.parse.quote_plus(DB_PASSWORD)

    # Montar a string de conexão corretamente
    db_uri = (
        f"mssql+pymssql://{DB_USER}:{password_encoded}@{DB_SERVER}:1433/"
        f"{DB_DATABASE}"
    )

    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    return SQLAlchemy(app)


db = init_db(app)

# Modelo de tabela SQL (Admat)


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

# Função para higienizar a entrada do usuário


def sanitize_input(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text)

# Função para extrair palavras-chave


def extract_keywords(question: str) -> list:
    doc = nlp(question)
    return [
        token.text for token in doc if token.pos_ in ("NOUN", "PROPN", "ADJ")
    ]

# Função para gerar filtros para a query SQL


def generate_filters(keywords):
    conditions = []
    for kw in keywords:
        conditions.extend([
            Admat.nome.ilike(f"%{kw}%"),
            Admat.fabricante.ilike(f"%{kw}%"),
            Admat.categoria.ilike(f"%{kw}%"),
            Admat.grupo.ilike(f"%{kw}%")
        ])
    return conditions

# Função para formatar a resposta


def format_response(results: list) -> dict:
    response = [{
        'codigo': item.codigo,
        'nome': item.nome,
        'fabricante': item.fabricante,
        'preco': item.preco_38,
        'categoria': item.categoria,
        'grupo': item.grupo
    } for item in results]
    return {'answer': response}


# Blueprint para organizar as rotas
bp = Blueprint('main', __name__)

# Rota principal para consulta


@bp.route('/ask', methods=['POST'])
@cache.cached(query_string=True)  # Cache para melhorar desempenho
def ask():
    user_question = sanitize_input(request.json.get('question', '').strip())

    if not user_question:
        return jsonify({'answer': 'Por favor, forneça uma pergunta válida.'}),
    400

    if len(user_question) > 200:
        return jsonify(
            {'answer': 'A pergunta é muito longa. Por favor, seja mais breve.'}
        ), 400

    # Extrair palavras-chave
    keywords = extract_keywords(user_question)

    if not keywords:
        return jsonify({
            'answer': 'Não consegui identificar termos relevantes na pergunta'
        }), 400

    logging.info(f"Pergunta do usuário: {user_question}")
    logging.info(f"Palavras-chave extraídas: {keywords}")

    try:
        # Realizar a consulta no banco de dados
        query = db.session.query(Admat).filter(
            db.or_(*generate_filters(keywords))
        ).all()
        response = format_response(query) if query else {
            'answer': 'Desculpe, não encontrei informações relevantes.'}

    except SQLAlchemyError as e:
        logging.error(f"Erro ao consultar o banco de dados: {str(e)}")
        return jsonify({
            'answer': 'Erro ao processar sua solicitação.'
        }), 500

    return jsonify(response)


# Registrar o Blueprint
app.register_blueprint(bp)

# Configuração dos logs
logging.basicConfig(
    filename='/tmp/app.log',  # Diretório temporário para Docker
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Inicialização do servidor Flask
if __name__ == '__main__':
    DEBUG_MODE = os.getenv("FLASK_DEBUG", "False").lower() in ["true", "1"]
    app.run(host='0.0.0.0', port=int(
        os.getenv("PORT", 5000)), debug=DEBUG_MODE)
