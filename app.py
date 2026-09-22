import os
import uuid
import random
import secrets
import datetime
import logging
from datetime import timedelta
from functools import wraps
from flask import Flask, request, jsonify, session, render_template, send_from_directory, redirect, url_for
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

# O Flask, por padrão, procura os HTMLs numa pasta chamada 'templates' (com
# 's'). Como o projeto tem uma pasta 'template' (sem 's'), aceitamos as duas
# grafias automaticamente para não depender de qual delas você usou.
_PASTA_TEMPLATES = 'templates' if os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')) else 'template'
app = Flask(__name__, template_folder=_PASTA_TEMPLATES)

# Configurações de Segurança e Sessão
app.secret_key = os.getenv('SECRET_KEY', 'chave_secreta_padrao_para_testes')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

# Configuração das pastas de upload (uploads/capas, uploads/avatares, uploads/imagens)
UPLOADS_ROOT = os.path.join(os.getcwd(), 'uploads')
UPLOAD_FOLDER_AVATARES = os.path.join(UPLOADS_ROOT, 'avatares')
UPLOAD_FOLDER_CAPAS = os.path.join(UPLOADS_ROOT, 'capas')
UPLOAD_FOLDER_IMAGENS = os.path.join(UPLOADS_ROOT, 'imagens')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
os.makedirs(UPLOAD_FOLDER_AVATARES, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_CAPAS, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_IMAGENS, exist_ok=True)

# Dicionário temporário na memória para os códigos de recuperação de senha
codigos_recuperacao = {}

# =============================================================================
# 🛠️ CONEXÃO COM O BANCO DE DADOS
# =============================================================================

def get_db_connection():
    """Cria e retorna a conexão com o banco MySQL bibliotech."""
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'bibliotech'),
            port=int(os.getenv('DB_PORT', 3306))
        )
        return conn
    except Error as err:
        print(f"❌ Erro de conexão com o banco de dados: {err}")
        return None

# =============================================================================
# 📧 FUNÇÕES AUXILIARES
# =============================================================================

