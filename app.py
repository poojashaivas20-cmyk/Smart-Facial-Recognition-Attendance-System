from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from database import db, Student, Attendance, User, init_db
from face_handler import FaceHandler
from config import Config
from werkzeug.security import generate_password_hash, check_password_hash
import base64
import cv2
import numpy as np
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = os.urandom(24)
CORS(app)

# Initialize Database
init_db(app)

# Initialize Face Handler
fh = FaceHandler()

# --- EMAIL SERVICE ---
class EmailService:
    @staticmethod
    def send_absence_email(student_email, student_name):
        sender_email = app.config.get('MAIL_USERNAME')
        app_password = app.config.get('MAIL_PASSWORD')
        
        if not student_email or "@" not in student_email:
            return False

        today_formatted = datetime.now().strftime('%d:%b:%Y')  # e.g. 18:Apr:2026
        subject = f"Absent Notification - {student_name}"
        body = (
            f"Dear Parents,\n\n"
            f"{student_name} was absent today ({today_formatted}).\n\n"
            f"Regards,\n"
            f"SFRAS Attendance System"
        )
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = student_email

        try:
            with smtplib.SMTP_SSL(app.config.get('MAIL_SERVER', 'smtp.gmail.com'), app.config.get('MAIL_PORT', 465)) as server:
                server.login(sender_email, app_password)
                server.send_message(msg)
                print(f"DEBUG: Email sent to {student_email} for {student_name}")
            return True
        except Exception as e:
            print(f"Email Error: {e}")
            return False

# --- UTILS ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def retrain_system():
    students = Student.query.all()
    faces = []
    ids = []
    for s in students:
        path = f"static/faces/student_{s.id}.jpg"
        if os.path.exists(path):
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            img = cv2.resize(img, (200, 200))
            faces.append(img)
            ids.append(s.id)
    if faces:
        fh.train_recognizer(faces, ids)

# --- ROUTES ---
@app.route('/login')
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/user_registration')
def user_registration():
    return render_template('user_registration.html')

@app.route('/api/user_registration', methods=['POST'])
def api_user_registration():
    data = request.json
    hashed_pw = generate_password_hash(data.get('password'))
    new_user = User(fullname=data.get('fullname'), username=data.get('username'), password=hashed_pw)
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'success': True})
    except:
        return jsonify({'success': False, 'message': 'Username taken'})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    # Try admin user first
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        session['user_id'] = user.id
        session['fullname'] = user.fullname
        return jsonify({'success': True})
    
    # Try Faculty/Staff from Students table
    faculty = Student.query.filter(
        ((Student.roll_number == username) | (Student.email == username)),
        Student.role == 'Faculty',
        Student.password.isnot(None)
    ).first()
    
    if faculty and check_password_hash(faculty.password, password):
        session['user_id'] = f"faculty_{faculty.id}" # Use a unique prefix to avoid ID collisions
        session['fullname'] = faculty.name
        return jsonify({'success': True})
        
    return jsonify({'success': False, 'message': 'Invalid credentials'})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def home():
    """Default entry point: The Student Face Scanner."""
    return render_template('attendance.html')

@app.route('/dashboard')
@app.route('/admin/dashboard')
@login_required
def dashboard():
    total_students = Student.query.count()
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    attendance_today = Attendance.query.filter(
        Attendance.check_in_time >= today_start,
        Attendance.check_in_time <= today_end
    ).count()
    absent_today = total_students - attendance_today

    # Only show TODAY's recent activity — not historical records
    recent_logs = Attendance.query.filter(
        Attendance.check_in_time >= today_start,
        Attendance.check_in_time <= today_end
    ).order_by(Attendance.check_in_time.desc()).limit(8).all()
    
    labels, values = [], []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        d_start = datetime.combine(d, datetime.min.time())
        d_end = datetime.combine(d, datetime.max.time())
        labels.append(d.strftime('%b %d'))
        count = Attendance.query.filter(
            Attendance.check_in_time >= d_start,
            Attendance.check_in_time <= d_end
        ).count()
        values.append(count)
    
    return render_template('dashboard.html', total_students=total_students, attendance_today=attendance_today, 
                          absent_today=absent_today, recent_logs=recent_logs, 
                          chart_data={'labels': labels, 'values': values}, current_date=datetime.now().strftime('%A, %B %d, %Y'))

