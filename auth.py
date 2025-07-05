# Sistema de Controle de Acesso para VidaPlus
from flask import Flask, app, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import jwt
import os

# Configurações de segurança
SECRET_KEY = 'vidaplus-jwt-secret-2024'
TOKEN_EXPIRATION_HOURS = 8

# ===== MODELO DE USUÁRIO =====
# Adicione esta classe ao seu app.py, junto com os outros modelos

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nome_completo = db.Column(db.String(100), nullable=False)
    cargo = db.Column(db.String(50), nullable=False)  # admin, medico, enfermeiro, recepcionista
    ativo = db.Column(db.Boolean, default=True)
    ultimo_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_token(self):
        payload = {
            'user_id': self.id,
            'username': self.username,
            'cargo': self.cargo,
            'exp': datetime.utcnow() + timedelta(hours=TOKEN_EXPIRATION_HOURS)
        }
        return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    
    @staticmethod
    def verify_token(token):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

# ===== DECORADORES DE AUTENTICAÇÃO =====

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'erro': 'Token de acesso é obrigatório'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token.split(' ')[1]
            
            payload = Usuario.verify_token(token)
            if not payload:
                return jsonify({'erro': 'Token inválido ou expirado'}), 401
            
            # Verificar se usuário ainda está ativo
            usuario = Usuario.query.get(payload['user_id'])
            if not usuario or not usuario.ativo:
                return jsonify({'erro': 'Usuário inativo'}), 401
            
            request.current_user = usuario
            
        except Exception as e:
            return jsonify({'erro': 'Erro na validação do token'}), 401
        
        return f(*args, **kwargs)
    
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(request, 'current_user') or request.current_user.cargo != 'admin':
            return jsonify({'erro': 'Acesso negado. Apenas administradores.'}), 403
        return f(*args, **kwargs)
    return decorated

def medico_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(request, 'current_user') or request.current_user.cargo not in ['admin', 'medico']:
            return jsonify({'erro': 'Acesso negado. Apenas médicos.'}), 403
        return f(*args, **kwargs)
    return decorated

def staff_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(request, 'current_user') or request.current_user.cargo not in ['admin', 'medico', 'enfermeiro']:
            return jsonify({'erro': 'Acesso negado. Apenas equipe médica.'}), 403
        return f(*args, **kwargs)
    return decorated

# ===== ROTAS DE AUTENTICAÇÃO =====
# Adicione estas rotas ao seu app.py