def arquivo_permitido(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =============================================================================
# 🔒 MIDDLEWARES DE AUTENTICAÇÃO VIA SESSÃO
# =============================================================================

def login_requerido(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario' not in session:
            return jsonify({"sucesso": False, "mensagem": "Acesso não autorizado. Faça login primeiro."}), 401
        return f(*args, **kwargs)
    return decorated

def apenas_funcionario(f):
    """Permite acesso a qualquer funcionário (Bibliotecário ou Auxiliar),
    ao contrário de apenas_administrador que exige cargo de Bibliotecário (id_cargo=1)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        usuario = session.get('usuario')
        if not usuario:
            return jsonify({"sucesso": False, "mensagem": "Acesso não autorizado. Faça login primeiro."}), 401

        if usuario.get('tipo_perfil') != 'FUNCIONARIO':
            return jsonify({"sucesso": False, "mensagem": "Acesso restrito a funcionários."}), 403

        return f(*args, **kwargs)
    return decorated

def apenas_administrador(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        usuario = session.get('usuario')
        if not usuario:
            return jsonify({"sucesso": False, "mensagem": "Acesso não autorizado. Faça login primeiro."}), 401
        
        if usuario.get('tipo_perfil') != 'FUNCIONARIO' or usuario.get('id_cargo') != 1:
            return jsonify({"sucesso": False, "mensagem": "Acesso restrito apenas para administradores."}), 403

        return f(*args, **kwargs)
    return decorated

def apenas_leitor(f):
    """Permite acesso apenas a leitores autenticados."""
    @wraps(f)
    def decorated(*args, **kwargs):
        usuario = session.get('usuario')
        if not usuario:
            return jsonify({"sucesso": False, "mensagem": "Acesso não autorizado. Faça login primeiro."}), 401

        if usuario.get('tipo_perfil') != 'LEITOR':
            return jsonify({"sucesso": False, "mensagem": "Acesso restrito a leitores."}), 403

        return f(*args, **kwargs)
    return decorated

STATUS_RESERVA_VALIDOS = ('Pendente', 'Aguardando Retirada', 'Concluida', 'Cancelada')

# Configura um log focado em auditoria (Guarde em local seguro)
LOG_FOLDER = os.path.join(os.getcwd(), 'logs')
os.makedirs(LOG_FOLDER, exist_ok=True)

logger_lgpd = logging.getLogger('auditoria_lgpd')
logger_lgpd.setLevel(logging.INFO)
logger_lgpd.propagate = False

if not logger_lgpd.handlers:
    _handler_lgpd = logging.FileHandler(
        os.path.join(LOG_FOLDER, 'auditoria_lgpd.log'), encoding='utf-8'
    )
    _handler_lgpd.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    )
    logger_lgpd.addHandler(_handler_lgpd)

# =============================================================================
# 🌐 MÓDULO: PÁGINAS DO SITE E ARQUIVOS DE UPLOAD
# =============================================================================

# 1. PÁGINA INICIAL DO SITE (templates/home.html) - OK
@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')

@app.route('/gestor', methods=['GET'])
def gestor():
    usuario = session.get('usuario')
    if not usuario or usuario.get('tipo_perfil') != 'FUNCIONARIO':
        return redirect(url_for('home'))
    return render_template('index.html')

# 1.1 PÁGINA DE CATÁLOGO (templates/catalogo.html) - OK
@app.route('/catalogo', methods=['GET'])
def catalogo():
    return render_template('catalogo.html', pagina_reservas=False, pagina_sobre_nos=False)

@app.route('/minhas-reservas', methods=['GET'])
@apenas_leitor
def pagina_minhas_reservas():
    return redirect(url_for('catalogo') + '?pagina=reservas')

@app.route('/sobre-nos', methods=['GET'])
def pagina_sobre_nos():
    return redirect(url_for('catalogo') + '#Sobre-nos')

# 2. SERVIR ARQUIVOS ENVIADOS (capas de livro, avatares de leitor, imagens do site) - OK
# Ex.: GET /static/capas/capa_livro_1_a1b2c3d4.png
#      GET /static/avatares/avatar_leitor_2_a1b2c3d4.jpg
#      GET /static/imagens/logo.png
SUBPASTAS_STATIC_VALIDAS = {
    'capas': UPLOAD_FOLDER_CAPAS,
    'avatares': UPLOAD_FOLDER_AVATARES,
    'img': UPLOAD_FOLDER_IMAGENS,
}

@app.route('/static/<subpasta>/<path:nome_arquivo>', methods=['GET'])
def servir_upload(subpasta, nome_arquivo):
    pasta = SUBPASTAS_STATIC_VALIDAS.get(subpasta)
    if not pasta:
        return send_from_directory(app.static_folder, f'{subpasta}/{nome_arquivo}')
    if os.path.isfile(os.path.join(pasta, nome_arquivo)):
        return send_from_directory(pasta, nome_arquivo)
    if subpasta == 'img' and os.path.isfile(os.path.join(app.static_folder, subpasta, nome_arquivo)):
        return send_from_directory(app.static_folder, f'{subpasta}/{nome_arquivo}')
    return jsonify({"sucesso": False, "mensagem": "Arquivo não encontrado."}), 404

@app.route('/uploads/<subpasta>/<path:nome_arquivo>', methods=['GET'])
def servir_upload_compatibilidade(subpasta, nome_arquivo):
    pasta = SUBPASTAS_STATIC_VALIDAS.get(subpasta)
    if not pasta:
        return jsonify({"sucesso": False, "mensagem": "Pasta de upload inválida."}), 404
    return send_from_directory(pasta, nome_arquivo)

# =============================================================================
# 🔐 MÓDULO DE AUTENTICAÇÃO E SESSÃO
# =============================================================================
# 1. INICIAR SESSÃO (LOGIN) - OK
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = str(data.get('email', '')).strip()
    senha = str(data.get('senha', '')).strip()

    if not email or not senha:
        return jsonify({"sucesso": False, "mensagem": "E-mail e senha são obrigatórios."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        usuario = None
        tipo_perfil = None

        # 1. Busca em funcionários
        sql_func = """
            SELECT f.id_funcionario AS id, f.nome, f.email, f.telefone, f.foto_perfil, f.senha, f.status_funcionario AS status, 
                   f.id_cargo, c.nome_cargo 
            FROM funcionarios f
            INNER JOIN cargos c ON f.id_cargo = c.id_cargo
            WHERE f.email = %s
        """
        cursor.execute(sql_func, (email,))
        usuario = cursor.fetchone()

        if usuario:
            tipo_perfil = 'FUNCIONARIO'
        else:
            # 2. Busca em leitores
            sql_leitor = """
                SELECT id_leitor AS id, nome, email, telefone, foto_perfil, senha, status_conta AS status
                FROM leitores
                WHERE email = %s
            """
            cursor.execute(sql_leitor, (email,))
            usuario = cursor.fetchone()
            if usuario:
                tipo_perfil = 'LEITOR'

        # 3. Validação de credenciais
        if not usuario or not check_password_hash(usuario['senha'], senha):
            return jsonify({"sucesso": False, "mensagem": "E-mail ou senha incorretos."}), 401

        # 4. Validação do status da conta
        status_normalizado = str(usuario.get('status', '')).upper()
        if status_normalizado in ['INATIVO', 'SUSPENSO', 'BLOQUEADO']:
            return jsonify({
                "sucesso": False,
                "mensagem": f"Conta {usuario['status'].lower()}. Entre em contato com o suporte."
            }), 403

        # 5. Criação da Sessão
        session.permanent = True
        dados_usuario = {
            "id": usuario['id'],
            "nome": usuario['nome'],
            "email": usuario['email'],
            "telefone": usuario.get('telefone'),
            "foto_perfil": usuario.get('foto_perfil'),
            "tipo_perfil": tipo_perfil,
            "id_cargo": usuario.get('id_cargo'),
            "cargo": usuario.get('nome_cargo'),
            "status": usuario.get('status')
        }
        session['usuario'] = dados_usuario

        return jsonify({
            "sucesso": True,
            "mensagem": "Login realizado com sucesso!",
            "usuario": dados_usuario
        }), 200

    except Exception as e:
        logging.error(f"Erro na autenticação: {e}")
        return jsonify({"sucesso": False, "mensagem": "Erro interno ao autenticar o usuário."}), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# 2. ENCERRAR SESSÃO (LOGOUT) - OK
@app.route('/logout', methods=['POST'])
@login_requerido
def logout():
    session.clear()
    return jsonify({"sucesso": True, "mensagem": "Sessão encerrada com sucesso."}), 200

# 3. RETORNAR PERFIL DO USUÁRIO LOGADO - OK
@app.route('/me', methods=['GET'])
@login_requerido
def obter_perfil_logado():
    return jsonify({
        "sucesso": True,
        "usuario": session.get('usuario')
    }), 200

# =============================================================================
# ⚙️ MÓDULO ADMINISTRATIVO: CRUD DE FUNCIONÁRIOS (SESSÃO)
# =============================================================================
# 1. LISTAR TODOS OS FUNCIONÁRIOS - OK
@app.route('/funcionarios', methods=['GET'])
@apenas_administrador
def listar_funcionarios():
    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        sql = """
                 SELECT f.id_funcionario, f.nome, f.email, f.telefone, f.id_cargo,
                     f.status_funcionario, f.data_cadastro, c.nome_cargo 
            FROM funcionarios f
            INNER JOIN cargos c ON f.id_cargo = c.id_cargo
        """
        cursor.execute(sql)
        funcionarios = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({"sucesso": True, "funcionarios": funcionarios}), 200
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao buscar funcionários: {str(e)}"}), 500

@app.route('/funcionarios/me', methods=['PUT'])
@apenas_funcionario
def editar_meus_dados_funcionario():
    data = request.get_json() or {}
    usuario_logado = session.get('usuario', {})
    email = str(data.get('email', '')).strip().lower()
    telefone = str(data.get('telefone', '')).strip()
    nome = str(data.get('nome', '')).strip()
    status_funcionario = str(data.get('status_funcionario', '')).strip()
    senha_atual = str(data.get('senha_atual', ''))
    nova_senha = str(data.get('nova_senha', ''))
    id_funcionario = usuario_logado.get('id')
    pode_editar_tudo = usuario_logado.get('id_cargo') == 1

    if not email or not telefone or (pode_editar_tudo and (not nome or not status_funcionario)):
        return jsonify({"sucesso": False, "mensagem": "Preencha os dados obrigatórios do perfil."}), 400
    if senha_atual or nova_senha:
        if not senha_atual or not nova_senha:
            return jsonify({"sucesso": False, "mensagem": "Informe a senha atual e a nova senha."}), 400
        if len(nova_senha) < 6:
            return jsonify({"sucesso": False, "mensagem": "A nova senha deve ter pelo menos 6 caracteres."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id_funcionario, senha, nome, id_cargo, status_funcionario FROM funcionarios WHERE id_funcionario = %s",
            (id_funcionario,)
        )
        funcionario = cursor.fetchone()
        if not funcionario:
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Funcionário não encontrado."}), 404
        if not pode_editar_tudo and (
            (nome and nome != funcionario['nome']) or
            data.get('id_cargo') is not None or
            (status_funcionario and status_funcionario != funcionario['status_funcionario'])
        ):
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Somente o bibliotecário pode alterar nome, cargo ou status."}), 403
        if senha_atual and (not funcionario or not check_password_hash(funcionario['senha'], senha_atual)):
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "A senha atual está incorreta."}), 400

        cursor.execute(
            "SELECT id_funcionario FROM funcionarios WHERE email = %s AND id_funcionario <> %s",
            (email, id_funcionario)
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Este e-mail já está cadastrado."}), 400

        if pode_editar_tudo and nova_senha:
            cursor.execute(
                "UPDATE funcionarios SET nome = %s, id_cargo = %s, status_funcionario = %s, email = %s, telefone = %s, senha = %s WHERE id_funcionario = %s",
                (nome, data.get('id_cargo'), status_funcionario, email, telefone, generate_password_hash(nova_senha), id_funcionario)
            )
        elif pode_editar_tudo:
            cursor.execute(
                "UPDATE funcionarios SET nome = %s, id_cargo = %s, status_funcionario = %s, email = %s, telefone = %s WHERE id_funcionario = %s",
                (nome, data.get('id_cargo'), status_funcionario, email, telefone, id_funcionario)
            )
        elif nova_senha:
            cursor.execute(
                "UPDATE funcionarios SET email = %s, telefone = %s, senha = %s WHERE id_funcionario = %s",
                (email, telefone, generate_password_hash(nova_senha), id_funcionario)
            )
        else:
            cursor.execute(
                "UPDATE funcionarios SET email = %s, telefone = %s WHERE id_funcionario = %s",
                (email, telefone, id_funcionario)
            )
        conn.commit()
        cursor.close()
        conn.close()

        session['usuario']['email'] = email
        session['usuario']['telefone'] = telefone
        if pode_editar_tudo:
            session['usuario']['nome'] = nome
            session['usuario']['id_cargo'] = int(data.get('id_cargo'))
            session['usuario']['status'] = status_funcionario
        session.modified = True
        return jsonify({"sucesso": True, "mensagem": "Seus dados foram atualizados com sucesso."}), 200
    except Exception as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao atualizar seus dados: {str(e)}"}), 500

@app.route('/funcionarios/avatar', methods=['POST'])
@apenas_funcionario
def upload_avatar_funcionario():
    if 'foto' not in request.files or not request.files['foto'].filename:
        return jsonify({"sucesso": False, "mensagem": "Nenhuma foto selecionada."}), 400

    file = request.files['foto']
    if not arquivo_permitido(file.filename):
        return jsonify({"sucesso": False, "mensagem": "Formato não permitido (use PNG, JPG, JPEG ou WEBP)."}), 400

    usuario_logado = session.get('usuario', {})
    extensao = file.filename.rsplit('.', 1)[1].lower()
    nome_arquivo = f"avatar_funcionario_{usuario_logado['id']}_{uuid.uuid4().hex[:8]}.{extensao}"
    file.save(os.path.join(UPLOAD_FOLDER_AVATARES, nome_arquivo))
    url_relativa = f"/static/avatares/{nome_arquivo}"

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE funcionarios SET foto_perfil = %s WHERE id_funcionario = %s",
            (url_relativa, usuario_logado['id'])
        )
        conn.commit()
        cursor.close()
        conn.close()
        session['usuario']['foto_perfil'] = url_relativa
        session.modified = True
        return jsonify({"sucesso": True, "mensagem": "Foto de perfil atualizada!", "foto_perfil": url_relativa}), 200
    except Exception as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao salvar a foto: {str(e)}"}), 500

# 2. CADASTRAR FUNCIONÁRIO - OK 
@app.route('/funcionarios', methods=['POST'])
@apenas_administrador
def criar_funcionario():
    data = request.get_json() or {}

    nome = str(data.get('nome', '')).strip()
    email = str(data.get('email', '')).strip()
    telefone = str(data.get('telefone', '')).strip()
    senha = str(data.get('senha', '')).strip()
    id_cargo = data.get('id_cargo')

    if not nome or not email or not telefone or not senha or not id_cargo:
        return jsonify({"sucesso": False, "mensagem": "Preencha todos os campos obrigatórios."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id_funcionario FROM funcionarios WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Este e-mail já está cadastrado."}), 400

        senha_hash = generate_password_hash(senha)

        sql = """
            INSERT INTO funcionarios (nome, id_cargo, email, telefone, senha, tipo_perfil, status_funcionario)
            VALUES (%s, %s, %s, %s, %s, 'FUNCIONARIO', 'Ativo')
        """
        cursor.execute(sql, (nome, id_cargo, email, telefone, senha_hash))
        conn.commit()

        novo_id = cursor.lastrowid
        cursor.close()
        conn.close()

        return jsonify({"sucesso": True, "mensagem": "Funcionário cadastrado com sucesso!", "id_funcionario": novo_id}), 201

    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao cadastrar funcionário: {str(e)}"}), 400

# 3. EDITAR FUNCIONÁRIO (EXCLUSIVO PARA ADMINISTRADOR) - OK
@app.route('/funcionarios/<int:id_funcionario>', methods=['PUT'])
@apenas_administrador
def editar_funcionario(id_funcionario):
    data = request.get_json() or {}

    usuario_responsavel = session.get('usuario', {}).get('email')

    nome = str(data.get('nome', '')).strip()
    telefone = str(data.get('telefone', '')).strip()
    status_funcionario = str(data.get('status_funcionario', 'Ativo')).strip()
    
    try:
        id_cargo = int(data.get('id_cargo'))
    except (ValueError, TypeError):
        id_cargo = None

    if not nome or not telefone or not id_cargo:
        return jsonify({"sucesso": False, "mensagem": "Nome, Telefone e Cargo são obrigatórios."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)

        sql = """
            UPDATE funcionarios 
            SET nome = %s, telefone = %s, id_cargo = %s, status_funcionario = %s
            WHERE id_funcionario = %s
        """
        cursor.execute(sql, (nome, telefone, id_cargo, status_funcionario, id_funcionario))
        conn.commit()
        linhas_afetadas = cursor.rowcount

        cursor.close()
        conn.close()

        if linhas_afetadas == 0:
            return jsonify({"sucesso": False, "mensagem": "Nenhum funcionário encontrado ou nenhuma alteração realizada."}), 404

        # 2. TRILHA DE AUDITORIA (Exigência da LGPD)
        # Registra a ação sem expor explicitamente o dado novo no log de texto comum
        logger_lgpd.info(
            f"Auditoria LGPD: Usuário [{usuario_responsavel}] MODIFICOU os dados "
            f"pessoais do funcionário ID [{id_funcionario}]."
        )

        return jsonify({"sucesso": True, "mensagem": "Dados do funcionário atualizados com sucesso!"}), 200

    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        
        # 3. SEGURANÇA: Salva o erro real no servidor, mas esconde do usuário externo
        logger_lgpd.error(f"Erro crítico na edição do funcionário {id_funcionario}: {str(e)}")
        return jsonify({
            "sucesso": False, 
            "mensagem": "Erro interno no servidor ao processar a atualização. Tente novamente mais tarde."
        }), 500

# 4. EXCLUIR / INATIVAR FUNCIONÁRIO - OK
@app.route('/funcionarios/<int:id_funcionario>', methods=['DELETE'])
@apenas_administrador
def excluir_funcionario(id_funcionario):
    usuario_logado = session.get('usuario', {})

    if id_funcionario == usuario_logado.get('id'):
        return jsonify({"sucesso": False, "mensagem": "Você não pode excluir sua própria conta enquanto estiver logado."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM funcionarios WHERE id_funcionario = %s", (id_funcionario,))
            conn.commit()
            cursor.close()
            conn.close()

            logger_lgpd.info(f"Auditoria LGPD: Exclusão total do funcionário ID [{id_funcionario}].")
            return jsonify({"sucesso": True, "mensagem": "Funcionário excluído com sucesso."}), 200

        except mysql.connector.Error as err:
            conn.rollback()
            if err.errno == 1451:  # Restrição de Chave Estrangeira (vínculos com empréstimos)
                senha_inutilizavel = generate_password_hash(secrets.token_hex(16))
                cursor.execute("""
                    UPDATE funcionarios 
                    SET nome = 'Ex-Funcionário (Anonimizado)',
                        email = CONCAT('ex_func_', id_funcionario, '@lgpd.deleted'),
                        telefone = '',
                        senha = %s,
                        foto_perfil = 'default_profile.png',
                        status_funcionario = 'Bloqueado'
                    WHERE id_funcionario = %s
                """, (senha_inutilizavel, id_funcionario))
                conn.commit()
                cursor.close()
                conn.close()

                logger_lgpd.info(f"Auditoria LGPD: Dados pessoais do funcionário ID [{id_funcionario}] foram anonimizados devido a vínculos históricos.")
                return jsonify({
                    "sucesso": True, 
                    "mensagem": "O funcionário possui registros vinculados no histórico. Seus dados pessoais foram anonimizados conforme a LGPD."
                }), 200
            
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Restrição de banco de dados ao tentar excluir."}), 400

    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro interno ao tentar excluir: {str(e)}"}), 500

# =============================================================================
# 📚 MÓDULO: ACERVO DE LIVROS
# =============================================================================
STATUS_LIVRO_VALIDOS = ('Ativo', 'Indisponível')

def _recalcular_status_exemplar(cursor, id_livro):
    """Recalcula e grava livro.status_exemplar com base no estoque atual
    e nos empréstimos ativos, mantendo o campo sincronizado após qualquer
    alteração manual de quant_estoque. Se o livro passar a ficar
    'Disponível' (saindo de outro status), dispara as notificações de
    interesse pendentes para esse livro."""
    cursor.execute("SELECT status_exemplar FROM livro WHERE id_livro = %s", (id_livro,))
    status_anterior = cursor.fetchone()['status_exemplar']

    cursor.execute(
        "SELECT COUNT(*) AS total FROM emprestimos WHERE id_livro = %s AND data_devolucao_real IS NULL",
        (id_livro,)
    )
    total_emprestados = cursor.fetchone()['total']

    cursor.execute("SELECT quant_estoque FROM livro WHERE id_livro = %s", (id_livro,))
    qtd_estoque = cursor.fetchone()['quant_estoque']

    if total_emprestados >= qtd_estoque:
        novo_status = 'Emprestado'
    else:
        cursor.execute(
            "SELECT COUNT(*) AS total FROM reservas WHERE id_livro = %s AND status_reserva = 'Aguardando Retirada'",
            (id_livro,)
        )
        aguardando_retirada = cursor.fetchone()['total']
        novo_status = 'Reservado' if aguardando_retirada > 0 else 'Disponível'

    cursor.execute("UPDATE livro SET status_exemplar = %s WHERE id_livro = %s", (novo_status, id_livro))

    if novo_status == 'Disponível' and status_anterior != 'Disponível':
        pass
    return novo_status

# 1. LISTAR CATÁLOGO PÚBLICO DE LIVROS ATIVOS - OK
@app.route('/livros', methods=['GET'])
def listar_livros():
    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT l.id_livro, l.titulo, l.autor, l.ano_publicacao, l.quant_estoque, l.sinopse,
                   l.capa, l.posicao_estante, l.status_exemplar, l.status_livro,
                   l.id_categoria, c.nome_categoria,
                       ROUND(AVG(a.nota), 1) AS media_avaliacoes, COUNT(a.id_avaliacao) AS total_avaliacoes,
                       (SELECT COUNT(*) FROM emprestimos e1 WHERE e1.id_livro = l.id_livro AND e1.data_devolucao_real IS NULL) AS exemplares_emprestados,
                       (SELECT COUNT(*) FROM reservas r1 WHERE r1.id_livro = l.id_livro AND r1.status_reserva IN ('Pendente', 'Aguardando Retirada')) AS exemplares_reservados,
                       (SELECT MIN(e2.data_devolucao_prevista) FROM emprestimos e2 WHERE e2.id_livro = l.id_livro AND e2.data_devolucao_real IS NULL) AS proxima_devolucao
            FROM livro l
            INNER JOIN categorias c ON l.id_categoria = c.id_categoria
            LEFT JOIN avaliacoes a ON a.livro_id = l.id_livro
            WHERE l.status_livro = 'Ativo'
            GROUP BY l.id_livro
            ORDER BY l.titulo ASC
        """
        cursor.execute(sql)
        livros = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({"sucesso": True, "livros": livros}), 200
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao buscar livros: {str(e)}"}), 500


# 3. EXIBIR DETALHES DO LIVRO E MÉDIA DE NOTAS - OK
@app.route('/livros/<int:id_livro>', methods=['GET'])
def detalhar_livro(id_livro):
    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT l.id_livro, l.titulo, l.autor, l.ano_publicacao, l.quant_estoque, l.sinopse,
                   l.capa, l.posicao_estante, l.status_exemplar, l.status_livro,
                   l.id_categoria, c.nome_categoria,
                       ROUND(AVG(a.nota), 1) AS media_avaliacoes, COUNT(a.id_avaliacao) AS total_avaliacoes,
                       (SELECT COUNT(*) FROM emprestimos e1 WHERE e1.id_livro = l.id_livro AND e1.data_devolucao_real IS NULL) AS exemplares_emprestados,
                       (SELECT COUNT(*) FROM reservas r1 WHERE r1.id_livro = l.id_livro AND r1.status_reserva IN ('Pendente', 'Aguardando Retirada')) AS exemplares_reservados,
                       (SELECT MIN(e2.data_devolucao_prevista) FROM emprestimos e2 WHERE e2.id_livro = l.id_livro AND e2.data_devolucao_real IS NULL) AS proxima_devolucao
            FROM livro l
            INNER JOIN categorias c ON l.id_categoria = c.id_categoria
            LEFT JOIN avaliacoes a ON a.livro_id = l.id_livro
            WHERE l.id_livro = %s
            GROUP BY l.id_livro
        """
        cursor.execute(sql, (id_livro,))
        livro = cursor.fetchone()
        cursor.close()
        conn.close()

        if not livro:
            return jsonify({"sucesso": False, "mensagem": "Livro não encontrado."}), 404

        return jsonify({"sucesso": True, "livro": livro}), 200
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao buscar livro: {str(e)}"}), 500

# 4. CADASTRAR LIVRO E VINCULAR CATEGORIA (funcionários) - OK
@app.route('/livros', methods=['POST'])
@apenas_funcionario
def criar_livro():
    data = request.get_json() or {}

    titulo = str(data.get('titulo', '')).strip()
    autor = str(data.get('autor', '')).strip()
    ano_publicacao = data.get('ano_publicacao')
    quant_estoque = data.get('quant_estoque', 1)
    sinopse = data.get('sinopse')
    posicao_estante = data.get('posicao_estante')
    id_categoria = data.get('id_categoria')

    if not titulo or not autor or not id_categoria:
        return jsonify({"sucesso": False, "mensagem": "Título, autor e id_categoria são obrigatórios."}), 400

    try:
        quant_estoque = int(quant_estoque)
        if quant_estoque < 1:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"sucesso": False, "mensagem": "quant_estoque deve ser um número inteiro maior que zero."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id_categoria FROM categorias WHERE id_categoria = %s", (id_categoria,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Categoria informada não existe."}), 400

        sql = """
            INSERT INTO livro (titulo, autor, ano_publicacao, quant_estoque, sinopse, posicao_estante, id_categoria)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (titulo, autor, ano_publicacao, quant_estoque, sinopse, posicao_estante, id_categoria))
        conn.commit()

        novo_id = cursor.lastrowid
        cursor.close()
        conn.close()

        return jsonify({"sucesso": True, "mensagem": "Livro cadastrado com sucesso!", "id_livro": novo_id}), 201

    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao cadastrar livro: {str(e)}"}), 400

# 5. EDITAR INFORMAÇÕES DO LIVRO (funcionários) - OK
@app.route('/livros/<int:id_livro>', methods=['PUT'])
@apenas_funcionario
def editar_livro(id_livro):
    data = request.get_json() or {}

    titulo = str(data.get('titulo', '')).strip()
    autor = str(data.get('autor', '')).strip()
    ano_publicacao = data.get('ano_publicacao')
    sinopse = data.get('sinopse')
    posicao_estante = data.get('posicao_estante')
    id_categoria = data.get('id_categoria')

    try:
        quant_estoque = int(data.get('quant_estoque'))
        if quant_estoque < 1:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"sucesso": False, "mensagem": "quant_estoque deve ser um número inteiro maior que zero."}), 400

    if not titulo or not autor or not id_categoria:
        return jsonify({"sucesso": False, "mensagem": "Título, autor e id_categoria são obrigatórios."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id_livro FROM livro WHERE id_livro = %s", (id_livro,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Livro não encontrado."}), 404

        cursor.execute("SELECT id_categoria FROM categorias WHERE id_categoria = %s", (id_categoria,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Categoria informada não existe."}), 400

        sql = """
            UPDATE livro
            SET titulo = %s, autor = %s, ano_publicacao = %s, quant_estoque = %s,
                sinopse = %s, posicao_estante = %s, id_categoria = %s
            WHERE id_livro = %s
        """
        cursor.execute(sql, (titulo, autor, ano_publicacao, quant_estoque, sinopse, posicao_estante, id_categoria, id_livro))

        # Mantém livro.status_exemplar sincronizado com o novo quant_estoque
        novo_status_exemplar = _recalcular_status_exemplar(cursor, id_livro)

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "sucesso": True,
            "mensagem": "Livro atualizado com sucesso!",
            "status_exemplar": novo_status_exemplar
        }), 200

    except Exception as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao editar livro: {str(e)}"}), 400

