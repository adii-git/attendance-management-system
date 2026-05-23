from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from functools import wraps
from models import db, User, Teacher, Student, Subject, Attendance, QRSession
from datetime import datetime, timedelta
import qrcode, uuid, os, io, csv
from io import StringIO, BytesIO

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')

def teacher_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'teacher':
            return render_template('access_denied.html'), 403
        return f(*args, **kwargs)
    return decorated

def get_teacher():
    return Teacher.query.filter_by(user_id=current_user.id).first()

@teacher_bp.route('/dashboard')
@login_required
@teacher_required
def dashboard():
    teacher = get_teacher()
    subjects = Subject.query.filter_by(teacher_id=teacher.id).all()
    total_students = Student.query.count()
    total_attendance = Attendance.query.join(Subject).filter(Subject.teacher_id == teacher.id).count()
    present_count = Attendance.query.join(Subject).filter(Subject.teacher_id == teacher.id, Attendance.status == 'present').count()
    att_pct = round((present_count / total_attendance * 100) if total_attendance else 0, 1)

    labels, present_data, absent_data = [], [], []
    for i in range(6, -1, -1):
        day = (datetime.utcnow() - timedelta(days=i)).date()
        p = Attendance.query.join(Subject).filter(Subject.teacher_id == teacher.id, Attendance.date == day, Attendance.status == 'present').count()
        a = Attendance.query.join(Subject).filter(Subject.teacher_id == teacher.id, Attendance.date == day, Attendance.status == 'absent').count()
        labels.append(day.strftime('%b %d'))
        present_data.append(p)
        absent_data.append(a)

    return render_template('teacher/dashboard.html', teacher=teacher,
        subjects=subjects, total_students=total_students,
        total_attendance=total_attendance, att_pct=att_pct,
        chart_labels=labels, chart_present=present_data, chart_absent=absent_data)

@teacher_bp.route('/students')
@login_required
@teacher_required
def students():
    students = db.session.query(User, Student).join(Student, User.id == Student.user_id).all()
    return render_template('teacher/students.html', students=students)

@teacher_bp.route('/students/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_student():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        roll_number = request.form.get('roll_number', '').strip()
        department = request.form.get('department', '').strip()
        semester = request.form.get('semester', 1)
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('teacher.create_student'))
        if Student.query.filter_by(roll_number=roll_number).first():
            flash('Roll number already exists.', 'danger')
            return redirect(url_for('teacher.create_student'))
        user = User(name=name, email=email, password=generate_password_hash(password), role='student')
        db.session.add(user)
        db.session.flush()
        student = Student(user_id=user.id, roll_number=roll_number, department=department, semester=int(semester))
        db.session.add(student)
        db.session.commit()
        flash(f'Student {name} created successfully!', 'success')
        return redirect(url_for('teacher.students'))
    return render_template('teacher/create_student.html')

