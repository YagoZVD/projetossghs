from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import jwt
import os

# Criando a aplicação Flask
app = Flask(__name__)

app.config['JWT_SECRET_KEY'] = 'vidaplus-jwt-secret-2024'
SECRET_KEY = 'vidaplus-jwt-secret-2024'
TOKEN_EXPIRATION_HOURS = 8

# Configuração do banco de dados SQLite (mais fácil pra começar)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vidaplus.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'chave-secreta-vidaplus-2024'

# Inicializando o banco
db = SQLAlchemy(app)

# ===== MODELOS DO BANCO DE DADOS =====

class Paciente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(11), unique=True, nullable=False)
    telefone = db.Column(db.String(15))
    email = db.Column(db.String(100))
    endereco = db.Column(db.Text)
    data_nascimento = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    consultas = db.relationship('Consulta', backref='paciente_ref', lazy=True)
    exames = db.relationship('Exame', backref='paciente_ref', lazy=True)
    atendimentos_online = db.relationship('AtendimentoOnline', backref='paciente_ref', lazy=True)
    prescricoes = db.relationship('Prescricao', backref='paciente_ref', lazy=True)

class Profissional(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    especialidade = db.Column(db.String(50), nullable=False)
    crm_coren = db.Column(db.String(20), unique=True, nullable=False)
    telefone = db.Column(db.String(15))
    email = db.Column(db.String(100))
    tipo = db.Column(db.String(20), nullable=False) # médico, enfermeiro, técnico
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    consultas = db.relationship('Consulta', backref='profissional_ref', lazy=True)
    atendimentos_online = db.relationship('AtendimentoOnline', backref='profissional_ref', lazy=True)
    prescricoes = db.relationship('Prescricao', backref='profissional_ref', lazy=True)
    agenda_disponivel = db.relationship('AgendaDisponivel', backref='profissional_ref', lazy=True)

class Consulta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=False)
    profissional_id = db.Column(db.Integer, db.ForeignKey('profissional.id'), nullable=False)
    data_consulta = db.Column(db.DateTime, nullable=False)
    tipo = db.Column(db.String(20), nullable=False) # presencial, telemedicina
    status = db.Column(db.String(20), default='agendada') # agendada, realizada, cancelada
    observacoes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Exame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=False)
    tipo_exame = db.Column(db.String(100), nullable=False)
    data_exame = db.Column(db.DateTime, nullable=False)
    resultado = db.Column(db.Text)
    status = db.Column(db.String(20), default='agendado') # agendado, realizado, cancelado
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Leito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(10), unique=True, nullable=False)
    setor = db.Column(db.String(50), nullable=False) # UTI, enfermaria, etc
    ocupado = db.Column(db.Boolean, default=False)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=True)
    data_ocupacao = db.Column(db.DateTime)

class AtendimentoOnline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=False)
    profissional_id = db.Column(db.Integer, db.ForeignKey('profissional.id'), nullable=False)
    data_inicio = db.Column(db.DateTime, nullable=False)
    data_fim = db.Column(db.DateTime)
    link_videochamada = db.Column(db.String(200))
    status = db.Column(db.String(20), default='agendado') # agendado, em_andamento, finalizado, cancelado
    observacoes = db.Column(db.Text)
    sintomas_relatados = db.Column(db.Text)
    diagnostico = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    prescricoes = db.relationship('Prescricao', backref='atendimento_ref', lazy=True)