@app.route('/livros/<int:id_livro>', methods=['DELETE'])
@apenas_funcionario
def excluir_livro(id_livro):
    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_livro FROM livro WHERE id_livro = %s", (id_livro,))
        if not cursor.fetchone():
            return jsonify({"sucesso": False, "mensagem": "Livro não encontrado."}), 404
        cursor.execute("UPDATE livro SET status_livro = 'Indisponível' WHERE id_livro = %s", (id_livro,))
        conn.commit()
        return jsonify({"sucesso": True, "mensagem": "Livro movido para excluídos com sucesso!"}), 200
    except Exception as e:
        if conn and conn.is_connected():
            conn.rollback()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao excluir livro: {str(e)}"}), 400
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/livros-excluidos', methods=['GET'])
@apenas_funcionario
def listar_livros_excluidos():
    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT l.id_livro, l.titulo, l.autor, l.ano_publicacao, l.quant_estoque,
                   l.sinopse, l.id_categoria, c.nome_categoria, l.posicao_estante,
                   l.status_livro
            FROM livro l
            INNER JOIN categorias c ON c.id_categoria = l.id_categoria
            WHERE l.status_livro IN ('Indisponível', 'Indisponivel')
            ORDER BY l.titulo ASC
        """)
        livros = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"sucesso": True, "livros": livros}), 200
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao buscar livros excluídos: {str(e)}"}), 500

@app.route('/livros/<int:id_livro>/restaurar', methods=['PUT'])
@apenas_funcionario
def restaurar_livro(id_livro):
    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE livro SET status_livro = 'Ativo' WHERE id_livro = %s AND status_livro IN ('Indisponível', 'Indisponivel')", (id_livro,))
        if cursor.rowcount == 0:
            return jsonify({"sucesso": False, "mensagem": "Livro excluído não encontrado."}), 404
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"sucesso": True, "mensagem": "Livro restaurado com sucesso!"}), 200
    except Exception as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao restaurar livro: {str(e)}"}), 400

# 6. ALTERNAR STATUS DO LIVRO (Ativo/Indisponível) (funcionários) - OK
@app.route('/livrosstatus/<int:id_livro>/', methods=['PUT'])
@apenas_funcionario
def alternar_status_livro(id_livro):
    data = request.get_json() or {}
    novo_status = str(data.get('status_livro', '')).strip()

    if novo_status not in STATUS_LIVRO_VALIDOS:
        return jsonify({
            "sucesso": False,
            "mensagem": f"Status inválido. Use um dos seguintes: {', '.join(STATUS_LIVRO_VALIDOS)}."
        }), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE livro SET status_livro = %s WHERE id_livro = %s", (novo_status, id_livro))
        conn.commit()
        linhas_afetadas = cursor.rowcount
        cursor.close()
        conn.close()

        if linhas_afetadas == 0:
            return jsonify({"sucesso": False, "mensagem": "Livro não encontrado."}), 404

        return jsonify({"sucesso": True, "mensagem": f"Status do livro atualizado para '{novo_status}'."}), 200

    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao atualizar status: {str(e)}"}), 500

# 7. ENVIAR IMAGEM DA CAPA (funcionários) - OK
@app.route('/livros/<int:id_livro>/capa', methods=['POST'])
@apenas_funcionario
def upload_capa_livro(id_livro):
    if 'capa' not in request.files:
        return jsonify({"sucesso": False, "mensagem": "Nenhum arquivo enviado."}), 400

    file = request.files['capa']

    if file.filename == '':
        return jsonify({"sucesso": False, "mensagem": "Nenhum arquivo selecionado."}), 400

    if not file or not arquivo_permitido(file.filename):
        return jsonify({"sucesso": False, "mensagem": "Formato não permitido (use PNG, JPG, JPEG ou WEBP)."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id_livro FROM livro WHERE id_livro = %s", (id_livro,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Livro não encontrado."}), 404

        extensao = file.filename.rsplit('.', 1)[1].lower()
        nome_arquivo = f"capa_livro_{id_livro}_{uuid.uuid4().hex[:8]}.{extensao}"
        caminho_salvar = os.path.join(UPLOAD_FOLDER_CAPAS, nome_arquivo)
        file.save(caminho_salvar)

        url_relativa = f"/uploads/capas/{nome_arquivo}"

        cursor.execute("UPDATE livro SET capa = %s WHERE id_livro = %s", (url_relativa, id_livro))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"sucesso": True, "mensagem": "Capa atualizada com sucesso!", "capa": url_relativa}), 200

    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao salvar capa: {str(e)}"}), 500

# =============================================================================
# 📂 MÓDULO: CATEGORIAS (CRUD COMPLETO)
# =============================================================================

# 1. CADASTRAR CATEGORIA (funcionários) - OK
@app.route('/categorias', methods=['POST'])
@apenas_funcionario
def criar_categoria():
    data = request.get_json() or {}
    nome_categoria = str(data.get('nome_categoria', '')).strip()

    if not nome_categoria:
        return jsonify({"sucesso": False, "mensagem": "O campo nome_categoria é obrigatório."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categorias (nome_categoria) VALUES (%s)", (nome_categoria,))
        conn.commit()
        novo_id = cursor.lastrowid
        cursor.close()
        conn.close()

        return jsonify({"sucesso": True, "mensagem": "Categoria cadastrada com sucesso!", "id_categoria": novo_id}), 201

    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao cadastrar categoria: {str(e)}"}), 400

# 2. LISTAR TODAS AS CATEGORIAS - OK
@app.route('/categorias', methods=['GET'])
def listar_categorias():
    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_categoria, nome_categoria FROM categorias ORDER BY nome_categoria ASC")
        categorias = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({"sucesso": True, "categorias": categorias}), 200
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao listar categorias: {str(e)}"}), 500

@app.route('/catalogos-em-alta', methods=['GET'])
def listar_catalogos_em_alta():
    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.id_categoria, c.nome_categoria,
                   COUNT(r.id_reserva) AS total_reservas
            FROM categorias c
            INNER JOIN livro l ON l.id_categoria = c.id_categoria
            LEFT JOIN reservas r ON r.id_livro = l.id_livro
            WHERE l.status_livro = 'Ativo'
            GROUP BY c.id_categoria, c.nome_categoria
            ORDER BY total_reservas DESC, c.nome_categoria ASC
            LIMIT 3
        """)
        catalogos = cursor.fetchall()
        return jsonify({"sucesso": True, "catalogos": catalogos}), 200
    except Exception as e:
        return jsonify({"sucesso": False, "mensagem": f"Erro ao buscar catálogos em alta: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# 4. EDITAR NOME DA CATEGORIA (funcionários) - OK
@app.route('/categorias/<int:id_categoria>', methods=['PUT'])
@apenas_funcionario
def editar_categoria(id_categoria):
    data = request.get_json() or {}
    nome_categoria = str(data.get('nome_categoria', '')).strip()

    if not nome_categoria:
        return jsonify({"sucesso": False, "mensagem": "O campo nome_categoria é obrigatório."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE categorias SET nome_categoria = %s WHERE id_categoria = %s", (nome_categoria, id_categoria))
        conn.commit()
        linhas_afetadas = cursor.rowcount
        cursor.close()
        conn.close()

        if linhas_afetadas == 0:
            return jsonify({"sucesso": False, "mensagem": "Categoria não encontrada."}), 404

        return jsonify({"sucesso": True, "mensagem": "Categoria atualizada com sucesso!"}), 200
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao editar categoria: {str(e)}"}), 500

# 5. EXCLUIR CATEGORIA (funcionários) - OK
@app.route('/categorias/<int:id_categoria>', methods=['DELETE'])
@apenas_funcionario
def excluir_categoria(id_categoria):
    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM categorias WHERE id_categoria = %s", (id_categoria,))
            conn.commit()
            linhas_afetadas = cursor.rowcount
            cursor.close()
            conn.close()

            if linhas_afetadas == 0:
                return jsonify({"sucesso": False, "mensagem": "Categoria não encontrada."}), 404

            return jsonify({"sucesso": True, "mensagem": "Categoria excluída com sucesso."}), 200

        except mysql.connector.Error as err:
            conn.rollback()
            cursor.close()
            conn.close()
            if err.errno == 1451:  # Restrição de Chave Estrangeira (livros vinculados)
                return jsonify({
                    "sucesso": False,
                    "mensagem": "Não é possível excluir: existem livros vinculados a esta categoria."
                }), 400
            return jsonify({"sucesso": False, "mensagem": "Restrição de banco de dados ao tentar excluir."}), 400

    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro interno ao tentar excluir: {str(e)}"}), 500

# =============================================================================
# 👥 MÓDULO: LEITORES E LGPD
# =============================================================================

@app.route('/leitores', methods=['POST'])
def cadastrar_leitor():
    data = request.get_json() or {}

    nome = str(data.get('nome', '')).strip()
    email = str(data.get('email', '')).strip()
    telefone = str(data.get('telefone', '')).strip()
    senha = str(data.get('senha', '')).strip()
    foto_perfil = str(data.get('foto_perfil', '')).strip() or 'https://api.dicebear.com/9.x/notionists/svg?seed=Lumina'
    consentimento_lgpd = data.get('consentimento_lgpd')

    if not nome or not email or not telefone or not senha:
        return jsonify({"sucesso": False, "mensagem": "Nome, e-mail, telefone e senha são obrigatórios."}), 400
    
    if not bool(consentimento_lgpd):
        return jsonify({
            "sucesso": False, 
            "mensagem": "É necessário aceitar os termos da LGPD para se cadastrar."
        }), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id_leitor FROM leitores WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Este e-mail já está cadastrado."}), 400

        senha_hash = generate_password_hash(senha)

        sql = """
            INSERT INTO leitores (nome, email, telefone, senha, consentimento_lgpd, foto_perfil, tipo_perfil, status_conta)
            VALUES (%s, %s, %s, %s, %s, %s, 'LEITOR', 'Ativo')
        """
        cursor.execute(sql, (nome, email, telefone, senha_hash, consentimento_lgpd, foto_perfil))
        conn.commit()

        novo_id = cursor.lastrowid
        cursor.close()
        conn.close()

        logger_lgpd.info(f"Auditoria LGPD: Novo leitor cadastrado ID [{novo_id}] com consentimento registrado ({consentimento_lgpd}).")
        
        return jsonify({"sucesso": True, "mensagem": "Cadastro realizado com sucesso!", "id_leitor": novo_id}), 201

    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao cadastrar leitor: {str(e)}"}), 500


@app.route('/reservas', methods=['POST'])
@apenas_leitor
def criar_reserva():
    usuario_logado = session.get('usuario')
    data = request.get_json() or {}
    id_livro = data.get('id_livro')

    if not id_livro:
        return jsonify({"sucesso": False, "mensagem": "O campo id_livro é obrigatório."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_livro, quant_estoque, status_livro FROM livro WHERE id_livro = %s", (id_livro,))
        livro = cursor.fetchone()
        if not livro:
            return jsonify({"sucesso": False, "mensagem": "Livro não encontrado."}), 404
        if livro['status_livro'] != 'Ativo':
            return jsonify({"sucesso": False, "mensagem": "Este livro está indisponível."}), 400

        cursor.execute("SELECT id_reserva FROM reservas WHERE id_livro = %s AND id_leitor = %s AND status_reserva IN ('Pendente', 'Aguardando Retirada')", (id_livro, usuario_logado['id']))
        if cursor.fetchone():
            return jsonify({"sucesso": False, "mensagem": "Você já possui uma reserva ativa para este livro."}), 400

        cursor.execute("SELECT COUNT(*) AS total FROM emprestimos WHERE id_leitor = %s AND data_devolucao_real IS NULL", (usuario_logado['id'],))
        if cursor.fetchone()['total'] >= 3:
            return jsonify({"sucesso": False, "mensagem": "Você já atingiu o limite de 3 empréstimos ativos e não pode fazer novas reservas."}), 400

        cursor.execute("SELECT COUNT(*) AS total FROM reservas WHERE id_leitor = %s AND status_reserva IN ('Pendente', 'Aguardando Retirada')", (usuario_logado['id'],))
        if cursor.fetchone()['total'] >= 3:
            return jsonify({"sucesso": False, "mensagem": "Você já atingiu o limite de 3 reservas ativas."}), 400

        cursor.execute("SELECT COUNT(*) AS total FROM emprestimos WHERE id_livro = %s AND data_devolucao_real IS NULL", (id_livro,))
        emprestados = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) AS total FROM reservas WHERE id_livro = %s AND status_reserva IN ('Pendente', 'Aguardando Retirada')", (id_livro,))
        reservados = cursor.fetchone()['total']
        disponiveis = int(livro['quant_estoque']) - emprestados - reservados
        if disponiveis <= 0:
            return jsonify({"sucesso": False, "mensagem": "Não há exemplares disponíveis para reserva no momento."}), 400

        cursor.execute(
            "INSERT INTO reservas (id_livro, id_leitor, status_reserva) VALUES (%s, %s, 'Aguardando Retirada')",
            (id_livro, usuario_logado['id'])
        )
        conn.commit()
        novo_id = cursor.lastrowid
        return jsonify({"sucesso": True, "mensagem": "Reserva realizada com sucesso!", "id_reserva": novo_id}), 201
    except mysql.connector.Error as err:
        if conn.is_connected():
            conn.rollback()
        if err.errno == 1644:
            return jsonify({"sucesso": False, "mensagem": err.msg}), 400
        return jsonify({"sucesso": False, "mensagem": "Erro ao registrar reserva."}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route('/reservas', methods=['GET'])
@apenas_leitor
def listar_minhas_reservas():
    usuario_logado = session.get('usuario')
    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT r.id_reserva, r.id_livro, l.titulo, l.autor, l.capa,
                   r.data_reserva, r.status_reserva, r.posicao_fila_notificada
            FROM reservas r
            INNER JOIN livro l ON l.id_livro = r.id_livro
            WHERE r.id_leitor = %s
            ORDER BY r.data_reserva DESC
        """, (usuario_logado['id'],))
        reservas = cursor.fetchall()
        return jsonify({"sucesso": True, "reservas": reservas}), 200
    except Exception as e:
        return jsonify({"sucesso": False, "mensagem": f"Erro ao buscar reservas: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route('/reservas/<int:id_reserva>', methods=['DELETE'])
@apenas_leitor
def cancelar_reserva(id_reserva):
    usuario_logado = session.get('usuario')
    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE reservas
            SET status_reserva = 'Cancelada'
            WHERE id_reserva = %s AND id_leitor = %s
              AND status_reserva IN ('Pendente', 'Aguardando Retirada')
        """, (id_reserva, usuario_logado['id']))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"sucesso": False, "mensagem": "Reserva não encontrada ou não pode mais ser cancelada."}), 404
        return jsonify({"sucesso": True, "mensagem": "Reserva cancelada com sucesso."}), 200
    except Exception as e:
        if conn and conn.is_connected():
            conn.rollback()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao cancelar reserva: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route('/leitores', methods=['GET'])
@apenas_administrador
def listar_leitores():
    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT id_leitor, nome, email, telefone, foto_perfil, status_conta, consentimento_lgpd, data_cadastro FROM leitores"
        cursor.execute(sql)
        leitores = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({"sucesso": True, "leitores": leitores}), 200

    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao listar leitores: {str(e)}"}), 500


@app.route('/leitores/busca', methods=['GET'])
@apenas_funcionario
def buscar_leitores_funcionario():
    termo = request.args.get('q', '').strip()
    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id_leitor, nome, email, status_conta FROM leitores WHERE status_conta = 'Ativo' AND nome LIKE %s ORDER BY nome ASC LIMIT 100",
            (f"%{termo}%",)
        )
        leitores = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"sucesso": True, "leitores": leitores}), 200
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao buscar leitores: {str(e)}"}), 500

