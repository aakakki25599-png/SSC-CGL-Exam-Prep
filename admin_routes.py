from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import db, User, Question, Notes
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    total_users = User.query.count()
    total_questions = Question.query.count()
    total_notes = Notes.query.count()
    subjects = db.session.query(Question.subject).distinct().count()
    return render_template('admin/dashboard.html', total_users=total_users, total_questions=total_questions, total_notes=total_notes, subjects=subjects)

@admin_bp.route('/questions', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_questions():
    if request.method == 'POST':
        data = request.json
        q = Question(
            year=data.get('year'),
            month=data.get('month'),
            subject=data.get('subject'),
            topic=data.get('topic'),
            q_en=data.get('q_en'),
            q_hi=data.get('q_hi'),
            options_json=json.dumps(data.get('options', [])),
            answer=data.get('answer'),
            exp_en=data.get('exp_en'),
            exp_hi=data.get('exp_hi')
        )
        db.session.add(q)
        db.session.commit()
        return jsonify({'success': True, 'id': q.id})
    
    questions = Question.query.order_by(Question.year.desc()).all()
    return render_template('admin/questions.html', questions=questions)

@admin_bp.route('/questions/<int:qid>/edit', methods=['POST'])
@login_required
@admin_required
def edit_question(qid):
    q = Question.query.get_or_404(qid)
    data = request.json
    q.year = data.get('year', q.year)
    q.month = data.get('month', q.month)
    q.subject = data.get('subject', q.subject)
    q.topic = data.get('topic', q.topic)
    q.q_en = data.get('q_en', q.q_en)
    q.q_hi = data.get('q_hi', q.q_hi)
    q.options_json = json.dumps(data.get('options', q.get_options()))
    q.answer = data.get('answer', q.answer)
    q.exp_en = data.get('exp_en', q.exp_en)
    q.exp_hi = data.get('exp_hi', q.exp_hi)
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/questions/<int:qid>/delete', methods=['POST'])
@login_required
@admin_required
def delete_question(qid):
    q = Question.query.get_or_404(qid)
    db.session.delete(q)
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/notes', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_notes():
    if request.method == 'POST':
        data = request.json
        n = Notes(
            subject=data.get('subject'),
            topic=data.get('topic'),
            title_en=data.get('title_en'),
            title_hi=data.get('title_hi'),
            body_en=data.get('body_en'),
            body_hi=data.get('body_hi')
        )
        db.session.add(n)
        db.session.commit()
        return jsonify({'success': True, 'id': n.id})
    
    notes = Notes.query.all()
    return render_template('admin/notes.html', notes=notes)

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:uid>/role', methods=['POST'])
@login_required
@admin_required
def change_user_role(uid):
    user = User.query.get_or_404(uid)
    data = request.json
    user.role = data.get('role', user.role)
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    from sqlalchemy import func
    from models import UserProgress
    
    subject_stats = db.session.query(
        UserProgress.subject,
        func.avg(UserProgress.accuracy).label('avg_accuracy'),
        func.count(UserProgress.user_id).label('users_count')
    ).group_by(UserProgress.subject).all()
    
    return render_template('admin/analytics.html', subject_stats=subject_stats)
