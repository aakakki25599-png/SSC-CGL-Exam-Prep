from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from pyq_data import PYQ_QUESTIONS, NOTES_DATA
import json

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        
        if not username or not email or not password:
            flash('All fields required', 'error')
            return redirect(url_for('auth.register'))
        
        if password != confirm:
            flash('Passwords do not match', 'error')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('auth.register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=request.form.get('remember'))
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('main.home'))
        
        flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('main.home'))

@auth_bp.route('/init-db')
def init_db():
    """Initialize DB with sample data (run once)"""
    # Add all PYQ questions
    for q in PYQ_QUESTIONS:
        existing = Question.query.filter_by(year=q['year'], q_en=q['q_en']).first()
        if not existing:
            question = Question(
                year=q['year'],
                month=q['month'],
                subject=q['subject'],
                topic=q['topic'],
                q_en=q['q_en'],
                q_hi=q['q_hi'],
                options_json=json.dumps(q['options']),
                answer=q['answer'],
                exp_en=q['exp_en'],
                exp_hi=q['exp_hi']
            )
            db.session.add(question)
    
    # Add notes
    for n in NOTES_DATA:
        existing = Notes.query.filter_by(subject=n['subject'], topic=n['topic']).first()
        if not existing:
            note = Notes(
                subject=n['subject'],
                topic=n['topic'],
                title_en=n['title_en'],
                title_hi=n['title_hi'],
                body_en=n['body_en'],
                body_hi=n['body_hi']
            )
            db.session.add(note)
    
    # Add sample admin
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@ssc.local', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
    
    db.session.commit()
    return 'Database initialized! Username: admin, Password: admin123'