@app.route('/leitores/<int:id_leitor>', methods=['GET'])
@login_requerido
def consultar_leitor(id_leitor):
    usuario_logado = session.get('usuario')

    if usuario_logado['tipo_perfil'] == 'LEITOR' and usuario_logado['id'] != id_leitor:
        return jsonify({"sucesso": False, "mensagem": "Você só pode consultar seu próprio perfil."}), 403

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT id_leitor, nome, email, telefone, foto_perfil, status_conta, consentimento_lgpd, data_cadastro FROM leitores WHERE id_leitor = %s"
        cursor.execute(sql, (id_leitor,))
        leitor = cursor.fetchone()

        cursor.close()
        conn.close()

        if not leitor:
            return jsonify({"sucesso": False, "mensagem": "Leitor não encontrado."}), 404

        return jsonify({"sucesso": True, "leitor": leitor}), 200

    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao consultar leitor: {str(e)}"}), 500

#ROTA ATUALIZAR DADOS DO LEITOR - OK
@app.route('/leitores/dados', methods=['PUT'])
@login_requerido
def atualizar_dados_leitor():
    usuario_logado = session.get('usuario')
    if usuario_logado['tipo_perfil'] != 'LEITOR':
        return jsonify({"sucesso": False, "mensagem": "Esta rota é exclusiva para leitores."}), 403

    data = request.get_json() or {}
    nome = str(data.get('nome', '')).strip()
    telefone = str(data.get('telefone', '')).strip()
    foto_perfil = str(data.get('foto_perfil', '')).strip()

    if not nome or not telefone or not foto_perfil:
        return jsonify({"sucesso": False, "mensagem": "Nome, telefone e avatar são obrigatórios."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor()
        sql = "UPDATE leitores SET nome = %s, telefone = %s, foto_perfil = %s WHERE id_leitor = %s"
        cursor.execute(sql, (nome, telefone, foto_perfil, usuario_logado['id']))
        conn.commit()

        cursor.close()
        conn.close()

        session['usuario']['nome'] = nome
        session['usuario']['telefone'] = telefone
        session['usuario']['foto_perfil'] = foto_perfil

        return jsonify({"sucesso": True, "mensagem": "Dados pessoais atualizados com sucesso!"}), 200

    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao atualizar dados: {str(e)}"}), 500

@app.route('/leitores/senha', methods=['PUT'])
@login_requerido
def atualizar_senha_leitor():
    usuario_logado = session.get('usuario')
    if usuario_logado['tipo_perfil'] != 'LEITOR':
        return jsonify({"sucesso": False, "mensagem": "Esta rota é exclusiva para leitores."}), 403

    data = request.get_json() or {}
    senha_atual = str(data.get('senha_atual', '')).strip()
    nova_senha = str(data.get('nova_senha', '')).strip()

    if not senha_atual or not nova_senha:
        return jsonify({"sucesso": False, "mensagem": "Senha atual e nova senha são obrigatórias."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT senha FROM leitores WHERE id_leitor = %s", (usuario_logado['id'],))
        leitor = cursor.fetchone()

        if not leitor or not check_password_hash(leitor['senha'], senha_atual):
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Senha atual incorreta."}), 400

        nova_senha_hash = generate_password_hash(nova_senha)
        cursor.execute("UPDATE leitores SET senha = %s WHERE id_leitor = %s", (nova_senha_hash, usuario_logado['id']))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"sucesso": True, "mensagem": "Senha alterada com sucesso!"}), 200

    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao alterar senha: {str(e)}"}), 500

@app.route('/leitores/avatar', methods=['POST'])
@login_requerido
def upload_avatar_leitor():
    usuario_logado = session.get('usuario')
    if usuario_logado['tipo_perfil'] != 'LEITOR':
        return jsonify({"sucesso": False, "mensagem": "Esta rota é exclusiva para leitores."}), 403

    if 'foto' not in request.files:
        return jsonify({"sucesso": False, "mensagem": "Nenhum arquivo enviado."}), 400

    file = request.files['foto']

    if file.filename == '':
        return jsonify({"sucesso": False, "mensagem": "Nenhum arquivo selecionado."}), 400

    if file and arquivo_permitido(file.filename):
        extensao = file.filename.rsplit('.', 1)[1].lower()
        nome_arquivo = f"avatar_leitor_{usuario_logado['id']}_{uuid.uuid4().hex[:8]}.{extensao}"
        caminho_salvar = os.path.join(UPLOAD_FOLDER_AVATARES, nome_arquivo)
        file.save(caminho_salvar)

        url_relativa = f"/static/avatares/{nome_arquivo}"

        conn = get_db_connection()
        if not conn:
            return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE leitores SET foto_perfil = %s WHERE id_leitor = %s", (url_relativa, usuario_logado['id']))
            conn.commit()
            cursor.close()
            conn.close()

            return jsonify({"sucesso": True, "mensagem": "Foto de perfil atualizada!", "foto_perfil": url_relativa}), 200

        except Exception as e:
            if conn and conn.is_connected():
                conn.close()
            return jsonify({"sucesso": False, "mensagem": f"Erro ao salvar no banco: {str(e)}"}), 500

    return jsonify({"sucesso": False, "mensagem": "Formato não permitido (use PNG, JPG, JPEG ou WEBP)."}), 400

#ROTA PARA LEITOR EXPORTAR SEUS DADOS DE ACORDO COM A LGPD - OK
@app.route('/leitores/exportar-dados', methods=['GET'])
@login_requerido
def exportar_dados_leitor():
    usuario_logado = session.get('usuario')
    if usuario_logado['tipo_perfil'] != 'LEITOR':
        return jsonify({"sucesso": False, "mensagem": "Esta rota é exclusiva para leitores."}), 403

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)

        # 1. Dados Pessoais
        cursor.execute("""
            SELECT id_leitor, nome, email, telefone, foto_perfil, status_conta, consentimento_lgpd, data_cadastro 
            FROM leitores WHERE id_leitor = %s
        """, (usuario_logado['id'],))
        perfil = cursor.fetchone()

        # 2. Histórico de Empréstimos (Relacionando diretamente e.id_livro = l.id_livro)
        cursor.execute("""
            SELECT e.id_emprestimo, l.titulo AS livro, e.data_emprestimo, e.data_devolucao_prevista, e.data_devolucao_real, e.status_emprestimo
            FROM emprestimos e
            INNER JOIN livro l ON e.id_livro = l.id_livro
            WHERE e.id_leitor = %s
        """, (usuario_logado['id'],))
        emprestimos = cursor.fetchall()

        # 3. Histórico de Reservas
        cursor.execute("""
            SELECT r.id_reserva, l.titulo AS livro, r.data_reserva, r.status_reserva
            FROM reservas r
            INNER JOIN livro l ON r.id_livro = l.id_livro
            WHERE r.id_leitor = %s
        """, (usuario_logado['id'],))
        reservas = cursor.fetchall()

        # 4. Avaliações (Corrigido para livro_id e leitor_id)
        cursor.execute("""
            SELECT a.id_avaliacao, l.titulo AS livro, a.nota, a.comentario, a.data_avaliacao
            FROM avaliacoes a
            INNER JOIN livro l ON a.livro_id = l.id_livro
            WHERE a.leitor_id = %s
        """, (usuario_logado['id'],))
        avaliacoes = cursor.fetchall()

        cursor.close()
        conn.close()

        logger_lgpd.info(f"Auditoria LGPD: O leitor ID [{usuario_logado['id']}] solicitou a exportação completa de seus dados (Art. 18 LGPD).")

        return jsonify({
            "sucesso": True,
            "direitos_lgpd": "Exportação de dados nos termos do Art. 18 da LGPD (Lei nº 13.709/2018)",
            "dados_pessoais": perfil,
            "historico_emprestimos": emprestimos,
            "historico_reservas": reservas,
            "avaliacoes_realizadas": avaliacoes
        }), 200

    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao exportar dados: {str(e)}"}), 500

#ROTA PARA SE AUTODELETAR OU ANONIMIZAR - OK
@app.route('/leitores/conta', methods=['DELETE'])
@login_requerido
def deletar_conta_leitor():
    usuario_logado = session.get('usuario')
    if usuario_logado.get('tipo_perfil') != 'LEITOR':
        return jsonify({"sucesso": False, "mensagem": "Esta rota é exclusiva para leitores."}), 403

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True, buffered=True)
        id_leitor = usuario_logado['id']

        # 1. Verifica se existem empréstimos pendentes/ativos
        cursor.execute("""
            SELECT id_emprestimo FROM emprestimos
            WHERE id_leitor = %s AND status_emprestimo = 'Ativo'
        """, (id_leitor,))
        emprestimo_ativo = cursor.fetchone()

        if emprestimo_ativo:
            cursor.close()
            conn.close()
            return jsonify({
                "sucesso": False,
                "mensagem": "Não é possível excluir a conta com empréstimos ativos pendentes de devolução."
            }), 400

        # 2. Anonimização e desativação na tabela LEITORES
        senha_inutilizavel = generate_password_hash(secrets.token_hex(16))
        cursor.execute("""
            UPDATE leitores 
            SET nome = 'Ex-Leitor (Anonimizado)',
                email = CONCAT('ex_leitor_', id_leitor, '@lgpd.deleted'),
                telefone = '00000000000',
                senha = %s,
                foto_perfil = 'default_profile.png',
                consentimento_lgpd = 0,
                status_conta = 'Bloqueado'
            WHERE id_leitor = %s
        """, (senha_inutilizavel, id_leitor))
        
        conn.commit()
        cursor.close()
        conn.close()

        # Encerra a sessão do usuário
        session.clear()

        logger_lgpd.info(f"Auditoria LGPD: O leitor ID [{id_leitor}] executou o direito de exclusão/anonimização de sua conta.")

        return jsonify({
            "sucesso": True,
            "mensagem": "Sua conta foi desativada e seus dados pessoais foram anonimizados com sucesso em conformidade com a LGPD."
        }), 200

    except Exception as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao processar solicitação: {str(e)}"}), 500

