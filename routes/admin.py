from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from functools import wraps
from models import db, User, Teacher, Student, Subject, Attendance, QRSession
from datetime import datetime, timedelta
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return render_template('access_denied.html'), 403
        return f(*args, **kwargs)
    return decorated

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_teachers = Teacher.query.count()
    total_students = Student.query.count()
    total_subjects = Subject.query.count()
    total_attendance = Attendance.query.count()
    present_count = Attendance.query.filter_by(status='present').count()
    absent_count = Attendance.query.filter_by(status='absent').count()
    att_pct = round((present_count / total_attendance * 100) if total_attendance else 0, 1)

    recent_teachers = db.session.query(User, Teacher).join(Teacher, User.id == Teacher.user_id).order_by(User.created_at.desc()).limit(5).all()

    # Chart data: last 7 days attendance
    labels, present_data, absent_data = [], [], []
    for i in range(6, -1, -1):
        day = (datetime.utcnow() - timedelta(days=i)).date()
        p = Attendance.query.filter_by(date=day, status='present').count()
        a = Attendance.query.filter_by(date=day, status='absent').count()
        labels.append(day.strftime('%b %d'))
        present_data.append(p)
        absent_data.append(a)

    return render_template('admin/dashboard.html',
        total_teachers=total_teachers, total_students=total_students,
        total_subjects=total_subjects, total_attendance=total_attendance,
        present_count=present_count, absent_count=absent_count,
        att_pct=att_pct, recent_teachers=recent_teachers,
        chart_labels=labels, chart_present=present_data, chart_absent=absent_data)

@admin_bp.route('/teachers')
@login_required
@admin_required
def teachers():
    teachers = db.session.query(User, Teacher).join(Teacher, User.id == Teacher.user_id).all()
    return render_template('admin/teachers.html', teachers=teachers)

@admin_bp.route('/teachers/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_teacher():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        department = request.form.get('department', '').strip()
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('admin.create_teacher'))
        user = User(name=name, email=email, password=generate_password_hash(password), role='teacher')
        db.session.add(user)
        db.session.flush()
        teacher = Teacher(user_id=user.id, department=department)
        db.session.add(teacher)
        db.session.commit()
        flash(f'Teacher {name} created successfully!', 'success')
        return redirect(url_for('admin.teachers'))
    return render_template('admin/create_teacher.html')

@admin_bp.route('/teachers/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_teacher(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Teacher deleted.', 'success')
    return redirect(url_for('admin.teachers'))

@admin_bp.route('/students')
@login_required
@admin_required
def students():
    students = db.session.query(User, Student).join(Student, User.id == Student.user_id).all()
    return render_template('admin/students.html', students=students)

@admin_bp.route('/subjects')
@login_required
@admin_required
def subjects():
    subjects = db.session.query(Subject, Teacher, User).join(Teacher, Subject.teacher_id == Teacher.id).join(User, Teacher.user_id == User.id).all()
    return render_template('admin/subjects.html', subjects=subjects)

@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    subjects = db.session.query(Subject, Teacher, User).join(Teacher, Subject.teacher_id == Teacher.id).join(User, Teacher.user_id == User.id).all()
    subject_labels, subject_pct = [], []
    for sub, _, _ in subjects:
        total = Attendance.query.filter_by(subject_id=sub.id).count()
        present = Attendance.query.filter_by(subject_id=sub.id, status='present').count()
        pct = round((present / total * 100) if total else 0, 1)
        subject_labels.append(sub.subject_name)
        subject_pct.append(pct)
    dept_data = db.session.query(Student.department, func.count(Student.id)).group_by(Student.department).all()
    dept_labels = [d[0] for d in dept_data]
    dept_counts = [d[1] for d in dept_data]
    return render_template('admin/analytics.html', subject_labels=subject_labels, subject_pct=subject_pct, dept_labels=dept_labels, dept_counts=dept_counts)
