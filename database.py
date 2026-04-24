from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import numpy as np

db = SQLAlchemy()

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    face_encoding_path = db.Column(db.String(255)) 

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(50), unique=True, nullable=False)
    course = db.Column(db.String(100)) # Used for Course/Semester
    phone = db.Column(db.String(20))
    dob = db.Column(db.String(20))
    role = db.Column(db.String(20), default='Student')
    email = db.Column(db.String(120))
    password = db.Column(db.String(255)) 
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    attendances = db.relationship('Attendance', backref='student', lazy=True, cascade="all, delete-orphan")

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(20), default='Present')
    check_in_time = db.Column(db.DateTime, default=datetime.now)