# =============================================================================
# 📋 MÓDULO: EMPRÉSTIMOS E DEVOLUÇÕES
# =============================================================================
STATUS_EMPRESTIMO_VALIDOS = ('Ativo', 'Devolvido', 'Atrasado')
VALOR_MULTA_POR_DIA = 1.00   # R$ por dia de atraso (não persistido no banco — calculado sob demanda)
DIAS_EMPRESTIMO = 14
DIAS_RENOVACAO = 7
MAX_RENOVACOES = 2

def _atualizar_emprestimos_atrasados(cursor):
    """Promove para 'Atrasado' qualquer empréstimo Ativo cujo prazo já venceu."""
    cursor.execute(
        "UPDATE emprestimos SET status_emprestimo = 'Atrasado' "
        "WHERE status_emprestimo = 'Ativo' AND data_devolucao_prevista < CURDATE()"
    )

def _calcular_multa(data_devolucao_prevista, data_devolucao_real):
    """Calcula multa por atraso sob demanda (não há coluna de multa no banco)."""
    if not data_devolucao_prevista:
        return {"dias_atraso": 0, "valor_multa": 0.0}

    if data_devolucao_real:
        referencia = data_devolucao_real.date() if isinstance(data_devolucao_real, datetime.datetime) else data_devolucao_real
    else:
        referencia = datetime.date.today()

    dias_atraso = max((referencia - data_devolucao_prevista).days, 0)
    return {"dias_atraso": dias_atraso, "valor_multa": round(dias_atraso * VALOR_MULTA_POR_DIA, 2)}

