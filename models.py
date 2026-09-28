from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(20), default='user')  # admin, user
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    progress = db.relationship('UserProgress', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer)
    month = db.Column(db.String(20))
    subject = db.Column(db.String(50), nullable=False)
    topic = db.Column(db.String(100))
    q_en = db.Column(db.Text, nullable=False)
    q_hi = db.Column(db.Text)
    options_json = db.Column(db.Text)  # JSON array
    answer = db.Column(db.Integer)
    exp_en = db.Column(db.Text)
    exp_hi = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_options(self):
        return json.loads(self.options_json) if self.options_json else []

class Notes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(50))
    topic = db.Column(db.String(100))
    title_en = db.Column(db.String(200))
    title_hi = db.Column(db.String(200))
    body_en = db.Column(db.Text)
    body_hi = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(50))
    topic = db.Column(db.String(100))
    total_attempts = db.Column(db.Integer, default=0)
    correct = db.Column(db.Integer, default=0)
    incorrect = db.Column(db.Integer, default=0)
    accuracy = db.Column(db.Float, default=0.0)
    last_attempt = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    bookmarked_ids = db.Column(db.Text, default='')  # Comma-separated question IDs
    
    def add_bookmark(self, q_id):
        ids = [int(x) for x in self.bookmarked_ids.split(',') if x]
        if q_id not in ids:
            ids.append(q_id)
            self.bookmarked_ids = ','.join(map(str, ids))
    
    def remove_bookmark(self, q_id):
        ids = [int(x) for x in self.bookmarked_ids.split(',') if x]
        if q_id in ids:
            ids.remove(q_id)
            self.bookmarked_ids = ','.join(map(str, ids))