@app.route('/api/send_absent_alerts', methods=['POST'])
@login_required
def send_absent_alerts():
    today = datetime.now().date()
    all_students = Student.query.all()
    absentees_emailed = 0
    
    for student in all_students:
        atd = Attendance.query.filter(Attendance.student_id == student.id, db.func.date(Attendance.check_in_time) == today).first()
        if not atd and student.email:
            EmailService.send_absence_email(student.email, student.name)
            absentees_emailed += 1
            
    return jsonify({'success': True, 'message': f'Attempted to email {absentees_emailed} absentees.'})

@app.route('/management')
@login_required
def management():
    return render_template('registration.html', students=Student.query.all())

@app.route('/manual_attendance')
@login_required
def manual_attendance():
    students = Student.query.all()
    # Check if already marked today
    today = datetime.now().date()
    marked_ids = [a.student_id for a in Attendance.query.filter(db.func.date(Attendance.check_in_time) == today).all()]
    return render_template('manual_attendance.html', students=students, marked_ids=marked_ids)

@app.route('/api/mark_manual', methods=['POST'])
@login_required
def api_mark_manual():
    data = request.json
    sid = data.get('student_id')
    
    # 8-hour check for manual as well
    eight_hours_ago = datetime.now() - timedelta(hours=8)
    if Attendance.query.filter(Attendance.student_id == sid, Attendance.check_in_time > eight_hours_ago).first():
        return jsonify({'success': False, 'message': 'Already marked in the last 8 hours'})
    
    log = Attendance(student_id=sid)
    db.session.add(log)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Attendance marked manually'})


@app.route('/logs')
@login_required
def logs_ui():
    range_type = request.args.get('range', 'daily')
    selected_date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except:
        selected_date = datetime.now().date()
        selected_date_str = selected_date.strftime('%Y-%m-%d')

    # Determine Start and End Dates based on Range
    if range_type == 'weekly':
        # Start of the week (Monday)
        start_date = selected_date - timedelta(days=selected_date.weekday())
        end_date = start_date + timedelta(days=6)
        total_days = 7 # Simplification: use calendar days in the week
    elif range_type == 'monthly':
        # Start of the month
        start_date = selected_date.replace(day=1)
        # End of the month
        import calendar
        _, last_day = calendar.monthrange(selected_date.year, selected_date.month)
        end_date = selected_date.replace(day=last_day)
        total_days = last_day
    else:
        # Daily
        start_date = selected_date
        end_date = selected_date
        total_days = 1

    day_start = datetime.combine(start_date, datetime.min.time())
    day_end   = datetime.combine(end_date, datetime.max.time())

    all_students = Student.query.all()
    attendance_records = Attendance.query.filter(
        Attendance.check_in_time >= day_start,
        Attendance.check_in_time <= day_end
    ).all()
    
    # Map student_id -> set of days present (to count unique days)
    student_attendance_days = {}
    # Map student_id -> latest scan time (for display)
    student_latest_scan = {}

    for a in attendance_records:
        sid = a.student_id
        day = a.check_in_time.date()
        
        if sid not in student_attendance_days:
            student_attendance_days[sid] = set()
        student_attendance_days[sid].add(day)
        
        if sid not in student_latest_scan or a.check_in_time > student_latest_scan[sid]:
            student_latest_scan[sid] = a.check_in_time
    
    report = []
    present_count = 0
    for student in all_students:
        days_present = len(student_attendance_days.get(student.id, []))
        is_present_today = 1 if days_present > 0 else 0
        if is_present_today: present_count += 1
        
        percentage = (days_present / total_days) * 100
        
        last_scan = student_latest_scan.get(student.id)
        last_scan_str = last_scan.strftime('%a, %d %b %Y - %I:%M:%S %p') if last_scan else '--:--:--'
        
        report.append({
            'roll': student.roll_number,
            'name': student.name,
            'course': student.course,
            'status': "PRESENT" if days_present > 0 else "ABSENT",
            'time': last_scan_str,
            'days_present': days_present,
            'percentage': round(percentage, 1)
        })
    
    return render_template('logs.html', 
                           report=report, 
                           selected_date=selected_date_str,
                           range_type=range_type,
                           total=len(all_students),
                           present=present_count,
                           absent=len(all_students) - present_count,
                           total_days=total_days)