class Prescricao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=False)
    profissional_id = db.Column(db.Integer, db.ForeignKey('profissional.id'), nullable=False)
    atendimento_online_id = db.Column(db.Integer, db.ForeignKey('atendimento_online.id'), nullable=True)
    consulta_id = db.Column(db.Integer, db.ForeignKey('consulta.id'), nullable=True)
    medicamento = db.Column(db.String(200), nullable=False)
    dosagem = db.Column(db.String(100), nullable=False)
    frequencia = db.Column(db.String(100), nullable=False) # ex: "8/8 horas", "2x ao dia"
    duracao = db.Column(db.String(50), nullable=False) # ex: "7 dias", "contínuo"
    instrucoes = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AgendaDisponivel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profissional_id = db.Column(db.Integer, db.ForeignKey('profissional.id'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fim = db.Column(db.Time, nullable=False)
    tipo_atendimento = db.Column(db.String(20), nullable=False) # presencial, online, ambos
    disponivel = db.Column(db.Boolean, default=True)
    observacoes = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

# ===== ROTAS DA API =====

@app.route('/')
def home():
    return {"sistema": "Sistema VidaPlus", "status": "online"}

# === ROTAS DE PACIENTES ===

@app.route('/pacientes/protegido', methods=['GET'])
@token_required
def listar_pacientes_protegido():
    
    return listar_pacientes()


@app.route('/pacientes', methods=['GET'])
def listar_pacientes():
    try:
        pacientes = Paciente.query.all()
        resultado = []
        for p in pacientes:
            resultado.append({
                'id': p.id,
                'nome': p.nome,
                'cpf': p.cpf,
                'telefone': p.telefone,
                'email': p.email,
                'endereco': p.endereco,
                'data_nascimento': p.data_nascimento.strftime('%Y-%m-%d') if p.data_nascimento else None
            })
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/pacientes/protegido', methods=['POST'])
@token_required
def cadastrar_paciente_protegido():
    
    return cadastrar_paciente()

@app.route('/pacientes', methods=['POST'])
def cadastrar_paciente():
    try:
        dados = request.get_json()
        
        # Validação básica
        if not dados.get('nome') or not dados.get('cpf'):
            return jsonify({"erro": "Nome e CPF são obrigatórios"}), 400
        
        # Verifica se CPF já existe
        if Paciente.query.filter_by(cpf=dados['cpf']).first():
            return jsonify({"erro": "CPF já cadastrado"}), 400
        
        novo_paciente = Paciente(
            nome=dados['nome'],
            cpf=dados['cpf'],
            telefone=dados.get('telefone'),
            email=dados.get('email'),
            endereco=dados.get('endereco'),
            data_nascimento=datetime.strptime(dados['data_nascimento'], '%Y-%m-%d').date() if dados.get('data_nascimento') else None
        )
        
        db.session.add(novo_paciente)
        db.session.commit()
        
        return jsonify({"message": "Paciente cadastrado com sucesso!", "id": novo_paciente.id}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/pacientes/<int:id>/protegido', methods=['GET'])
@token_required
def buscar_paciente_protegido(id):
    
    return buscar_paciente(id)

@app.route('/pacientes/<int:id>', methods=['GET'])
def buscar_paciente(id):
    try:
        paciente = Paciente.query.get_or_404(id)
        return jsonify({
            'id': paciente.id,
            'nome': paciente.nome,
            'cpf': paciente.cpf,
            'telefone': paciente.telefone,
            'email': paciente.email,
            'endereco': paciente.endereco,
            'data_nascimento': paciente.data_nascimento.strftime('%Y-%m-%d') if paciente.data_nascimento else None
        })
    except Exception as e:
        return jsonify({"erro": str(e)}), 404
    
@app.route('/pacientes/<int:id>/protegido', methods=['PUT'])
@token_required
def editar_paciente_protegido(id):
    
    return editar_paciente(id)

@app.route('/pacientes/<int:id>', methods=['PUT'])
def editar_paciente(id):
    try:
        paciente = Paciente.query.get_or_404(id)
        dados = request.get_json()
        
        # Validação básica
        if not dados.get('nome'):
            return jsonify({"erro": "Nome é obrigatório"}), 400
        
        # Verifica se o CPF foi alterado e se já existe para outro paciente
        if dados.get('cpf') and dados['cpf'] != paciente.cpf:
            cpf_existe = Paciente.query.filter(
                Paciente.cpf == dados['cpf'],
                Paciente.id != id
            ).first()
            if cpf_existe:
                return jsonify({"erro": "CPF já cadastrado para outro paciente"}), 400
            paciente.cpf = dados['cpf']
        
        # Atualiza os campos se fornecidos
        if dados.get('nome'):
            paciente.nome = dados['nome']
        if dados.get('telefone'):
            paciente.telefone = dados['telefone']
        if dados.get('email'):
            paciente.email = dados['email']
        if dados.get('endereco'):
            paciente.endereco = dados['endereco']
        if dados.get('data_nascimento'):
            paciente.data_nascimento = datetime.strptime(dados['data_nascimento'], '%Y-%m-%d').date()
        
        db.session.commit()
        
        return jsonify({
            "message": "Dados do paciente atualizados com sucesso!",
            "paciente": {
                'id': paciente.id,
                'nome': paciente.nome,
                'cpf': paciente.cpf,
                'telefone': paciente.telefone,
                'email': paciente.email,
                'endereco': paciente.endereco,
                'data_nascimento': paciente.data_nascimento.strftime('%Y-%m-%d') if paciente.data_nascimento else None
            }
        })
    except Exception as e:
        return jsonify({"erro": str(e)}), 500   

@app.route('/pacientes/<int:id>/protegido', methods=['DELETE'])
@token_required
def deletar_paciente_protegido(id):
    
    return deletar_paciente(id)

@app.route('/pacientes/<int:id>', methods=['DELETE'])
def deletar_paciente(id):
    try:
        paciente = Paciente.query.get_or_404(id)
        
        # Verifica se o paciente possui relacionamentos que impedem a exclusão
        # (consultas, exames, atendimentos online, prescrições ou leitos ocupados)
        
        consultas_ativas = Consulta.query.filter_by(paciente_id=id).count()
        exames_ativos = Exame.query.filter_by(paciente_id=id).count()
        atendimentos_ativos = AtendimentoOnline.query.filter_by(paciente_id=id).count()
        prescricoes_ativas = Prescricao.query.filter_by(paciente_id=id, ativo=True).count()
        leito_ocupado = Leito.query.filter_by(paciente_id=id, ocupado=True).first()
        
        if consultas_ativas > 0 or exames_ativos > 0 or atendimentos_ativos > 0 or prescricoes_ativas > 0 or leito_ocupado:
            return jsonify({
                "erro": "Não é possível excluir este paciente pois possui registros vinculados",
                "detalhes": {
                    "consultas": consultas_ativas,
                    "exames": exames_ativos,
                    "atendimentos_online": atendimentos_ativos,
                    "prescricoes_ativas": prescricoes_ativas,
                    "leito_ocupado": bool(leito_ocupado)
                }
            }), 400
        
        # Se não há relacionamentos, pode excluir
        nome_paciente = paciente.nome
        db.session.delete(paciente)
        db.session.commit()
        
        return jsonify({
            "message": f"Paciente {nome_paciente} excluído com sucesso!",
            "id": id
        }), 200
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# === ROTAS DE PROFISSIONAIS ===

@app.route('/profissionais/protegido', methods=['GET'])
@token_required
def listar_profissionais_protegido():
    
    return listar_profissionais()

@app.route('/profissionais', methods=['GET'])
def listar_profissionais():
    try:
        profissionais = Profissional.query.filter_by(ativo=True).all()
        resultado = []
        for p in profissionais:
            resultado.append({
                'id': p.id,
                'nome': p.nome,
                'especialidade': p.especialidade,
                'crm_coren': p.crm_coren,
                'tipo': p.tipo,
                'telefone': p.telefone,
                'email': p.email
            })
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/profissionais/protegido', methods=['POST'])
@token_required
def cadastrar_profissional_protegido():
    
    return cadastrar_profissional()

@app.route('/profissionais', methods=['POST'])
def cadastrar_profissional():
    try:
        dados = request.get_json()
        
        if not dados.get('nome') or not dados.get('crm_coren'):
            return jsonify({"erro": "Nome e CRM/COREN são obrigatórios"}), 400
        
        if Profissional.query.filter_by(crm_coren=dados['crm_coren']).first():
            return jsonify({"erro": "CRM/COREN já cadastrado"}), 400
        
        novo_profissional = Profissional(
            nome=dados['nome'],
            especialidade=dados.get('especialidade', ''),
            crm_coren=dados['crm_coren'],
            telefone=dados.get('telefone'),
            email=dados.get('email'),
            tipo=dados.get('tipo', 'médico')
        )
        
        db.session.add(novo_profissional)
        db.session.commit()
        
        return jsonify({"message": "Profissional cadastrado com sucesso!", "id": novo_profissional.id}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# === ROTAS DE CONSULTAS ===

@app.route('/consultas/protegido', methods=['GET'])
@token_required
def listar_consultas_protegido():
    
    return listar_consultas()

@app.route('/consultas', methods=['GET'])
def listar_consultas():
    try:
        consultas = Consulta.query.all()
        resultado = []
        for c in consultas:
            resultado.append({
                'id': c.id,
                'paciente': c.paciente_ref.nome,
                'profissional': c.profissional_ref.nome,
                'data_consulta': c.data_consulta.strftime('%Y-%m-%d %H:%M'),
                'tipo': c.tipo,
                'status': c.status,
                'observacoes': c.observacoes
            })
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/consultas/protegido', methods=['POST'])
@token_required
def agendar_consulta_protegido():
    
    return agendar_consulta()

@app.route('/consultas', methods=['POST'])
def agendar_consulta():
    try:
        dados = request.get_json()
        
        if not all([dados.get('paciente_id'), dados.get('profissional_id'), dados.get('data_consulta')]):
            return jsonify({"erro": "Paciente, profissional e data são obrigatórios"}), 400
        
        nova_consulta = Consulta(
            paciente_id=dados['paciente_id'],
            profissional_id=dados['profissional_id'],
            data_consulta=datetime.strptime(dados['data_consulta'], '%Y-%m-%d %H:%M'),
            tipo=dados.get('tipo', 'presencial'),
            observacoes=dados.get('observacoes')
        )
        
        db.session.add(nova_consulta)
        db.session.commit()
        
        return jsonify({"message": "Consulta agendada com sucesso!", "id": nova_consulta.id}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# === ROTAS DE EXAMES ===

@app.route('/exames/protegido', methods=['GET'])
@token_required
def listar_exames_protegido():
    
    return listar_exames()

@app.route('/exames', methods=['GET'])
def listar_exames():
    try:
        exames = Exame.query.all()
        resultado = []
        for e in exames:
            resultado.append({
                'id': e.id,
                'paciente': e.paciente_ref.nome,
                'tipo_exame': e.tipo_exame,
                'data_exame': e.data_exame.strftime('%Y-%m-%d %H:%M'),
                'status': e.status,
                'resultado': e.resultado
            })
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/exames/protegido', methods=['POST'])
@token_required
def agendar_exame_protegido():
    
    return agendar_exame()

@app.route('/exames', methods=['POST'])
def agendar_exame():
    try:
        dados = request.get_json()
        
        if not all([dados.get('paciente_id'), dados.get('tipo_exame'), dados.get('data_exame')]):
            return jsonify({"erro": "Paciente, tipo de exame e data são obrigatórios"}), 400
        
        novo_exame = Exame(
            paciente_id=dados['paciente_id'],
            tipo_exame=dados['tipo_exame'],
            data_exame=datetime.strptime(dados['data_exame'], '%Y-%m-%d %H:%M'),
            resultado=dados.get('resultado', '')
        )
        
        db.session.add(novo_exame)
        db.session.commit()
        
        return jsonify({"message": "Exame agendado com sucesso!", "id": novo_exame.id}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/exames/<int:id>/resultado/protegido', methods=['PUT'])
@token_required
def atualizar_resultado_exame_protegido(id):
    
    return atualizar_resultado_exame(id)

@app.route('/exames/<int:id>/resultado', methods=['PUT'])
def atualizar_resultado_exame(id):
    try:
        exame = Exame.query.get_or_404(id)
        dados = request.get_json()
        
        exame.resultado = dados.get('resultado', '')
        exame.status = 'realizado'
        
        db.session.commit()
        
        return jsonify({"message": "Resultado do exame atualizado!", "id": exame.id})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# === ROTAS DE LEITOS ===

@app.route('/leitos/protegido', methods=['GET'])
@token_required
def listar_leitos_protegido():
    
    return listar_leitos()

@app.route('/leitos', methods=['GET'])
def listar_leitos():
    try:
        leitos = Leito.query.all()
        resultado = []
        for l in leitos:
            paciente_nome = None
            if l.paciente_id:
                paciente = Paciente.query.get(l.paciente_id)
                paciente_nome = paciente.nome if paciente else None
            
            resultado.append({
                'id': l.id,
                'numero': l.numero,
                'setor': l.setor,
                'ocupado': l.ocupado,
                'paciente_id': l.paciente_id,
                'paciente_nome': paciente_nome,
                'data_ocupacao': l.data_ocupacao.strftime('%Y-%m-%d %H:%M') if l.data_ocupacao else None
            })
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/leitos/protegido', methods=['POST'])
@token_required
def cadastrar_leito_protegido():
    
    return cadastrar_leito()

@app.route('/leitos', methods=['POST'])
def cadastrar_leito():
    try:
        dados = request.get_json()
        
        if not dados.get('numero') or not dados.get('setor'):
            return jsonify({"erro": "Número e setor são obrigatórios"}), 400
        
        if Leito.query.filter_by(numero=dados['numero']).first():
            return jsonify({"erro": "Número do leito já existe"}), 400
        
        novo_leito = Leito(
            numero=dados['numero'],
            setor=dados['setor']
        )
        
        db.session.add(novo_leito)
        db.session.commit()
        
        return jsonify({"message": "Leito cadastrado com sucesso!", "id": novo_leito.id}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/leitos/<int:id>/ocupar/protegido', methods=['PUT'])
@token_required
def ocupar_leito_protegido(id):
    
    return ocupar_leito(id)

@app.route('/leitos/<int:id>/ocupar', methods=['PUT'])
def ocupar_leito(id):
    try:
        leito = Leito.query.get_or_404(id)
        dados = request.get_json()
        
        if leito.ocupado:
            return jsonify({"erro": "Leito já está ocupado"}), 400
        
        if not dados.get('paciente_id'):
            return jsonify({"erro": "ID do paciente é obrigatório"}), 400
        
        # Verifica se paciente existe
        paciente = Paciente.query.get(dados['paciente_id'])
        if not paciente:
            return jsonify({"erro": "Paciente não encontrado"}), 404
        
        leito.ocupado = True
        leito.paciente_id = dados['paciente_id']
        leito.data_ocupacao = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({"message": f"Leito {leito.numero} ocupado por {paciente.nome}"})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/leitos/<int:id>/liberar/protegido', methods=['PUT'])
@token_required
def liberar_leito_protegido(id):
    
    return liberar_leito(id)

@app.route('/leitos/<int:id>/liberar', methods=['PUT'])
def liberar_leito(id):
    try:
        leito = Leito.query.get_or_404(id)
        
        if not leito.ocupado:
            return jsonify({"erro": "Leito já está livre"}), 400
        
        leito.ocupado = False
        leito.paciente_id = None
        leito.data_ocupacao = None
        
        db.session.commit()
        
        return jsonify({"message": f"Leito {leito.numero} liberado com sucesso"})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# === ROTAS DE RELATÓRIOS ===

@app.route('/relatorios/ocupacao-leitos/protegido', methods=['GET'])
@token_required
def relatorio_ocupacao_leitos_protegido():
    
    return relatorio_ocupacao_leitos()

@app.route('/relatorios/ocupacao-leitos', methods=['GET'])
def relatorio_ocupacao_leitos():
    try:
        total_leitos = Leito.query.count()
        leitos_ocupados = Leito.query.filter_by(ocupado=True).count()
        leitos_livres = total_leitos - leitos_ocupados
        
        ocupacao_por_setor = db.session.query(
            Leito.setor,
            db.func.count(Leito.id).label('total'),
            db.func.sum(db.case(
                (Leito.ocupado == True, 1),
                else_=0
            )).label('ocupados')
        ).group_by(Leito.setor).all()
        
        setores = []
        for setor in ocupacao_por_setor:
            setores.append({
                'setor': setor.setor,
                'total_leitos': setor.total,
                'ocupados': setor.ocupados,
                'livres': setor.total - setor.ocupados,
                'taxa_ocupacao': round((setor.ocupados / setor.total) * 100, 2)
            })
        
        return jsonify({
            'resumo_geral': {
                'total_leitos': total_leitos,
                'ocupados': leitos_ocupados,
                'livres': leitos_livres,
                'taxa_ocupacao_geral': round((leitos_ocupados / total_leitos) * 100, 2) if total_leitos > 0 else 0
            },
            'por_setor': setores
        })
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/relatorios/consultas-dia/protegido', methods=['GET'])
@token_required
def relatorio_consultas_dia_protegido():
    
    return relatorio_consultas_dia()

@app.route('/relatorios/consultas-dia', methods=['GET'])
def relatorio_consultas_dia():
    try:
        data_param = request.args.get('data')
        if data_param:
            data_filtro = datetime.strptime(data_param, '%Y-%m-%d').date()
        else:
            data_filtro = datetime.now().date()
        
        consultas = Consulta.query.filter(
            db.func.date(Consulta.data_consulta) == data_filtro
        ).all()
        
        agendadas = len([c for c in consultas if c.status == 'agendada'])
        realizadas = len([c for c in consultas if c.status == 'realizada'])
        canceladas = len([c for c in consultas if c.status == 'cancelada'])
        
        consultas_detalhadas = []
        for c in consultas:
            consultas_detalhadas.append({
                'id': c.id,
                'paciente': c.paciente_ref.nome,
                'profissional': c.profissional_ref.nome,
                'horario': c.data_consulta.strftime('%H:%M'),
                'status': c.status,
                'tipo': c.tipo
            })
        
        return jsonify({
            'data': data_filtro.strftime('%Y-%m-%d'),
            'resumo': {
                'total': len(consultas),
                'agendadas': agendadas,
                'realizadas': realizadas,
                'canceladas': canceladas
            },
            'consultas': consultas_detalhadas
        })
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/relatorios/profissionais-produtividade/protegido', methods=['GET'])
@token_required
def relatorio_produtividade_profissionais_protegido():
    
    return relatorio_produtividade_profissionais()

@app.route('/relatorios/profissionais-produtividade', methods=['GET'])
def relatorio_produtividade_profissionais():
    try:
        profissionais_stats = db.session.query(
            Profissional.id,
            Profissional.nome,
            Profissional.especialidade,
            db.func.count(Consulta.id).label('total_consultas')
        ).outerjoin(Consulta).group_by(Profissional.id).all()
        
        resultado = []
        for prof in profissionais_stats:
            resultado.append({
                'id': prof.id,
                'nome': prof.nome,
                'especialidade': prof.especialidade,
                'total_consultas': prof.total_consultas
            })
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    
@app.route('/relatorios/atendimentos-online/protegido', methods=['GET'])
@token_required
def relatorio_atendimentos_online_protegido():
    
    return relatorio_atendimentos_online()

@app.route('/relatorios/atendimentos-online', methods=['GET'])
def relatorio_atendimentos_online():
    try:
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        query = AtendimentoOnline.query
        
        if data_inicio:
            query = query.filter(AtendimentoOnline.data_inicio >= datetime.strptime(data_inicio, '%Y-%m-%d'))
        if data_fim:
            query = query.filter(AtendimentoOnline.data_inicio <= datetime.strptime(data_fim, '%Y-%m-%d'))
        
        atendimentos = query.all()
        
        # Estatísticas
        total = len(atendimentos)
        finalizados = len([a for a in atendimentos if a.status == 'finalizado'])
        cancelados = len([a for a in atendimentos if a.status == 'cancelado'])
        em_andamento = len([a for a in atendimentos if a.status == 'em_andamento'])
        
        return jsonify({
            'periodo': {
                'inicio': data_inicio or 'Início dos registros',
                'fim': data_fim or 'Até hoje'
            },
            'estatisticas': {
                'total_atendimentos': total,
                'finalizados': finalizados,
                'cancelados': cancelados,
                'em_andamento': em_andamento,
                'taxa_conclusao': round((finalizados / total) * 100, 2) if total > 0 else 0
            }
        })
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/relatorios/prescricoes-ativas/protegido', methods=['GET'])
@token_required
@medico_required
def relatorio_prescricoes_ativas_protegido():
    
    return relatorio_prescricoes_ativas()

@app.route('/relatorios/prescricoes-ativas', methods=['GET'])
def relatorio_prescricoes_ativas():
    try:
        prescricoes = Prescricao.query.filter_by(ativo=True).all()
        
        # Agrupar por medicamento
        medicamentos_count = {}
        for p in prescricoes:
            if p.medicamento in medicamentos_count:
                medicamentos_count[p.medicamento] += 1
            else:
                medicamentos_count[p.medicamento] = 1
        
        # Ordenar por frequência
        medicamentos_ordenados = sorted(medicamentos_count.items(), key=lambda x: x[1], reverse=True)
        
        return jsonify({
            'total_prescricoes_ativas': len(prescricoes),
            'medicamentos_mais_prescritos': [
                {'medicamento': med, 'quantidade': qtd} 
                for med, qtd in medicamentos_ordenados[:10]
            ]
        })
    except Exception as e:
        return jsonify({"erro": str(e)}), 500   
    
# === ROTAS DE ATENDIMENTOS ONLINE ===

@app.route('/atendimentos-online/protegido', methods=['GET'])
@token_required
def listar_atendimentos_online_protegido():
    
    return listar_atendimentos_online()

@app.route('/atendimentos-online', methods=['GET'])
def listar_atendimentos_online():
    try:
        atendimentos = AtendimentoOnline.query.all()
        resultado = []
        for a in atendimentos:
            resultado.append({
                'id': a.id,
                'paciente': a.paciente_ref.nome,
                'profissional': a.profissional_ref.nome,
                'data_inicio': a.data_inicio.strftime('%Y-%m-%d %H:%M'),
                'data_fim': a.data_fim.strftime('%Y-%m-%d %H:%M') if a.data_fim else None,
                'status': a.status,
                'link_videochamada': a.link_videochamada,
                'sintomas_relatados': a.sintomas_relatados,
                'diagnostico': a.diagnostico,
                'observacoes': a.observacoes
            })
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/atendimentos-online/protegido', methods=['POST'])
@token_required
def agendar_atendimento_online_protegido():
    
    return agendar_atendimento_online()

@app.route('/atendimentos-online', methods=['POST'])
def agendar_atendimento_online():
    try:
        dados = request.get_json()
        
        if not all([dados.get('paciente_id'), dados.get('profissional_id'), dados.get('data_inicio')]):
            return jsonify({"erro": "Paciente, profissional e data de início são obrigatórios"}), 400
        
        # Gerar link de videochamada (simulado)
        import uuid
        link_videochamada = f"https://vidaplus-meet.com/room/{uuid.uuid4().hex[:8]}"
        
        novo_atendimento = AtendimentoOnline(
            paciente_id=dados['paciente_id'],
            profissional_id=dados['profissional_id'],
            data_inicio=datetime.strptime(dados['data_inicio'], '%Y-%m-%d %H:%M'),
            link_videochamada=link_videochamada,
            observacoes=dados.get('observacoes', '')
        )
        
        db.session.add(novo_atendimento)
        db.session.commit()
        
        return jsonify({
            "message": "Atendimento online agendado com sucesso!",
            "id": novo_atendimento.id,
            "link_videochamada": link_videochamada
        }), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/atendimentos-online/<int:id>/iniciar', methods=['PUT'])
def iniciar_atendimento_online(id):
    try:
        atendimento = AtendimentoOnline.query.get_or_404(id)
        
        if atendimento.status != 'agendado':
            return jsonify({"erro": "Atendimento não pode ser iniciado"}), 400
        
        atendimento.status = 'em_andamento'
        atendimento.data_inicio = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            "message": "Atendimento iniciado!",
            "link_videochamada": atendimento.link_videochamada
        })
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/atendimentos-online/<int:id>/finalizar', methods=['PUT'])
def finalizar_atendimento_online(id):
    try:
        atendimento = AtendimentoOnline.query.get_or_404(id)
        dados = request.get_json()
        
        if atendimento.status != 'em_andamento':
            return jsonify({"erro": "Atendimento não está em andamento"}), 400
        
        atendimento.status = 'finalizado'
        atendimento.data_fim = datetime.utcnow()
        atendimento.sintomas_relatados = dados.get('sintomas_relatados', '')
        atendimento.diagnostico = dados.get('diagnostico', '')
        atendimento.observacoes = dados.get('observacoes', '')
        
        db.session.commit()
        
        return jsonify({"message": "Atendimento finalizado com sucesso!"})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# === ROTAS DE PRESCRIÇÕES ===

@app.route('/prescricoes/protegido', methods=['GET'])
@token_required
@medico_required
def listar_prescricoes_protegida():
    
    return listar_prescricoes()

@app.route('/prescricoes', methods=['GET'])
def listar_prescricoes():
    try:
        paciente_id = request.args.get('paciente_id')
        if paciente_id:
            prescricoes = Prescricao.query.filter_by(paciente_id=paciente_id, ativo=True).all()
        else:
            prescricoes = Prescricao.query.filter_by(ativo=True).all()
        
        resultado = []
        for p in prescricoes:
            resultado.append({
                'id': p.id,
                'paciente': p.paciente_ref.nome,
                'profissional': p.profissional_ref.nome,
                'medicamento': p.medicamento,
                'dosagem': p.dosagem,
                'frequencia': p.frequencia,
                'duracao': p.duracao,
                'instrucoes': p.instrucoes,
                'data_prescricao': p.created_at.strftime('%Y-%m-%d %H:%M')
            })
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    
@app.route('/prescricoes/protegido', methods=['POST'])
@token_required
@medico_required
def criar_prescricao_protegida():
    
    return criar_prescricao()

@app.route('/prescricoes', methods=['POST'])
def criar_prescricao():
    try:
        dados = request.get_json()
        
        campos_obrigatorios = ['paciente_id', 'profissional_id', 'medicamento', 'dosagem', 'frequencia', 'duracao']
        if not all([dados.get(campo) for campo in campos_obrigatorios]):
            return jsonify({"erro": "Todos os campos da prescrição são obrigatórios"}), 400
        
        nova_prescricao = Prescricao(
            paciente_id=dados['paciente_id'],
            profissional_id=dados['profissional_id'],
            atendimento_online_id=dados.get('atendimento_online_id'),
            consulta_id=dados.get('consulta_id'),
            medicamento=dados['medicamento'],
            dosagem=dados['dosagem'],
            frequencia=dados['frequencia'],
            duracao=dados['duracao'],
            instrucoes=dados.get('instrucoes', '')
        )
        
        db.session.add(nova_prescricao)
        db.session.commit()
        
        return jsonify({"message": "Prescrição criada com sucesso!", "id": nova_prescricao.id}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/prescricoes/<int:id>/desativar/protegido', methods=['PUT'])
@token_required
@medico_required
def desativar_prescricao_protegida(id):
    
    return desativar_prescricao(id)

@app.route('/prescricoes/<int:id>/desativar', methods=['PUT'])
def desativar_prescricao(id):
    try:
        prescricao = Prescricao.query.get_or_404(id)
        prescricao.ativo = False
        
        db.session.commit()
        
        return jsonify({"message": "Prescrição desativada com sucesso!"})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# === ROTAS DE AGENDA E DISPONIBILIDADE ===

@app.route('/agenda-disponivel/protegido', methods=['GET'])
@token_required
def listar_agenda_disponivel_protegida():
    
    return listar_agenda_disponivel()

@app.route('/agenda-disponivel', methods=['GET'])
def listar_agenda_disponivel():
    try:
        profissional_id = request.args.get('profissional_id')
        data_param = request.args.get('data')
        tipo_atendimento = request.args.get('tipo', 'ambos')  # presencial, online, ambos
        
        query = AgendaDisponivel.query.filter_by(disponivel=True)
        
        if profissional_id:
            query = query.filter_by(profissional_id=profissional_id)
        
        if data_param:
            data_filtro = datetime.strptime(data_param, '%Y-%m-%d').date()
            query = query.filter_by(data=data_filtro)
        
        if tipo_atendimento != 'ambos':
            query = query.filter(
                (AgendaDisponivel.tipo_atendimento == tipo_atendimento) |
                (AgendaDisponivel.tipo_atendimento == 'ambos')
            )
        
        agenda = query.all()
        resultado = []
        for a in agenda:
            resultado.append({
                'id': a.id,
                'profissional': a.profissional_ref.nome,
                'especialidade': a.profissional_ref.especialidade,
                'data': a.data.strftime('%Y-%m-%d'),
                'hora_inicio': a.hora_inicio.strftime('%H:%M'),
                'hora_fim': a.hora_fim.strftime('%H:%M'),
                'tipo_atendimento': a.tipo_atendimento,
                'observacoes': a.observacoes
            })
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/agenda-disponivel/protegido', methods=['POST'])
@token_required
def cadastrar_agenda_disponivel_protegida():
    
    return cadastrar_agenda_disponivel()

@app.route('/agenda-disponivel', methods=['POST'])
def cadastrar_agenda_disponivel():
    try:
        dados = request.get_json()
        
        campos_obrigatorios = ['profissional_id', 'data', 'hora_inicio', 'hora_fim', 'tipo_atendimento']
        if not all([dados.get(campo) for campo in campos_obrigatorios]):
            return jsonify({"erro": "Todos os campos da agenda são obrigatórios"}), 400
        
        nova_agenda = AgendaDisponivel(
            profissional_id=dados['profissional_id'],
            data=datetime.strptime(dados['data'], '%Y-%m-%d').date(),
            hora_inicio=datetime.strptime(dados['hora_inicio'], '%H:%M').time(),
            hora_fim=datetime.strptime(dados['hora_fim'], '%H:%M').time(),
            tipo_atendimento=dados['tipo_atendimento'],
            observacoes=dados.get('observacoes', '')
        )
        
        db.session.add(nova_agenda)
        db.session.commit()
        
        return jsonify({"message": "Horário disponibilizado na agenda!", "id": nova_agenda.id}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/agenda-disponivel/<int:id>/ocupar/protegido', methods=['PUT'])
@token_required
def ocupar_agenda_protegida(id):
    
    return ocupar_agenda(id)

@app.route('/agenda-disponivel/<int:id>/ocupar', methods=['PUT'])
def ocupar_agenda(id):
    try:
        agenda = AgendaDisponivel.query.get_or_404(id)
        
        if not agenda.disponivel:
            return jsonify({"erro": "Horário já ocupado"}), 400
        
        agenda.disponivel = False
        db.session.commit()
        
        return jsonify({"message": "Horário reservado com sucesso!"})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# === ROTAS DE AUTENTICAÇÃO ===

@app.route('/auth/register', methods=['POST'])
def registrar_usuario():
    try:
        dados = request.get_json()
        
        campos_obrigatorios = ['username', 'email', 'password', 'nome_completo', 'cargo']
        if not all([dados.get(campo) for campo in campos_obrigatorios]):
            return jsonify({"erro": "Todos os campos são obrigatórios"}), 400
        
        if Usuario.query.filter_by(username=dados['username']).first():
            return jsonify({"erro": "Nome de usuário já existe"}), 400
        
        if Usuario.query.filter_by(email=dados['email']).first():
            return jsonify({"erro": "E-mail já cadastrado"}), 400
        
        cargos_validos = ['admin', 'medico', 'enfermeiro', 'recepcionista']
        if dados['cargo'] not in cargos_validos:
            return jsonify({"erro": "Cargo inválido"}), 400
        
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
        
        usuario = Usuario.query.filter_by(username=dados['username']).first()
        
        if not usuario or not usuario.check_password(dados['password']):
            return jsonify({"erro": "Credenciais inválidas"}), 401
        
        if not usuario.ativo:
            return jsonify({"erro": "Usuário inativo"}), 401
        
        usuario.ultimo_login = datetime.utcnow()
        db.session.commit()
        
        token = usuario.generate_token()
        
        return jsonify({
            "message": "Login realizado com sucesso!",
            "token": token,
            "usuario": {
                "id": usuario.id,
                "username": usuario.username,
                "nome_completo": usuario.nome_completo,
                "cargo": usuario.cargo
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
            "cargo": usuario.cargo
        })
    except Exception as e:
        return jsonify({"erro": str(e)}), 500    

# Função para criar as tabelas
def criar_tabelas():
    with app.app_context():
        db.create_all()
        
        # Criar usuário admin padrão
        admin_existente = Usuario.query.filter_by(cargo='admin').first()
        if not admin_existente:
            admin = Usuario(
                username='admin',
                email='admin@vidaplus.com',
                nome_completo='Administrador do Sistema',
                cargo='admin'
            )
            admin.set_password('admin123')
            
            db.session.add(admin)
            db.session.commit()
            print("✅ Usuário admin criado!")
            print("📧 Username: admin")
            print("🔒 Senha: admin123")
        
        print("Tabelas criadas com sucesso!")

if __name__ == '__main__':
    print("🏥 Iniciando Sistema de Gestão Hospitalar - VidaPlus")
    criar_tabelas()
    app.run(debug=True, host='0.0.0.0', port=5000)    
    print("✅ Banco de dados inicializado com sucesso!")
    print("\n🚀 Servidor rodando em http://localhost:5000")