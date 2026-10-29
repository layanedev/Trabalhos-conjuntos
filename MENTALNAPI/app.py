from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json

app = Flask(__name__)
app.secret_key = 'mentalnapi_secret_key_2026'

# ADICIONADO: Permite acesso à session nos templates
@app.context_processor
def inject_session():
    return dict(session=session)

EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'email_remetente': 'mentalnapi.suporte@gmail.com',
    'email_senha': 'myfasylkrjttpqyd',
    'email_destino': 'layaneraissatabletinfo@gmail.com'
}

def salvar_usuario_json(nome, usuario, senha, casa, data_cadastro):
    try:
        novo_usuario = {
            'nome': nome,
            'usuario': usuario,
            'senha': senha,
            'casa': casa,
            'data_cadastro': data_cadastro
        }
        
        if os.path.exists('usuarios.json'):
            with open('usuarios.json', 'r', encoding='utf-8') as f:
                try:
                    dados = json.load(f)
                    if isinstance(dados, dict) and 'usuarios' in dados:
                        usuarios = dados['usuarios']
                    else:
                        usuarios = dados if isinstance(dados, list) else []
                except json.JSONDecodeError:
                    usuarios = []
        else:
            usuarios = []
        
        usuario_existente = False
        for u in usuarios:
            if u.get('usuario') == usuario:
                usuario_existente = True
                break
        
        if not usuario_existente:
            usuarios.append(novo_usuario)
            
            with open('usuarios.json', 'w', encoding='utf-8') as f:
                json.dump({'usuarios': usuarios}, f, ensure_ascii=False, indent=2)
            
            return True, "Usuário salvo com sucesso!"
        else:
            return False, "Usuário já existe!"
            
    except Exception as e:
        print(f"Erro ao salvar no JSON: {str(e)}")
        return False, f"Erro ao salvar no JSON: {str(e)}"

def ler_usuarios_json():
    try:
        if os.path.exists('usuarios.json'):
            with open('usuarios.json', 'r', encoding='utf-8') as f:
                dados = json.load(f)
                if isinstance(dados, dict) and 'usuarios' in dados:
                    return dados['usuarios']
                elif isinstance(dados, list):
                    return dados
        return []
    except Exception as e:
        print(f"Erro ao ler JSON: {str(e)}")
        return []