# --- MANAGEMENT API ---
@app.route('/api/student/<int:sid>')
@login_required
def get_student(sid):
    student = Student.query.get_or_404(sid)
    return jsonify({
        'id': student.id,
        'name': student.name,
        'roll': student.roll_number,
        'course': student.course,
        'phone': student.phone,
        'dob': student.dob,
        'email': student.email,
        'role': student.role
    })

@app.route('/api/student/update/<int:sid>', methods=['POST'])
@login_required
def update_student(sid):
    data = request.json
    student = Student.query.get_or_404(sid)
    student.name = data.get('name')
    student.roll_number = data.get('roll')
    student.course = data.get('course')
    student.phone = data.get('phone')
    student.dob = data.get('dob')
    student.email = data.get('email')
    student.role = data.get('role')
    
    if data.get('role') == 'Faculty' and data.get('password'):
        student.password = generate_password_hash(data.get('password'))
        
    db.session.commit()
    return jsonify({'success': True, 'message': 'Record updated successfully'})

@app.route('/api/student/delete/<int:sid>', methods=['POST'])
@login_required
def delete_student(sid):
    try:
        student = Student.query.get_or_404(sid)
        # Remove face image
        path = f"static/faces/student_{student.id}.jpg"
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                print(f"File Warning: Could not delete image {path}: {e}")
        
        db.session.delete(student)
        db.session.commit()
        retrain_system()
        return jsonify({'success': True, 'message': 'Record deleted permanently'})
    except Exception as e:
        db.session.rollback()
        print(f"Delete Error: {e}")
        return jsonify({'success': False, 'message': f'Delete failed: {str(e)}'})

# --- RECOGNITION API ---
@app.route('/register', methods=['POST'])
@login_required
def register_student():
    data = request.json
    img_bytes = base64.b64decode(data.get('image').split(',')[1])
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    face_gray, error_msg = fh.extract_face(img)
    if face_gray is None:
        return jsonify({'success': False, 'message': error_msg})

    new_student = Student(name=data.get('name'), roll_number=data.get('roll'), 
                          course=data.get('course'), phone=data.get('phone'),
                          dob=data.get('dob'), role=data.get('role'), email=data.get('email'))
    
    # If Faculty, store hashed password
    if data.get('role') == 'Faculty' and data.get('password'):
        new_student.password = generate_password_hash(data.get('password'))
        
    db.session.add(new_student)
    db.session.commit()
    cv2.imwrite(f"static/faces/student_{new_student.id}.jpg", face_gray)
    retrain_system()
    return jsonify({'success': True, 'message': 'Person Enrolled Silently'})

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    data = request.json
    img_bytes = base64.b64decode(data.get('image').split(',')[1])
    nparr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    recognition_results = fh.recognize_face(frame)
    marked = []
    already_marked = []
    
    for sid, is_live, msg in recognition_results:
        if not is_live:
            return jsonify({'success': False, 'message': f'PROXY BLOCKED: {msg}'})
            
        # Check if student already marked in the last 8 hours
        eight_hours_ago = datetime.now() - timedelta(hours=8)
        existing = Attendance.query.filter(
            Attendance.student_id == sid, 
            Attendance.check_in_time > eight_hours_ago
        ).first()

        student = Student.query.get(sid)
        if not existing:
            log = Attendance(student_id=sid)
            db.session.add(log)
            marked.append(student.name)
        else:
            already_marked.append(student.name)
            
    db.session.commit()
    return jsonify({'success': True, 'marked': marked, 'already_marked': already_marked})

if __name__ == '__main__':
    with app.app_context():
        retrain_system()
    app.run(debug=True)
