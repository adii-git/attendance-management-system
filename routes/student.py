from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import db, User, Teacher, Student, Subject, Attendance, QRSession
from datetime import datetime

student_bp = Blueprint('student', __name__, url_prefix='/student')

def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            return render_template('access_denied.html'), 403
        return f(*args, **kwargs)
    return decorated

def get_student():
    return Student.query.filter_by(user_id=current_user.id).first()

@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    student = get_student()
    subjects = Subject.query.all()
    total_att = Attendance.query.filter_by(student_id=student.id).count()
    present_att = Attendance.query.filter_by(student_id=student.id, status='present').count()
    att_pct = round((present_att / total_att * 100) if total_att else 0, 1)

    subject_data = []
    for sub in subjects:
        total = Attendance.query.filter_by(student_id=student.id, subject_id=sub.id).count()
        present = Attendance.query.filter_by(student_id=student.id, subject_id=sub.id, status='present').count()
        pct = round((present / total * 100) if total else 0, 1)
        subject_data.append({'subject': sub, 'total': total, 'present': present, 'pct': pct})

    recent = Attendance.query.filter_by(student_id=student.id).order_by(Attendance.created_at.desc()).limit(10).all()
    recent_data = []
    for att in recent:
        subject = Subject.query.get(att.subject_id)
        recent_data.append({'subject': subject.subject_name, 'date': att.date, 'status': att.status})

    subject_labels = [d['subject'].subject_name for d in subject_data]
    subject_pct = [d['pct'] for d in subject_data]

    return render_template('student/dashboard.html', student=student,
        total_att=total_att, present_att=present_att, att_pct=att_pct,
        subject_data=subject_data, recent_data=recent_data,
        subject_labels=subject_labels, subject_pct=subject_pct)

@student_bp.route('/profile')
@login_required
@student_required
def profile():
    student = get_student()
    return render_template('student/profile.html', student=student)

@student_bp.route('/qr-scan')
@login_required
@student_required
def qr_scan():
    return render_template('student/qr_scan.html')

@student_bp.route('/qr/mark', methods=['POST'])
@login_required
@student_required
def mark_qr_attendance():
    data = request.get_json()
    qr_data = data.get('qr_data', '')
    student = get_student()

    if not qr_data.startswith('ATT:'):
        return jsonify({'success': False, 'message': 'Invalid QR code.'})

    session_id = qr_data.replace('ATT:', '')
    qr_session = QRSession.query.filter_by(session_id=session_id, is_active=True).first()

    if not qr_session:
        return jsonify({'success': False, 'message': 'QR session not found or inactive.'})

    if datetime.utcnow() > qr_session.expires_at:
        qr_session.is_active = False
        db.session.commit()
        return jsonify({'success': False, 'message': 'QR code has expired.'})

    today = datetime.utcnow().date()
    existing = Attendance.query.filter_by(student_id=student.id, subject_id=qr_session.subject_id, date=today).first()
    if existing:
        return jsonify({'success': False, 'message': 'Attendance already marked for today!'})

    att = Attendance(student_id=student.id, subject_id=qr_session.subject_id, date=today, status='present', marked_by='qr')
    db.session.add(att)
    db.session.commit()

    subject = Subject.query.get(qr_session.subject_id)
    return jsonify({'success': True, 'message': f'Attendance marked for {subject.subject_name}!'})

@student_bp.route('/attendance')
@login_required
@student_required
def attendance():
    student = get_student()
    subjects = Subject.query.all()
    subject_id = request.args.get('subject_id', '')
    records = Attendance.query.filter_by(student_id=student.id)
    if subject_id:
        records = records.filter_by(subject_id=int(subject_id))
    records = records.order_by(Attendance.date.desc()).all()
    att_data = []
    for att in records:
        subject = Subject.query.get(att.subject_id)
        att_data.append({'subject': subject.subject_name, 'date': att.date, 'status': att.status, 'marked_by': att.marked_by})
    return render_template('student/attendance.html', subjects=subjects, att_data=att_data, selected_subject=subject_id)