# 1. LISTAR TODOS OS EMPRÉSTIMOS REGISTRADOS (funcionários) - OK
@app.route('/emprestimos', methods=['GET'])
@apenas_funcionario
def listar_emprestimos():
    status_filtro = request.args.get('status')
    if status_filtro and status_filtro not in STATUS_EMPRESTIMO_VALIDOS:
        return jsonify({
            "sucesso": False,
            "mensagem": f"Status inválido. Use um dos seguintes: {', '.join(STATUS_EMPRESTIMO_VALIDOS)}."
        }), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        _atualizar_emprestimos_atrasados(cursor)
        conn.commit()

        sql = """
            SELECT e.id_emprestimo, e.id_livro, l.titulo, l.autor,
                   e.id_leitor, lt.nome AS nome_leitor, lt.email AS email_leitor,
                   e.id_funcionario, f.nome AS nome_funcionario,
                   e.data_emprestimo, e.data_devolucao_prevista, e.data_devolucao_real,
                   e.renovacoes_realizadas, e.status_emprestimo
            FROM emprestimos e
            INNER JOIN livro l ON e.id_livro = l.id_livro
            INNER JOIN leitores lt ON e.id_leitor = lt.id_leitor
            INNER JOIN funcionarios f ON e.id_funcionario = f.id_funcionario
        """
        params = ()
        if status_filtro:
            sql += " WHERE e.status_emprestimo = %s"
            params = (status_filtro,)
        sql += " ORDER BY e.data_emprestimo DESC"

        cursor.execute(sql, params)
        emprestimos = cursor.fetchall()

        for emp in emprestimos:
            emp['multa'] = _calcular_multa(emp['data_devolucao_prevista'], emp['data_devolucao_real'])

        cursor.close()
        conn.close()

        return jsonify({"sucesso": True, "emprestimos": emprestimos}), 200
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao buscar empréstimos: {str(e)}"}), 500