@teacher_bp.route('/students/delete/<int:user_id>', methods=['POST'])
@login_required
@teacher_required
def delete_student(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Student deleted.', 'success')
    return redirect(url_for('teacher.students'))

@teacher_bp.route('/subjects')
@login_required
@teacher_required
def subjects():
    teacher = get_teacher()
    subjects = Subject.query.filter_by(teacher_id=teacher.id).all()
    return render_template('teacher/subjects.html', subjects=subjects)

@teacher_bp.route('/subjects/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_subject():
    teacher = get_teacher()
    if request.method == 'POST':
        subject_name = request.form.get('subject_name', '').strip()
        subject_code = request.form.get('subject_code', '').strip().upper()
        if Subject.query.filter_by(subject_code=subject_code).first():
            flash('Subject code already exists.', 'danger')
            return redirect(url_for('teacher.create_subject'))
        subject = Subject(subject_name=subject_name, subject_code=subject_code, teacher_id=teacher.id)
        db.session.add(subject)
        db.session.commit()
        flash(f'Subject {subject_name} created!', 'success')
        return redirect(url_for('teacher.subjects'))
    return render_template('teacher/create_subject.html')

@teacher_bp.route('/subjects/delete/<int:subject_id>', methods=['POST'])
@login_required
@teacher_required
def delete_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    db.session.delete(subject)
    db.session.commit()
    flash('Subject deleted.', 'success')
    return redirect(url_for('teacher.subjects'))

@teacher_bp.route('/attendance')
@login_required
@teacher_required
def attendance():
    teacher = get_teacher()
    subjects = Subject.query.filter_by(teacher_id=teacher.id).all()
    students = db.session.query(User, Student).join(Student, User.id == Student.user_id).all()
    today = datetime.utcnow().date()
    return render_template('teacher/attendance.html', subjects=subjects, students=students, today=today)

@teacher_bp.route('/attendance/mark', methods=['POST'])
@login_required
@teacher_required
def mark_attendance():
    subject_id = request.form.get('subject_id')
    date_str = request.form.get('date')
    student_ids = request.form.getlist('student_ids')
    statuses = request.form.getlist('statuses')
    date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.utcnow().date()

    for sid, status in zip(student_ids, statuses):
        existing = Attendance.query.filter_by(student_id=int(sid), subject_id=int(subject_id), date=date).first()
        if existing:
            existing.status = status
        else:
            att = Attendance(student_id=int(sid), subject_id=int(subject_id), date=date, status=status, marked_by='teacher')
            db.session.add(att)
    db.session.commit()
    flash('Attendance marked successfully!', 'success')
    return redirect(url_for('teacher.attendance'))

@teacher_bp.route('/qr')
@login_required
@teacher_required
def qr_page():
    teacher = get_teacher()
    subjects = Subject.query.filter_by(teacher_id=teacher.id).all()
    active_sessions = QRSession.query.filter_by(teacher_id=teacher.id, is_active=True).filter(QRSession.expires_at > datetime.utcnow()).all()
    return render_template('teacher/qr.html', subjects=subjects, active_sessions=active_sessions)

@teacher_bp.route('/qr/generate', methods=['POST'])
@login_required
@teacher_required
def generate_qr():
    teacher = get_teacher()
    subject_id = request.form.get('subject_id')
    duration = int(request.form.get('duration', 5))
    subject = Subject.query.get_or_404(subject_id)

    # Deactivate old sessions for this subject
    QRSession.query.filter_by(teacher_id=teacher.id, subject_id=subject.id, is_active=True).update({'is_active': False})
    db.session.commit()

    session_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(minutes=duration)
    qr_session = QRSession(session_id=session_id, subject_id=subject.id, teacher_id=teacher.id, expires_at=expires_at)
    db.session.add(qr_session)
    db.session.commit()

    # Generate QR image
    qr_data = f"ATT:{session_id}"
    img = qrcode.make(qr_data)
    qr_folder = current_app.config['QR_FOLDER']
    os.makedirs(qr_folder, exist_ok=True)
    img_path = os.path.join(qr_folder, f"{session_id}.png")
    img.save(img_path)

    flash(f'QR generated for {subject.subject_name}! Expires in {duration} minutes.', 'success')
    return redirect(url_for('teacher.qr_page'))

@teacher_bp.route('/qr/deactivate/<int:session_id>', methods=['POST'])
@login_required
@teacher_required
def deactivate_qr(session_id):
    session = QRSession.query.get_or_404(session_id)
    session.is_active = False
    db.session.commit()
    flash('QR session deactivated.', 'info')
    return redirect(url_for('teacher.qr_page'))

@teacher_bp.route('/reports')
@login_required
@teacher_required
def reports():
    teacher = get_teacher()
    subjects = Subject.query.filter_by(teacher_id=teacher.id).all()
    selected_subject = request.args.get('subject_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Attendance.query.join(Subject).filter(Subject.teacher_id == teacher.id)
    if selected_subject:
        query = query.filter(Attendance.subject_id == int(selected_subject))
    if date_from:
        query = query.filter(Attendance.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    if date_to:
        query = query.filter(Attendance.date <= datetime.strptime(date_to, '%Y-%m-%d').date())

    records = query.order_by(Attendance.date.desc()).all()
    attendance_data = []
    for att in records:
        student = Student.query.get(att.student_id)
        user = User.query.get(student.user_id)
        subject = Subject.query.get(att.subject_id)
        attendance_data.append({'name': user.name, 'roll': student.roll_number, 'subject': subject.subject_name, 'date': att.date, 'status': att.status, 'marked_by': att.marked_by})

    return render_template('teacher/reports.html', subjects=subjects, attendance_data=attendance_data, selected_subject=selected_subject, date_from=date_from, date_to=date_to)

@teacher_bp.route('/reports/export/csv')
@login_required
@teacher_required
def export_csv():
    teacher = get_teacher()
    subject_id = request.args.get('subject_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Attendance.query.join(Subject).filter(Subject.teacher_id == teacher.id)
    if subject_id:
        query = query.filter(Attendance.subject_id == int(subject_id))
    if date_from:
        query = query.filter(Attendance.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    if date_to:
        query = query.filter(Attendance.date <= datetime.strptime(date_to, '%Y-%m-%d').date())

    records = query.order_by(Attendance.date.desc()).all()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Student Name', 'Roll Number', 'Subject', 'Date', 'Status', 'Marked By'])
    for att in records:
        student = Student.query.get(att.student_id)
        user = User.query.get(student.user_id)
        subject = Subject.query.get(att.subject_id)
        writer.writerow([user.name, student.roll_number, subject.subject_name, att.date, att.status, att.marked_by])

    output = BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='attendance_report.csv')

@teacher_bp.route('/analytics')
@login_required
@teacher_required
def analytics():
    teacher = get_teacher()
    subjects = Subject.query.filter_by(teacher_id=teacher.id).all()
    subject_labels, subject_pct = [], []
    for sub in subjects:
        total = Attendance.query.filter_by(subject_id=sub.id).count()
        present = Attendance.query.filter_by(subject_id=sub.id, status='present').count()
        pct = round((present / total * 100) if total else 0, 1)
        subject_labels.append(sub.subject_name)
        subject_pct.append(pct)
    return render_template('teacher/analytics.html', subjects=subjects, subject_labels=subject_labels, subject_pct=subject_pct)

@teacher_bp.route('/profile')
@login_required
@teacher_required
def profile():
    teacher = get_teacher()
    return render_template('teacher/profile.html', teacher=teacher)