def init_db():
    conn = sqlite3.connect('mentalnapi.db')
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            casa TEXT NOT NULL,
            data_cadastro TEXT NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS psicologas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            crp TEXT NOT NULL,
            especialidade TEXT NOT NULL,
            unidade TEXT NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS horarios_psicologas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            psicologa_id INTEGER NOT NULL,
            dia_semana INTEGER NOT NULL,
            horario TEXT NOT NULL,
            FOREIGN KEY (psicologa_id) REFERENCES psicologas(id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            psicologa_id INTEGER NOT NULL,
            unidade TEXT NOT NULL,
            data TEXT NOT NULL,
            horario TEXT NOT NULL,
            modalidade TEXT NOT NULL,
            status TEXT DEFAULT 'Agendado',
            observacoes TEXT,
            data_criacao TEXT NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (psicologa_id) REFERENCES psicologas(id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            psicologa_id INTEGER NOT NULL,
            mensagem TEXT NOT NULL,
            remetente TEXT NOT NULL,
            data_envio TEXT NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (psicologa_id) REFERENCES psicologas(id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS mensagens_contato (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL,
            telefone TEXT,
            assunto TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            status TEXT DEFAULT 'Nao lida',
            data_envio TEXT NOT NULL,
            usuario_id INTEGER
        )
    ''')
    
    c.execute("SELECT COUNT(*) FROM psicologas")
    if c.fetchone()[0] == 0:
        psicologas = [
            ('Barbara', 'CRP 12/34567', 'Psicopedagoga - Especialista em adolescentes', 'Unidade Natal-zn'),
            ('Carol', 'CRP 12/34568', 'Psicopedagoga - Foco em inclusao escolar', 'Unidade Natal-zn'),
            ('Evandilson', 'CRP 12/34569', 'Psicopedagogo - Acompanhamento de jovens', 'Unidade Mossoro'),
            ('Yara', 'CRP 12/34570', 'Psicologa - Saude mental e bem-estar', 'Unidade Mossoro')
        ]
        c.executemany('INSERT INTO psicologas (nome, crp, especialidade, unidade) VALUES (?, ?, ?, ?)', psicologas)
        
        horarios = [
            (1, 1, '08:00'), (1, 1, '09:00'), (1, 1, '10:00'),
            (1, 2, '08:00'), (1, 2, '09:00'), (1, 2, '10:00'),
            (1, 4, '14:00'), (1, 4, '15:00'), (1, 4, '16:00'),
            (2, 1, '14:00'), (2, 1, '15:00'), (2, 1, '16:00'),
            (2, 2, '14:00'), (2, 2, '15:00'), (2, 2, '16:00'),
            (2, 5, '08:00'), (2, 5, '09:00'), (2, 5, '10:00'),
            (3, 1, '08:00'), (3, 1, '09:00'), (3, 1, '10:00'),
            (3, 3, '08:00'), (3, 3, '09:00'), (3, 3, '10:00'),
            (3, 5, '14:00'), (3, 5, '15:00'), (3, 5, '16:00'),
            (4, 2, '14:00'), (4, 2, '15:00'), (4, 2, '16:00'),
            (4, 4, '14:00'), (4, 4, '15:00'), (4, 4, '16:00'),
            (4, 6, '08:00'), (4, 6, '09:00'), (4, 6, '10:00')
        ]
        c.executemany('INSERT INTO horarios_psicologas (psicologa_id, dia_semana, horario) VALUES (?, ?, ?)', horarios)
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('mentalnapi.db')
    conn.row_factory = sqlite3.Row
    return conn

def enviar_email_contato(nome, email, telefone, assunto, mensagem):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['email_remetente']
        msg['To'] = EMAIL_CONFIG['email_destino']
        msg['Subject'] = f"[MENTALNAPI] Contato - {assunto}"
        
        corpo_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 10px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .campo {{ margin-bottom: 15px; }}
                .label {{ font-weight: bold; color: #333; }}
                .valor {{ margin-left: 10px; color: #555; }}
                .footer {{ text-align: center; padding: 10px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Nova Mensagem de Contato</h2>
                </div>
                <div class="content">
                    <div class="campo">
                        <span class="label">Nome:</span>
                        <span class="valor">{nome}</span>
                    </div>
                    <div class="campo">
                        <span class="label">Email:</span>
                        <span class="valor">{email}</span>
                    </div>
                    <div class="campo">
                        <span class="label">Telefone:</span>
                        <span class="valor">{telefone if telefone else 'Nao informado'}</span>
                    </div>
                    <div class="campo">
                        <span class="label">Assunto:</span>
                        <span class="valor">{assunto}</span>
                    </div>
                    <div class="campo">
                        <span class="label">Mensagem:</span>
                        <div style="background-color: white; padding: 15px; border-radius: 5px; margin-top: 5px; border-left: 4px solid #4CAF50;">
                            {mensagem.replace(chr(10), '<br>')}
                        </div>
                    </div>
                    <div style="margin-top: 20px; padding-top: 10px; border-top: 1px solid #ddd; font-size: 14px; color: #888;">
                        <p>Data de envio: {datetime.now().strftime('%d/%m/%Y as %H:%M')}</p>
                        <p>Enviado atraves do site MentalNapi</p>
                    </div>
                </div>
                <div class="footer">
                    <p>Este email foi gerado automaticamente pelo sistema MentalNapi</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(corpo_html, 'html'))
        
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['email_remetente'], EMAIL_CONFIG['email_senha'])
            server.send_message(msg)
        
        enviar_email_confirmacao(nome, email)
        
        return True, "Email enviado com sucesso!"
    
    except Exception as e:
        print(f"Erro ao enviar email: {str(e)}")
        return False, f"Erro ao enviar email: {str(e)}"

def enviar_email_confirmacao(nome, email_destino):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['email_remetente']
        msg['To'] = email_destino
        msg['Subject'] = "MentalNapi - Recebemos sua mensagem"
        
        corpo_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 10px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .footer {{ text-align: center; padding: 10px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Mensagem Recebida</h2>
                </div>
                <div class="content">
                    <p>Ola <strong>{nome}</strong>,</p>
                    <p>Agradecemos por entrar em contato com a <strong>MentalNapi</strong>.</p>
                    <p>Recebemos sua mensagem e em breve nossa equipe entrara em contato.</p>
                    <div style="background-color: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p style="margin: 0; color: #2e7d32;">Agradecemos pelo seu interesse em nossos servicos</p>
                    </div>
                    <p style="color: #666; font-size: 14px;">
                        Atenciosamente,<br>
                        <strong>Equipe MentalNapi</strong>
                    </p>
                </div>
                <div class="footer">
                    <p>MentalNapi - Cuidando da sua saude mental</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(corpo_html, 'html'))
        
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['email_remetente'], EMAIL_CONFIG['email_senha'])
            server.send_message(msg)
        
        return True
    
    except Exception as e:
        print(f"Erro ao enviar email de confirmacao: {str(e)}")
        return False

@app.route('/')
def inicio():
    return render_template('inicio.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/logar', methods=['GET', 'POST'])
def logar():
    if request.method == 'POST':
        usuario = request.form.get('username')
        senha = request.form.get('password')
        casa = request.form.get('casa')
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM usuarios WHERE usuario = ? AND casa = ?',
            (usuario, casa)
        ).fetchone()
        conn.close()
        
        if user and user['senha'] == senha:
            session['usuario_logado'] = True
            session['usuario_id'] = user['id']
            session['usuario_nome'] = user['nome']
            session['usuario_casa'] = user['casa']
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('menu'))
        else:
            flash('Usuario, senha ou unidade incorretos.', 'danger')
    
    return render_template('log.html')

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        nome = request.form.get('nome')
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')
        casa = request.form.get('casa')
        data_cadastro = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn = get_db_connection()
        
        existe = conn.execute('SELECT id FROM usuarios WHERE usuario = ?', (usuario,)).fetchone()
        
        if existe:
            flash('Usuario ja cadastrado. Escolha outro nome.', 'danger')
            conn.close()
            return render_template('cadastro.html')
        
        try:
            conn.execute(
                'INSERT INTO usuarios (nome, usuario, senha, casa, data_cadastro) VALUES (?, ?, ?, ?, ?)',
                (nome, usuario, senha, casa, data_cadastro)
            )
            conn.commit()
            
            sucesso_json, mensagem_json = salvar_usuario_json(nome, usuario, senha, casa, data_cadastro)
            
            if sucesso_json:
                flash(f'Cadastro realizado com sucesso! {mensagem_json}', 'success')
            else:
                flash(f'Cadastro realizado no banco, mas {mensagem_json}', 'warning')
                
        except Exception as e:
            conn.rollback()
            flash(f'Erro ao cadastrar: {str(e)}', 'danger')
            conn.close()
            return render_template('cadastro.html')
        
        conn.close()
        return redirect(url_for('logar'))
    
    return render_template('cadastro.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso.', 'info')
    return redirect(url_for('inicio'))

@app.route('/menu')
def menu():
    if not session.get('usuario_logado'):
        flash('Por favor, faca login primeiro.', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    agendamentos = conn.execute('''
        SELECT a.*, p.nome as psicologa_nome 
        FROM agendamentos a
        JOIN psicologas p ON a.psicologa_id = p.id
        WHERE a.usuario_id = ? AND a.status = 'Agendado'
        ORDER BY a.data ASC, a.horario ASC
    ''', (session['usuario_id'],)).fetchall()
    conn.close()
    
    return render_template('menu.html', agendamentos=agendamentos)

@app.route('/unidades')
def unidades():
    if not session.get('usuario_logado'):
        flash('Por favor, faca login primeiro.', 'warning')
        return redirect(url_for('login'))
    
    unidade_selecionada = request.args.get('unidade', 'Unidade Natal-zn')
    
    unidades = {
        'Unidade Natal-zn': 'Natal - Zona Norte',
        'Unidade Mossoro': 'Mossoro'
    }
    
    conn = get_db_connection()
    psicologas = conn.execute('''
        SELECT p.*, GROUP_CONCAT(h.horario) as horarios
        FROM psicologas p
        LEFT JOIN horarios_psicologas h ON p.id = h.psicologa_id
        WHERE p.unidade = ?
        GROUP BY p.id
    ''', (unidade_selecionada,)).fetchall()
    
    psicologas_lista = []
    for p in psicologas:
        horarios_list = p['horarios'].split(',') if p['horarios'] else []
        horarios_exibir = horarios_list[:3] if horarios_list else ['Sem horarios disponiveis']
        psicologas_lista.append({
            'id': p['id'],
            'nome': p['nome'],
            'crp': p['crp'],
            'especialidade': p['especialidade'],
            'unidade': p['unidade'],
            'horarios': horarios_exibir
        })
    
    conn.close()
    
    return render_template('unidades.html', 
                         unidades=unidades, 
                         unidade_atual=unidade_selecionada,
                         psicologas=psicologas_lista)

@app.route('/agendar_direto')
def agendar_direto():
    if not session.get('usuario_logado'):
        flash('Por favor, faca login primeiro.', 'warning')
        return redirect(url_for('login'))
    
    unidade = session.get('usuario_casa', 'Unidade Natal-zn')
    return redirect(url_for('unidades', unidade=unidade))

@app.route('/meus_agendamentos')
def meus_agendamentos():
    if not session.get('usuario_logado'):
        flash('Por favor, faca login primeiro.', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    agendamentos = conn.execute('''
        SELECT a.*, p.nome as psicologa_nome 
        FROM agendamentos a
        JOIN psicologas p ON a.psicologa_id = p.id
        WHERE a.usuario_id = ? AND a.status = 'Agendado'
        ORDER BY a.data ASC, a.horario ASC
    ''', (session['usuario_id'],)).fetchall()
    conn.close()
    
    return render_template('meus_agendamentos.html', agendamentos=agendamentos)

@app.route('/historico')
def historico():
    if not session.get('usuario_logado'):
        flash('Por favor, faca login primeiro.', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    consultas = conn.execute('''
        SELECT a.*, p.nome as psicologa_nome 
        FROM agendamentos a
        JOIN psicologas p ON a.psicologa_id = p.id
        WHERE a.usuario_id = ?
        ORDER BY a.data DESC, a.horario DESC
    ''', (session['usuario_id'],)).fetchall()
    
    chats = conn.execute('''
        SELECT 
            c.psicologa_id,
            p.nome as psicologa_nome,
            COUNT(c.id) as total_mensagens,
            MAX(c.data_envio) as ultima_mensagem
        FROM chats c
        JOIN psicologas p ON c.psicologa_id = p.id
        WHERE c.usuario_id = ?
        GROUP BY c.psicologa_id
        ORDER BY ultima_mensagem DESC
    ''', (session['usuario_id'],)).fetchall()
    
    conn.close()
    
    return render_template('historico.html', consultas=consultas, chats=chats)

@app.route('/chats')
def chats():
    if not session.get('usuario_logado'):
        flash('Por favor, faca login primeiro.', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    psicologas = conn.execute('''
        SELECT DISTINCT p.* 
        FROM psicologas p
        INNER JOIN agendamentos a ON p.id = a.psicologa_id
        WHERE a.usuario_id = ? 
        AND a.status = 'Agendado' 
        AND a.modalidade = 'Online'
        ORDER BY p.nome ASC
    ''', (session['usuario_id'],)).fetchall()
    
    chats_existentes = conn.execute('''
        SELECT DISTINCT psicologa_id 
        FROM chats 
        WHERE usuario_id = ?
    ''', (session['usuario_id'],)).fetchall()
    
    chat_psicologas = [row['psicologa_id'] for row in chats_existentes]
    
    agendamentos_dict = {}
    for p in psicologas:
        agend = conn.execute('''
            SELECT id, data, horario, modalidade, status, observacoes
            FROM agendamentos 
            WHERE usuario_id = ? 
            AND psicologa_id = ? 
            AND status = 'Agendado' 
            AND modalidade = 'Online'
            ORDER BY data ASC, horario ASC
            LIMIT 1
        ''', (session['usuario_id'], p['id'])).fetchone()
        if agend:
            agendamentos_dict[p['id']] = dict(agend)
    
    conn.close()
    
    return render_template('chats.html', 
                         psicologas=psicologas, 
                         chat_psicologas=chat_psicologas,
                         agendamentos=agendamentos_dict)

@app.route('/chat/<int:psicologa_id>')
def chat(psicologa_id):
    if not session.get('usuario_logado'):
        flash('Por favor, faca login primeiro.', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    psicologa = conn.execute('SELECT * FROM psicologas WHERE id = ?', (psicologa_id,)).fetchone()
    
    mensagens = conn.execute('''
        SELECT * FROM chats 
        WHERE usuario_id = ? AND psicologa_id = ?
        ORDER BY data_envio ASC
    ''', (session['usuario_id'], psicologa_id)).fetchall()
    
    conn.close()
    
    if not psicologa:
        flash('Psicologa nao encontrada.', 'danger')
        return redirect(url_for('unidades'))
    
    return render_template('chat_detalhe.html', psicologa=psicologa, mensagens=mensagens)

@app.route('/enviar_mensagem', methods=['POST'])
def enviar_mensagem():
    if not session.get('usuario_logado'):
        return {'erro': 'Nao autorizado'}, 401
    
    psicologa_id = request.form.get('psicologa_id')
    mensagem = request.form.get('mensagem')
    
    if not mensagem or mensagem.strip() == '':
        flash('Digite uma mensagem.', 'warning')
        return redirect(url_for('chat', psicologa_id=psicologa_id))
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO chats (usuario_id, psicologa_id, mensagem, remetente, data_envio)
        VALUES (?, ?, ?, ?, ?)
    ''', (session['usuario_id'], psicologa_id, mensagem, 'Usuario', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    
    flash('Mensagem enviada!', 'success')
    return redirect(url_for('chat', psicologa_id=psicologa_id))

@app.route('/cancelar_agendamento/<int:agendamento_id>', methods=['POST'])
def cancelar_agendamento(agendamento_id):
    if not session.get('usuario_logado'):
        flash('Por favor, faca login.', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    agendamento = conn.execute(
        'SELECT * FROM agendamentos WHERE id = ? AND usuario_id = ?',
        (agendamento_id, session['usuario_id'])
    ).fetchone()
    
    if not agendamento:
        flash('Agendamento nao encontrado.', 'danger')
        conn.close()
        return redirect(url_for('meus_agendamentos'))
    
    conn.execute(
        'UPDATE agendamentos SET status = ? WHERE id = ?',
        ('Cancelado', agendamento_id)
    )
    conn.commit()
    conn.close()
    
    flash('Agendamento cancelado com sucesso!', 'success')
    return redirect(url_for('meus_agendamentos'))

@app.route('/agendar', methods=['POST'])
def agendar():
    if not session.get('usuario_logado'):
        flash('Por favor, faca login.', 'warning')
        return redirect(url_for('login'))
    
    unidade = request.form.get('unidade')
    psicologa_nome = request.form.get('psicologa')
    data = request.form.get('data')
    horario = request.form.get('horario')
    modalidade = request.form.get('modalidade')
    observacoes = request.form.get('observacoes', '')
    
    if not all([unidade, psicologa_nome, data, horario, modalidade]):
        flash('Preencha todos os campos obrigatorios.', 'danger')
        return redirect(url_for('menu'))
    
    conn = get_db_connection()
    
    psicologa = conn.execute(
        'SELECT id FROM psicologas WHERE nome = ? AND unidade = ?',
        (psicologa_nome, unidade)
    ).fetchone()
    
    if not psicologa:
        flash('Psicologa nao encontrada.', 'danger')
        conn.close()
        return redirect(url_for('menu'))
    
    existe = conn.execute('''
        SELECT id FROM agendamentos 
        WHERE psicologa_id = ? AND data = ? AND horario = ? AND status = 'Agendado'
    ''', (psicologa['id'], data, horario)).fetchone()
    
    if existe:
        flash('Este horario ja esta ocupado.', 'danger')
        conn.close()
        return redirect(url_for('menu'))
    
    conn.execute('''
        INSERT INTO agendamentos (usuario_id, psicologa_id, unidade, data, horario, modalidade, status, observacoes, data_criacao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (session['usuario_id'], psicologa['id'], unidade, data, horario, modalidade, 'Agendado', observacoes, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    
    flash('Agendamento realizado com sucesso!', 'success')
    return redirect(url_for('meus_agendamentos'))

@app.route('/sobre')
def sobre():
    return render_template('sobre.html')

@app.route('/contato')
def contato():
    return render_template('contato.html')

@app.route('/enviar_contato', methods=['POST'])
def enviar_contato():
    nome = request.form.get('nome')
    email = request.form.get('email')
    telefone = request.form.get('telefone')
    assunto = request.form.get('assunto')
    mensagem = request.form.get('mensagem')
    
    if not all([nome, email, assunto, mensagem]):
        flash('Preencha todos os campos obrigatorios.', 'danger')
        return redirect(url_for('contato'))
    
    conn = get_db_connection()
    usuario_id = session.get('usuario_id', None)
    
    conn.execute('''
        INSERT INTO mensagens_contato (nome, email, telefone, assunto, mensagem, status, data_envio, usuario_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (nome, email, telefone, assunto, mensagem, 'Nao lida', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), usuario_id))
    conn.commit()
    conn.close()
    
    sucesso, mensagem_retorno = enviar_email_contato(nome, email, telefone, assunto, mensagem)
    
    if sucesso:
        flash('Mensagem enviada com sucesso! Entraremos em contato em breve. Voce recebera uma confirmacao por email.', 'success')
    else:
        flash(f'Mensagem salva no sistema, mas houve um erro ao enviar o email: {mensagem_retorno}. Entraremos em contato em breve.', 'warning')
    
    return redirect(url_for('contato'))

@app.route('/admin/mensagens')
def admin_mensagens():
    if not session.get('usuario_logado'):
        flash('Por favor, faca login primeiro.', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    mensagens = conn.execute('''
        SELECT m.*, u.nome as usuario_nome 
        FROM mensagens_contato m
        LEFT JOIN usuarios u ON m.usuario_id = u.id
        ORDER BY m.data_envio DESC
    ''').fetchall()
    
    total = conn.execute('SELECT COUNT(*) FROM mensagens_contato').fetchone()[0]
    nao_lidas = conn.execute("SELECT COUNT(*) FROM mensagens_contato WHERE status = 'Nao lida'").fetchone()[0]
    
    conn.close()
    
    return render_template('admin_mensagens.html', 
                         mensagens=mensagens,
                         total=total,
                         nao_lidas=nao_lidas)

@app.route('/admin/mensagem/<int:mensagem_id>/status', methods=['POST'])
def atualizar_status_mensagem(mensagem_id):
    if not session.get('usuario_logado'):
        flash('Por favor, faca login.', 'warning')
        return redirect(url_for('login'))
    
    novo_status = request.form.get('status')
    
    if novo_status not in ['Nao lida', 'Lida', 'Respondida']:
        flash('Status invalido.', 'danger')
        return redirect(url_for('admin_mensagens'))
    
    conn = get_db_connection()
    conn.execute(
        'UPDATE mensagens_contato SET status = ? WHERE id = ?',
        (novo_status, mensagem_id)
    )
    conn.commit()
    conn.close()
    
    flash('Status atualizado com sucesso!', 'success')
    return redirect(url_for('admin_mensagens'))

@app.route('/ver_usuarios')
def ver_usuarios():
    conn = get_db_connection()
    usuarios = conn.execute('SELECT * FROM usuarios').fetchall()
    conn.close()
    
    usuarios_json = ler_usuarios_json()
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Usuarios Cadastrados</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; background: #f5f9f8; }
            h1 { color: #1a3a3f; }
            h2 { color: #2a5a5f; margin-top: 30px; }
            table { border-collapse: collapse; width: 100%; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.06); }
            th { background: #4a9e8f; color: white; padding: 12px; text-align: left; }
            td { padding: 10px 12px; border-bottom: 1px solid #eee; }
            tr:hover { background: #f0f7f5; }
            .voltar { display: inline-block; margin-top: 20px; padding: 10px 25px; background: #4a9e8f; color: white; text-decoration: none; border-radius: 8px; }
            .voltar:hover { background: #3a8a7a; }
            .total { margin-bottom: 15px; color: #5a7a7f; }
            .json-tag { background: #e8f5e9; padding: 2px 8px; border-radius: 4px; font-size: 12px; color: #2e7d32; }
        </style>
    </head>
    <body>
        <h1>Usuarios Cadastrados</h1>
        <p class="total">Total no Banco de Dados: <strong>""" + str(len(usuarios)) + """</strong></p>
        <p class="total">Total no JSON: <strong>""" + str(len(usuarios_json)) + """</strong></p>
        
        <h2>Banco de Dados (mentalnapi.db)</h2>
        <table>
            <tr>
                <th>ID</th>
                <th>Nome</th>
                <th>Usuario</th>
                <th>Senha</th>
                <th>Unidade</th>
                <th>Data Cadastro</th>
            </tr>
    """
    
    for u in usuarios:
        html += f"""
            <tr>
                <td>{u['id']}</td>
                <td>{u['nome']}</td>
                <td>{u['usuario']}</td>
                <td>{u['senha']}</td>
                <td>{u['casa']}</td>
                <td>{u['data_cadastro']}</td>
            </tr>
        """
    
    html += """
        </table>
        
        <h2>Arquivo JSON (usuarios.json)</h2>
        <table>
            <tr>
                <th>#</th>
                <th>Nome</th>
                <th>Usuario</th>
                <th>Senha</th>
                <th>Unidade</th>
                <th>Data Cadastro</th>
            </tr>
    """
    
    for i, u in enumerate(usuarios_json, 1):
        html += f"""
            <tr>
                <td>{i}</td>
                <td>{u.get('nome', '')}</td>
                <td>{u.get('usuario', '')}</td>
                <td>{u.get('senha', '')}</td>
                <td>{u.get('casa', '')}</td>
                <td>{u.get('data_cadastro', '')}</td>
            </tr>
        """
    
    html += """
        </table>
        <br>
        <a href="/" class="voltar">Voltar para o inicio</a>
    </body>
    </html>
    """
    
    return html

@app.route('/ver_sessao')
def ver_sessao():
    return {
        'usuario_logado': session.get('usuario_logado'),
        'usuario_id': session.get('usuario_id'),
        'usuario_nome': session.get('usuario_nome'),
        'usuario_casa': session.get('usuario_casa')
    }

if __name__ == '__main__':
    init_db()
    print("Banco de dados inicializado (dados mantidos)")
    print("Servidor em: http://127.0.0.1:5000")
    app.run(debug=True)