# 2. REGISTRAR RETIRADA FÍSICA NO BALCÃO (funcionários) - OK
@app.route('/emprestimos', methods=['POST'])
@apenas_funcionario
def registrar_emprestimo_balcao():
    data = request.get_json() or {}
    id_livro = data.get('id_livro')
    id_leitor = data.get('id_leitor')
    id_funcionario = session.get('usuario', {}).get('id')

    if not id_livro or not id_leitor:
        return jsonify({"sucesso": False, "mensagem": "Os campos id_livro e id_leitor são obrigatórios."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT status_conta FROM leitores WHERE id_leitor = %s", (id_leitor,))
        leitor = cursor.fetchone()
        if not leitor:
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Leitor não encontrado."}), 404
        if leitor['status_conta'] != 'Ativo':
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": f"Leitor com conta '{leitor['status_conta']}' não pode retirar livros."}), 403

        cursor.execute("SELECT quant_estoque, status_livro FROM livro WHERE id_livro = %s", (id_livro,))
        livro = cursor.fetchone()
        if not livro:
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Livro não encontrado."}), 404
        if livro['status_livro'] != 'Ativo':
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Este livro está indisponível para empréstimo."}), 400

        cursor.execute(
            "SELECT COUNT(*) AS total FROM emprestimos WHERE id_livro = %s AND data_devolucao_real IS NULL",
            (id_livro,)
        )
        if cursor.fetchone()['total'] >= livro['quant_estoque']:
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Não há exemplares disponíveis para empréstimo no momento."}), 400

        _atualizar_emprestimos_atrasados(cursor)
        conn.commit()
        cursor.execute(
            "SELECT COUNT(*) AS total FROM emprestimos WHERE id_leitor = %s AND status_emprestimo = 'Atrasado'",
            (id_leitor,)
        )
        if cursor.fetchone()['total'] > 0:
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Leitor possui empréstimo em atraso. Regularize a devolução antes de retirar outro livro."}), 400

        try:
            cursor.execute(
                """INSERT INTO emprestimos (id_livro, id_leitor, id_funcionario, data_devolucao_prevista)
                   VALUES (%s, %s, %s, DATE_ADD(CURRENT_DATE(), INTERVAL %s DAY))""",
                (id_livro, id_leitor, id_funcionario, DIAS_EMPRESTIMO)
            )
        except mysql.connector.Error as err:
            conn.rollback()
            cursor.close()
            conn.close()
            # errno 1644 = SIGNAL SQLSTATE '45000' da trigger antes_inserir_emprestimo (limite de 3 livros ativos)
            if err.errno == 1644:
                return jsonify({"sucesso": False, "mensagem": err.msg}), 400
            return jsonify({"sucesso": False, "mensagem": f"Erro ao registrar empréstimo: {str(err)}"}), 400

        novo_id = cursor.lastrowid
        cursor.execute(
            "UPDATE reservas SET status_reserva = 'Concluida' WHERE id_livro = %s AND id_leitor = %s AND status_reserva IN ('Pendente', 'Aguardando Retirada') ORDER BY data_reserva ASC LIMIT 1",
            (id_livro, id_leitor)
        )
        novo_status_exemplar = _recalcular_status_exemplar(cursor, id_livro)
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "sucesso": True,
            "mensagem": "Empréstimo registrado com sucesso!",
            "id_emprestimo": novo_id,
            "status_exemplar": novo_status_exemplar
        }), 201

    except Exception as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro interno ao registrar empréstimo: {str(e)}"}), 500

# 3. REGISTRAR DEVOLUÇÃO DO EXEMPLAR (funcionários) - OK
@app.route('/emprestimos/<int:id_emprestimo>/devolver', methods=['PUT'])
@apenas_funcionario
def devolver_emprestimo(id_emprestimo):
    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id_livro, id_leitor, data_devolucao_prevista, data_devolucao_real FROM emprestimos WHERE id_emprestimo = %s",
            (id_emprestimo,)
        )
        emprestimo = cursor.fetchone()

        if not emprestimo:
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Empréstimo não encontrado."}), 404

        if emprestimo['data_devolucao_real'] is not None:
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Este empréstimo já foi devolvido."}), 400

        cursor.execute(
            "UPDATE emprestimos SET data_devolucao_real = NOW(), status_emprestimo = 'Devolvido' WHERE id_emprestimo = %s",
            (id_emprestimo,)
        )

        multa = _calcular_multa(emprestimo['data_devolucao_prevista'], datetime.datetime.now())

        id_livro = emprestimo['id_livro']

        # Promove a próxima reserva pendente da fila, se houver
        cursor.execute(
            "SELECT id_reserva FROM reservas WHERE id_livro = %s AND status_reserva = 'Pendente' ORDER BY data_reserva ASC LIMIT 1",
            (id_livro,)
        )
        proxima_reserva = cursor.fetchone()
        if proxima_reserva:
            cursor.execute(
                "UPDATE reservas SET status_reserva = 'Aguardando Retirada' WHERE id_reserva = %s",
                (proxima_reserva['id_reserva'],)
            )

        novo_status_exemplar = _recalcular_status_exemplar(cursor, id_livro)
        conn.commit()
        cursor.close()
        conn.close()

        mensagem = "Devolução registrada com sucesso."
        if proxima_reserva:
            mensagem += " Há uma reserva na fila que passou a aguardar retirada."

        return jsonify({
            "sucesso": True,
            "mensagem": mensagem,
            "status_exemplar": novo_status_exemplar,
            "multa": multa
        }), 200

    except Exception as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao registrar devolução: {str(e)}"}), 500

# 4. INCREMENTAR RENOVAÇÕES E ESTENDER PRAZO (leitor dono do empréstimo ou funcionário) - OK
@app.route('/emprestimos-renovar/<int:id_emprestimo>', methods=['PUT'])
@login_requerido
def renovar_emprestimo(id_emprestimo):
    usuario_logado = session.get('usuario')

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id_livro, id_leitor, data_devolucao_real, renovacoes_realizadas FROM emprestimos WHERE id_emprestimo = %s",
            (id_emprestimo,)
        )
        emprestimo = cursor.fetchone()

        if not emprestimo:
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Empréstimo não encontrado."}), 404

        if usuario_logado['tipo_perfil'] == 'LEITOR' and emprestimo['id_leitor'] != usuario_logado['id']:
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Você só pode renovar seus próprios empréstimos."}), 403

        if emprestimo['data_devolucao_real'] is not None:
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Este empréstimo já foi devolvido."}), 400

        _atualizar_emprestimos_atrasados(cursor)
        conn.commit()
        cursor.execute("SELECT status_emprestimo FROM emprestimos WHERE id_emprestimo = %s", (id_emprestimo,))
        if cursor.fetchone()['status_emprestimo'] == 'Atrasado':
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Não é possível renovar um empréstimo em atraso. Regularize a devolução primeiro."}), 400

        if emprestimo['renovacoes_realizadas'] >= MAX_RENOVACOES:
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": f"Limite de {MAX_RENOVACOES} renovações já atingido para este empréstimo."}), 400

        cursor.execute(
            "SELECT COUNT(*) AS total FROM reservas WHERE id_livro = %s AND status_reserva IN ('Pendente', 'Aguardando Retirada')",
            (emprestimo['id_livro'],)
        )
        if cursor.fetchone()['total'] > 0:
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Não é possível renovar: há leitores na fila de espera por este livro."}), 400

        cursor.execute(
            """UPDATE emprestimos
               SET data_devolucao_prevista = DATE_ADD(data_devolucao_prevista, INTERVAL %s DAY),
                   renovacoes_realizadas = renovacoes_realizadas + 1
               WHERE id_emprestimo = %s""",
            (DIAS_RENOVACAO, id_emprestimo)
        )
        conn.commit()

        cursor.execute(
            "SELECT data_devolucao_prevista, renovacoes_realizadas FROM emprestimos WHERE id_emprestimo = %s",
            (id_emprestimo,)
        )
        atualizado = cursor.fetchone()
        cursor.close()
        conn.close()

        return jsonify({
            "sucesso": True,
            "mensagem": "Empréstimo renovado com sucesso!",
            "nova_data_devolucao_prevista": str(atualizado['data_devolucao_prevista']),
            "renovacoes_realizadas": atualizado['renovacoes_realizadas']
        }), 200

    except Exception as e:
        if conn and conn.is_connected():
            conn.rollback()
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao renovar empréstimo: {str(e)}"}), 500

# 5. HISTÓRICO DE EMPRÉSTIMOS DO LEITOR LOGADO - OK
@app.route('/meus-emprestimos', methods=['GET'])
@apenas_leitor
def meus_emprestimos():
    usuario_logado = session.get('usuario')

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        _atualizar_emprestimos_atrasados(cursor)
        conn.commit()

        cursor.execute("""
            SELECT e.id_emprestimo, e.id_livro, l.titulo, l.autor, l.capa,
                   e.data_emprestimo, e.data_devolucao_prevista, e.data_devolucao_real,
                   e.renovacoes_realizadas, e.status_emprestimo
            FROM emprestimos e
            INNER JOIN livro l ON e.id_livro = l.id_livro
            WHERE e.id_leitor = %s
            ORDER BY e.data_emprestimo DESC
        """, (usuario_logado['id'],))
        emprestimos = cursor.fetchall()

        for emp in emprestimos:
            emp['multa'] = _calcular_multa(emp['data_devolucao_prevista'], emp['data_devolucao_real'])

        cursor.close()
        conn.close()

        return jsonify({"sucesso": True, "emprestimos": emprestimos}), 200
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao buscar empréstimos: {str(e)}"}), 500