@app.route('/auth/register', methods=['POST'])
def registrar_usuario():
    try:
        dados = request.get_json()
        
        # Validação básica
        campos_obrigatorios = ['username', 'email', 'password', 'nome_completo', 'cargo']
        if not all([dados.get(campo) for campo in campos_obrigatorios]):
            return jsonify({"erro": "Todos os campos são obrigatórios"}), 400
        
        # Verificar se usuário já existe
        if Usuario.query.filter_by(username=dados['username']).first():
            return jsonify({"erro": "Nome de usuário já existe"}), 400
        
        if Usuario.query.filter_by(email=dados['email']).first():
            return jsonify({"erro": "E-mail já cadastrado"}), 400
        
        # Validar cargo
        cargos_validos = ['admin', 'medico', 'enfermeiro', 'recepcionista']
        if dados['cargo'] not in cargos_validos:
            return jsonify({"erro": "Cargo inválido"}), 400
        
        # Criar novo usuário
        novo_usuario = Usuario(
            username=dados['username'],
            email=dados['email'],
            nome_completo=dados['nome_completo'],
            cargo=dados['cargo']
        )
        novo_usuario.set_password(dados['password'])
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        return jsonify({
            "message": "Usuário registrado com sucesso!",
            "usuario": {
                "id": novo_usuario.id,
                "username": novo_usuario.username,
                "nome_completo": novo_usuario.nome_completo,
                "cargo": novo_usuario.cargo
            }
        }), 201
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/auth/login', methods=['POST'])
def login():
    try:
        dados = request.get_json()
        
        if not dados.get('username') or not dados.get('password'):
            return jsonify({"erro": "Username e senha são obrigatórios"}), 400
        
        # Buscar usuário
        usuario = Usuario.query.filter_by(username=dados['username']).first()
        
        if not usuario or not usuario.check_password(dados['password']):
            return jsonify({"erro": "Credenciais inválidas"}), 401
        
        if not usuario.ativo:
            return jsonify({"erro": "Usuário inativo"}), 401
        
        # Atualizar último login
        usuario.ultimo_login = datetime.utcnow()
        db.session.commit()
        
        # Gerar token
        token = usuario.generate_token()
        
        return jsonify({
            "message": "Login realizado com sucesso!",
            "token": token,
            "usuario": {
                "id": usuario.id,
                "username": usuario.username,
                "nome_completo": usuario.nome_completo,
                "cargo": usuario.cargo,
                "ultimo_login": usuario.ultimo_login.strftime('%Y-%m-%d %H:%M:%S')
            }
        }), 200
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/auth/me', methods=['GET'])
@token_required
def usuario_atual():
    try:
        usuario = request.current_user
        return jsonify({
            "id": usuario.id,
            "username": usuario.username,
            "nome_completo": usuario.nome_completo,
            "email": usuario.email,
            "cargo": usuario.cargo,
            "ultimo_login": usuario.ultimo_login.strftime('%Y-%m-%d %H:%M:%S') if usuario.ultimo_login else None
        })
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/auth/usuarios', methods=['GET'])
@token_required
@admin_required
def listar_usuarios():
    try:
        usuarios = Usuario.query.all()
        resultado = []
        for u in usuarios:
            resultado.append({
                'id': u.id,
                'username': u.username,
                'nome_completo': u.nome_completo,
                'email': u.email,
                'cargo': u.cargo,
                'ativo': u.ativo,
                'ultimo_login': u.ultimo_login.strftime('%Y-%m-%d %H:%M:%S') if u.ultimo_login else None,
                'created_at': u.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/auth/usuarios/<int:id>/toggle', methods=['PUT'])
@token_required
@admin_required
def toggle_usuario(id):
    try:
        usuario = Usuario.query.get_or_404(id)
        
        # Não permitir desativar o próprio usuário
        if usuario.id == request.current_user.id:
            return jsonify({"erro": "Não é possível desativar seu próprio usuário"}), 400
        
        usuario.ativo = not usuario.ativo
        db.session.commit()
        
        status = "ativado" if usuario.ativo else "desativado"
        return jsonify({"message": f"Usuário {status} com sucesso!"})
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/auth/change-password', methods=['PUT'])
@token_required
def alterar_senha():
    try:
        dados = request.get_json()
        
        if not dados.get('senha_atual') or not dados.get('nova_senha'):
            return jsonify({"erro": "Senha atual e nova senha são obrigatórias"}), 400
        
        usuario = request.current_user
        
        # Verificar senha atual
        if not usuario.check_password(dados['senha_atual']):
            return jsonify({"erro": "Senha atual incorreta"}), 400
        
        # Validar nova senha (mínimo 6 caracteres)
        if len(dados['nova_senha']) < 6:
            return jsonify({"erro": "Nova senha deve ter pelo menos 6 caracteres"}), 400
        
        # Atualizar senha
        usuario.set_password(dados['nova_senha'])
        db.session.commit()
        
        return jsonify({"message": "Senha alterada com sucesso!"})
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# ===== PROTEÇÕES DAS ROTAS =====

@app.route('/pacientes-protegido', methods=['POST'])
@token_required
@staff_required
def cadastrar_paciente_protegido():  
    return cadastrar_paciente()

@app.route('/pacientes/protegido', methods=['GET'])
@token_required
@staff_required
def listar_pacientes_protegido():   
    return listar_pacientes()

@app.route('/pacientes/<int:id>/protegido', methods=['PUT'])
@token_required
@staff_required
def editar_paciente_protegido(id):   
    return editar_paciente(id)

@app.route('/pacientes/<int:id>/protegido', methods=['GET'])
@token_required
@staff_required
def buscar_paciente_protegido(id):   
    return buscar_paciente(id)

@app.route('/pacientes/<int:id>/protegido', methods=['DELETE'])
@token_required
@staff_required
def deletar_paciente_protegido(id):
    return deletar_paciente(id)

@app.route('/profissionais/protegido', methods=['GET'])
@token_required
@admin_required
def listar_profissionais_protegido():  
    return listar_profissionais()

@app.route('/profissionais/protegido', methods=['POST'])
@token_required
@admin_required
def cadastrar_profissional_protegido():   
    return cadastrar_profissional()

@app.route('/consultas/protegido', methods=['GET'])
@token_required
@staff_required
def listar_consultas_protegido():   
    return listar_consultas()

@app.route('/consultas/protegido', methods=['POST'])
@token_required
@staff_required
def agendar_consulta_protegido():   
    return agendar_consulta()

@app.route('/exames/protegido', methods=['GET'])
@token_required
@medico_required
def listar_exames_protegido():   
    return listar_exames()

@app.route('/exames/protegido', methods=['POST'])
@token_required
@medico_required
def agendar_exame_protegido():   
    return agendar_exame()

@app.route('/exames/<int:id>/resultado/protegido', methods=['PUT'])
@token_required
@medico_required
def atualizar_resultado_exame_protegido(id):    
    return atualizar_resultado_exame(id)

@app.route('/leitos/protegido', methods=['GET'])
@token_required
@staff_required
def listar_leitos_protegido():    
    return listar_leitos()

@app.route('/leitos/protegido', methods=['POST'])
@token_required
@staff_required
def cadastrar_leito_protegido():   
    return cadastrar_leito()

@app.route('/leitos/<int:id>/ocupar/protegido', methods=['PUT'])
@token_required
@staff_required
def ocupar_leito_protegido(id):    
    return ocupar_leito(id)

@app.route('/leitos/<int:id>/liberar/protegido', methods=['PUT'])
@token_required
@staff_required
def liberar_leito_protegido(id):   
    return liberar_leito(id)

@app.route('/relatorios/ocupacao-leitos/protegido', methods=['GET'])
@token_required
@staff_required
def relatorio_ocupacao_leitos_protegido():    
    return relatorio_ocupacao_leitos()

@app.route('/relatorios/consultas-dia/protegido', methods=['GET'])
@token_required
@staff_required
def relatorio_consultas_dia_protegido():   
    return relatorio_consultas_dia()

@app.route('/relatorios/profissionais-produtividade/protegido', methods=['GET'])
@token_required
@admin_required
def relatorio_produtividade_profissionais_protegido():    
    return relatorio_produtividade_profissionais()

@app.route('/relatorios/atendimentos-online/protegido', methods=['GET'])
@token_required
@staff_required
def relatorio_atendimentos_online_protegido():    
    return relatorio_atendimentos_online()

@app.route('/relatorios/prescricoes-ativas/protegido', methods=['GET'])
@token_required
@staff_required
def relatorio_prescricoes_ativas_protegido():    
    return relatorio_prescricoes_ativas()

@app.route('/atendimentos-online/protegido', methods=['GET'])
@token_required
@staff_required
def listar_atendimentos_online_protegido():    
    return listar_atendimentos_online()

@app.route('/atendimentos-online/protegido', methods=['POST'])
@token_required
@staff_required
def agendar_atendimento_online_protegido():    
    return agendar_atendimento_online()

@app.route('/prescricoes/protegido', methods=['GET'])
@token_required
@medico_required
def listar_prescricoes_protegida():
    return listar_prescricoes()

@app.route('/prescricoes-protegidas', methods=['POST'])
@token_required
@medico_required
def criar_prescricao_protegida():
    return criar_prescricao()

@app.route('/prescricoes/<int:id>/desativar/protegido', methods=['PUT'])
@token_required
@medico_required
def desativar_prescricao_protegida(id):    
    return desativar_prescricao(id)

@app.route('/agenda-disponivel/protegido', methods=['GET'])
@token_required
@staff_required
def listar_agenda_disponivel_protegida():    
    return listar_agenda_disponivel()

@app.route('/agenda-disponivel/protegido', methods=['POST'])
@token_required
@staff_required
def cadastrar_agenda_disponivel_protegida():    
    return cadastrar_agenda_disponivel()

@app.route('/agenda-disponivel/<int:id>/ocupar/protegido', methods=['PUT'])
@token_required
@staff_required
def ocupar_agenda_protegida(id):
    return ocupar_agenda(id)

@app.route('/relatorios-protegidos/ocupacao-leitos', methods=['GET'])
@token_required
@staff_required
def relatorio_ocupacao_leitos_protegido():
    return relatorio_ocupacao_leitos()

# ===== FUNÇÃO PARA CRIAR USUÁRIO ADMIN PADRÃO =====
def criar_admin_padrao():
    with app.app_context():
        # Verificar se já existe um admin
        admin_existente = Usuario.query.filter_by(cargo='admin').first()
        if not admin_existente:
            admin = Usuario(
                username='admin',
                email='admin@vidaplus.com',
                nome_completo='Administrador do Sistema',
                cargo='admin'
            )
            admin.set_password('admin123')  # Senha padrão
            
            db.session.add(admin)
            db.session.commit()
            print("✅ Usuário admin criado!")
            print("📧 Username: admin")
            print("🔒 Senha: admin123")
            print("⚠️  IMPORTANTE: Altere a senha padrão após o primeiro login!")
        else:
            print("ℹ️  Usuário admin já existe no sistema")
