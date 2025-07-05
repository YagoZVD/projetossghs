from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import os

# =============================================================================
# CONFIGURAÇÃO DA APLICAÇÃO FLASK E BANCO DE DADOS
# =============================================================================

app = Flask(__name__)

# Configuração do banco de dados SQLite (ideal para desenvolvimento/estudos)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "vidaplus.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializando SQLAlchemy
db = SQLAlchemy(app)

# =============================================================================
# MODELOS DO BANCO DE DADOS (TABELAS)
# =============================================================================

class RelatorioFinanceiro(db.Model):
    """Modelo para relatórios financeiros das unidades"""
    __tablename__ = 'relatorios_financeiros'
    
    id = db.Column(db.Integer, primary_key=True)
    unidade = db.Column(db.String(100), nullable=False)
    periodo = db.Column(db.String(20), nullable=False)  # formato: YYYY-MM
    receita_total = db.Column(db.Float, nullable=False)
    despesas_operacionais = db.Column(db.Float, nullable=False)
    lucro_liquido = db.Column(db.Float, nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<RelatorioFinanceiro {self.unidade} - {self.periodo}>'
    
    def to_dict(self):
        """Converte o objeto para dicionário (para JSON)"""
        return {
            'id': self.id,
            'unidade': self.unidade,
            'periodo': self.periodo,
            'receita_total': self.receita_total,
            'despesas_operacionais': self.despesas_operacionais,
            'lucro_liquido': self.lucro_liquido,
            'data_criacao': self.data_criacao.strftime('%Y-%m-%d')
        }

class Suprimento(db.Model):
    """Modelo para controle de suprimentos"""
    __tablename__ = 'suprimentos'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    quantidade_estoque = db.Column(db.Integer, nullable=False, default=0)
    quantidade_minima = db.Column(db.Integer, nullable=False, default=0)
    preco_unitario = db.Column(db.Float, nullable=False)
    fornecedor = db.Column(db.String(100), nullable=False)
    validade = db.Column(db.String(20))  # formato: YYYY-MM-DD
    unidade = db.Column(db.String(100), nullable=False)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Suprimento {self.nome} - {self.unidade}>'
    
    def to_dict(self):
        """Converte o objeto para dicionário (para JSON)"""
        return {
            'id': self.id,
            'nome': self.nome,
            'categoria': self.categoria,
            'quantidade_estoque': self.quantidade_estoque,
            'quantidade_minima': self.quantidade_minima,
            'preco_unitario': self.preco_unitario,
            'fornecedor': self.fornecedor,
            'validade': self.validade,
            'unidade': self.unidade,
            'data_cadastro': self.data_cadastro.strftime('%Y-%m-%d'),
            'status_estoque': 'BAIXO' if self.quantidade_estoque < self.quantidade_minima else 'OK'
        }

# =============================================================================
# FUNÇÃO PARA INICIALIZAR O BANCO E DADOS DE EXEMPLO
# =============================================================================

def criar_dados_exemplo():
    """Cria dados de exemplo se o banco estiver vazio"""
    
    # Verificar se já existem dados
    if RelatorioFinanceiro.query.first() is None:
        # Relatórios de exemplo
        relatorios_exemplo = [
            RelatorioFinanceiro(
                unidade="SGHSS",
                periodo="2025-05",
                receita_total=850000.00,
                despesas_operacionais=620000.00,
                lucro_liquido=230000.00
            ),
        ]
        
        for relatorio in relatorios_exemplo:
            db.session.add(relatorio)
    
    if Suprimento.query.first() is None:
        # Suprimentos de exemplo
        suprimentos_exemplo = [
            Suprimento(
                nome="Luvas Descartáveis",
                categoria="EPI",
                quantidade_estoque=5000,
                quantidade_minima=1000,
                preco_unitario=0.25,
                fornecedor="MedSupply Ltda",
                validade="2025-03-15",
                unidade="Hospital Central"
            ),
            Suprimento(
                nome="Seringa 10ml",
                categoria="Material Hospitalar",
                quantidade_estoque=800,
                quantidade_minima=500,
                preco_unitario=1.50,
                fornecedor="Hospitalmed S.A.",
                validade="2026-01-20",
                unidade="Hospital Central"
            ),
            Suprimento(
                nome="Álcool Gel 70%",
                categoria="Higienização",
                quantidade_estoque=200,
                quantidade_minima=300,
                preco_unitario=12.50,
                fornecedor="Química Hospitalar",
                validade="2025-08-10",
                unidade="Clínica Bairro Norte"
            )
        ]
        
        for suprimento in suprimentos_exemplo:
            db.session.add(suprimento)
    
    # Salvar todas as alterações
    db.session.commit()

# =============================================================================
# ROTAS DA API - HOME E INFORMAÇÕES
# =============================================================================

@app.route('/')
def home():
    return {"sistema": "Sistema VidaPlus - ADM", "status": "online"}

# =============================================================================
# ROTAS DA API - RELATÓRIOS FINANCEIROS
# =============================================================================

@app.route('/api/relatorios', methods=['GET'])
def listar_relatorios():
    """Lista todos os relatórios financeiros"""
    relatorios = RelatorioFinanceiro.query.all()
    
    return jsonify({
        "status": "sucesso",
        "total_relatorios": len(relatorios),
        "relatorios": [relatorio.to_dict() for relatorio in relatorios]
    })

@app.route('/api/relatorios/<int:relatorio_id>', methods=['GET'])
def obter_relatorio(relatorio_id):
    """Obtém um relatório específico pelo ID"""
    relatorio = RelatorioFinanceiro.query.get(relatorio_id)
    
    if relatorio:
        return jsonify({
            "status": "sucesso",
            "relatorio": relatorio.to_dict()
        })
    else:
        return jsonify({
            "status": "erro",
            "mensagem": "Relatório não encontrado"
        }), 404

@app.route('/api/relatorios', methods=['POST'])
def criar_relatorio():
    """Cria um novo relatório financeiro"""
    dados = request.get_json()
    
    # Validação dos campos obrigatórios
    campos_obrigatorios = ['unidade', 'periodo', 'receita_total', 'despesas_operacionais']
    for campo in campos_obrigatorios:
        if campo not in dados:
            return jsonify({
                "status": "erro",
                "mensagem": f"Campo obrigatório '{campo}' não fornecido"
            }), 400
    
    try:
        # Calculando lucro líquido automaticamente
        receita = float(dados['receita_total'])
        despesas = float(dados['despesas_operacionais'])
        lucro_liquido = receita - despesas
        
        # Criando novo relatório
        novo_relatorio = RelatorioFinanceiro(
            unidade=dados['unidade'],
            periodo=dados['periodo'],
            receita_total=receita,
            despesas_operacionais=despesas,
            lucro_liquido=lucro_liquido
        )
        
        # Salvando no banco
        db.session.add(novo_relatorio)
        db.session.commit()
        
        return jsonify({
            "status": "sucesso",
            "mensagem": "Relatório criado com sucesso",
            "relatorio": novo_relatorio.to_dict()
        }), 201
        
    except ValueError:
        return jsonify({
            "status": "erro",
            "mensagem": "Valores numéricos inválidos"
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "erro",
            "mensagem": f"Erro interno: {str(e)}"
        }), 500



# =============================================================================
# ROTAS DA API - SUPRIMENTOS
# =============================================================================

@app.route('/api/suprimentos', methods=['GET'])
def listar_suprimentos():
    """Lista todos os suprimentos"""
    suprimentos = Suprimento.query.all()
    
    return jsonify({
        "status": "sucesso",
        "total_suprimentos": len(suprimentos),
        "suprimentos": [suprimento.to_dict() for suprimento in suprimentos]
    })

@app.route('/api/suprimentos/<int:suprimento_id>', methods=['GET'])
def obter_suprimento(suprimento_id):
    """Obtém um suprimento específico pelo ID"""
    suprimento = Suprimento.query.get(suprimento_id)
    
    if suprimento:
        return jsonify({
            "status": "sucesso",
            "suprimento": suprimento.to_dict()
        })
    else:
        return jsonify({
            "status": "erro",
            "mensagem": "Suprimento não encontrado"
        }), 404

@app.route('/api/suprimentos', methods=['POST'])
def criar_suprimento():
    """Adiciona um novo suprimento"""
    dados = request.get_json()
    
    # Validação dos campos obrigatórios
    campos_obrigatorios = ['nome', 'categoria', 'quantidade_estoque', 'quantidade_minima', 'preco_unitario', 'fornecedor', 'unidade']
    for campo in campos_obrigatorios:
        if campo not in dados:
            return jsonify({
                "status": "erro",
                "mensagem": f"Campo obrigatório '{campo}' não fornecido"
            }), 400
    
    try:
        novo_suprimento = Suprimento(
            nome=dados['nome'],
            categoria=dados['categoria'],
            quantidade_estoque=int(dados['quantidade_estoque']),
            quantidade_minima=int(dados['quantidade_minima']),
            preco_unitario=float(dados['preco_unitario']),
            fornecedor=dados['fornecedor'],
            validade=dados.get('validade', ''),  # Campo opcional
            unidade=dados['unidade']
        )
        
        db.session.add(novo_suprimento)
        db.session.commit()
        
        return jsonify({
            "status": "sucesso",
            "mensagem": "Suprimento adicionado com sucesso",
            "suprimento": novo_suprimento.to_dict()
        }), 201
        
    except ValueError:
        return jsonify({
            "status": "erro",
            "mensagem": "Valores numéricos inválidos"
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "erro",
            "mensagem": f"Erro interno: {str(e)}"
        }), 500

@app.route('/api/suprimentos/<int:suprimento_id>', methods=['PUT'])
def atualizar_suprimento(suprimento_id):
    """Atualiza informações de um suprimento"""
    dados = request.get_json()
    
    suprimento = Suprimento.query.get(suprimento_id)
    
    if not suprimento:
        return jsonify({
            "status": "erro",
            "mensagem": "Suprimento não encontrado"
        }), 404
    
    try:
        # Atualiza apenas os campos fornecidos
        if 'quantidade_estoque' in dados:
            suprimento.quantidade_estoque = int(dados['quantidade_estoque'])
        
        if 'preco_unitario' in dados:
            suprimento.preco_unitario = float(dados['preco_unitario'])
            
        if 'quantidade_minima' in dados:
            suprimento.quantidade_minima = int(dados['quantidade_minima'])
        
        db.session.commit()
        
        return jsonify({
            "status": "sucesso",
            "mensagem": "Suprimento atualizado com sucesso",
            "suprimento": suprimento.to_dict()
        })
        
    except ValueError:
        return jsonify({
            "status": "erro",
            "mensagem": "Valores numéricos inválidos"
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "erro",
            "mensagem": f"Erro ao atualizar: {str(e)}"
        }), 500


@app.route('/api/suprimentos/estoque-baixo', methods=['GET'])
def suprimentos_estoque_baixo():
    """Lista suprimentos com estoque abaixo do mínimo"""
    suprimentos_baixo = Suprimento.query.filter(
        Suprimento.quantidade_estoque < Suprimento.quantidade_minima
    ).all()
    
    return jsonify({
        "status": "sucesso",
        "total_itens_estoque_baixo": len(suprimentos_baixo),
        "suprimentos_estoque_baixo": [s.to_dict() for s in suprimentos_baixo]
    })

@app.route('/api/suprimentos/categoria/<categoria>', methods=['GET'])
def suprimentos_por_categoria(categoria):
    """Lista suprimentos por categoria"""
    suprimentos = Suprimento.query.filter_by(categoria=categoria).all()
    
    return jsonify({
        "status": "sucesso",
        "categoria": categoria,
        "total_suprimentos": len(suprimentos),
        "suprimentos": [s.to_dict() for s in suprimentos]
    })

# =============================================================================
# ROTA PARA DASHBOARD RESUMIDO
# =============================================================================

@app.route('/api/dashboard', methods=['GET'])
def dashboard():
    """Retorna informações resumidas para o dashboard"""
    
    # Consultas ao banco de dados
    total_relatorios = RelatorioFinanceiro.query.count()
    receita_total = db.session.query(db.func.sum(RelatorioFinanceiro.receita_total)).scalar() or 0
    lucro_total = db.session.query(db.func.sum(RelatorioFinanceiro.lucro_liquido)).scalar() or 0
    
    total_suprimentos = Suprimento.query.count()
    estoque_baixo = Suprimento.query.filter(
        Suprimento.quantidade_estoque < Suprimento.quantidade_minima
    ).count()
    
    # Cálculo do valor total do estoque
    suprimentos = Suprimento.query.all()
    valor_total_estoque = sum(s.quantidade_estoque * s.preco_unitario for s in suprimentos)
    
    return jsonify({
        "status": "sucesso",
        "dashboard": {
            "resumo_financeiro": {
                "receita_total_periodo": float(receita_total),
                "lucro_total_periodo": float(lucro_total),
                "total_relatorios": total_relatorios,
                "margem_lucro_media": float(lucro_total / receita_total * 100) if receita_total > 0 else 0
            },
            "resumo_suprimentos": {
                "total_suprimentos": total_suprimentos,
                "itens_estoque_baixo": estoque_baixo,
                "valor_total_estoque": float(valor_total_estoque),
                "percentual_estoque_baixo": float(estoque_baixo / total_suprimentos * 100) if total_suprimentos > 0 else 0
            }
        }
    })

# =============================================================================
# INICIALIZAÇÃO E EXECUÇÃO DA APLICAÇÃO
# =============================================================================

if __name__ == '__main__':
    print("🏥 Iniciando Sistema de Gestão Hospitalar - VidaPlus")
    
    # Criar todas as tabelas
    with app.app_context():
        db.create_all()
        criar_dados_exemplo()
        print("✅ Banco de dados inicializado com sucesso!") 
    print("\n🚀 Servidor rodando em http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)