# 6. ATENDIMENTOS REGISTRADOS PELO FUNCIONÁRIO LOGADO - OK
@app.route('/funcionarios/meus-atendimentos', methods=['GET'])
@apenas_funcionario
def meus_atendimentos():
    usuario_logado = session.get('usuario')

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT e.id_emprestimo, e.id_livro, l.titulo, e.id_leitor, lt.nome AS nome_leitor,
                   e.data_emprestimo, e.data_devolucao_prevista, e.data_devolucao_real, e.status_emprestimo
            FROM emprestimos e
            INNER JOIN livro l ON e.id_livro = l.id_livro
            INNER JOIN leitores lt ON e.id_leitor = lt.id_leitor
            WHERE e.id_funcionario = %s
            ORDER BY e.data_emprestimo DESC
        """, (usuario_logado['id'],))
        atendimentos = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({"sucesso": True, "atendimentos": atendimentos}), 200
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao buscar atendimentos: {str(e)}"}), 500

# =============================================================================
# ⭐ MÓDULO: AVALIAÇÕES E RESENHAS (CRUD COMPLETO)
# =============================================================================

# 1. ENVIAR NOTA (1 A 5) E COMENTÁRIO (qualquer leitor autenticado)
@app.route('/livros/<int:id_livro>/avaliacoes', methods=['POST'])
@apenas_leitor
def criar_avaliacao(id_livro):
    usuario_logado = session.get('usuario')
    data = request.get_json() or {}

    try:
        nota = int(data.get('nota'))
        if nota < 1 or nota > 5:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"sucesso": False, "mensagem": "O campo nota é obrigatório e deve ser um número entre 1 e 5."}), 400

    comentario = data.get('comentario')

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id_livro FROM livro WHERE id_livro = %s", (id_livro,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Livro não encontrado."}), 404

        cursor.execute(
            "SELECT id_avaliacao FROM avaliacoes WHERE livro_id = %s AND leitor_id = %s",
            (id_livro, usuario_logado['id'])
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Você já avaliou este livro. Use PUT /avaliacoes/<id> para editar sua avaliação."}), 400

        cursor.execute(
            "INSERT INTO avaliacoes (livro_id, leitor_id, nota, comentario) VALUES (%s, %s, %s, %s)",
            (id_livro, usuario_logado['id'], nota, comentario)
        )
        conn.commit()
        novo_id = cursor.lastrowid
        cursor.close()
        conn.close()

        return jsonify({"sucesso": True, "mensagem": "Avaliação registrada com sucesso!", "id_avaliacao": novo_id}), 201

    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao registrar avaliação: {str(e)}"}), 400

# 2. LISTAR RESENHAS DE UM LIVRO - OK
@app.route('/livros-avaliacoes/<int:id_livro>', methods=['GET'])
def listar_avaliacoes_livro(id_livro):
    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.id_avaliacao, a.leitor_id, lt.nome AS nome_leitor, a.nota, a.comentario, a.data_avaliacao
            FROM avaliacoes a
            INNER JOIN leitores lt ON a.leitor_id = lt.id_leitor
            WHERE a.livro_id = %s
            ORDER BY a.data_avaliacao DESC
        """, (id_livro,))
        avaliacoes = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({"sucesso": True, "avaliacoes": avaliacoes}), 200
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao buscar avaliações: {str(e)}"}), 500

# 3. CONSULTAR UMA AVALIAÇÃO ESPECÍFICA - OK
@app.route('/avaliacoes/<int:id_avaliacao>', methods=['GET'])
def consultar_avaliacao(id_avaliacao):
    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.id_avaliacao, a.livro_id, l.titulo, a.leitor_id, lt.nome AS nome_leitor,
                   a.nota, a.comentario, a.data_avaliacao
            FROM avaliacoes a
            INNER JOIN livro l ON a.livro_id = l.id_livro
            INNER JOIN leitores lt ON a.leitor_id = lt.id_leitor
            WHERE a.id_avaliacao = %s
        """, (id_avaliacao,))
        avaliacao = cursor.fetchone()
        cursor.close()
        conn.close()

        if not avaliacao:
            return jsonify({"sucesso": False, "mensagem": "Avaliação não encontrada."}), 404

        return jsonify({"sucesso": True, "avaliacao": avaliacao}), 200
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao consultar avaliação: {str(e)}"}), 500

# 4. EDITAR AVALIAÇÃO FEITA PELO LEITOR (somente o próprio autor) - OK
@app.route('/avaliacoes/<int:id_avaliacao>', methods=['PUT'])
@apenas_leitor
def editar_avaliacao(id_avaliacao):
    usuario_logado = session.get('usuario')
    data = request.get_json() or {}

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT leitor_id FROM avaliacoes WHERE id_avaliacao = %s", (id_avaliacao,))
        avaliacao = cursor.fetchone()

        if not avaliacao:
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Avaliação não encontrada."}), 404

        if avaliacao['leitor_id'] != usuario_logado['id']:
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Você só pode editar sua própria avaliação."}), 403

        campos = []
        valores = []

        if 'nota' in data:
            try:
                nota = int(data.get('nota'))
                if nota < 1 or nota > 5:
                    raise ValueError
            except (TypeError, ValueError):
                cursor.close()
                conn.close()
                return jsonify({"sucesso": False, "mensagem": "nota deve ser um número entre 1 e 5."}), 400
            campos.append("nota = %s")
            valores.append(nota)

        if 'comentario' in data:
            campos.append("comentario = %s")
            valores.append(data.get('comentario'))

        if not campos:
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Informe ao menos nota ou comentario para atualizar."}), 400

        valores.append(id_avaliacao)
        cursor.execute(f"UPDATE avaliacoes SET {', '.join(campos)} WHERE id_avaliacao = %s", tuple(valores))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"sucesso": True, "mensagem": "Avaliação atualizada com sucesso!"}), 200

    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao editar avaliação: {str(e)}"}), 500

# 5. REMOVER AVALIAÇÃO (autor da avaliação ou funcionário para moderação) - OK
@app.route('/avaliacoes/<int:id_avaliacao>', methods=['DELETE'])
@login_requerido
def excluir_avaliacao(id_avaliacao):
    usuario_logado = session.get('usuario')

    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT leitor_id FROM avaliacoes WHERE id_avaliacao = %s", (id_avaliacao,))
        avaliacao = cursor.fetchone()

        if not avaliacao:
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Avaliação não encontrada."}), 404

        if usuario_logado['tipo_perfil'] == 'LEITOR' and avaliacao['leitor_id'] != usuario_logado['id']:
            cursor.close()
            conn.close()
            return jsonify({"sucesso": False, "mensagem": "Você só pode excluir sua própria avaliação."}), 403

        cursor.execute("DELETE FROM avaliacoes WHERE id_avaliacao = %s", (id_avaliacao,))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"sucesso": True, "mensagem": "Avaliação removida com sucesso."}), 200

    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao excluir avaliação: {str(e)}"}), 500

# =============================================================================
# 📊 MÓDULO: RELATÓRIOS E ADMINISTRATIVO
# =============================================================================
# 1. MÉTRICAS CONSOLIDADAS DO SISTEMA (funcionários) - OK
@app.route('/relatorios/dashboard', methods=['GET'])
@apenas_funcionario
def dashboard_metrics():
    conn = get_db_connection()
    if not conn:
        return jsonify({"sucesso": False, "mensagem": "Erro de conexão com o banco de dados."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        _atualizar_emprestimos_atrasados(cursor)
        conn.commit()

        cursor.execute("SELECT COUNT(*) AS total FROM livro WHERE status_livro = 'Ativo'")
        total_livros_ativos = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) AS total FROM leitores WHERE status_conta = 'Ativo'")
        total_leitores_ativos = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) AS total FROM funcionarios WHERE status_funcionario = 'Ativo'")
        total_funcionarios_ativos = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) AS total FROM emprestimos WHERE status_emprestimo = 'Ativo'")
        emprestimos_ativos = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) AS total FROM emprestimos WHERE status_emprestimo = 'Atrasado'")
        emprestimos_atrasados = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) AS total FROM emprestimos WHERE status_emprestimo = 'Ativo'")
        emprestimos_a_vencer = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) AS total FROM reservas WHERE status_reserva IN ('Pendente', 'Aguardando Retirada')")
        reservas_ativas = cursor.fetchone()['total']

        cursor.execute("""
            SELECT l.id_livro, l.titulo, COUNT(e.id_emprestimo) AS total_emprestimos
            FROM emprestimos e
            INNER JOIN livro l ON e.id_livro = l.id_livro
            GROUP BY l.id_livro
            ORDER BY total_emprestimos DESC
            LIMIT 5
        """)
        livros_mais_emprestados = cursor.fetchall()

        cursor.execute("""
            SELECT l.id_livro, l.titulo, ROUND(AVG(a.nota), 1) AS media_avaliacoes, COUNT(a.id_avaliacao) AS total_avaliacoes
            FROM avaliacoes a
            INNER JOIN livro l ON a.livro_id = l.id_livro
            GROUP BY l.id_livro
            HAVING total_avaliacoes > 0
            ORDER BY media_avaliacoes DESC
            LIMIT 5
        """)
        livros_mais_bem_avaliados = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            "sucesso": True,
            "dashboard": {
                "total_livros_ativos": total_livros_ativos,
                "total_leitores_ativos": total_leitores_ativos,
                "total_funcionarios_ativos": total_funcionarios_ativos,
                "emprestimos_ativos": emprestimos_ativos,
                "emprestimos_a_vencer": emprestimos_a_vencer,
                "emprestimos_atrasados": emprestimos_atrasados,
                "reservas_ativas": reservas_ativas,
                "livros_mais_emprestados": livros_mais_emprestados,
                "livros_mais_bem_avaliados": livros_mais_bem_avaliados
            }
        }), 200

    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return jsonify({"sucesso": False, "mensagem": f"Erro ao gerar dashboard: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
    